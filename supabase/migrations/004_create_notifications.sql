-- Migration: 004_create_notifications
-- Date: 2026-04-18
-- Description: Create change_notifications table for tracking vote changes by region.
-- Note: Notifications are shared between all users (no per-user read tracking).

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

-- Comentario
COMMENT ON TABLE change_notifications IS 'Notificaciones de cambios por región (excluye TOTAL). Compartidas entre todos los usuarios.';
