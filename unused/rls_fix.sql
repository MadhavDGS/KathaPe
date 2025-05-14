-- Update RLS policies for users table
ALTER TABLE IF EXISTS users ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if any
DROP POLICY IF EXISTS "Public users read access" ON users;
DROP POLICY IF EXISTS "Public users write access" ON users;
DROP POLICY IF EXISTS "Public users access" ON users;

-- Create policies that allow complete public access
CREATE POLICY "Public users access" ON users FOR ALL USING (true);

-- Make sure service role can bypass
ALTER TABLE IF EXISTS users FORCE ROW LEVEL SECURITY;

-- Enable postgres auth functions
CREATE OR REPLACE FUNCTION public.get_auth(p_email TEXT) 
RETURNS TABLE(id uuid, email TEXT, password TEXT) 
SECURITY DEFINER 
AS $$
BEGIN
    RETURN QUERY
    SELECT users.id::uuid, users.phone_number::TEXT, users.password::TEXT
    FROM users
    WHERE users.phone_number = p_email;
END;
$$ LANGUAGE plpgsql; 