-- Insert seed data

-- Sample business owner user (password = 'password123')
INSERT INTO users (id, name, phone_number, password_hash, email, user_type, use_email_otp, created_at, updated_at)
VALUES 
    ('11111111-1111-1111-1111-111111111111', 'Demo Business Owner', '9876543210', 
     '$2a$10$UxQpkjI9UtUJ0d3ZCOxE4uCoo66/k9O.dqJSC5lYvSRf/RHJVxBuS',
     'business@example.com', 'business', false, NOW(), NOW());

-- Sample customer user (password = 'password123')
INSERT INTO users (id, name, phone_number, password_hash, email, user_type, use_email_otp, created_at, updated_at)
VALUES 
    ('22222222-2222-2222-2222-222222222222', 'Demo Customer', '1234567890', 
     '$2a$10$UxQpkjI9UtUJ0d3ZCOxE4uCoo66/k9O.dqJSC5lYvSRf/RHJVxBuS',
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

-- Sample customer with no user account
INSERT INTO customers (id, name, phone_number, email, address, notes, created_at, updated_at)
VALUES 
    ('55555555-5555-5555-5555-555555555555', 
     'Walk-in Customer', '5555555555', 'walkin@example.com', '789 Pine St', 'Walk-in customer', NOW(), NOW());

-- Sample credit relationship
INSERT INTO customer_credits (id, business_id, customer_id, current_balance, created_at, updated_at)
VALUES 
    ('66666666-6666-6666-6666-666666666666', '33333333-3333-3333-3333-333333333333', 
     '44444444-4444-4444-4444-444444444444', 500.00, NOW(), NOW());

-- Sample credit relationship for walk-in customer
INSERT INTO customer_credits (id, business_id, customer_id, current_balance, created_at, updated_at)
VALUES 
    ('77777777-7777-7777-7777-777777777777', '33333333-3333-3333-3333-333333333333', 
     '55555555-5555-5555-5555-555555555555', 250.00, NOW(), NOW());

-- Sample transactions
INSERT INTO transactions (id, business_id, customer_id, amount, transaction_type, notes, created_at, created_by)
VALUES 
    ('88888888-8888-8888-8888-888888888888', '33333333-3333-3333-3333-333333333333', 
     '44444444-4444-4444-4444-444444444444', 500.00, 'credit', 'Initial credit', NOW(), 
     '11111111-1111-1111-1111-111111111111');

INSERT INTO transactions (id, business_id, customer_id, amount, transaction_type, notes, created_at, created_by)
VALUES 
    ('99999999-9999-9999-9999-999999999999', '33333333-3333-3333-3333-333333333333', 
     '55555555-5555-5555-5555-555555555555', 250.00, 'credit', 'Initial credit', NOW(), 
     '11111111-1111-1111-1111-111111111111');

-- Add function to add a new customer and create credit
CREATE OR REPLACE FUNCTION add_customer_with_credit(
    p_business_id UUID,
    p_name TEXT,
    p_phone_number TEXT,
    p_email TEXT,
    p_address TEXT,
    p_notes TEXT,
    p_initial_credit DECIMAL DEFAULT 0,
    p_created_by UUID
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    new_customer_id UUID;
    credit_id UUID;
    transaction_id UUID;
    result JSONB;
BEGIN
    -- Check if phone number already exists for this business
    IF EXISTS (
        SELECT 1 FROM customers c
        JOIN customer_credits cc ON c.id = cc.customer_id
        WHERE c.phone_number = p_phone_number AND cc.business_id = p_business_id
    ) THEN
        RETURN jsonb_build_object(
            'success', false,
            'message', 'Phone number already exists for this business'
        );
    END IF;
    
    -- Create new customer
    INSERT INTO customers (
        name,
        phone_number,
        email,
        address,
        notes,
        created_at,
        updated_at
    )
    VALUES (
        p_name,
        p_phone_number,
        p_email,
        p_address,
        p_notes,
        NOW(),
        NOW()
    )
    RETURNING id INTO new_customer_id;
    
    -- Create credit record
    INSERT INTO customer_credits (
        business_id,
        customer_id,
        current_balance,
        created_at,
        updated_at
    )
    VALUES (
        p_business_id,
        new_customer_id,
        p_initial_credit,
        NOW(),
        NOW()
    )
    RETURNING id INTO credit_id;
    
    -- Add transaction if initial credit > 0
    IF p_initial_credit > 0 THEN
        INSERT INTO transactions (
            business_id,
            customer_id,
            amount,
            transaction_type,
            notes,
            created_at,
            created_by
        )
        VALUES (
            p_business_id,
            new_customer_id,
            p_initial_credit,
            'credit',
            'Initial credit',
            NOW(),
            p_created_by
        )
        RETURNING id INTO transaction_id;
    END IF;
    
    RETURN jsonb_build_object(
        'success', true,
        'customer_id', new_customer_id,
        'credit_id', credit_id,
        'transaction_id', transaction_id,
        'message', 'Customer added successfully'
    );
END;
$$;

-- Add function to create a transaction
CREATE OR REPLACE FUNCTION add_transaction(
    p_business_id UUID,
    p_customer_id UUID,
    p_amount DECIMAL,
    p_transaction_type TEXT,
    p_notes TEXT,
    p_created_by UUID
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    new_transaction_id UUID;
    result JSONB;
BEGIN
    -- Validate inputs
    IF p_amount <= 0 THEN
        RETURN jsonb_build_object(
            'success', false,
            'message', 'Amount must be greater than 0'
        );
    END IF;
    
    IF p_transaction_type NOT IN ('credit', 'payment') THEN
        RETURN jsonb_build_object(
            'success', false,
            'message', 'Transaction type must be either credit or payment'
        );
    END IF;
    
    -- Check if customer exists for this business
    IF NOT EXISTS (
        SELECT 1 FROM customer_credits
        WHERE business_id = p_business_id AND customer_id = p_customer_id
    ) THEN
        -- Create a new credit record if it doesn't exist
        INSERT INTO customer_credits (business_id, customer_id, current_balance)
        VALUES (p_business_id, p_customer_id, 0);
    END IF;
    
    -- Create transaction
    INSERT INTO transactions (
        business_id,
        customer_id,
        amount,
        transaction_type,
        notes,
        created_at,
        created_by
    )
    VALUES (
        p_business_id,
        p_customer_id,
        p_amount,
        p_transaction_type,
        p_notes,
        NOW(),
        p_created_by
    )
    RETURNING id INTO new_transaction_id;
    
    -- Get updated balance
    RETURN jsonb_build_object(
        'success', true,
        'transaction_id', new_transaction_id,
        'message', 'Transaction added successfully'
    );
END;
$$; 