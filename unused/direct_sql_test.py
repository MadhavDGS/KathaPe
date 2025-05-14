#!/usr/bin/env python
"""
Test script that uses direct SQL queries to bypass ORM and RLS.
"""

import os
from dotenv import load_dotenv
import requests
import json
import uuid

# Load environment variables
load_dotenv()

# Get Supabase credentials
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

# Set up headers for API request
headers = {
    'apikey': SUPABASE_SERVICE_KEY,
    'Authorization': f'Bearer {SUPABASE_SERVICE_KEY}',
    'Content-Type': 'application/json',
    'Prefer': 'return=representation'
}

def run_sql(query, params=None):
    """Run a SQL query directly against Supabase"""
    endpoint = f"{SUPABASE_URL}/rest/v1/rpc/exec_sql"
    payload = {"query": query}
    if params:
        payload["params"] = params
        
    print(f"Running SQL: {query}")
    
    try:
        response = requests.post(endpoint, headers=headers, json=payload)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 404:
            print("Function 'exec_sql' not found. Creating it...")
            create_function()
            return run_sql(query, params)
            
        if response.status_code != 200:
            print(f"Error: {response.text}")
            return None
            
        return response.json()
    except Exception as e:
        print(f"Error: {str(e)}")
        return None

def create_function():
    """Create the exec_sql function in the database"""
    endpoint = f"{SUPABASE_URL}/rest/v1/"
    
    # Use a special endpoint to create functions
    sql = """
    CREATE OR REPLACE FUNCTION exec_sql(query text, params jsonb DEFAULT NULL)
    RETURNS jsonb AS $$
    DECLARE
        result jsonb;
    BEGIN
        IF params IS NULL THEN
            EXECUTE query INTO result;
        ELSE
            EXECUTE query INTO result USING params;
        END IF;
        RETURN result;
    EXCEPTION WHEN OTHERS THEN
        RETURN jsonb_build_object('error', SQLERRM);
    END;
    $$ LANGUAGE plpgsql SECURITY DEFINER;
    """
    
    # Try to create the function directly
    try:
        # This will only work if you have sufficient permissions
        response = requests.post(
            f"{SUPABASE_URL}/sql",
            headers=headers, 
            data=sql
        )
        print(f"Create function status: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error creating function: {str(e)}")

def create_tables():
    """Create the tables directly using SQL"""
    # Drop existing tables
    run_sql("DROP SCHEMA public CASCADE;")
    run_sql("CREATE SCHEMA public;")
    run_sql("GRANT ALL ON SCHEMA public TO postgres;")
    run_sql("GRANT ALL ON SCHEMA public TO public;")
    
    # Create users table
    run_sql("""
    CREATE TABLE IF NOT EXISTS users (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        name TEXT NOT NULL,
        phone_number TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        user_type TEXT NOT NULL DEFAULT 'customer',
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # Grant permissions on users table
    run_sql("GRANT ALL ON users TO postgres;")
    run_sql("GRANT ALL ON users TO anon;")
    run_sql("GRANT ALL ON users TO authenticated;")
    run_sql("GRANT ALL ON users TO service_role;")
    
    # Create sample user
    user_id = str(uuid.uuid4())
    run_sql(f"""
    INSERT INTO users (id, name, phone_number, password, user_type)
    VALUES ('{user_id}', 'Test User', '1234567890', 'password123', 'customer');
    """)
    
    print(f"Created user with ID: {user_id}")
    
    return user_id

def check_auth(phone, password):
    """Check authentication for a user"""
    result = run_sql(f"""
    SELECT id, name, phone_number, user_type
    FROM users
    WHERE phone_number = '{phone}' AND password = '{password}';
    """)
    
    print(f"Auth result: {json.dumps(result, indent=2)}")
    return result

def main():
    """Main function"""
    print("=== DIRECT SQL TEST ===")
    
    # Create tables
    user_id = create_tables()
    
    # Check auth
    check_auth("1234567890", "password123")
    
    print("=== TEST COMPLETE ===")

if __name__ == "__main__":
    main() 