-- Add missing columns to the customers table
ALTER TABLE IF EXISTS customers 
ADD COLUMN IF NOT EXISTS address TEXT,
ADD COLUMN IF NOT EXISTS notes TEXT,
ADD COLUMN IF NOT EXISTS profile_photo_url TEXT;

-- Add missing columns to the customer_credits table
ALTER TABLE IF EXISTS customer_credits
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
ADD COLUMN IF NOT EXISTS last_transaction_date TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS last_reminder_date TIMESTAMP WITH TIME ZONE;

-- Add missing columns to the transactions table
ALTER TABLE IF EXISTS transactions
ADD COLUMN IF NOT EXISTS created_by UUID,
ADD COLUMN IF NOT EXISTS media_url TEXT,
ADD COLUMN IF NOT EXISTS notes TEXT;

-- Add trigger for automatically updating the updated_at timestamp
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Add trigger to customer_credits table for updated_at
DROP TRIGGER IF EXISTS update_customer_credits_timestamp ON customer_credits;
CREATE TRIGGER update_customer_credits_timestamp
BEFORE UPDATE ON customer_credits
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();

-- Make sure customer_credits enforces unique business-customer relationships
CREATE UNIQUE INDEX IF NOT EXISTS unique_business_customer_idx ON customer_credits (business_id, customer_id);

-- Function to update credit balance when a transaction is added
CREATE OR REPLACE FUNCTION update_customer_credit_balance()
RETURNS TRIGGER AS $$
BEGIN
    -- Update the balance in customer_credits table
    IF NEW.transaction_type = 'credit' THEN
        -- Credit transaction (business gives credit to customer, balance increases)
        UPDATE customer_credits
        SET current_balance = current_balance + NEW.amount,
            last_transaction_date = CURRENT_TIMESTAMP
        WHERE business_id = NEW.business_id AND customer_id = NEW.customer_id;
    ELSIF NEW.transaction_type = 'payment' THEN
        -- Payment transaction (customer pays back, balance decreases)
        UPDATE customer_credits
        SET current_balance = current_balance - NEW.amount,
            last_transaction_date = CURRENT_TIMESTAMP
        WHERE business_id = NEW.business_id AND customer_id = NEW.customer_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Add trigger to automatically update balances after transactions
DROP TRIGGER IF EXISTS update_balance_trigger ON transactions;
CREATE TRIGGER update_balance_trigger
AFTER INSERT ON transactions
FOR EACH ROW
EXECUTE FUNCTION update_customer_credit_balance();

-- Function to ensure customer_credits entries persist and are unique
CREATE OR REPLACE FUNCTION ensure_customer_credit()
RETURNS TRIGGER AS $$
BEGIN
    -- If a row doesn't exist yet, insert it
    IF NOT EXISTS (
        SELECT 1 FROM customer_credits 
        WHERE business_id = NEW.business_id AND customer_id = NEW.customer_id
    ) THEN
        INSERT INTO customer_credits (
            id, business_id, customer_id, current_balance, created_at, updated_at, last_transaction_date
        ) VALUES (
            gen_random_uuid(), NEW.business_id, NEW.customer_id, 
            CASE WHEN NEW.transaction_type = 'credit' THEN NEW.amount ELSE -NEW.amount END,
            CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Add trigger to transactions table to ensure customer_credits entries exist
DROP TRIGGER IF EXISTS ensure_customer_credit_trigger ON transactions;
CREATE TRIGGER ensure_customer_credit_trigger
BEFORE INSERT ON transactions
FOR EACH ROW
EXECUTE FUNCTION ensure_customer_credit();

-- Add function to update reminder date
CREATE OR REPLACE FUNCTION update_reminder_date()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE customer_credits
    SET last_reminder_date = CURRENT_TIMESTAMP
    WHERE business_id = NEW.business_id AND customer_id = NEW.customer_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create reminders table for tracking reminders sent
CREATE TABLE IF NOT EXISTS reminders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL,
    customer_id UUID NOT NULL,
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    sent_by UUID, -- user who sent the reminder
    reminder_type TEXT DEFAULT 'whatsapp',
    message TEXT,
    FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
);

-- Add trigger to update reminder date when reminder is sent
CREATE TRIGGER update_reminder_date_trigger
AFTER INSERT ON reminders
FOR EACH ROW
EXECUTE FUNCTION update_reminder_date(); 