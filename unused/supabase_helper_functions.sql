-- Additional helper functions

-- Search customers by name or phone number for a business
CREATE OR REPLACE FUNCTION search_customers(
    p_business_id UUID,
    p_search_text TEXT
)
RETURNS TABLE (
    customer_id UUID,
    name TEXT,
    phone_number TEXT,
    email TEXT,
    address TEXT,
    notes TEXT,
    current_balance DECIMAL(12, 2),
    last_transaction_date TIMESTAMPTZ
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
        COALESCE(cc.current_balance, 0) as current_balance,
        MAX(t.created_at) as last_transaction_date
    FROM customers c
    LEFT JOIN customer_credits cc ON c.id = cc.customer_id AND cc.business_id = p_business_id
    LEFT JOIN transactions t ON c.id = t.customer_id AND t.business_id = p_business_id
    WHERE cc.business_id = p_business_id AND (
        c.name ILIKE '%' || p_search_text || '%' OR 
        c.phone_number ILIKE '%' || p_search_text || '%'
    )
    GROUP BY c.id, c.name, c.phone_number, c.email, c.address, c.notes, cc.current_balance
    ORDER BY c.name;
END;
$$;

-- Get customer details with transactions
CREATE OR REPLACE FUNCTION get_customer_details(
    p_business_id UUID,
    p_customer_id UUID
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    customer_info JSONB;
    transaction_list JSONB;
BEGIN
    -- Get customer information
    SELECT 
        jsonb_build_object(
            'id', c.id,
            'name', c.name,
            'phone_number', c.phone_number,
            'email', c.email,
            'address', c.address,
            'notes', c.notes,
            'current_balance', COALESCE(cc.current_balance, 0),
            'created_at', c.created_at
        )
    INTO customer_info
    FROM customers c
    LEFT JOIN customer_credits cc ON c.id = cc.customer_id AND cc.business_id = p_business_id
    WHERE c.id = p_customer_id;
    
    -- Get transaction history
    SELECT 
        jsonb_agg(
            jsonb_build_object(
                'id', t.id,
                'amount', t.amount,
                'transaction_type', t.transaction_type,
                'notes', t.notes,
                'created_at', t.created_at,
                'created_by_name', u.name
            )
        )
    INTO transaction_list
    FROM transactions t
    LEFT JOIN users u ON t.created_by = u.id
    WHERE t.customer_id = p_customer_id AND t.business_id = p_business_id
    ORDER BY t.created_at DESC;
    
    -- Return combined data
    RETURN jsonb_build_object(
        'customer', customer_info,
        'transactions', COALESCE(transaction_list, '[]'::jsonb)
    );
END;
$$;

-- Get business details with customer summary
CREATE OR REPLACE FUNCTION get_business_dashboard(
    p_business_id UUID
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    business_info JSONB;
    customer_summary JSONB;
    recent_transactions JSONB;
    total_customers INT;
    total_credit DECIMAL;
    total_payments DECIMAL;
BEGIN
    -- Get business information
    SELECT 
        jsonb_build_object(
            'id', b.id,
            'name', b.name,
            'description', b.description,
            'address', b.address,
            'access_pin', b.access_pin,
            'business_phone', b.business_phone,
            'business_email', b.business_email,
            'logo_url', b.logo_url
        )
    INTO business_info
    FROM businesses b
    WHERE b.id = p_business_id;
    
    -- Get customer summary
    SELECT
        COUNT(DISTINCT cc.customer_id),
        COALESCE(SUM(CASE WHEN cc.current_balance > 0 THEN cc.current_balance ELSE 0 END), 0),
        COALESCE(SUM(CASE WHEN t.transaction_type = 'payment' THEN t.amount ELSE 0 END), 0)
    INTO
        total_customers,
        total_credit,
        total_payments
    FROM customer_credits cc
    LEFT JOIN transactions t ON cc.customer_id = t.customer_id AND cc.business_id = t.business_id
    WHERE cc.business_id = p_business_id;
    
    -- Get recent transactions
    SELECT 
        jsonb_agg(
            jsonb_build_object(
                'id', t.id,
                'customer_name', c.name,
                'amount', t.amount,
                'transaction_type', t.transaction_type,
                'created_at', t.created_at
            )
        )
    INTO recent_transactions
    FROM transactions t
    JOIN customers c ON t.customer_id = c.id
    WHERE t.business_id = p_business_id
    ORDER BY t.created_at DESC
    LIMIT 10;
    
    -- Build summary object
    customer_summary := jsonb_build_object(
        'total_customers', total_customers,
        'total_credit', total_credit,
        'total_payments', total_payments
    );
    
    -- Return combined data
    RETURN jsonb_build_object(
        'business', business_info,
        'summary', customer_summary,
        'recent_transactions', COALESCE(recent_transactions, '[]'::jsonb)
    );
END;
$$;

-- Update customer details
CREATE OR REPLACE FUNCTION update_customer(
    p_customer_id UUID,
    p_name TEXT,
    p_phone_number TEXT,
    p_email TEXT,
    p_address TEXT,
    p_notes TEXT
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    UPDATE customers
    SET name = COALESCE(p_name, name),
        phone_number = COALESCE(p_phone_number, phone_number),
        email = COALESCE(p_email, email),
        address = COALESCE(p_address, address),
        notes = COALESCE(p_notes, notes),
        updated_at = NOW()
    WHERE id = p_customer_id;
    
    IF FOUND THEN
        RETURN jsonb_build_object(
            'success', true,
            'message', 'Customer updated successfully'
        );
    ELSE
        RETURN jsonb_build_object(
            'success', false,
            'message', 'Customer not found'
        );
    END IF;
END;
$$;

-- Update business details
CREATE OR REPLACE FUNCTION update_business(
    p_business_id UUID,
    p_name TEXT,
    p_description TEXT,
    p_address TEXT,
    p_business_phone TEXT,
    p_business_email TEXT
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    UPDATE businesses
    SET name = COALESCE(p_name, name),
        description = COALESCE(p_description, description),
        address = COALESCE(p_address, address),
        business_phone = COALESCE(p_business_phone, business_phone),
        business_email = COALESCE(p_business_email, business_email),
        updated_at = NOW()
    WHERE id = p_business_id;
    
    IF FOUND THEN
        RETURN jsonb_build_object(
            'success', true,
            'message', 'Business updated successfully'
        );
    ELSE
        RETURN jsonb_build_object(
            'success', false,
            'message', 'Business not found'
        );
    END IF;
END;
$$;

-- Reset password function
CREATE OR REPLACE FUNCTION reset_password(
    p_phone_number TEXT,
    p_user_type TEXT,
    p_new_password TEXT
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    hashed_password TEXT;
BEGIN
    -- Validate inputs
    IF p_phone_number IS NULL OR p_phone_number = '' THEN
        RETURN jsonb_build_object(
            'success', false,
            'message', 'Phone number is required'
        );
    END IF;
    
    IF p_user_type IS NULL OR p_user_type = '' OR 
       p_user_type NOT IN ('business', 'customer') THEN
        RETURN jsonb_build_object(
            'success', false,
            'message', 'Valid user type (business or customer) is required'
        );
    END IF;
    
    IF p_new_password IS NULL OR p_new_password = '' THEN
        RETURN jsonb_build_object(
            'success', false,
            'message', 'New password is required'
        );
    END IF;
    
    -- Hash the password
    hashed_password := crypt(p_new_password, gen_salt('bf'));
    
    -- Update the password
    UPDATE users
    SET password_hash = hashed_password,
        updated_at = NOW()
    WHERE phone_number = p_phone_number AND user_type = p_user_type;
    
    IF FOUND THEN
        RETURN jsonb_build_object(
            'success', true,
            'message', 'Password reset successfully'
        );
    ELSE
        RETURN jsonb_build_object(
            'success', false,
            'message', 'User not found'
        );
    END IF;
END;
$$; 