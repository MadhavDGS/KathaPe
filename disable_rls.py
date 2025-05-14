#!/usr/bin/env python3
import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get Supabase credentials
supabase_url = os.getenv('SUPABASE_URL')
supabase_service_key = os.getenv('SUPABASE_SERVICE_KEY')

if not supabase_url or not supabase_service_key:
    print("Error: Supabase credentials not found in .env file.")
    exit(1)

# List of tables to disable RLS for
tables = ['users', 'businesses', 'customers', 'customer_credits', 'transactions']

# Headers for REST API calls
headers = {
    'apikey': supabase_service_key,
    'Authorization': f'Bearer {supabase_service_key}',
    'Content-Type': 'application/json',
    'Prefer': 'return=representation'
}

def disable_rls_for_table(table_name):
    """Disable RLS for a specific table using PostgreSQL query"""
    rpc_url = f"{supabase_url}/rest/v1/rpc/exec_sql"
    
    sql_query = f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY;"
    
    try:
        response = requests.post(
            rpc_url,
            headers=headers,
            json={"query": sql_query},
            timeout=10
        )
        
        if response.status_code < 300:
            print(f"✅ Successfully disabled RLS for table: {table_name}")
            return True
        else:
            print(f"❌ Failed to disable RLS for table: {table_name}")
            print(f"   Error: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error disabling RLS for table {table_name}: {str(e)}")
        return False

def check_table_exists(table_name):
    """Check if the table exists in the database"""
    rpc_url = f"{supabase_url}/rest/v1/rpc/exec_sql"
    
    sql_query = f"""
    SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = '{table_name}'
    );
    """
    
    try:
        response = requests.post(
            rpc_url,
            headers=headers,
            json={"query": sql_query},
            timeout=10
        )
        
        if response.status_code < 300:
            result = response.json()
            if result and len(result) > 0 and 'exists' in result[0]:
                return result[0]['exists']
        return False
    except Exception as e:
        print(f"❌ Error checking if table {table_name} exists: {str(e)}")
        return False

# Main execution
print("🔄 Checking connection to Supabase...")
try:
    # Test connection
    test_query = "SELECT current_database();"
    response = requests.post(
        f"{supabase_url}/rest/v1/rpc/exec_sql",
        headers=headers,
        json={"query": test_query},
        timeout=10
    )
    
    if response.status_code < 300:
        db_name = response.json()[0]['current_database']
        print(f"✅ Successfully connected to Supabase database: {db_name}")
    else:
        print(f"❌ Failed to connect to Supabase. Error: {response.status_code} - {response.text}")
        exit(1)
except Exception as e:
    print(f"❌ Error connecting to Supabase: {str(e)}")
    exit(1)

print("\n🔄 Disabling RLS for all tables...")

# Disable RLS for each table
for table in tables:
    # Check if table exists
    if check_table_exists(table):
        disable_rls_for_table(table)
    else:
        print(f"⚠️ Table '{table}' does not exist in the database.")

print("\n✅ Done!")
print("Note: You may need to create the tables if they don't exist yet. Check the Supabase dashboard for more details.") 