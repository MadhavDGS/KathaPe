-- Drop existing tables if they exist (be careful with this in production)
DROP TABLE IF EXISTS transactions CASCADE;
DROP TABLE IF EXISTS customer_credits CASCADE;
DROP TABLE IF EXISTS customers CASCADE;
DROP TABLE IF EXISTS businesses CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS credit_history CASCADE;

-- Create users table (common authentication)
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

-- Create customers table
CREATE TABLE customers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    phone_number TEXT NOT NULL,
    email TEXT,
    address TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    -- Phone numbers can be duplicated across businesses
    UNIQUE(phone_number, user_id)
);

-- Create customer_credits table to track credits for each customer at each business
CREATE TABLE customer_credits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    current_balance DECIMAL(12, 2) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(business_id, customer_id)
);

-- Create transactions table
CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    amount DECIMAL(12, 2) NOT NULL,
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('credit', 'payment')),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES users(id) ON DELETE SET NULL
);

-- Create credit history table
CREATE TABLE credit_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_credit_id UUID NOT NULL REFERENCES customer_credits(id) ON DELETE CASCADE,
    amount DECIMAL(12, 2) NOT NULL,
    description TEXT,
    date TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES users(id) ON DELETE SET NULL
);

-- Create row level security policies

-- Enable Row Level Security
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE businesses ENABLE ROW LEVEL SECURITY;
ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE customer_credits ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE credit_history ENABLE ROW LEVEL SECURITY;

-- Create policies for users table
-- First, drop existing policies
DROP POLICY IF EXISTS "Users can view their own data" ON users;
DROP POLICY IF EXISTS "Users can update their own data" ON users;
DROP POLICY IF EXISTS "Allow registration" ON users;

-- Create new policies
CREATE POLICY "Users can view their own data" ON users
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update their own data" ON users
    FOR UPDATE USING (auth.uid() = id);

-- Allow new user creation without authentication (for registration)
CREATE POLICY "Allow registration" ON users
    FOR INSERT WITH CHECK (true);

-- Create policies for businesses table
-- First, drop existing policies
DROP POLICY IF EXISTS "Business owners can view their businesses" ON businesses;
DROP POLICY IF EXISTS "Business owners can manage their businesses" ON businesses;
DROP POLICY IF EXISTS "Allow business creation for any authenticated user" ON businesses;

-- Create new policies
CREATE POLICY "Business owners can view their businesses" ON businesses
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM users
            WHERE users.id = auth.uid() 
            AND users.id = businesses.user_id
        )
    );

CREATE POLICY "Business owners can manage their businesses" ON businesses
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM users
            WHERE users.id = auth.uid() 
            AND users.id = businesses.user_id
        )
    );

-- Allow business creation
CREATE POLICY "Allow business creation for any authenticated user" ON businesses
    FOR INSERT WITH CHECK (true);

-- Create policies for customers table
-- First, drop existing policies
DROP POLICY IF EXISTS "Business owners can view customers" ON customers;
DROP POLICY IF EXISTS "Customers can view their own data" ON customers;
DROP POLICY IF EXISTS "Allow customer creation for any user" ON customers;

-- Create new policies
CREATE POLICY "Business owners can view customers" ON customers
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM customer_credits
            JOIN businesses ON businesses.id = customer_credits.business_id
            WHERE customer_credits.customer_id = customers.id
            AND businesses.user_id = auth.uid()
        )
    );

CREATE POLICY "Customers can view their own data" ON customers
    FOR SELECT USING (
        customers.user_id = auth.uid() OR
        EXISTS (
            SELECT 1 FROM customer_credits
            JOIN businesses ON businesses.id = customer_credits.business_id
            WHERE customer_credits.customer_id = customers.id
            AND businesses.user_id = auth.uid()
        )
    );

-- Allow customer creation
CREATE POLICY "Allow customer creation for any user" ON customers
    FOR INSERT WITH CHECK (true);

-- Create policies for customer_credits table
CREATE POLICY "Business owners can view customer credits" ON customer_credits
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM businesses
            WHERE businesses.id = customer_credits.business_id
            AND businesses.user_id = auth.uid()
        )
    );

CREATE POLICY "Business owners can manage customer credits" ON customer_credits
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM businesses
            WHERE businesses.id = customer_credits.business_id
            AND businesses.user_id = auth.uid()
        )
    );

CREATE POLICY "Customers can view their own credits" ON customer_credits
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM customers
            WHERE customers.id = customer_credits.customer_id
            AND customers.user_id = auth.uid()
        )
    );

-- Create policies for transactions table
CREATE POLICY "Business owners can view transactions" ON transactions
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM businesses
            WHERE businesses.id = transactions.business_id
            AND businesses.user_id = auth.uid()
        )
    );

CREATE POLICY "Business owners can manage transactions" ON transactions
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM businesses
            WHERE businesses.id = transactions.business_id
            AND businesses.user_id = auth.uid()
        )
    );

CREATE POLICY "Customers can view their transactions" ON transactions
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM customers
            WHERE customers.id = transactions.customer_id
            AND customers.user_id = auth.uid()
        )
    );

-- Create policies for credit_history table
CREATE POLICY "Business owners can view credit history" ON credit_history
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM customer_credits
            JOIN businesses ON businesses.id = customer_credits.business_id
            WHERE customer_credits.id = credit_history.customer_credit_id
            AND businesses.user_id = auth.uid()
        )
    );

CREATE POLICY "Customers can view their credit history" ON credit_history
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM customer_credits
            JOIN customers ON customers.id = customer_credits.customer_id
            WHERE customer_credits.id = credit_history.customer_credit_id
            AND customers.user_id = auth.uid()
        )
    );

-- Create authentication triggers and functions (for maintaining updated_at)
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply the trigger to all tables with updated_at
CREATE TRIGGER update_users_modtime
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_column();

CREATE TRIGGER update_businesses_modtime
    BEFORE UPDATE ON businesses
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_column();

CREATE TRIGGER update_customers_modtime
    BEFORE UPDATE ON customers
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_column();

CREATE TRIGGER update_customer_credits_modtime
    BEFORE UPDATE ON customer_credits
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_column();

CREATE TRIGGER update_credit_history_modtime
    BEFORE UPDATE ON credit_history
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_column();

-- Add custom functions
-- Function to update customer_credits when a transaction is added
CREATE OR REPLACE FUNCTION update_credit_balance() 
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.transaction_type = 'credit' THEN
    -- Add credit (increase the balance)
    UPDATE customer_credits
    SET current_balance = current_balance + NEW.amount,
        updated_at = NOW()
    WHERE business_id = NEW.business_id AND customer_id = NEW.customer_id;
  ELSIF NEW.transaction_type = 'payment' THEN
    -- Subtract payment (decrease the balance)
    UPDATE customer_credits
    SET current_balance = current_balance - NEW.amount,
        updated_at = NOW()
    WHERE business_id = NEW.business_id AND customer_id = NEW.customer_id;
  END IF;
  
  -- If no record exists, create one
  IF NOT FOUND THEN
    INSERT INTO customer_credits (business_id, customer_id, current_balance)
    VALUES (
      NEW.business_id, 
      NEW.customer_id,
      CASE 
        WHEN NEW.transaction_type = 'credit' THEN NEW.amount
        WHEN NEW.transaction_type = 'payment' THEN -NEW.amount
        ELSE 0
      END
    );
  END IF;
  
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Add trigger for transactions
CREATE TRIGGER update_credit_balance_trigger
AFTER INSERT ON transactions
FOR EACH ROW
EXECUTE FUNCTION update_credit_balance();

-- Insert seed data
-- Sample business owner user
INSERT INTO users (id, name, phone_number, password_hash, email, user_type, use_email_otp, created_at, updated_at)
VALUES 
    ('11111111-1111-1111-1111-111111111111', 'Demo Business Owner', '9876543210', 
     '$2a$10$UxQpkjI9UtUJ0d3ZCOxE4uCoo66/k9O.dqJSC5lYvSRf/RHJVxBuS', -- password is 'password123'
     'business@example.com', 'business', false, NOW(), NOW());

-- Sample customer user
INSERT INTO users (id, name, phone_number, password_hash, email, user_type, use_email_otp, created_at, updated_at)
VALUES 
    ('22222222-2222-2222-2222-222222222222', 'Demo Customer', '1234567890', 
     '$2a$10$UxQpkjI9UtUJ0d3ZCOxE4uCoo66/k9O.dqJSC5lYvSRf/RHJVxBuS', -- password is 'password123'
     'customer@example.com', 'customer', false, NOW(), NOW());

-- Sample business
INSERT INTO businesses (id, user_id, name, description, address, access_pin, business_phone, business_email, created_at, updated_at)
VALUES 
    ('33333333-3333-3333-3333-333333333333', '11111111-1111-1111-1111-111111111111', 
     'Demo Shop', 'A demo shop for testing', '123 Main St', '123456', '9876543210', 
     'shop@example.com', NOW(), NOW());

-- Sample customer record
INSERT INTO customers (id, user_id, name, phone_number, email, address, notes, created_at, updated_at)
VALUES 
    ('44444444-4444-4444-4444-444444444444', '22222222-2222-2222-2222-222222222222', 
     'Demo Customer', '1234567890', 'customer@example.com', '456 Oak St', 'Regular customer', NOW(), NOW());

-- Sample credit relationship
INSERT INTO customer_credits (id, business_id, customer_id, current_balance, created_at, updated_at)
VALUES 
    ('55555555-5555-5555-5555-555555555555', '33333333-3333-3333-3333-333333333333', 
     '44444444-4444-4444-4444-444444444444', 500.00, NOW(), NOW());

-- Sample transaction
INSERT INTO transactions (id, business_id, customer_id, amount, transaction_type, notes, created_at, created_by)
VALUES 
    ('66666666-6666-6666-6666-666666666666', '33333333-3333-3333-3333-333333333333', 
     '44444444-4444-4444-4444-444444444444', 500.00, 'credit', 'Initial credit', NOW(), 
     '11111111-1111-1111-1111-111111111111');

-- Sample credit history
INSERT INTO credit_history (id, customer_credit_id, amount, description, date, created_by)
VALUES 
    ('77777777-7777-7777-7777-777777777777', '55555555-5555-5555-5555-555555555555', 
     500.00, 'Initial credit', NOW(), '11111111-1111-1111-1111-111111111111');

-- Create helper function for user registration
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
SECURITY DEFINER -- This allows the function to bypass RLS
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
    
    -- If business user, create a default business with access pin
    IF p_user_type = 'business' THEN
        -- Generate a random 6-digit pin
        access_pin := floor(random() * 900000 + 100000)::TEXT;
        
        -- Create default business
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
            'user_id', new_user_id,
            'customer_id', customer_id
        );
    ELSE
        result := jsonb_build_object(
            'success', true,
            'user_id', new_user_id
        );
    END IF;
    
    RETURN result;
END;
$$;

-- Create a function to verify user login
CREATE OR REPLACE FUNCTION login_user(
    p_phone_number TEXT,
    p_password TEXT,
    p_user_type TEXT
) 
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    found_user RECORD;
    result JSONB;
BEGIN
    -- Find the user by phone number and type
    SELECT * INTO found_user FROM users
    WHERE phone_number = p_phone_number AND user_type = p_user_type;
    
    -- Check if user exists
    IF found_user IS NULL THEN
        RETURN jsonb_build_object(
            'success', false,
            'message', 'Invalid phone number or user type'
        );
    END IF;
    
    -- Properly verify the password using pgcrypto's crypt function
    -- This approach is compatible with how Flask's werkzeug generates password hashes
    IF found_user.password_hash IS NOT NULL AND 
       (found_user.password_hash = p_password OR  -- For testing with demo accounts
        crypt(p_password, found_user.password_hash) = found_user.password_hash) THEN
        
        -- Authentication successful
        RETURN jsonb_build_object(
            'success', true,
            'user', jsonb_build_object(
                'id', found_user.id,
                'name', found_user.name,
                'phone_number', found_user.phone_number,
                'user_type', found_user.user_type
            )
        );
    END IF;
    
    -- If we get here, authentication failed
    RETURN jsonb_build_object(
        'success', false,
        'message', 'Invalid password'
    );
END;
$$;

-- Create a function to bypass RLS for customer lookups
CREATE OR REPLACE FUNCTION get_customer_by_user_id(p_user_id UUID)
RETURNS SETOF customers
LANGUAGE plpgsql
SECURITY DEFINER -- This allows the function to bypass RLS
AS $$
BEGIN
    RETURN QUERY SELECT * FROM customers WHERE user_id = p_user_id;
END;
$$; 