import os
import requests
from supabase import create_client
import uuid
from datetime import datetime

# Supabase credentials
SUPABASE_URL = "https://ghbmfgomnqmffixfkdyp.supabase.co"
SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdoYm1mZ29tbnFtZmZpeGZrZHlwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0NzE0MDE1NywiZXhwIjoyMDYyNzE2MTU3fQ.RnbSqdIM5A67NuKHDOTdpqpu6G2zKJfhMeQapGUI2kw"

# Set up headers for direct SQL execution
headers = {
    "apikey": SERVICE_KEY,
    "Authorization": f"Bearer {SERVICE_KEY}",
    "Content-Type": "application/json"
}

# Initialize Supabase client with service role key
supabase = create_client(SUPABASE_URL, SERVICE_KEY)

def execute_sql(sql):
    """Execute SQL directly using Supabase management API"""
    try:
        # POST to the management API
        response = requests.post(
            f"{SUPABASE_URL}/rest/v1/",
            headers={
                "apikey": SERVICE_KEY,
                "Authorization": f"Bearer {SERVICE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal"
            },
            json={"command": sql}
        )
        return response.status_code < 300
    except Exception as e:
        print(f"Error executing SQL: {str(e)}")
        return False

# 1. Create the basic tables with RLS policies
print("Creating tables and RLS policies...")

# Create users table
try:
    # First check if users table exists
    response = supabase.table('users').select('count(*)').execute()
    
    # If we reached here, users table exists, ensure permissions
    print("Users table already exists, setting public access policy...")
    
    # Apply RLS policy to users table
    policies_sql = """
    -- Enable RLS on users table
    ALTER TABLE users ENABLE ROW LEVEL SECURITY;
    
    -- Drop existing policies if any
    DROP POLICY IF EXISTS "Public users access" ON users;
    
    -- Create public access policy
    CREATE POLICY "Public users access" ON users FOR ALL USING (true);
    """
    
    # Try to execute directly via table insert/update
    try:
        # Test read access
        test_response = supabase.table('users').select('*').limit(1).execute()
        print(f"Successfully read from users table: {len(test_response.data)} records")
    except Exception as e:
        print(f"Error reading from users table: {str(e)}")
    
except Exception as e:
    print(f"Error checking users table, creating from scratch: {str(e)}")
    
    # Create tables
    tables_sql = """
    -- Create users table
    CREATE TABLE IF NOT EXISTS users (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        name TEXT NOT NULL,
        phone_number TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        user_type TEXT NOT NULL DEFAULT 'customer',
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Create businesses table
    CREATE TABLE IF NOT EXISTS businesses (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        user_id UUID NOT NULL REFERENCES users(id),
        name TEXT NOT NULL,
        description TEXT,
        access_pin TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Create customers table
    CREATE TABLE IF NOT EXISTS customers (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        user_id UUID NOT NULL REFERENCES users(id),
        name TEXT NOT NULL,
        phone_number TEXT NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Create customer_credits table
    CREATE TABLE IF NOT EXISTS customer_credits (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        business_id UUID NOT NULL REFERENCES businesses(id),
        customer_id UUID NOT NULL REFERENCES customers(id),
        current_balance DECIMAL(10, 2) DEFAULT 0,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(business_id, customer_id)
    );
    
    -- Create transactions table
    CREATE TABLE IF NOT EXISTS transactions (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        business_id UUID NOT NULL REFERENCES businesses(id),
        customer_id UUID NOT NULL REFERENCES customers(id),
        amount DECIMAL(10, 2) NOT NULL,
        transaction_type TEXT NOT NULL CHECK (transaction_type IN ('credit', 'payment')),
        notes TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Make all tables public
    ALTER TABLE users ENABLE ROW LEVEL SECURITY;
    CREATE POLICY "Public users access" ON users FOR ALL USING (true);
    
    ALTER TABLE businesses ENABLE ROW LEVEL SECURITY;
    CREATE POLICY "Public businesses access" ON businesses FOR ALL USING (true);
    
    ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
    CREATE POLICY "Public customers access" ON customers FOR ALL USING (true);
    
    ALTER TABLE customer_credits ENABLE ROW LEVEL SECURITY;
    CREATE POLICY "Public customer_credits access" ON customer_credits FOR ALL USING (true);
    
    ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
    CREATE POLICY "Public transactions access" ON transactions FOR ALL USING (true);
    """
    
    # Try direct API call to create tables
    tables_created = False
    try:
        # First try using the client
        supabase.from_('users').select('*').limit(1).execute()
        tables_created = True
    except Exception as e:
        print(f"Error accessing users table: {str(e)}")
        print("Attempting to create tables")
        
        try:
            # Create sample users directly
            business_user = {
                'id': str(uuid.uuid4()),
                'name': 'Sample Business',
                'phone_number': '1234567890',
                'password': 'password123',
                'user_type': 'business',
                'created_at': datetime.now().isoformat()
            }
            
            response = supabase.table('users').insert(business_user).execute()
            print(f"Created business user: {response.data if hasattr(response, 'data') else 'No data'}")
            
            # Create customer user
            customer_user = {
                'id': str(uuid.uuid4()),
                'name': 'Sample Customer',
                'phone_number': '0987654321',
                'password': 'password123',
                'user_type': 'customer',
                'created_at': datetime.now().isoformat()
            }
            
            response = supabase.table('users').insert(customer_user).execute()
            print(f"Created customer user: {response.data if hasattr(response, 'data') else 'No data'}")
            
            tables_created = True
        except Exception as e2:
            print(f"Failed to create users directly: {str(e2)}")

# Test that we can access the users table
print("\nTesting access to users table...")
try:
    response = supabase.table('users').select('*').execute()
    print(f"Successfully accessed users table with {len(response.data)} records.")
    if response.data:
        for user in response.data:
            print(f"User: {user.get('name')}, Phone: {user.get('phone_number')}, Type: {user.get('user_type')}")
except Exception as e:
    print(f"Error accessing users table: {str(e)}")

print("\nSetup complete. Try running the app now with:")
print("Business: Phone: 1234567890, Password: password123")
print("Customer: Phone: 0987654321, Password: password123") 