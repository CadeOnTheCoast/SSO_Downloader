-- Create the SSO reports table
CREATE TABLE IF NOT EXISTS sso_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sso_id TEXT UNIQUE,
    utility_id TEXT,
    utility_name TEXT,
    sewer_system TEXT,
    county TEXT,
    location_desc TEXT,
    date_sso_began TIMESTAMPTZ,
    date_sso_stopped TIMESTAMPTZ,
    volume_gallons NUMERIC,
    est_volume TEXT,
    est_volume_gal INTEGER,
    est_volume_is_range BOOLEAN,
    est_volume_range_label TEXT,
    cause TEXT,
    receiving_water TEXT,
    x DOUBLE PRECISION,
    y DOUBLE PRECISION,
    raw JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for common searches
CREATE INDEX IF NOT EXISTS idx_sso_reports_utility_name ON sso_reports(utility_name);
CREATE INDEX IF NOT EXISTS idx_sso_reports_county ON sso_reports(county);
CREATE INDEX IF NOT EXISTS idx_sso_reports_date_began ON sso_reports(date_sso_began);

-- Set up Row Level Security (RLS)
ALTER TABLE sso_reports ENABLE ROW LEVEL SECURITY;

-- Policy: Allow all authenticated users to view reports
CREATE POLICY "Allow authenticated users to read" 
ON sso_reports FOR SELECT 
TO authenticated 
USING (true);

-- Policy: Only allow service_role or specific authorized users to insert/update (optional, defaults to restricted)
-- For now, we will rely on service_role for migrations.
