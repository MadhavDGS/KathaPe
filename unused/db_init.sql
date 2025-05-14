-- Database initialization script for Katha
-- This script ensures that all required extensions and functions exist

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Check if tables exist, if not create them
DO $$
BEGIN
    -- Check if users table exists
    IF NOT EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'users') THEN
        -- Create users table
        CREATE TABLE users (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            name TEXT NOT NULL,
            phone_number TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            email TEXT UNIQUE,
            user_type TEXT NOT NULL CHECK (user_type IN ('business', 'customer')),
            use_email_otp BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );
    END IF;

    -- Check if businesses table exists
    IF NOT EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'businesses') THEN
        -- Create businesses table
        CREATE TABLE businesses (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            description TEXT,
            address TEXT,
            access_pin TEXT UNIQUE,
            business_phone TEXT,
            business_email TEXT,
            logo_url TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );
    END IF;

    -- Check if customers table exists
    IF NOT EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'customers') THEN
        -- Create customers table
        CREATE TABLE customers (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id UUID REFERENCES users(id) ON DELETE SET NULL,
            name TEXT NOT NULL,
            phone_number TEXT NOT NULL,
            email TEXT,
            address TEXT,
            notes TEXT,
            profile_photo_url TEXT,
            whatsapp_number TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(phone_number, user_id)
        );
    END IF;

    -- Check if customer_credits table exists
    IF NOT EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'customer_credits') THEN
        -- Create customer_credits table
        CREATE TABLE customer_credits (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
            customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
            current_balance DECIMAL(12, 2) DEFAULT 0,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(business_id, customer_id)
        );
    END IF;

    -- Check if transactions table exists
    IF NOT EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'transactions') THEN
        -- Create transactions table
        CREATE TABLE transactions (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
            customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
            amount DECIMAL(12, 2) NOT NULL,
            transaction_type TEXT NOT NULL CHECK (transaction_type IN ('credit', 'payment')),
            notes TEXT,
            media_url TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            created_by UUID REFERENCES users(id) ON DELETE SET NULL
        );
    END IF;
END $$;

-- Create or replace register_user function
CREATE OR REPLACE FUNCTION register_user(
    p_name TEXT,
    p_phone_number TEXT,
    p_password_hash TEXT,
    p_email TEXT,
    p_user_type TEXT,
    p_use_email_otp BOOLEAN DEFAULT FALSE
) 
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    new_user_id UUID;
    business_id UUID;
    customer_id UUID;
    access_pin TEXT;
    result JSONB;
BEGIN
    -- Check if user with this phone already exists
    IF EXISTS (SELECT 1 FROM users WHERE phone_number = p_phone_number) THEN
        RETURN jsonb_build_object(
            'success', false,
            'message', 'Phone number already registered'
        );
    END IF;
    
    -- Check if email is provided and already exists
    IF p_email IS NOT NULL AND p_email != '' AND
       EXISTS (SELECT 1 FROM users WHERE email = p_email) THEN
        RETURN jsonb_build_object(
            'success', false,
            'message', 'Email already registered'
        );
    END IF;
    
    -- Insert new user
    INSERT INTO users (
        name, 
        phone_number, 
        password_hash, 
        email, 
        user_type, 
        use_email_otp,
        created_at, 
        updated_at
    )
    VALUES (
        p_name, 
        p_phone_number, 
        p_password_hash, 
        CASE WHEN p_email = '' THEN NULL ELSE p_email END,
        p_user_type, 
        p_use_email_otp,
        NOW(), 
        NOW()
    )
    RETURNING id INTO new_user_id;
    
    -- Generate an access pin for business
    SELECT LPAD(FLOOR(RANDOM() * 10000)::TEXT, 4, '0') INTO access_pin;
    
    -- If business user, create a default business
    IF p_user_type = 'business' THEN
        INSERT INTO businesses (
            user_id, 
            name, 
            description,
            access_pin, 
            created_at, 
            updated_at
        )
        VALUES (
            new_user_id, 
            p_name || '''s Business', 
            'My business account',
            access_pin, 
            NOW(), 
            NOW()
        )
        RETURNING id INTO business_id;
        
        result := jsonb_build_object(
            'success', true,
            'message', 'Business registration successful!',
            'user_id', new_user_id,
            'business_id', business_id,
            'access_pin', access_pin
        );
    ELSIF p_user_type = 'customer' THEN
        -- Create customer record for this user
        INSERT INTO customers (
            user_id,
            name,
            phone_number,
            email,
            created_at,
            updated_at
        )
        VALUES (
            new_user_id,
            p_name,
            p_phone_number,
            CASE WHEN p_email = '' THEN NULL ELSE p_email END,
            NOW(),
            NOW()
        )
        RETURNING id INTO customer_id;
        
        result := jsonb_build_object(
            'success', true,
            'message', 'Customer registration successful!',
            'user_id', new_user_id,
            'customer_id', customer_id
        );
    ELSE
        result := jsonb_build_object(
            'success', true,
            'message', 'Registration successful!',
            'user_id', new_user_id
        );
    END IF;
    
    RETURN result;
END;
$$;

-- Create business PIN generation function if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM pg_proc 
        WHERE proname = 'generate_business_access_pin'
    ) THEN
        -- Create the function
        EXECUTE $func$
        CREATE OR REPLACE FUNCTION generate_business_access_pin()
        RETURNS text AS $$
        DECLARE
            new_pin TEXT;
            pin_exists BOOLEAN;
        BEGIN
            LOOP
                -- Generate a random 4-digit PIN
                new_pin := LPAD(FLOOR(RANDOM() * 10000)::TEXT, 4, '0');
                
                -- Check if this PIN already exists
                SELECT EXISTS (
                    SELECT 1 FROM businesses WHERE access_pin = new_pin
                ) INTO pin_exists;
                
                -- If the PIN doesn't exist, we can use it
                IF NOT pin_exists THEN
                    RETURN new_pin;
                END IF;
            END LOOP;
        END;
        $$ LANGUAGE plpgsql;
        $func$;
    END IF;
END
$$; 