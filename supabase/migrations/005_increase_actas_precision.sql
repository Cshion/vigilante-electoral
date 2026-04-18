-- Migration: 005_increase_actas_precision
-- Date: 2026-04-18
-- Description: Increase actas_percentage decimal precision to capture ALL changes from ONPE
-- Reason: ONPE sends exact percentages, we were losing precision due to DECIMAL(6,3) limiting to 3 decimals

-- =============================================================================
-- INCREASE PRECISION: position_snapshots.actas_percentage
-- From DECIMAL(6,3) to DECIMAL(10,6) - 6 decimal places
-- =============================================================================
ALTER TABLE position_snapshots
ALTER COLUMN actas_percentage TYPE DECIMAL(10,6);

-- =============================================================================
-- INCREASE PRECISION: change_notifications.actas_percentage
-- From DECIMAL(5,2) to DECIMAL(10,6) - 6 decimal places
-- =============================================================================
ALTER TABLE change_notifications
ALTER COLUMN actas_percentage TYPE DECIMAL(10,6);

-- Update comments
COMMENT ON COLUMN position_snapshots.actas_percentage IS 'Porcentaje de actas contabilizadas al momento del snapshot (6 decimales para capturar TODOS los cambios de ONPE)';
COMMENT ON COLUMN change_notifications.actas_percentage IS 'Porcentaje de actas procesadas (6 decimales para capturar TODOS los cambios de ONPE)';
