#!/usr/bin/env python3
import os
import requests
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get Supabase credentials
supabase_url = os.getenv('SUPABASE_URL')
supabase_service_key = os.getenv('SUPABASE_SERVICE_KEY')

if not supabase_url or not supabase_service_key:
    print("Error: Supabase credentials not found in .env file.")
    exit(1)

# Headers for REST API calls
headers = {
    'apikey': supabase_service_key,
    'Authorization': f'Bearer {supabase_service_key}',
    'Content-Type': 'application/json',
    'Prefer': 'return=representation'
}

def exec_sql(query):
    """Execute an SQL query via Supabase REST API"""
    rpc_url = f"{supabase_url}/rest/v1/rpc/exec_sql"
    
    try:
        response = requests.post(
            rpc_url,
            headers=headers,
            json={"query": query},
            timeout=20
        )
        
        if response.status_code < 300:
            return response.json(), True
        else:
            print(f"❌ SQL Error: {response.status_code} - {response.text}")
            return None, False
    except Exception as e:
        print(f"❌ Error executing SQL: {str(e)}")
        return None, False

def check_table_exists(table_name):
    """Check if the table exists in the database"""
    sql_query = f"""
    SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = '{table_name}'
    );
    """
    
    result, success = exec_sql(sql_query)
    
    if success and result and len(result) > 0 and 'exists' in result[0]:
        return result[0]['exists']
    return False

# Database schema for Katha application
schema = [
    # Users table
    """
    CREATE TABLE IF NOT EXISTS users (
        id UUID PRIMARY KEY,
        name TEXT NOT NULL,
        phone_number TEXT UNIQUE NOT NULL,
        email TEXT,
        user_type TEXT NOT NULL CHECK (user_type IN ('business', 'customer')),
        password TEXT NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """,
    
    # Businesses table
    """
    CREATE TABLE IF NOT EXISTS businesses (
        id UUID PRIMARY KEY,
        user_id UUID NOT NULL REFERENCES users(id),
        name TEXT NOT NULL,
        description TEXT,
        address TEXT,
        phone TEXT,
        email TEXT,
        access_pin TEXT,
        profile_photo_url TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """,
    
    # Customers table
    """
    CREATE TABLE IF NOT EXISTS customers (
        id UUID PRIMARY KEY,
        user_id UUID NOT NULL REFERENCES users(id),
        name TEXT NOT NULL,
        phone_number TEXT NOT NULL,
        whatsapp_number TEXT,
        email TEXT,
        address TEXT,
        notes TEXT,
        profile_photo_url TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """,
    
    # Customer Credits table
    """
    CREATE TABLE IF NOT EXISTS customer_credits (
        id UUID PRIMARY KEY,
        customer_id UUID NOT NULL REFERENCES customers(id),
        business_id UUID NOT NULL REFERENCES businesses(id),
        current_balance NUMERIC(10, 2) DEFAULT 0,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(customer_id, business_id)
    );
    """,
    
    # Transactions table
    """
    CREATE TABLE IF NOT EXISTS transactions (
        id UUID PRIMARY KEY,
        customer_id UUID NOT NULL REFERENCES customers(id),
        business_id UUID NOT NULL REFERENCES businesses(id),
        amount NUMERIC(10, 2) NOT NULL,
        transaction_type TEXT NOT NULL CHECK (transaction_type IN ('credit', 'payment')),
        notes TEXT,
        media_url TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        created_by UUID REFERENCES users(id)
    );
    """
]

# Disable RLS statements
disable_rls = [
    "ALTER TABLE users DISABLE ROW LEVEL SECURITY;",
    "ALTER TABLE businesses DISABLE ROW LEVEL SECURITY;",
    "ALTER TABLE customers DISABLE ROW LEVEL SECURITY;",
    "ALTER TABLE customer_credits DISABLE ROW LEVEL SECURITY;",
    "ALTER TABLE transactions DISABLE ROW LEVEL SECURITY;"
]

# Create triggers to update balance on transactions
transaction_trigger = """
CREATE OR REPLACE FUNCTION update_balance_on_transaction()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.transaction_type = 'credit' THEN
        UPDATE customer_credits
        SET current_balance = current_balance + NEW.amount,
            updated_at = CURRENT_TIMESTAMP
        WHERE customer_id = NEW.customer_id AND business_id = NEW.business_id;
    ELSIF NEW.transaction_type = 'payment' THEN
        UPDATE customer_credits
        SET current_balance = current_balance - NEW.amount,
            updated_at = CURRENT_TIMESTAMP
        WHERE customer_id = NEW.customer_id AND business_id = NEW.business_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_balance_trigger ON transactions;

CREATE TRIGGER update_balance_trigger
AFTER INSERT ON transactions
FOR EACH ROW
EXECUTE FUNCTION update_balance_on_transaction();
"""

# Main execution
print("🔄 Checking connection to Supabase...")
result, success = exec_sql("SELECT current_database();")

if success:
    db_name = result[0]['current_database']
    print(f"✅ Successfully connected to Supabase database: {db_name}")
else:
    print("❌ Failed to connect to Supabase database.")
    exit(1)

print("\n🔄 Creating database tables...")

# Create tables
for i, sql in enumerate(schema):
    table_name = sql.strip().split('CREATE TABLE IF NOT EXISTS ')[1].split(' ')[0]
    print(f"Creating table: {table_name}...")
    
    result, success = exec_sql(sql)
    
    if success:
        print(f"✅ Table {table_name} created or already exists.")
    else:
        print(f"❌ Failed to create table {table_name}.")

# Allow a moment for tables to be fully created
time.sleep(1)

print("\n🔄 Disabling Row Level Security (RLS) for all tables...")
for sql in disable_rls:
    table_name = sql.split('ALTER TABLE ')[1].split(' ')[0]
    
    if check_table_exists(table_name):
        result, success = exec_sql(sql)
        
        if success:
            print(f"✅ RLS disabled for table: {table_name}")
        else:
            print(f"❌ Failed to disable RLS for table: {table_name}")
    else:
        print(f"⚠️ Table {table_name} does not exist, skipping RLS configuration.")

print("\n🔄 Creating transaction trigger for automatic balance updates...")
result, success = exec_sql(transaction_trigger)

if success:
    print("✅ Transaction trigger created successfully.")
else:
    print("❌ Failed to create transaction trigger.")

print("\n✅ Database initialization complete!")
print("You can now run the application and it should connect to your Supabase database.") 