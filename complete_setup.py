#!/usr/bin/env python3
import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get Supabase credentials
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')
supabase_service_key = os.getenv('SUPABASE_SERVICE_KEY')

if not supabase_url or not supabase_service_key:
    print("Error: Supabase credentials not found in .env file.")
    exit(1)

# Headers for API requests
headers = {
    'apikey': supabase_service_key,
    'Authorization': f'Bearer {supabase_service_key}',
    'Content-Type': 'application/json'
}

# SQL commands to run
sql_commands = [
    # Disable RLS for tables
    "ALTER TABLE IF EXISTS users DISABLE ROW LEVEL SECURITY;",
    "ALTER TABLE IF EXISTS businesses DISABLE ROW LEVEL SECURITY;",
    "ALTER TABLE IF EXISTS customers DISABLE ROW LEVEL SECURITY;",
    "ALTER TABLE IF EXISTS customer_credits DISABLE ROW LEVEL SECURITY;",
    "ALTER TABLE IF EXISTS transactions DISABLE ROW LEVEL SECURITY;",
    
    # Create tables
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
    
    """
    CREATE TABLE IF NOT EXISTS businesses (
        id UUID PRIMARY KEY,
        user_id UUID NOT NULL,
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
    
    """
    CREATE TABLE IF NOT EXISTS customers (
        id UUID PRIMARY KEY,
        user_id UUID NOT NULL,
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
    
    """
    CREATE TABLE IF NOT EXISTS customer_credits (
        id UUID PRIMARY KEY,
        customer_id UUID NOT NULL,
        business_id UUID NOT NULL,
        current_balance NUMERIC(10, 2) DEFAULT 0,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(customer_id, business_id)
    );
    """,
    
    """
    CREATE TABLE IF NOT EXISTS transactions (
        id UUID PRIMARY KEY,
        customer_id UUID NOT NULL,
        business_id UUID NOT NULL,
        amount NUMERIC(10, 2) NOT NULL,
        transaction_type TEXT NOT NULL CHECK (transaction_type IN ('credit', 'payment')),
        notes TEXT,
        media_url TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        created_by UUID
    );
    """,
    
    # Create trigger for transaction balance updates
    """
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
    """,
    
    "DROP TRIGGER IF EXISTS update_balance_trigger ON transactions;",
    
    """
    CREATE TRIGGER update_balance_trigger
    AFTER INSERT ON transactions
    FOR EACH ROW
    EXECUTE FUNCTION update_balance_on_transaction();
    """
]

# Execute each SQL command
print("🔄 Running complete Supabase setup...")

for i, sql in enumerate(sql_commands):
    print(f"\nExecuting SQL command #{i+1}...")
    
    try:
        response = requests.post(
            f"{supabase_url}/rest/v1/rpc/exec_sql_noreturn",
            headers=headers,
            json={"query": sql}
        )
        
        if response.status_code < 300:
            result = response.json()
            if result.get('success', False):
                print("✅ Success!")
            else:
                print(f"❌ Error: {result.get('error', 'Unknown error')}")
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"❌ Exception: {str(e)}")

print("\n✅ Setup complete!")
print("Now restart your application and try using it with Supabase.") 