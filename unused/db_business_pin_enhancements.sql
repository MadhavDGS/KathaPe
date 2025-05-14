-- Ensure PIN is generated for all businesses
-- First add a function to generate random 4-digit PINs

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

-- Add trigger to automatically generate PIN when creating a business if none is provided
CREATE OR REPLACE FUNCTION ensure_business_pin()
RETURNS TRIGGER AS $$
BEGIN
    -- If access_pin is NULL or empty, generate one
    IF NEW.access_pin IS NULL OR NEW.access_pin = '' THEN
        NEW.access_pin := generate_business_access_pin();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop the trigger if it exists
DROP TRIGGER IF EXISTS ensure_business_pin_trigger ON businesses;

-- Create the trigger
CREATE TRIGGER ensure_business_pin_trigger
BEFORE INSERT OR UPDATE ON businesses
FOR EACH ROW
EXECUTE FUNCTION ensure_business_pin();

-- Update any existing businesses that don't have PINs
UPDATE businesses
SET access_pin = generate_business_access_pin()
WHERE access_pin IS NULL OR access_pin = ''; 