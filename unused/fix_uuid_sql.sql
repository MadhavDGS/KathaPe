-- SQL script to add a safe_uuid function to the database
-- This function will handle invalid UUIDs and return a new UUID instead of failing
-- Run this script in the Supabase SQL Editor

-- Make sure UUID extension is enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create a function to safely handle UUIDs
CREATE OR REPLACE FUNCTION safe_uuid(text)
RETURNS uuid AS $$
BEGIN
    BEGIN
        -- Try to convert the text to a UUID
        RETURN $1::uuid;
    EXCEPTION WHEN OTHERS THEN
        -- If it fails, generate a new UUID
        RETURN uuid_generate_v4();
    END;
END;
$$ LANGUAGE plpgsql;

-- Test the function
DO $$
DECLARE
    test_result uuid;
    valid_uuid text := '123e4567-e89b-12d3-a456-426655440000';
    invalid_uuid text := 'not-a-uuid';
    null_uuid text := NULL;
BEGIN
    -- Test with valid UUID
    test_result := safe_uuid(valid_uuid);
    RAISE NOTICE 'Valid UUID result: %', test_result;
    
    -- Test with invalid UUID
    test_result := safe_uuid(invalid_uuid);
    RAISE NOTICE 'Invalid UUID result: %', test_result;
    
    -- Test with NULL
    test_result := safe_uuid(null_uuid);
    RAISE NOTICE 'NULL UUID result: %', test_result;
END $$;

-- Create function to update tables with invalid UUIDs
CREATE OR REPLACE FUNCTION replace_invalid_uuids()
RETURNS text AS $$
DECLARE
    table_rec RECORD;
    column_rec RECORD;
    row_count integer := 0;
    total_count integer := 0;
    query text;
BEGIN
    -- Loop through all tables
    FOR table_rec IN 
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
    LOOP
        -- Loop through columns that might contain UUIDs
        FOR column_rec IN 
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = table_rec.table_name
            AND (data_type = 'uuid' OR column_name = 'id' OR column_name LIKE '%_id')
        LOOP
            -- Check if it's a UUID column
            BEGIN
                -- Update rows with invalid UUIDs
                query := 'UPDATE ' || table_rec.table_name || 
                         ' SET ' || column_rec.column_name || ' = safe_uuid(' || 
                         column_rec.column_name || '::text) ' ||
                         'WHERE ' || column_rec.column_name || ' IS NOT NULL AND ' ||
                         column_rec.column_name || '::text NOT SIMILAR TO ' ||
                         '''[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}''';
                
                EXECUTE query;
                GET DIAGNOSTICS row_count = ROW_COUNT;
                
                IF row_count > 0 THEN
                    RAISE NOTICE 'Fixed % invalid UUIDs in %.%', 
                        row_count, table_rec.table_name, column_rec.column_name;
                    total_count := total_count + row_count;
                END IF;
            EXCEPTION 
                WHEN OTHERS THEN
                    RAISE NOTICE 'Error checking %.%: %', 
                        table_rec.table_name, column_rec.column_name, SQLERRM;
            END;
        END LOOP;
    END LOOP;
    
    RETURN 'Fixed ' || total_count || ' invalid UUIDs';
END
$$ LANGUAGE plpgsql;

-- Run the function to fix any existing invalid UUIDs
SELECT replace_invalid_uuids(); 