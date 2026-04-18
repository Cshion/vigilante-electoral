-- Migración: Agregar columna actas_percentage a position_snapshots
-- Para trackear el % de avance de actas junto con cada snapshot de votos

-- Agregar columna de % de actas a position_snapshots
ALTER TABLE position_snapshots
ADD COLUMN IF NOT EXISTS actas_percentage DECIMAL(6,3) DEFAULT 0;

-- Agregar columnas adicionales de actas para más contexto
ALTER TABLE position_snapshots
ADD COLUMN IF NOT EXISTS actas_counted INTEGER DEFAULT 0;

ALTER TABLE position_snapshots
ADD COLUMN IF NOT EXISTS actas_total INTEGER DEFAULT 0;

-- Comentarios
COMMENT ON COLUMN position_snapshots.actas_percentage IS 'Porcentaje de actas contabilizadas al momento del snapshot';
COMMENT ON COLUMN position_snapshots.actas_counted IS 'Número de actas contabilizadas';
COMMENT ON COLUMN position_snapshots.actas_total IS 'Total de actas esperadas';
