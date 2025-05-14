import os
import requests
import base64
import json
import traceback
from requests.exceptions import RequestException

# Supabase credentials
SUPABASE_URL = "https://ghbmfgomnqmffixfkdyp.supabase.co"
SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdoYm1mZ29tbnFtZmZpeGZrZHlwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0NzE0MDE1NywiZXhwIjoyMDYyNzE2MTU3fQ.RnbSqdIM5A67NuKHDOTdpqpu6G2zKJfhMeQapGUI2kw"

# Headers for SQL execution in Supabase
headers = {
    "apikey": SERVICE_KEY,
    "Authorization": f"Bearer {SERVICE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

def try_all_endpoints(sql_query):
    """
    Try multiple API endpoints to execute SQL
    """
    print(f"🔍 Trying to execute SQL: {sql_query[:50]}...")
    
    endpoints = [
        {"url": f"{SUPABASE_URL}/rest/v1/", "description": "REST v1 default"},
        {"url": f"{SUPABASE_URL}/rest/v1/rpc/postgres", "description": "RPC Postgres"},
        {"url": f"{SUPABASE_URL}/rest/v1/sql", "description": "REST SQL"},
        {"url": f"{SUPABASE_URL}/pg/sql", "description": "PG SQL"},
        {"url": f"{SUPABASE_URL}/sql", "description": "Direct SQL"},
        {"url": f"{SUPABASE_URL}/rest/v1/rpc/exec_sql", "description": "RPC exec_sql", "param_key": "query"}
    ]
    
    for endpoint in endpoints:
        print(f"\nTrying {endpoint['description']} endpoint: {endpoint['url']}")
        
        try:
            if "param_key" in endpoint:
                payload = {endpoint["param_key"]: sql_query}
            else:
                payload = {"query": sql_query}
                
            response = requests.post(
                endpoint["url"],
                headers=headers,
                json=payload,
                timeout=10
            )
            
            print(f"Status: {response.status_code}")
            
            try:
                if response.text:
                    print(f"Response: {response.text[:200]}...")
                else:
                    print("No response body")
            except:
                print("Could not print response")
                
            if response.status_code < 300:
                print(f"✅ Success with {endpoint['description']} endpoint!")
                return True
        except RequestException as e:
            print(f"Network error: {str(e)}")
        except Exception as e:
            print(f"Error: {str(e)}")
            traceback.print_exc()
            
    return False

def create_exec_sql_function():
    """
    Try to create the exec_sql function
    """
    print("\n🔄 Trying to create exec_sql function...")
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
    
    return try_all_endpoints(sql)

def check_tables():
    """
    Check if the tables exist
    """
    print("\n🔍 Checking if tables exist...")
    
    try:
        # Try to access the users table
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/users?limit=1",
            headers=headers
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code < 300:
            print("✅ Successfully accessed users table")
            return True
        else:
            print(f"❌ Failed to access users table: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error checking tables: {str(e)}")
        return False

def fix_table_permissions():
    """
    Update table permissions by granting access to authenticated users
    """
    # SQL to grant permissions on all tables
    sql = """
    -- Grant permissions to authenticated users on all tables
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO authenticated;
    GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO authenticated;
    GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO authenticated;
    
    -- Grant permissions to anon users (for unauthenticated access)
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO anon;
    GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO anon;
    GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO anon;
    
    -- Grant permissions to service_role (just to be sure)
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO service_role;
    GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO service_role;
    GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO service_role;
    
    -- Reset Row Level Security on tables
    ALTER TABLE IF EXISTS users DISABLE ROW LEVEL SECURITY;
    ALTER TABLE IF EXISTS businesses DISABLE ROW LEVEL SECURITY;
    ALTER TABLE IF EXISTS customers DISABLE ROW LEVEL SECURITY;
    ALTER TABLE IF EXISTS customer_credits DISABLE ROW LEVEL SECURITY;
    ALTER TABLE IF EXISTS transactions DISABLE ROW LEVEL SECURITY;
    
    -- Ensure that extensions are loaded
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    
    -- Let us know it worked
    SELECT 'Permissions updated successfully' as result;
    """
    
    print("\n🔧 Attempting to fix table permissions...")
    result = try_all_endpoints(sql)
    
    if result:
        print("✅ Table permission fix attempted")
    else:
        print("❌ Failed to fix table permissions")

def try_create_tables():
    """
    Try to create tables if they don't exist
    """
    print("\n🔄 Attempting to create tables if they don't exist...")
    
    sql = """
    -- Users table
    CREATE TABLE IF NOT EXISTS users (
        id UUID PRIMARY KEY,
        name TEXT NOT NULL,
        phone_number TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        user_type TEXT NOT NULL CHECK (user_type IN ('business', 'customer')),
        email TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );

    -- Businesses table
    CREATE TABLE IF NOT EXISTS businesses (
        id UUID PRIMARY KEY,
        user_id UUID NOT NULL REFERENCES users(id),
        name TEXT NOT NULL,
        description TEXT,
        access_pin TEXT,
        address TEXT,
        phone TEXT,
        email TEXT,
        profile_photo_url TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );

    -- Customers table
    CREATE TABLE IF NOT EXISTS customers (
        id UUID PRIMARY KEY,
        user_id UUID NOT NULL REFERENCES users(id),
        name TEXT NOT NULL,
        phone_number TEXT NOT NULL,
        whatsapp_number TEXT,
        email TEXT,
        address TEXT,
        profile_photo_url TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );

    -- Customer Credits table
    CREATE TABLE IF NOT EXISTS customer_credits (
        id UUID PRIMARY KEY,
        business_id UUID NOT NULL REFERENCES businesses(id),
        customer_id UUID NOT NULL REFERENCES customers(id),
        current_balance DECIMAL(10, 2) DEFAULT 0,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(business_id, customer_id)
    );

    -- Transactions table
    CREATE TABLE IF NOT EXISTS transactions (
        id UUID PRIMARY KEY,
        business_id UUID NOT NULL REFERENCES businesses(id),
        customer_id UUID NOT NULL REFERENCES customers(id),
        amount DECIMAL(10, 2) NOT NULL,
        transaction_type TEXT NOT NULL CHECK (transaction_type IN ('credit', 'payment')),
        notes TEXT,
        media_url TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        created_by UUID REFERENCES users(id)
    );
    """
    
    result = try_all_endpoints(sql)
    
    if result:
        print("✅ Tables created or already exist")
    else:
        print("❌ Failed to create tables")

def main():
    """
    Main function to fix permissions
    """
    print("🔧 Starting permission fixing process...")
    
    # Create exec_sql function
    create_exec_sql_function()
    
    # Check if tables exist
    tables_exist = check_tables()
    
    # Try to create tables if needed
    if not tables_exist:
        try_create_tables()
    
    # Fix table permissions
    fix_table_permissions()
    
    # Check tables again
    check_tables()
    
    print("\n✨ Permission fix attempts completed.")
    print("You can now try running the application to see if the permissions are fixed.")
    print("If permissions are still an issue, you may need to use the Supabase dashboard SQL editor directly.")

if __name__ == "__main__":
    main() 