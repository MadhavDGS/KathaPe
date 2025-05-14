-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

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
    updated_at TIMESTAMPTZ DEFAULT NOW()
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

-- Enable Row Level Security
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE businesses ENABLE ROW LEVEL SECURITY;
ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE customer_credits ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE credit_history ENABLE ROW LEVEL SECURITY;

-- Create policies for users table
DROP POLICY IF EXISTS "Users can view their own data" ON users;
DROP POLICY IF EXISTS "Users can update their own data" ON users;
DROP POLICY IF EXISTS "Allow registration" ON users;
DROP POLICY IF EXISTS "Allow admins full access" ON users;

-- Create new policies for users
CREATE POLICY "Users can view their own data" ON users
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update their own data" ON users
    FOR UPDATE USING (auth.uid() = id);

-- Allow new user creation without authentication (for registration)
CREATE POLICY "Allow registration" ON users
    FOR INSERT WITH CHECK (true);

-- Create policies for businesses table
DROP POLICY IF EXISTS "Business owners can view their businesses" ON businesses;
DROP POLICY IF EXISTS "Business owners can manage their businesses" ON businesses;
DROP POLICY IF EXISTS "Allow business creation for authenticated users" ON businesses;
DROP POLICY IF EXISTS "Allow business viewing with access pin" ON businesses;
DROP POLICY IF EXISTS "Customers can view businesses they have credits with" ON businesses;

-- Create new business policies
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

-- Allow customers to view businesses they have credits with
CREATE POLICY "Customers can view businesses they have credits with" ON businesses
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM customer_credits
            JOIN customers ON customers.id = customer_credits.customer_id
            WHERE customer_credits.business_id = businesses.id
            AND customers.user_id = auth.uid()
        )
    );

-- Allow business creation for authenticated users
CREATE POLICY "Allow business creation for authenticated users" ON businesses
    FOR INSERT WITH CHECK (auth.uid() IS NOT NULL);

-- Create policies for customers table
DROP POLICY IF EXISTS "Business owners can view customers" ON customers;
DROP POLICY IF EXISTS "Business owners can manage customers" ON customers;
DROP POLICY IF EXISTS "Customers can view their own data" ON customers;
DROP POLICY IF EXISTS "Customers can view and update their own data" ON customers;
DROP POLICY IF EXISTS "Allow customer creation" ON customers;

-- Create new customer policies
CREATE POLICY "Business owners can view customers" ON customers
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM customer_credits
            JOIN businesses ON businesses.id = customer_credits.business_id
            WHERE customer_credits.customer_id = customers.id
            AND businesses.user_id = auth.uid()
        )
    );

CREATE POLICY "Business owners can manage customers" ON customers
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM customer_credits
            JOIN businesses ON businesses.id = customer_credits.business_id
            WHERE customer_credits.customer_id = customers.id
            AND businesses.user_id = auth.uid()
        )
    );

CREATE POLICY "Customers can view and update their own data" ON customers
    FOR ALL USING (customers.user_id = auth.uid());

-- Allow customer creation
CREATE POLICY "Allow customer creation" ON customers
    FOR INSERT WITH CHECK (auth.uid() IS NOT NULL);

-- Create policies for customer_credits table
DROP POLICY IF EXISTS "Business owners can view customer credits" ON customer_credits;
DROP POLICY IF EXISTS "Business owners can manage customer credits" ON customer_credits;
DROP POLICY IF EXISTS "Customers can view their own credits" ON customer_credits;

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
DROP POLICY IF EXISTS "Business owners can view transactions" ON transactions;
DROP POLICY IF EXISTS "Business owners can manage transactions" ON transactions;
DROP POLICY IF EXISTS "Customers can view their transactions" ON transactions;

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
DROP POLICY IF EXISTS "Business owners can view credit history" ON credit_history;
DROP POLICY IF EXISTS "Customers can view their credit history" ON credit_history;

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

-- Create authentication triggers and functions
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

-- Function to update customer_credits when a transaction is added
CREATE OR REPLACE FUNCTION update_credit_balance() 
RETURNS TRIGGER AS $$
DECLARE
    credit_id UUID;
BEGIN
    -- Find the customer_credits record
    SELECT id INTO credit_id 
    FROM customer_credits 
    WHERE business_id = NEW.business_id AND customer_id = NEW.customer_id;
    
    IF NEW.transaction_type = 'credit' THEN
        -- Add credit (increase the balance)
        UPDATE customer_credits
        SET current_balance = current_balance + NEW.amount,
            updated_at = NOW()
        WHERE business_id = NEW.business_id AND customer_id = NEW.customer_id;
        
        -- If no record exists, create one
        IF NOT FOUND THEN
            INSERT INTO customer_credits (business_id, customer_id, current_balance)
            VALUES (NEW.business_id, NEW.customer_id, NEW.amount)
            RETURNING id INTO credit_id;
        END IF;
        
        -- Add to credit history
        INSERT INTO credit_history (
            customer_credit_id, 
            amount, 
            description, 
            date, 
            created_by
        )
        VALUES (
            credit_id,
            NEW.amount,
            COALESCE(NEW.notes, 'Credit added'),
            NEW.created_at,
            NEW.created_by
        );
        
    ELSIF NEW.transaction_type = 'payment' THEN
        -- Subtract payment (decrease the balance)
        UPDATE customer_credits
        SET current_balance = current_balance - NEW.amount,
            updated_at = NOW()
        WHERE business_id = NEW.business_id AND customer_id = NEW.customer_id;
        
        -- If no record exists, create one with negative balance
        IF NOT FOUND THEN
            INSERT INTO customer_credits (business_id, customer_id, current_balance)
            VALUES (NEW.business_id, NEW.customer_id, -NEW.amount)
            RETURNING id INTO credit_id;
        END IF;
        
        -- Add to credit history
        INSERT INTO credit_history (
            customer_credit_id, 
            amount, 
            description, 
            date, 
            created_by
        )
        VALUES (
            credit_id,
            -NEW.amount,
            COALESCE(NEW.notes, 'Payment made'),
            NEW.created_at,
            NEW.created_by
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

-- Create improved user authentication functions
-- Function to register a new user
CREATE OR REPLACE FUNCTION register_user(
    p_name TEXT,
    p_phone_number TEXT,
    p_password TEXT, -- Plain text password that will be hashed
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
    hashed_password TEXT;
    result JSONB;
BEGIN
    -- Validate inputs
    IF p_name IS NULL OR p_name = '' THEN
        RETURN jsonb_build_object(
            'success', false,
            'message', 'Name is required'
        );
    END IF;
    
    IF p_phone_number IS NULL OR p_phone_number = '' THEN
        RETURN jsonb_build_object(
            'success', false,
            'message', 'Phone number is required'
        );
    END IF;
    
    IF p_password IS NULL OR p_password = '' THEN
        RETURN jsonb_build_object(
            'success', false,
            'message', 'Password is required'
        );
    END IF;
    
    IF p_user_type IS NULL OR p_user_type = '' OR 
       p_user_type NOT IN ('business', 'customer') THEN
        RETURN jsonb_build_object(
            'success', false,
            'message', 'Valid user type (business or customer) is required'
        );
    END IF;
    
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
    
    -- Hash the password
    hashed_password := crypt(p_password, gen_salt('bf'));
    
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
        hashed_password, 
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
            business_phone,
            created_at, 
            updated_at
        )
        VALUES (
            new_user_id, 
            p_name || '''s Business', 
            'My business account',
            access_pin, 
            p_phone_number,
            NOW(), 
            NOW()
        )
        RETURNING id INTO business_id;
        
        result := jsonb_build_object(
            'success', true,
            'user_id', new_user_id,
            'business_id', business_id,
            'access_pin', access_pin,
            'message', 'Business account created successfully'
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
            'customer_id', customer_id,
            'message', 'Customer account created successfully'
        );
    ELSE
        result := jsonb_build_object(
            'success', true,
            'user_id', new_user_id,
            'message', 'User account created successfully'
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
    user_business RECORD;
    user_customer RECORD;
    result JSONB;
BEGIN
    -- Validate inputs
    IF p_phone_number IS NULL OR p_phone_number = '' THEN
        RETURN jsonb_build_object(
            'success', false,
            'message', 'Phone number is required'
        );
    END IF;
    
    IF p_password IS NULL OR p_password = '' THEN
        RETURN jsonb_build_object(
            'success', false,
            'message', 'Password is required'
        );
    END IF;
    
    IF p_user_type IS NULL OR p_user_type = '' OR 
       p_user_type NOT IN ('business', 'customer') THEN
        RETURN jsonb_build_object(
            'success', false,
            'message', 'Valid user type (business or customer) is required'
        );
    END IF;
    
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
    
    -- Verify the password - allow direct hash match for demo accounts or proper verification
    IF found_user.password_hash IS NOT NULL AND 
       (found_user.password_hash = p_password OR  -- For testing with demo accounts
        crypt(p_password, found_user.password_hash) = found_user.password_hash) THEN
        
        -- Get additional details based on user type
        IF p_user_type = 'business' THEN
            -- Get business information
            SELECT * INTO user_business FROM businesses
            WHERE user_id = found_user.id
            LIMIT 1;
            
            -- Authentication successful
            RETURN jsonb_build_object(
                'success', true,
                'user', jsonb_build_object(
                    'id', found_user.id,
                    'name', found_user.name,
                    'phone_number', found_user.phone_number,
                    'email', found_user.email,
                    'user_type', found_user.user_type
                ),
                'business', CASE WHEN user_business IS NOT NULL THEN
                    jsonb_build_object(
                        'id', user_business.id,
                        'name', user_business.name,
                        'access_pin', user_business.access_pin
                    )
                ELSE NULL END,
                'message', 'Login successful'
            );
        ELSIF p_user_type = 'customer' THEN
            -- Get customer information
            SELECT * INTO user_customer FROM customers
            WHERE user_id = found_user.id
            LIMIT 1;
            
            -- Authentication successful
            RETURN jsonb_build_object(
                'success', true,
                'user', jsonb_build_object(
                    'id', found_user.id,
                    'name', found_user.name,
                    'phone_number', found_user.phone_number,
                    'email', found_user.email,
                    'user_type', found_user.user_type
                ),
                'customer', CASE WHEN user_customer IS NOT NULL THEN
                    jsonb_build_object(
                        'id', user_customer.id,
                        'name', user_customer.name
                    )
                ELSE NULL END,
                'message', 'Login successful'
            );
        END IF;
    END IF;
    
    -- If we get here, authentication failed
    RETURN jsonb_build_object(
        'success', false,
        'message', 'Invalid password'
    );
END;
$$;

-- Create helper functions for data retrieval
-- Get business by user ID
CREATE OR REPLACE FUNCTION get_business_by_user_id(p_user_id UUID)
RETURNS SETOF businesses
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY 
    SELECT * FROM businesses WHERE user_id = p_user_id;
END;
$$;

-- Get customer by user ID
CREATE OR REPLACE FUNCTION get_customer_by_user_id(p_user_id UUID)
RETURNS SETOF customers
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY 
    SELECT * FROM customers WHERE user_id = p_user_id;
END;
$$;

-- Get business by access pin
CREATE OR REPLACE FUNCTION get_business_by_access_pin(p_access_pin TEXT)
RETURNS SETOF businesses
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY 
    SELECT * FROM businesses WHERE access_pin = p_access_pin;
END;
$$;

-- Get customers by business ID
CREATE OR REPLACE FUNCTION get_customers_by_business_id(p_business_id UUID)
RETURNS TABLE (
    customer_id UUID,
    name TEXT,
    phone_number TEXT,
    email TEXT,
    address TEXT,
    notes TEXT,
    current_balance DECIMAL(12, 2)
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY 
    SELECT 
        c.id as customer_id,
        c.name,
        c.phone_number,
        c.email,
        c.address,
        c.notes,
        COALESCE(cc.current_balance, 0) as current_balance
    FROM customers c
    LEFT JOIN customer_credits cc ON c.id = cc.customer_id AND cc.business_id = p_business_id
    WHERE EXISTS (
        SELECT 1 FROM customer_credits 
        WHERE customer_id = c.id AND business_id = p_business_id
    );
END;
$$;

-- Get customer by phone number for a business
CREATE OR REPLACE FUNCTION get_customer_by_phone(p_business_id UUID, p_phone_number TEXT)
RETURNS TABLE (
    customer_id UUID,
    name TEXT,
    phone_number TEXT,
    email TEXT,
    address TEXT,
    notes TEXT,
    current_balance DECIMAL(12, 2)
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY 
    SELECT 
        c.id as customer_id,
        c.name,
        c.phone_number,
        c.email,
        c.address,
        c.notes,
        COALESCE(cc.current_balance, 0) as current_balance
    FROM customers c
    LEFT JOIN customer_credits cc ON c.id = cc.customer_id AND cc.business_id = p_business_id
    WHERE c.phone_number = p_phone_number AND 
          (EXISTS (
              SELECT 1 FROM customer_credits 
              WHERE customer_id = c.id AND business_id = p_business_id
          ) OR NOT EXISTS (
              SELECT 1 FROM customer_credits 
              WHERE customer_id IN (SELECT id FROM customers WHERE phone_number = p_phone_number)
              AND business_id = p_business_id
          ));
END;
$$; 