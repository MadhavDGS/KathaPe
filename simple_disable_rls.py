#!/usr/bin/env python3

# Simple script to generate SQL to disable RLS
# You'll need to run this SQL in the Supabase Studio SQL Editor

sql_commands = """
-- Disable Row Level Security for all Katha tables
ALTER TABLE IF EXISTS users DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS businesses DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS customers DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS customer_credits DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS transactions DISABLE ROW LEVEL SECURITY;

-- Create tables if they don't exist
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    phone_number TEXT UNIQUE NOT NULL,
    email TEXT,
    user_type TEXT NOT NULL CHECK (user_type IN ('business', 'customer')),
    password TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS businesses (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
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

CREATE TABLE IF NOT EXISTS customers (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    name TEXT NOT NULL,
    phone_number TEXT NOT NULL,
    whatsapp_number TEXT,
    email TEXT,
    address TEXT,
    notes TEXT,
    profile_photo_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS customer_credits (
    id UUID PRIMARY KEY,
    customer_id UUID NOT NULL,
    business_id UUID NOT NULL,
    current_balance NUMERIC(10, 2) DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(customer_id, business_id)
);

CREATE TABLE IF NOT EXISTS transactions (
    id UUID PRIMARY KEY,
    customer_id UUID NOT NULL,
    business_id UUID NOT NULL,
    amount NUMERIC(10, 2) NOT NULL,
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('credit', 'payment')),
    notes TEXT,
    media_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by UUID
);

-- Create trigger to update balance on transactions
CREATE OR REPLACE FUNCTION update_balance_on_transaction()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.transaction_type = 'credit' THEN
        UPDATE customer_credits
        SET current_balance = current_balance + NEW.amount,
            updated_at = CURRENT_TIMESTAMP
        WHERE customer_id = NEW.customer_id AND business_id = NEW.business_id;
    ELSIF NEW.transaction_type = 'payment' THEN
        UPDATE customer_credits
        SET current_balance = current_balance - NEW.amount,
            updated_at = CURRENT_TIMESTAMP
        WHERE customer_id = NEW.customer_id AND business_id = NEW.business_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_balance_trigger ON transactions;

CREATE TRIGGER update_balance_trigger
AFTER INSERT ON transactions
FOR EACH ROW
EXECUTE FUNCTION update_balance_on_transaction();
"""

print("==== SQL to Disable RLS and Setup Tables ====")
print(sql_commands)
print("\n==== INSTRUCTIONS ====")
print("1. Log in to your Supabase dashboard at: https://app.supabase.com")
print("2. Select your project (ghbmfgomnqmffixfkdyp)")
print("3. Click on the SQL Editor tab in the left sidebar")
print("4. Create a new query, paste the SQL above")
print("5. Run the query to disable RLS for all tables")
print("6. Your Katha application should now be able to connect to Supabase") 