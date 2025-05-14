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

if not supabase_url or not supabase_key or not supabase_service_key:
    print("Error: Supabase credentials not found in .env file.")
    exit(1)

# Method 1: Directly access the table via REST API
def direct_table_access():
    print("\n=== Testing Direct Table Access ===")
    headers = {
        'apikey': supabase_key,
        'Authorization': f'Bearer {supabase_key}'
    }
    
    try:
        response = requests.get(
            f"{supabase_url}/rest/v1/users?select=*&limit=1",
            headers=headers
        )
        
        if response.status_code == 200:
            print("✅ Success! Direct table access worked.")
            print(f"Response: {response.json()}")
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"❌ Exception: {str(e)}")

# Method 2: Using service role key (if not working with anon key)
def service_role_access():
    print("\n=== Testing Service Role Access ===")
    headers = {
        'apikey': supabase_service_key,
        'Authorization': f'Bearer {supabase_service_key}'
    }
    
    try:
        response = requests.get(
            f"{supabase_url}/rest/v1/users?select=*&limit=1",
            headers=headers
        )
        
        if response.status_code == 200:
            print("✅ Success! Service role access worked.")
            print(f"Response: {response.json()}")
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"❌ Exception: {str(e)}")

# Method 3: Create a user directly
def create_test_user():
    print("\n=== Testing User Creation ===")
    headers = {
        'apikey': supabase_service_key,
        'Authorization': f'Bearer {supabase_service_key}',
        'Content-Type': 'application/json'
    }
    
    import uuid
    user_id = str(uuid.uuid4())
    
    user_data = {
        "id": user_id,
        "name": "Test User",
        "phone_number": f"test{uuid.uuid4().hex[:8]}",
        "user_type": "customer",
        "password": "test123",
        "created_at": "2023-01-01T00:00:00Z"
    }
    
    try:
        response = requests.post(
            f"{supabase_url}/rest/v1/users",
            headers=headers,
            json=user_data
        )
        
        if response.status_code < 300:
            print("✅ Success! User creation worked.")
            print(f"Response: {response.json() if response.text else 'No content'}")
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"❌ Exception: {str(e)}")

# Method 4: Disable RLS directly
def disable_rls():
    print("\n=== Testing RLS Disabling ===")
    headers = {
        'apikey': supabase_service_key,
        'Authorization': f'Bearer {supabase_service_key}',
        'Content-Type': 'application/json'
    }
    
    # Try to create or use the exec_sql function
    try:
        response = requests.post(
            f"{supabase_url}/rest/v1/rpc/exec_sql_noreturn",
            headers=headers,
            json={"query": "ALTER TABLE users DISABLE ROW LEVEL SECURITY;"}
        )
        
        if response.status_code < 300:
            print("✅ Success! RLS disabling worked through exec_sql_noreturn function.")
            print(f"Response: {response.json() if response.text else 'No content'}")
        else:
            print(f"❌ Error with exec_sql_noreturn: {response.status_code}")
            print(f"Response: {response.text}")
            
            # Try with exec_sql instead
            print("\nTrying with exec_sql function instead...")
            response = requests.post(
                f"{supabase_url}/rest/v1/rpc/exec_sql",
                headers=headers,
                json={"query": "SELECT 'Disabling RLS'; ALTER TABLE users DISABLE ROW LEVEL SECURITY;"}
            )
            
            if response.status_code < 300:
                print("✅ Success! RLS disabling worked through exec_sql function.")
                print(f"Response: {response.json() if response.text else 'No content'}")
            else:
                print(f"❌ Error with exec_sql: {response.status_code}")
                print(f"Response: {response.text}")
                
                # The function might not exist yet
                print("\nFunction might not exist. Check Supabase dashboard to create the exec_sql functions.")
    
    except Exception as e:
        print(f"❌ Exception: {str(e)}")

if __name__ == "__main__":
    print("🔄 Testing Supabase connection and RLS issues...")
    direct_table_access()
    service_role_access()
    create_test_user()
    disable_rls()
    
    print("\n=== Summary ===")
    print("If all methods failed, you need to:")
    print("1. Go to your Supabase dashboard (https://app.supabase.com)")
    print("2. Open the SQL Editor")
    print("3. Run the SQL in create_exec_sql_function.sql or create_exec_sql_selectable_function.sql")
    print("4. Then run the SQL in supabase_setup.sql")
    
    print("\nAfter doing that, run this script again to check if RLS has been disabled properly.") 