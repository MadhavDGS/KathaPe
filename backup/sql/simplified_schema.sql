-- COMPLETELY SIMPLIFIED DATABASE SCHEMA FOR KATHA
-- WARNING: This will delete ALL existing data!

-- ====================================================================
-- PART 1: DROP EVERYTHING
-- ====================================================================

-- First drop all schemas
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO public;

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ====================================================================
-- PART 2: CREATE MINIMAL SET OF TABLES
-- ====================================================================

-- Users table - simplified with phone-based auth
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    phone_number TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    user_type TEXT NOT NULL DEFAULT 'customer',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create index for phone number lookups
CREATE INDEX idx_users_phone_number ON users(phone_number);

-- Businesses table - minimal required fields
CREATE TABLE businesses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id),
    name TEXT NOT NULL,
    description TEXT,
    access_pin TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Customers table - minimal required fields
CREATE TABLE customers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id),
    name TEXT NOT NULL,
    phone_number TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Customer credits table - minimal required fields
CREATE TABLE customer_credits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    business_id UUID NOT NULL REFERENCES businesses(id),
    customer_id UUID NOT NULL REFERENCES customers(id),
    current_balance DECIMAL(10, 2) DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(business_id, customer_id)
);

-- Transactions table - minimal required fields
CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    business_id UUID NOT NULL REFERENCES businesses(id),
    customer_id UUID NOT NULL REFERENCES customers(id),
    amount DECIMAL(10, 2) NOT NULL,
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('credit', 'payment')),
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ====================================================================
-- PART 3: ENABLE ROW LEVEL SECURITY (RLS)
-- ====================================================================

-- Allow public access to users table for login/registration
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public users access" ON users FOR ALL USING (true);

-- Allow public access to businesses table
ALTER TABLE businesses ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public businesses access" ON businesses FOR ALL USING (true);

-- Allow public access to customers table
ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public customers access" ON customers FOR ALL USING (true);

-- Allow public access to customer_credits table
ALTER TABLE customer_credits ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public customer_credits access" ON customer_credits FOR ALL USING (true);

-- Allow public access to transactions table
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public transactions access" ON transactions FOR ALL USING (true);

-- ====================================================================
-- PART 4: CREATE SIMPLE TRIGGERS
-- ====================================================================

-- Trigger to automatically create customer record when user is created
CREATE OR REPLACE FUNCTION create_customer_after_user()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.user_type = 'customer' THEN
        INSERT INTO customers (id, user_id, name, phone_number)
        VALUES (uuid_generate_v4(), NEW.id, NEW.name, NEW.phone_number);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER create_customer_trigger
AFTER INSERT ON users
FOR EACH ROW
EXECUTE FUNCTION create_customer_after_user();

-- Trigger to automatically create business record when user is created
CREATE OR REPLACE FUNCTION create_business_after_user()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.user_type = 'business' THEN
        INSERT INTO businesses (
            id, 
            user_id, 
            name, 
            description,
            access_pin
        )
        VALUES (
            uuid_generate_v4(), 
            NEW.id, 
            NEW.name || ' Business', 
            'Business account',
            SUBSTRING(CAST(EXTRACT(EPOCH FROM CURRENT_TIMESTAMP) AS TEXT), LENGTH(CAST(EXTRACT(EPOCH FROM CURRENT_TIMESTAMP) AS TEXT))-3, 4)
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER create_business_trigger
AFTER INSERT ON users
FOR EACH ROW
EXECUTE FUNCTION create_business_after_user();

-- ====================================================================
-- PART 5: CREATE SAMPLE DATA FOR TESTING
-- ====================================================================

-- Sample business user
INSERT INTO users (id, name, phone_number, password, user_type)
VALUES (
    uuid_generate_v4(),
    'Sample Business',
    '1234567890',
    'password123',
    'business'
);

-- Sample customer user
INSERT INTO users (id, name, phone_number, password, user_type)
VALUES (
    uuid_generate_v4(),
    'Sample Customer',
    '0987654321',
    'password123',
    'customer'
); 