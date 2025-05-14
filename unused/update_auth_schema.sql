-- SQL script to update Supabase database schema for phone-based authentication
-- This script aligns the database with our Flask application's authentication approach

-- ====================================================================
-- PART 1: CLEANUP - Remove any previous authentication tables/data
-- ====================================================================

-- First, drop any existing triggers to avoid dependency issues
DROP TRIGGER IF EXISTS create_customer_trigger ON users;
DROP TRIGGER IF EXISTS create_business_trigger ON users;

-- Drop functions
DROP FUNCTION IF EXISTS create_customer_after_user();
DROP FUNCTION IF EXISTS create_business_after_user();
DROP FUNCTION IF EXISTS authenticate_by_phone(TEXT, TEXT);

-- Drop views that depend on these tables
DROP VIEW IF EXISTS customer_balance_view;

-- Drop foreign key constraints to avoid dependency issues when dropping tables
-- You may need to adjust these based on your actual constraint names
ALTER TABLE IF EXISTS customer_credits DROP CONSTRAINT IF EXISTS customer_credits_customer_id_fkey;
ALTER TABLE IF EXISTS customer_credits DROP CONSTRAINT IF EXISTS customer_credits_business_id_fkey;
ALTER TABLE IF EXISTS transactions DROP CONSTRAINT IF EXISTS transactions_customer_id_fkey;
ALTER TABLE IF EXISTS transactions DROP CONSTRAINT IF EXISTS transactions_business_id_fkey;
ALTER TABLE IF EXISTS customers DROP CONSTRAINT IF EXISTS customers_user_id_fkey;
ALTER TABLE IF EXISTS businesses DROP CONSTRAINT IF EXISTS businesses_user_id_fkey;

-- Optional: Drop and recreate auth-related tables 
-- Uncomment these if you want to completely reset the authentication tables
-- WARNING: This will delete all user data!
-- DROP TABLE IF EXISTS transactions;
-- DROP TABLE IF EXISTS customer_credits;
-- DROP TABLE IF EXISTS customers;
-- DROP TABLE IF EXISTS businesses;
-- DROP TABLE IF EXISTS users;

-- ====================================================================
-- PART 2: SCHEMA UPDATES - Modify tables for phone-based auth
-- ====================================================================

-- 1. Ensure phone_number column exists and is not null in users table
ALTER TABLE users
ADD COLUMN IF NOT EXISTS phone_number TEXT;

-- 2. Add unique constraint to phone_number
ALTER TABLE users
DROP CONSTRAINT IF EXISTS users_phone_number_key;

ALTER TABLE users
ADD CONSTRAINT users_phone_number_key UNIQUE (phone_number);

-- 3. Ensure password_hash column exists
ALTER TABLE users
ADD COLUMN IF NOT EXISTS password_hash TEXT;

-- 4. Create index on phone_number for faster lookups
DROP INDEX IF EXISTS idx_users_phone_number;
CREATE INDEX idx_users_phone_number ON users(phone_number);

-- 5. Make user_type column not null with a default
ALTER TABLE users
ALTER COLUMN user_type SET DEFAULT 'customer';

ALTER TABLE users
ALTER COLUMN user_type SET NOT NULL;

-- 6. Ensure customers table has phone_number that matches users
ALTER TABLE customers
ADD COLUMN IF NOT EXISTS phone_number TEXT;

-- ====================================================================
-- PART 3: AUTOMATION - Create triggers and functions
-- ====================================================================

-- 7. Create trigger to automatically create customer record when user is created
CREATE OR REPLACE FUNCTION create_customer_after_user()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.user_type = 'customer' AND NOT EXISTS (SELECT 1 FROM customers WHERE user_id = NEW.id) THEN
        INSERT INTO customers (id, user_id, name, phone_number, created_at)
        VALUES (uuid_generate_v4(), NEW.id, NEW.name, NEW.phone_number, CURRENT_TIMESTAMP);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS create_customer_trigger ON users;
CREATE TRIGGER create_customer_trigger
AFTER INSERT ON users
FOR EACH ROW
EXECUTE FUNCTION create_customer_after_user();

-- 8. Create a similar trigger for business users
CREATE OR REPLACE FUNCTION create_business_after_user()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.user_type = 'business' AND NOT EXISTS (SELECT 1 FROM businesses WHERE user_id = NEW.id) THEN
        INSERT INTO businesses (
            id, 
            user_id, 
            name, 
            description,
            access_pin,
            created_at
        )
        VALUES (
            uuid_generate_v4(), 
            NEW.id, 
            COALESCE(NEW.name, 'Business') || ' Business', 
            'Auto-created business account',
            SUBSTRING(CAST(EXTRACT(EPOCH FROM CURRENT_TIMESTAMP) AS TEXT), LENGTH(CAST(EXTRACT(EPOCH FROM CURRENT_TIMESTAMP) AS TEXT))-3, 4),
            CURRENT_TIMESTAMP
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS create_business_trigger ON users;
CREATE TRIGGER create_business_trigger
AFTER INSERT ON users
FOR EACH ROW
EXECUTE FUNCTION create_business_after_user();

-- 9. Add function to safely authenticate by phone and password
CREATE OR REPLACE FUNCTION authenticate_by_phone(phone TEXT, password TEXT)
RETURNS TABLE(
    id UUID,
    name TEXT,
    phone_number TEXT,
    user_type TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT u.id, u.name, u.phone_number, u.user_type
    FROM users u
    WHERE u.phone_number = phone
    AND (
        u.password_hash = password -- Direct comparison for plaintext
        -- Add bcrypt check here if using hashed passwords
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 10. Create view for customer balance
CREATE OR REPLACE VIEW customer_balance_view AS
SELECT 
    cc.customer_id,
    cc.business_id,
    c.name as customer_name,
    b.name as business_name,
    COALESCE(
        (SELECT SUM(amount) FROM transactions WHERE customer_id = cc.customer_id AND business_id = cc.business_id AND transaction_type = 'credit'),
        0
    ) - 
    COALESCE(
        (SELECT SUM(amount) FROM transactions WHERE customer_id = cc.customer_id AND business_id = cc.business_id AND transaction_type = 'payment'),
        0
    ) as current_balance
FROM customer_credits cc
JOIN customers c ON cc.customer_id = c.id
JOIN businesses b ON cc.business_id = b.id; 