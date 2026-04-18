-- Migration: Add region_code to position_snapshots
-- Run this on existing databases to support regional history filtering

-- Add region_code column with default NACIONAL for backward compatibility
ALTER TABLE position_snapshots 
ADD COLUMN IF NOT EXISTS region_code VARCHAR(20) NOT NULL DEFAULT 'NACIONAL';

-- Create index for efficient region-based queries
CREATE INDEX IF NOT EXISTS idx_position_snapshots_region_timestamp 
ON position_snapshots(region_code, timestamp DESC);

-- Verify the migration
SELECT 
    column_name, 
    data_type, 
    column_default
FROM information_schema.columns 
WHERE table_name = 'position_snapshots' 
AND column_name = 'region_code';
