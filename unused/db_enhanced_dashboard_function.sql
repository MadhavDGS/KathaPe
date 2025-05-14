-- Enhanced business dashboard function to include access_pin
CREATE OR REPLACE FUNCTION get_business_dashboard_enhanced(p_business_id UUID)
RETURNS JSONB AS $$
DECLARE
    business_data JSONB;
    summary_data JSONB;
    transaction_data JSONB;
    result JSONB;
BEGIN
    -- Get business details
    SELECT jsonb_build_object(
        'name', b.name,
        'description', b.description,
        'address', b.address,
        'access_pin', b.access_pin,
        'business_phone', b.business_phone,
        'business_email', b.business_email,
        'profile_photo_url', b.logo_url
    ) INTO business_data
    FROM businesses b
    WHERE b.id = p_business_id;

    -- Get summary data
    SELECT jsonb_build_object(
        'total_customers', (SELECT COUNT(*) FROM customer_credits WHERE business_id = p_business_id),
        'total_credit', COALESCE((
            SELECT SUM(amount)
            FROM transactions
            WHERE business_id = p_business_id
            AND transaction_type = 'credit'
        ), 0),
        'total_payments', COALESCE((
            SELECT SUM(amount)
            FROM transactions
            WHERE business_id = p_business_id
            AND transaction_type = 'payment'
        ), 0)
    ) INTO summary_data;

    -- Get recent transactions
    SELECT jsonb_agg(t)
    FROM (
        SELECT 
            t.id,
            t.amount,
            t.transaction_type,
            t.notes,
            t.created_at,
            c.name as customer_name
        FROM transactions t
        JOIN customers c ON c.id = t.customer_id
        WHERE t.business_id = p_business_id
        ORDER BY t.created_at DESC
        LIMIT 10
    ) t INTO transaction_data;

    -- Build final result
    result := jsonb_build_object(
        'business', business_data,
        'summary', summary_data,
        'transactions', COALESCE(transaction_data, '[]'::jsonb)
    );

    RETURN result;
END;
$$ LANGUAGE plpgsql; 