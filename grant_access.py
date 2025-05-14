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

# Headers for API requests
headers = {
    'apikey': supabase_service_key,
    'Authorization': f'Bearer {supabase_service_key}',
    'Content-Type': 'application/json'
}

# SQL commands to grant permissions
sql_commands = [
    # Grant access to anon and authenticated roles
    "GRANT ALL ON TABLE users TO anon, authenticated;",
    "GRANT ALL ON TABLE businesses TO anon, authenticated;",
    "GRANT ALL ON TABLE customers TO anon, authenticated;",
    "GRANT ALL ON TABLE customer_credits TO anon, authenticated;",
    "GRANT ALL ON TABLE transactions TO anon, authenticated;",
    
    # Ensure public can access these tables
    "GRANT ALL ON TABLE users TO public;",
    "GRANT ALL ON TABLE businesses TO public;",
    "GRANT ALL ON TABLE customers TO public;",
    "GRANT ALL ON TABLE customer_credits TO public;",
    "GRANT ALL ON TABLE transactions TO public;",
    
    # Make sure sequences are accessible 
    "GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated, public;",
    
    # Double-check RLS is disabled
    "ALTER TABLE users DISABLE ROW LEVEL SECURITY;",
    "ALTER TABLE businesses DISABLE ROW LEVEL SECURITY;",
    "ALTER TABLE customers DISABLE ROW LEVEL SECURITY;",
    "ALTER TABLE customer_credits DISABLE ROW LEVEL SECURITY;",
    "ALTER TABLE transactions DISABLE ROW LEVEL SECURITY;"
]

# Execute each SQL command
print("🔄 Granting access permissions...")

for i, sql in enumerate(sql_commands):
    print(f"\nExecuting SQL command #{i+1}: {sql}")
    
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

print("\n✅ Permissions updated!")
print("Now restart your application and try using it with Supabase.") 