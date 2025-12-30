-- Add policy to allow anonymous/public read access to sso_reports
-- This is needed when authentication is disabled for debugging

CREATE POLICY "Allow anonymous users to read" 
ON sso_reports FOR SELECT 
TO anon 
USING (true);
