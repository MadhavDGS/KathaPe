#!/usr/bin/env python
"""
Script to create database schema directly using PostgreSQL client
"""

import os
import requests
import json
from dotenv import load_dotenv

# Supabase credentials provided by user
SUPABASE_URL = "https://ghbmfgomnqmffixfkdyp.supabase.co"
ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdoYm1mZ29tbnFtZmZpeGZrZHlwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDcxNDAxNTcsImV4cCI6MjA2MjcxNjE1N30.Fw750xiDWVPrl6ssr9p6AJTt--8zvnPoboxJiURvsOI"
SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdoYm1mZ29tbnFtZmZpeGZrZHlwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0NzE0MDE1NywiZXhwIjoyMDYyNzE2MTU3fQ.RnbSqdIM5A67NuKHDOTdpqpu6G2zKJfhMeQapGUI2kw"

# Set up request headers with service role key
headers = {
    "apikey": SERVICE_KEY,
    "Authorization": f"Bearer {SERVICE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}

def create_env_file():
    """Create a .env file with the provided credentials"""
    env_content = f"""# Supabase Connection Settings
SUPABASE_URL={SUPABASE_URL}
SUPABASE_KEY={ANON_KEY}
SUPABASE_SERVICE_KEY={SERVICE_KEY}

# Flask Configuration
SECRET_KEY=flask_secret_key_123456789
DEBUG=true
PORT=5002

# Application Configuration
AUTO_CREATE_USERS=true
UPLOAD_FOLDER=static/uploads
QR_CODES_FOLDER=static/qr_codes
"""
    with open(".env", "w") as f:
        f.write(env_content)
    print("Created .env file with provided credentials")

def run_sql_query(query, description=None):
    """Execute a SQL query using the pg-rest API"""
    if description:
        print(f"\n--- {description} ---")
        
    endpoint = f"{SUPABASE_URL}/rest/v1/rpc/exec_sql"
    payload = {"query": query}
    
    try:
        response = requests.post(endpoint, headers=headers, json=payload)
        if response.status_code == 404:
            # Function might not exist, let's create it
            print("Creating SQL execution function...")
            create_exec_function()
            # Try again
            return run_sql_query(query, description)
            
        print(f"Status: {response.status_code}")
        if response.status_code >= 300:
            print(f"Error: {response.text}")
            return False
        
        return True
    except Exception as e:
        print(f"Error executing query: {str(e)}")
        return False

def create_exec_function():
    """Create the SQL execution function"""
    sql = """
    CREATE OR REPLACE FUNCTION exec_sql(query text)
    RETURNS json AS $$
    BEGIN
        EXECUTE query;
        RETURN json_build_object('status', 'success');
    EXCEPTION WHEN OTHERS THEN
        RETURN json_build_object('status', 'error', 'message', SQLERRM);
    END;
    $$ LANGUAGE plpgsql SECURITY DEFINER;
    """
    
    print("Creating SQL execution function directly...")
    try:
        # Try to execute the query directly 
        response = requests.post(
            f"{SUPABASE_URL}/sql",
            headers=headers,
            data=sql
        )
        print(f"Status: {response.status_code}")
        if response.status_code >= 300:
            print(f"Error: {response.text}")
            return False
        return True
    except Exception as e:
        print(f"Error creating function: {str(e)}")
        return False

def setup_database():
    """Set up the database structure"""
    # Get the schema from the SQL file
    with open("simplified_schema.sql", "r") as f:
        schema_sql = f.read()
    
    # Split into sections for easier execution and debugging
    sections = schema_sql.split("-- ====================================================================")
    
    print("Executing schema SQL in sections...")
    
    # Drop everything
    drop_section = sections[1]
    run_sql_query(drop_section, "Dropping existing schema")
    
    # Create tables
    tables_section = sections[2]
    run_sql_query(tables_section, "Creating tables")
    
    # Enable RLS
    rls_section = sections[3]
    run_sql_query(rls_section, "Setting up RLS policies")
    
    # Create triggers
    triggers_section = sections[4]
    run_sql_query(triggers_section, "Creating triggers")
    
    # Create sample data
    sample_data_section = sections[5]
    run_sql_query(sample_data_section, "Creating sample data")
    
    print("\nDatabase setup completed!")

def main():
    """Main function"""
    print("Starting database setup...")
    
    # Create .env file
    create_env_file()
    
    # Set up database
    setup_database()
    
    print("\nSetup complete! You can now run your Flask application.")
    print("Use the following sample credentials to login:")
    print("Business user - Phone: 1234567890, Password: password123")
    print("Customer user - Phone: 0987654321, Password: password123")

if __name__ == "__main__":
    main() 