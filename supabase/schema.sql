-- Vigilante Electoral - Supabase Database Schema
-- Optimizado para tracking del 2do y 3er puesto cada 15 min
-- Run this SQL in your Supabase SQL Editor

-- =============================================================================
-- CONFIGURACIÓN DE ZONA HORARIA (Perú: America/Lima, UTC-5)
-- =============================================================================
SET timezone = 'America/Lima';

-- =============================================================================
-- TABLA PRINCIPAL: Snapshots de posiciones 2 y 3
-- =============================================================================
CREATE TABLE IF NOT EXISTS position_snapshots (
  id BIGSERIAL PRIMARY KEY,
  
  -- Región (departamento o NACIONAL/EXTRANJERO)
  region_code VARCHAR(20) NOT NULL DEFAULT 'NACIONAL',
  
  -- Timestamp del snapshot (en hora peruana)
  timestamp TIMESTAMPTZ NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Lima'),
  
  -- Datos del 2do puesto
  pos2_candidate_id VARCHAR(20) NOT NULL,
  pos2_candidate_name VARCHAR(255) NOT NULL,
  pos2_party_name VARCHAR(255) NOT NULL,
  pos2_party_id VARCHAR(20),
  pos2_votes BIGINT NOT NULL,
  pos2_percentage DECIMAL(6,3) NOT NULL,
  pos2_percentage_emitted DECIMAL(6,3),
  
  -- Datos del 3er puesto
  pos3_candidate_id VARCHAR(20) NOT NULL,
  pos3_candidate_name VARCHAR(255) NOT NULL,
  pos3_party_name VARCHAR(255) NOT NULL,
  pos3_party_id VARCHAR(20),
  pos3_votes BIGINT NOT NULL,
  pos3_percentage DECIMAL(6,3) NOT NULL,
  pos3_percentage_emitted DECIMAL(6,3),
  
  -- Diferencia entre 2do y 3er puesto
  vote_gap BIGINT GENERATED ALWAYS AS (pos2_votes - pos3_votes) STORED,
  percentage_gap DECIMAL(6,3) GENERATED ALWAYS AS (pos2_percentage - pos3_percentage) STORED,
  
  -- Totales para contexto
  total_valid_votes BIGINT,
  total_emitted_votes BIGINT,
  blank_votes BIGINT,
  null_votes BIGINT,
  
  -- Referencia al 1er puesto (para contexto)
  pos1_candidate_name VARCHAR(255),
  pos1_votes BIGINT,
  pos1_percentage DECIMAL(6,3),
  
  -- Metadatos
  created_at TIMESTAMPTZ DEFAULT (NOW() AT TIME ZONE 'America/Lima')
);

-- =============================================================================
-- TABLA: Cambios detectados entre snapshots
-- =============================================================================
CREATE TABLE IF NOT EXISTS position_changes (
  id BIGSERIAL PRIMARY KEY,
  
  snapshot_id BIGINT REFERENCES position_snapshots(id),
  timestamp TIMESTAMPTZ NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Lima'),
  
  -- Cambios en 2do puesto
  pos2_vote_change BIGINT DEFAULT 0,
  pos2_percentage_change DECIMAL(6,3) DEFAULT 0,
  
  -- Cambios en 3er puesto
  pos3_vote_change BIGINT DEFAULT 0,
  pos3_percentage_change DECIMAL(6,3) DEFAULT 0,
  
  -- Cambio en la brecha
  gap_change BIGINT DEFAULT 0,
  
  -- ¿Hubo cambio de posición?
  position_swap BOOLEAN DEFAULT FALSE,
  
  -- Tiempo desde último snapshot (en minutos)
  minutes_since_last INT,
  
  created_at TIMESTAMPTZ DEFAULT (NOW() AT TIME ZONE 'America/Lima')
);

-- =============================================================================
-- TABLA: Candidatos (normalizada para referencia)
-- =============================================================================
CREATE TABLE IF NOT EXISTS candidates (
  id VARCHAR(20) PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  party_name VARCHAR(255),
  party_id VARCHAR(20),
  candidate_image_url TEXT,
  party_image_url TEXT,
  first_seen_at TIMESTAMPTZ DEFAULT (NOW() AT TIME ZONE 'America/Lima'),
  updated_at TIMESTAMPTZ DEFAULT (NOW() AT TIME ZONE 'America/Lima')
);

-- =============================================================================
-- INDEXES
-- =============================================================================
CREATE INDEX IF NOT EXISTS idx_position_snapshots_timestamp 
ON position_snapshots(timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_position_snapshots_region_timestamp 
ON position_snapshots(region_code, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_position_snapshots_pos2 
ON position_snapshots(pos2_candidate_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_position_snapshots_pos3 
ON position_snapshots(pos3_candidate_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_position_changes_snapshot 
ON position_changes(snapshot_id);

CREATE INDEX IF NOT EXISTS idx_position_changes_timestamp 
ON position_changes(timestamp DESC);

-- =============================================================================
-- ROW LEVEL SECURITY
-- =============================================================================
ALTER TABLE position_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE position_changes ENABLE ROW LEVEL SECURITY;
ALTER TABLE candidates ENABLE ROW LEVEL SECURITY;

-- Políticas de lectura pública
CREATE POLICY "Allow public read snapshots" ON position_snapshots
  FOR SELECT USING (true);

CREATE POLICY "Allow public read changes" ON position_changes
  FOR SELECT USING (true);

CREATE POLICY "Allow public read candidates" ON candidates
  FOR SELECT USING (true);

-- Políticas de escritura (service role)
CREATE POLICY "Allow service insert snapshots" ON position_snapshots
  FOR INSERT WITH CHECK (true);

CREATE POLICY "Allow service insert changes" ON position_changes
  FOR INSERT WITH CHECK (true);

CREATE POLICY "Allow service upsert candidates" ON candidates
  FOR ALL USING (true);

-- =============================================================================
-- FUNCIONES
-- =============================================================================

-- Función para obtener el último snapshot
CREATE OR REPLACE FUNCTION get_latest_snapshot()
RETURNS TABLE (
  snapshot_id BIGINT,
  snapshot_timestamp TIMESTAMPTZ,
  pos2_name VARCHAR,
  pos2_votes BIGINT,
  pos2_percentage DECIMAL,
  pos3_name VARCHAR,
  pos3_votes BIGINT,
  pos3_percentage DECIMAL,
  vote_gap BIGINT,
  percentage_gap DECIMAL
) AS $$
BEGIN
  RETURN QUERY
  SELECT 
    ps.id,
    ps.timestamp,
    ps.pos2_candidate_name,
    ps.pos2_votes,
    ps.pos2_percentage,
    ps.pos3_candidate_name,
    ps.pos3_votes,
    ps.pos3_percentage,
    ps.vote_gap,
    ps.percentage_gap
  FROM position_snapshots ps
  ORDER BY ps.timestamp DESC
  LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- Función para obtener historial de las últimas N horas
CREATE OR REPLACE FUNCTION get_snapshot_history(hours_back INT DEFAULT 24)
RETURNS TABLE (
  snapshot_timestamp TIMESTAMPTZ,
  pos2_name VARCHAR,
  pos2_votes BIGINT,
  pos2_percentage DECIMAL,
  pos3_name VARCHAR,
  pos3_votes BIGINT,
  pos3_percentage DECIMAL,
  vote_gap BIGINT
) AS $$
BEGIN
  RETURN QUERY
  SELECT 
    ps.timestamp,
    ps.pos2_candidate_name,
    ps.pos2_votes,
    ps.pos2_percentage,
    ps.pos3_candidate_name,
    ps.pos3_votes,
    ps.pos3_percentage,
    ps.vote_gap
  FROM position_snapshots ps
  WHERE ps.timestamp > (NOW() AT TIME ZONE 'America/Lima') - (hours_back || ' hours')::INTERVAL
  ORDER BY ps.timestamp DESC;
END;
$$ LANGUAGE plpgsql;

-- Función para detectar si hubo cambio de posición (swap)
CREATE OR REPLACE FUNCTION check_position_swap()
RETURNS TRIGGER AS $$
DECLARE
  prev_snapshot RECORD;
BEGIN
  -- Obtener snapshot anterior
  SELECT * INTO prev_snapshot
  FROM position_snapshots
  WHERE timestamp < NEW.timestamp
  ORDER BY timestamp DESC
  LIMIT 1;
  
  -- Si existe snapshot previo, verificar si hubo swap
  IF FOUND THEN
    -- Insertar registro de cambio
    INSERT INTO position_changes (
      snapshot_id,
      timestamp,
      pos2_vote_change,
      pos2_percentage_change,
      pos3_vote_change,
      pos3_percentage_change,
      gap_change,
      position_swap,
      minutes_since_last
    ) VALUES (
      NEW.id,
      NEW.timestamp,
      NEW.pos2_votes - prev_snapshot.pos2_votes,
      NEW.pos2_percentage - prev_snapshot.pos2_percentage,
      NEW.pos3_votes - prev_snapshot.pos3_votes,
      NEW.pos3_percentage - prev_snapshot.pos3_percentage,
      NEW.vote_gap - prev_snapshot.vote_gap,
      -- Detectar swap: el 3ro anterior es ahora el 2do
      (NEW.pos2_candidate_id = prev_snapshot.pos3_candidate_id),
      EXTRACT(EPOCH FROM (NEW.timestamp - prev_snapshot.timestamp)) / 60
    );
  END IF;
  
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger para auto-calcular cambios
CREATE TRIGGER trigger_check_position_swap
AFTER INSERT ON position_snapshots
FOR EACH ROW
EXECUTE FUNCTION check_position_swap();

-- Función de limpieza (mantener últimos N días)
CREATE OR REPLACE FUNCTION cleanup_old_data(days_to_keep INT DEFAULT 30)
RETURNS TABLE (snapshots_deleted INT, changes_deleted INT) AS $$
DECLARE
  snap_count INT;
  change_count INT;
BEGIN
  -- Eliminar cambios antiguos
  DELETE FROM position_changes 
  WHERE timestamp < (NOW() AT TIME ZONE 'America/Lima') - (days_to_keep || ' days')::INTERVAL;
  GET DIAGNOSTICS change_count = ROW_COUNT;
  
  -- Eliminar snapshots antiguos
  DELETE FROM position_snapshots 
  WHERE timestamp < (NOW() AT TIME ZONE 'America/Lima') - (days_to_keep || ' days')::INTERVAL;
  GET DIAGNOSTICS snap_count = ROW_COUNT;
  
  RETURN QUERY SELECT snap_count, change_count;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- VISTA: Resumen actual con cambios
-- =============================================================================
CREATE OR REPLACE VIEW current_race_status AS
SELECT 
  ps.timestamp,
  ps.pos2_candidate_name AS segundo_lugar,
  ps.pos2_party_name AS partido_2do,
  ps.pos2_votes AS votos_2do,
  ps.pos2_percentage AS porcentaje_2do,
  ps.pos3_candidate_name AS tercer_lugar,
  ps.pos3_party_name AS partido_3ro,
  ps.pos3_votes AS votos_3ro,
  ps.pos3_percentage AS porcentaje_3ro,
  ps.vote_gap AS diferencia_votos,
  ps.percentage_gap AS diferencia_porcentaje,
  pc.pos2_vote_change AS cambio_votos_2do,
  pc.pos3_vote_change AS cambio_votos_3ro,
  pc.gap_change AS cambio_brecha,
  pc.position_swap AS hubo_cambio_posicion,
  pc.minutes_since_last AS minutos_desde_anterior
FROM position_snapshots ps
LEFT JOIN position_changes pc ON pc.snapshot_id = ps.id
ORDER BY ps.timestamp DESC
LIMIT 1;

-- =============================================================================
-- TABLA: Notificaciones de cambios por región
-- Excluye TOTAL (siempre visible en portada), solo departamentos y extranjero
-- =============================================================================
CREATE TABLE IF NOT EXISTS change_notifications (
  id BIGSERIAL PRIMARY KEY,
  
  -- Región donde ocurrió el cambio
  region_code VARCHAR(20) NOT NULL,
  region_name VARCHAR(100) NOT NULL,
  
  -- Timestamp del cambio
  timestamp TIMESTAMPTZ NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Lima'),
  
  -- Tipo de notificación
  notification_type VARCHAR(50) NOT NULL DEFAULT 'vote_change',
  -- Valores posibles: 'vote_change', 'leader_change', 'significant_gap', 'milestone'
  
  -- Quién lidera en esta región (POS2 = JUNTOS, POS3 = RENOVACIÓN)
  leader VARCHAR(20) NOT NULL,
  
  -- Datos del cambio
  juntos_votes BIGINT NOT NULL,
  juntos_change INT NOT NULL DEFAULT 0,
  renovacion_votes BIGINT NOT NULL,
  renovacion_change INT NOT NULL DEFAULT 0,
  
  -- Brecha actual y cambio
  gap INT NOT NULL,
  gap_change INT NOT NULL DEFAULT 0,
  
  -- Actas procesadas
  actas_percentage DECIMAL(5,2) DEFAULT 0,
  
  -- Mensaje para mostrar (pre-calculado)
  message TEXT NOT NULL,
  
  created_at TIMESTAMPTZ DEFAULT (NOW() AT TIME ZONE 'America/Lima')
);

-- Indexes para notificaciones
CREATE INDEX IF NOT EXISTS idx_notifications_timestamp 
ON change_notifications(timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_notifications_region 
ON change_notifications(region_code, timestamp DESC);

-- RLS para notificaciones
ALTER TABLE change_notifications ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow public read notifications" ON change_notifications
  FOR SELECT USING (true);

CREATE POLICY "Allow service insert notifications" ON change_notifications
  FOR INSERT WITH CHECK (true);

CREATE POLICY "Allow service update notifications" ON change_notifications
  FOR UPDATE USING (true);

-- =============================================================================
-- COMENTARIOS
-- =============================================================================
COMMENT ON TABLE position_snapshots IS 'Snapshots cada 15 min del 2do y 3er lugar';
COMMENT ON TABLE position_changes IS 'Cambios detectados entre snapshots consecutivos';
COMMENT ON COLUMN position_snapshots.vote_gap IS 'Diferencia de votos entre 2do y 3er lugar (calculado)';
COMMENT ON COLUMN position_changes.position_swap IS 'TRUE si el 3ro anterior pasó a ser 2do';
COMMENT ON TABLE change_notifications IS 'Notificaciones de cambios por región (excluye TOTAL)';
-- Vigilante Electoral - Supabase Database Schema
-- Run this SQL in your Supabase SQL Editor

-- Main table for storing election snapshots
CREATE TABLE IF NOT EXISTS election_snapshots (
  id BIGSERIAL PRIMARY KEY,
  election_type VARCHAR(50) NOT NULL DEFAULT 'PRESI',
  data JSONB NOT NULL,
  actas_percentage FLOAT,
  total_valid_votes BIGINT,
  total_emitted_votes BIGINT,
  timestamp TIMESTAMPTZ DEFAULT (NOW() AT TIME ZONE 'America/Lima'),
  created_at TIMESTAMPTZ DEFAULT (NOW() AT TIME ZONE 'America/Lima')
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_snapshots_type_time 
ON election_snapshots(election_type, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_snapshots_timestamp 
ON election_snapshots(timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_snapshots_actas 
ON election_snapshots(actas_percentage);

-- Enable Row Level Security
ALTER TABLE election_snapshots ENABLE ROW LEVEL SECURITY;

-- Policy: Allow public read access
CREATE POLICY "Allow public read" ON election_snapshots
  FOR SELECT USING (true);

-- Policy: Allow authenticated insert (for the scraper)
CREATE POLICY "Allow service role insert" ON election_snapshots
  FOR INSERT WITH CHECK (true);

-- Optional: Table for normalized candidate data (if needed later)
-- CREATE TABLE IF NOT EXISTS candidates (
--   id VARCHAR(20) PRIMARY KEY,
--   name VARCHAR(255) NOT NULL,
--   party_name VARCHAR(255),
--   party_id VARCHAR(20),
--   candidate_image_url TEXT,
--   party_image_url TEXT,
--   created_at TIMESTAMPTZ DEFAULT NOW(),
--   updated_at TIMESTAMPTZ DEFAULT NOW()
-- );

-- Function to clean old snapshots (optional - run periodically)
CREATE OR REPLACE FUNCTION cleanup_old_snapshots(days_to_keep INT DEFAULT 30)
RETURNS INT AS $$
DECLARE
  deleted_count INT;
BEGIN
  DELETE FROM election_snapshots 
  WHERE timestamp < (NOW() AT TIME ZONE 'America/Lima') - (days_to_keep || ' days')::INTERVAL;
  GET DIAGNOSTICS deleted_count = ROW_COUNT;
  RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Example: To clean snapshots older than 30 days
-- SELECT cleanup_old_snapshots(30);
