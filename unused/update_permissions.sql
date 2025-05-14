-- Drop and recreate RLS policies for all tables
-- Users table
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Public users access" ON users;
CREATE POLICY "Public users access" ON users FOR ALL USING (true);

-- Businesses table
ALTER TABLE businesses ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Public businesses access" ON businesses;
CREATE POLICY "Public businesses access" ON businesses FOR ALL USING (true);

-- Customers table
ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Public customers access" ON customers;
CREATE POLICY "Public customers access" ON customers FOR ALL USING (true);

-- Customer_credits table
ALTER TABLE customer_credits ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Public customer_credits access" ON customer_credits;
CREATE POLICY "Public customer_credits access" ON customer_credits FOR ALL USING (true);

-- Transactions table
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Public transactions access" ON transactions;
CREATE POLICY "Public transactions access" ON transactions FOR ALL USING (true);

-- Check that tables exist
SELECT EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'users') AS users_exists;
SELECT EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'businesses') AS businesses_exists;
SELECT EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'customers') AS customers_exists;
SELECT EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'customer_credits') AS customer_credits_exists;
SELECT EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'transactions') AS transactions_exists; 