-- SQL script to completely reset the database and rebuild for phone-based authentication
-- WARNING: This will delete ALL existing data!

-- ====================================================================
-- PART 1: DROP ALL EXISTING TABLES
-- ====================================================================

-- First drop all triggers
DROP TRIGGER IF EXISTS create_customer_trigger ON users;
DROP TRIGGER IF EXISTS create_business_trigger ON users;

-- Drop all functions
DROP FUNCTION IF EXISTS create_customer_after_user();
DROP FUNCTION IF EXISTS create_business_after_user();
DROP FUNCTION IF EXISTS authenticate_by_phone(TEXT, TEXT);

-- Drop all views
DROP VIEW IF EXISTS customer_balance_view;

-- Drop dependent tables first (media_attachments depends on transactions)
DROP TABLE IF EXISTS media_attachments;

-- Drop remaining tables (in correct order to respect foreign keys)
DROP TABLE IF EXISTS transactions;
DROP TABLE IF EXISTS customer_credits;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS businesses;
DROP TABLE IF EXISTS users;

-- ====================================================================
-- PART 2: CREATE FRESH TABLES
-- ====================================================================

-- Make sure the uuid-ossp extension is enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    phone_number TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    user_type TEXT NOT NULL DEFAULT 'customer',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create index for phone number lookups
CREATE INDEX idx_users_phone_number ON users(phone_number);

-- Businesses table
CREATE TABLE businesses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id),
    name TEXT NOT NULL,
    description TEXT,
    address TEXT,
    phone TEXT,
    email TEXT,
    access_pin TEXT,
    profile_photo_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Customers table
CREATE TABLE customers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id),
    name TEXT NOT NULL,
    phone_number TEXT NOT NULL,
    email TEXT,
    address TEXT,
    whatsapp_number TEXT,
    profile_photo_url TEXT,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Customer credits table
CREATE TABLE customer_credits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    business_id UUID NOT NULL REFERENCES businesses(id),
    customer_id UUID NOT NULL REFERENCES customers(id),
    current_balance DECIMAL(10, 2) DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(business_id, customer_id)
);

-- Transactions table
CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    business_id UUID NOT NULL REFERENCES businesses(id),
    customer_id UUID NOT NULL REFERENCES customers(id),
    amount DECIMAL(10, 2) NOT NULL,
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('credit', 'payment')),
    notes TEXT,
    media_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES users(id)
);

-- Media attachments table
CREATE TABLE media_attachments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    transaction_id UUID REFERENCES transactions(id),
    file_url TEXT NOT NULL,
    file_type TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ====================================================================
-- PART 3: CREATE TRIGGERS AND FUNCTIONS
-- ====================================================================

-- Trigger to automatically create customer record when user is created
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

CREATE TRIGGER create_customer_trigger
AFTER INSERT ON users
FOR EACH ROW
EXECUTE FUNCTION create_customer_after_user();

-- Trigger to automatically create business record when user is created
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

CREATE TRIGGER create_business_trigger
AFTER INSERT ON users
FOR EACH ROW
EXECUTE FUNCTION create_business_after_user();

-- Function to authenticate by phone and password
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

-- View for customer balance
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

-- ====================================================================
-- PART 4: CREATE SAMPLE DATA (Optional)
-- ====================================================================

-- Uncomment and modify this section if you want to create sample data

/*
-- Create sample business user
INSERT INTO users (id, name, phone_number, password_hash, user_type)
VALUES (
    uuid_generate_v4(),
    'Sample Business',
    '1234567890',
    'password123',
    'business'
);

-- Create sample customer user
INSERT INTO users (id, name, phone_number, password_hash, user_type)
VALUES (
    uuid_generate_v4(),
    'Sample Customer',
    '0987654321',
    'password123',
    'customer'
);
*/ 