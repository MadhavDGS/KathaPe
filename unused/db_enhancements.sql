-- Add support for media attachments, profile photos, and WhatsApp integration

-- Add WhatsApp number to customers table
ALTER TABLE customers ADD COLUMN whatsapp_number TEXT;
ALTER TABLE customers ADD COLUMN profile_photo_url TEXT;

-- Add profile photo to businesses table
ALTER TABLE businesses ADD COLUMN profile_photo_url TEXT;

-- Create media attachments table for transaction receipts
CREATE TABLE media_attachments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    transaction_id UUID REFERENCES transactions(id) ON DELETE CASCADE,
    media_type TEXT NOT NULL, -- 'image', 'pdf', etc.
    media_url TEXT NOT NULL,
    thumbnail_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES users(id) ON DELETE SET NULL
);

-- Enable Row Level Security for media_attachments
ALTER TABLE media_attachments ENABLE ROW LEVEL SECURITY;

-- Create policies for media_attachments
CREATE POLICY "Business owners can view attachments" ON media_attachments
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM transactions t
            JOIN businesses b ON t.business_id = b.id
            WHERE t.id = media_attachments.transaction_id
            AND b.user_id = auth.uid()
        )
    );

CREATE POLICY "Customers can view their attachments" ON media_attachments
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM transactions t
            JOIN customers c ON t.customer_id = c.id
            WHERE t.id = media_attachments.transaction_id
            AND c.user_id = auth.uid()
        )
    );

-- Enhanced transaction function with media attachment support
CREATE OR REPLACE FUNCTION add_transaction_with_media(
    p_business_id UUID,
    p_customer_id UUID,
    p_amount DECIMAL,
    p_transaction_type TEXT,
    p_notes TEXT,
    p_created_by UUID,
    p_media_url TEXT DEFAULT NULL,
    p_media_type TEXT DEFAULT 'image'
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    new_transaction_id UUID;
    new_media_id UUID;
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
    
    -- Add media attachment if provided
    IF p_media_url IS NOT NULL AND p_media_url != '' THEN
        INSERT INTO media_attachments (
            transaction_id,
            media_type,
            media_url,
            created_at,
            created_by
        )
        VALUES (
            new_transaction_id,
            p_media_type,
            p_media_url,
            NOW(),
            p_created_by
        )
        RETURNING id INTO new_media_id;
    END IF;
    
    -- Return success result
    RETURN jsonb_build_object(
        'success', true,
        'transaction_id', new_transaction_id,
        'media_id', new_media_id,
        'message', 'Transaction added successfully'
    );
END;
$$;

-- Function to update profile photo
CREATE OR REPLACE FUNCTION update_user_profile_photo(
    p_user_id UUID,
    p_photo_url TEXT
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    user_type TEXT;
    result JSONB;
BEGIN
    -- Find user type
    SELECT user_type INTO user_type FROM users WHERE id = p_user_id;
    
    IF user_type IS NULL THEN
        RETURN jsonb_build_object(
            'success', false,
            'message', 'User not found'
        );
    END IF;
    
    -- Update photo based on user type
    IF user_type = 'business' THEN
        UPDATE businesses 
        SET profile_photo_url = p_photo_url
        WHERE user_id = p_user_id;
    ELSIF user_type = 'customer' THEN
        UPDATE customers 
        SET profile_photo_url = p_photo_url
        WHERE user_id = p_user_id;
    END IF;
    
    RETURN jsonb_build_object(
        'success', true,
        'message', 'Profile photo updated successfully'
    );
END;
$$;

-- Enhanced function to get customer details with transactions and media
CREATE OR REPLACE FUNCTION get_customer_details_enhanced(
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
            'whatsapp_number', c.whatsapp_number,
            'email', c.email,
            'address', c.address,
            'notes', c.notes,
            'profile_photo_url', c.profile_photo_url,
            'current_balance', COALESCE(cc.current_balance, 0),
            'created_at', c.created_at
        )
    INTO customer_info
    FROM customers c
    LEFT JOIN customer_credits cc ON c.id = cc.customer_id AND cc.business_id = p_business_id
    WHERE c.id = p_customer_id;
    
    -- Get transaction history with media attachments
    SELECT 
        jsonb_agg(
            jsonb_build_object(
                'id', t.id,
                'amount', t.amount,
                'transaction_type', t.transaction_type,
                'notes', t.notes,
                'created_at', t.created_at,
                'created_by_name', u.name,
                'media_attachments', (
                    SELECT jsonb_agg(
                        jsonb_build_object(
                            'id', ma.id,
                            'media_type', ma.media_type,
                            'media_url', ma.media_url,
                            'thumbnail_url', ma.thumbnail_url
                        )
                    )
                    FROM media_attachments ma
                    WHERE ma.transaction_id = t.id
                )
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

-- Get enhanced business dashboard with photo URLs
CREATE OR REPLACE FUNCTION get_business_dashboard_enhanced(
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
            'logo_url', b.logo_url,
            'profile_photo_url', b.profile_photo_url
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
    
    -- Get recent transactions with customer photos
    SELECT 
        jsonb_agg(
            jsonb_build_object(
                'id', t.id,
                'customer_id', c.id,
                'customer_name', c.name,
                'customer_photo_url', c.profile_photo_url,
                'amount', t.amount,
                'transaction_type', t.transaction_type,
                'created_at', t.created_at,
                'has_media', EXISTS (
                    SELECT 1 FROM media_attachments ma WHERE ma.transaction_id = t.id
                )
            )
        )
    INTO recent_transactions
    FROM transactions t
    JOIN customers c ON t.customer_id = c.id
    WHERE t.business_id = p_business_id
    ORDER BY t.created_at DESC
    LIMIT 20;
    
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

-- Function to generate WhatsApp reminder link
CREATE OR REPLACE FUNCTION generate_whatsapp_reminder(
    p_business_id UUID,
    p_customer_id UUID
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    customer_name TEXT;
    business_name TEXT;
    whatsapp_number TEXT;
    balance DECIMAL;
    reminder_message TEXT;
    whatsapp_link TEXT;
BEGIN
    -- Get required information
    SELECT 
        c.name, 
        COALESCE(c.whatsapp_number, c.phone_number),
        b.name,
        COALESCE(cc.current_balance, 0)
    INTO
        customer_name,
        whatsapp_number,
        business_name,
        balance
    FROM customers c
    JOIN businesses b ON b.id = p_business_id
    LEFT JOIN customer_credits cc ON cc.customer_id = c.id AND cc.business_id = p_business_id
    WHERE c.id = p_customer_id;
    
    -- Create reminder message
    reminder_message := 'Hi ' || customer_name || ', this is a reminder that you have an outstanding balance of ₹' || 
                        balance || ' at ' || business_name || '. Please clear your dues at your earliest convenience. Thank you.';
    
    -- Generate WhatsApp link
    -- Remove any non-numeric characters from phone number
    whatsapp_number := regexp_replace(whatsapp_number, '[^0-9]', '', 'g');
    
    -- If number doesn't start with country code, add India's country code
    IF NOT whatsapp_number ~ '^91' THEN
        whatsapp_number := '91' || whatsapp_number;
    END IF;
    
    whatsapp_link := 'https://wa.me/' || whatsapp_number || '?text=' || 
                    replace(reminder_message, ' ', '%20');
    
    RETURN jsonb_build_object(
        'success', true,
        'whatsapp_link', whatsapp_link,
        'customer_name', customer_name,
        'balance', balance,
        'message', 'WhatsApp reminder link generated successfully'
    );
END;
$$;

-- Enhanced function for business customers list with balance and photo
CREATE OR REPLACE FUNCTION get_business_customers_enhanced(
    p_business_id UUID
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    customers_list JSONB;
BEGIN
    SELECT 
        jsonb_agg(
            jsonb_build_object(
                'id', c.id,
                'name', c.name,
                'phone_number', c.phone_number,
                'whatsapp_number', c.whatsapp_number,
                'profile_photo_url', c.profile_photo_url,
                'current_balance', COALESCE(cc.current_balance, 0),
                'last_transaction', (
                    SELECT jsonb_build_object(
                        'amount', t.amount,
                        'transaction_type', t.transaction_type,
                        'created_at', t.created_at
                    )
                    FROM transactions t
                    WHERE t.customer_id = c.id AND t.business_id = p_business_id
                    ORDER BY t.created_at DESC
                    LIMIT 1
                )
            )
        )
    INTO customers_list
    FROM customers c
    JOIN customer_credits cc ON c.id = cc.customer_id
    WHERE cc.business_id = p_business_id
    ORDER BY c.name;
    
    RETURN jsonb_build_object(
        'success', true,
        'customers', COALESCE(customers_list, '[]'::jsonb),
        'count', jsonb_array_length(COALESCE(customers_list, '[]'::jsonb))
    );
END;
$$; 