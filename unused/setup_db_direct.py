import os
import requests
import json
import uuid
from datetime import datetime

# Supabase credentials
SUPABASE_URL = "https://ghbmfgomnqmffixfkdyp.supabase.co"
SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdoYm1mZ29tbnFtZmZpeGZrZHlwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0NzE0MDE1NywiZXhwIjoyMDYyNzE2MTU3fQ.RnbSqdIM5A67NuKHDOTdpqpu6G2zKJfhMeQapGUI2kw"

# Headers for SQL execution in Supabase
headers = {
    "apikey": SERVICE_KEY,
    "Authorization": f"Bearer {SERVICE_KEY}",
    "Content-Type": "application/json"
}

# Direct API headers for table operations
api_headers = {
    "apikey": SERVICE_KEY,
    "Authorization": f"Bearer {SERVICE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

def check_tables_exist():
    """
    Check if the tables already exist in the database
    """
    print("Checking if tables exist...")
    
    # Try to access each table and check the result
    tables = ['users', 'businesses', 'customers', 'customer_credits', 'transactions']
    table_status = {}
    
    for table in tables:
        try:
            # Use the REST API to check if the table is accessible
            response = requests.get(
                f"{SUPABASE_URL}/rest/v1/{table}?limit=1",
                headers=api_headers
            )
            table_status[table] = response.status_code < 300
            print(f"Table '{table}' exists: {table_status[table]} (Status: {response.status_code})")
        except Exception as e:
            print(f"Error checking table '{table}': {str(e)}")
            table_status[table] = False
    
    return table_status

def create_sample_data():
    """
    Create sample business and customer users with relationship
    """
    print("\nCreating sample data...")
    
    # Create sample business user
    business_user_id = str(uuid.uuid4())
    business_user = {
        "id": business_user_id,
        "name": "Sample Business",
        "phone_number": "1234567890",
        "password": "password123",
        "user_type": "business",
        "created_at": datetime.now().isoformat()
    }
    
    business_id = str(uuid.uuid4())
    business = {
        "id": business_id,
        "user_id": business_user_id,
        "name": "Sample Business Account",
        "description": "Test business account",
        "access_pin": "1234",
        "created_at": datetime.now().isoformat()
    }
    
    # Create sample customer user
    customer_user_id = str(uuid.uuid4())
    customer_user = {
        "id": customer_user_id,
        "name": "Sample Customer",
        "phone_number": "0987654321",
        "password": "password123",
        "user_type": "customer",
        "created_at": datetime.now().isoformat()
    }
    
    customer_id = str(uuid.uuid4())
    customer = {
        "id": customer_id,
        "user_id": customer_user_id,
        "name": "Sample Customer",
        "phone_number": "0987654321",
        "created_at": datetime.now().isoformat()
    }
    
    # Create relationship between business and customer
    credit_id = str(uuid.uuid4())
    credit = {
        "id": credit_id,
        "business_id": business_id,
        "customer_id": customer_id,
        "current_balance": 500,
        "created_at": datetime.now().isoformat()
    }
    
    # Insert data using REST API
    entities = [
        {"table": "users", "data": business_user, "description": "business user"},
        {"table": "businesses", "data": business, "description": "business record"},
        {"table": "users", "data": customer_user, "description": "customer user"},
        {"table": "customers", "data": customer, "description": "customer record"},
        {"table": "customer_credits", "data": credit, "description": "customer credit"}
    ]
    
    for entity in entities:
        try:
            # First try to delete existing record to avoid conflicts
            delete_url = f"{SUPABASE_URL}/rest/v1/{entity['table']}?id=eq.{entity['data']['id']}"
            requests.delete(delete_url, headers=api_headers)
            
            # Insert the new record
            insert_url = f"{SUPABASE_URL}/rest/v1/{entity['table']}"
            response = requests.post(insert_url, headers=api_headers, json=entity['data'])
            
            if response.status_code < 300:
                print(f"✅ Created {entity['description']} successfully")
            else:
                print(f"❌ Failed to create {entity['description']}: {response.status_code}")
                print(response.text)
        except Exception as e:
            print(f"❌ Error creating {entity['description']}: {str(e)}")

def update_rls_policies():
    """
    Update RLS policies to allow public access
    """
    print("\nUpdating Row Level Security policies...")
    
    # SQL to update RLS policies
    rls_sql = """
    -- Users table
    ALTER TABLE users ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS "Public users access" ON users;
    CREATE POLICY "Public users access" ON users FOR ALL USING (true);

    -- Businesses table
    ALTER TABLE businesses ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS "Public businesses access" ON businesses;
    CREATE POLICY "Public businesses access" ON businesses FOR ALL USING (true);

    -- Customers table
    ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS "Public customers access" ON customers;
    CREATE POLICY "Public customers access" ON customers FOR ALL USING (true);

    -- Customer_credits table
    ALTER TABLE customer_credits ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS "Public customer_credits access" ON customer_credits;
    CREATE POLICY "Public customer_credits access" ON customer_credits FOR ALL USING (true);

    -- Transactions table
    ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS "Public transactions access" ON transactions;
    CREATE POLICY "Public transactions access" ON transactions FOR ALL USING (true);
    """
    
    try:
        response = requests.post(
            f"{SUPABASE_URL}/rest/v1/rpc/exec_sql",
            headers=headers,
            json={"query": rls_sql}
        )
        
        if response.status_code < 300:
            print("✅ RLS policies updated successfully")
        else:
            print(f"❌ Failed to update RLS policies: {response.status_code}")
            print(response.text)
            
            # Try to create the exec_sql function if it doesn't exist
            if response.status_code == 404:
                print("Creating SQL execution function...")
                exec_sql_function = """
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
                
                try:
                    create_response = requests.post(
                        f"{SUPABASE_URL}/sql",
                        headers=headers,
                        data=exec_sql_function
                    )
                    
                    if create_response.status_code < 300:
                        print("✅ SQL execution function created")
                        print("Trying to update RLS policies again...")
                        
                        # Try again with the RLS SQL
                        retry_response = requests.post(
                            f"{SUPABASE_URL}/rest/v1/rpc/exec_sql",
                            headers=headers,
                            json={"query": rls_sql}
                        )
                        
                        if retry_response.status_code < 300:
                            print("✅ RLS policies updated successfully")
                        else:
                            print(f"❌ Still failed to update RLS policies: {retry_response.status_code}")
                            print(retry_response.text)
                    else:
                        print(f"❌ Failed to create SQL execution function: {create_response.status_code}")
                        print(create_response.text)
                except Exception as e:
                    print(f"❌ Error creating SQL execution function: {str(e)}")
    except Exception as e:
        print(f"❌ Error updating RLS policies: {str(e)}")

def check_access():
    """
    Check if we can access the tables with the public RLS policies
    """
    print("\nTesting table access...")
    
    tables = ['users', 'businesses', 'customers', 'customer_credits', 'transactions']
    
    for table in tables:
        try:
            response = requests.get(
                f"{SUPABASE_URL}/rest/v1/{table}?limit=10",
                headers={
                    "apikey": SERVICE_KEY,
                    "Authorization": f"Bearer {SERVICE_KEY}",
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code < 300:
                records = response.json()
                print(f"✅ Successfully accessed {table} table: {len(records)} records")
            else:
                print(f"❌ Failed to access {table} table: {response.status_code}")
                print(response.text)
        except Exception as e:
            print(f"❌ Error accessing {table} table: {str(e)}")

def main():
    """
    Main function to set up the database
    """
    print("🔄 Starting database setup...")
    
    # Check if tables exist
    tables_exist = check_tables_exist()
    
    # Update RLS policies
    update_rls_policies()
    
    # Create sample data
    create_sample_data()
    
    # Check access
    check_access()
    
    print("\n🏁 Setup complete! You can now use the app with these credentials:")
    print("Business: Phone: 1234567890, Password: password123")
    print("Customer: Phone: 0987654321, Password: password123")

if __name__ == "__main__":
    main() 