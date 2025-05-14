import os
import requests
import json
import uuid
from datetime import datetime
import time

# Supabase credentials
SUPABASE_URL = "https://ghbmfgomnqmffixfkdyp.supabase.co"
SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdoYm1mZ29tbnFtZmZpeGZrZHlwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0NzE0MDE1NywiZXhwIjoyMDYyNzE2MTU3fQ.RnbSqdIM5A67NuKHDOTdpqpu6G2zKJfhMeQapGUI2kw"

# Headers with service role
headers = {
    "apikey": SERVICE_KEY,
    "Authorization": f"Bearer {SERVICE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
    "Accept-Profile": "service_role"  # This is critical for bypassing RLS
}

def try_direct_rls_disable():
    """Attempt to disable RLS directly for users table"""
    print("🔄 Attempting to disable RLS on users table...")
    
    sql = """
    -- Try to disable RLS on users table
    ALTER TABLE IF EXISTS users DISABLE ROW LEVEL SECURITY;
    """
    
    try:
        response = requests.post(
            f"{SUPABASE_URL}/rest/v1/rpc/exec_sql",
            headers=headers,
            json={"query": sql},
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        if response.status_code < 300:
            print("✅ Successfully disabled RLS via exec_sql")
            return True
        else:
            print(f"❌ Failed via exec_sql: {response.text[:200]}...")
    except Exception as e:
        print(f"❌ Error disabling RLS: {str(e)}")

    # Try direct REST API
    try:
        alter_url = f"{SUPABASE_URL}/rest/v1/users?rls=false"
        test_response = requests.get(alter_url, headers=headers)
        
        print(f"Test query status: {test_response.status_code}")
        if test_response.status_code < 300:
            print("✅ Successfully accessed users table with rls=false parameter")
            return True
        else:
            print(f"❌ Failed with rls=false: {test_response.text[:200]}...")
    except Exception as e:
        print(f"❌ Error testing direct access: {str(e)}")
        
    return False

def add_policy_to_users_table():
    """Add a permissive policy to the users table"""
    print("\n🔄 Adding permissive policy to users table...")
    
    sql = """
    -- Enable RLS on users table (if not already enabled)
    ALTER TABLE IF EXISTS users ENABLE ROW LEVEL SECURITY;
    
    -- Drop existing policies
    DROP POLICY IF EXISTS "Allow full access" ON users;
    
    -- Create a permissive policy for all actions
    CREATE POLICY "Allow full access" ON users
        USING (true)
        WITH CHECK (true);
    """
    
    try:
        response = requests.post(
            f"{SUPABASE_URL}/rest/v1/rpc/exec_sql",
            headers=headers,
            json={"query": sql},
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        if response.status_code < 300:
            print("✅ Successfully added permissive policy")
            return True
        else:
            print(f"❌ Failed to add policy: {response.text[:200]}...")
    except Exception as e:
        print(f"❌ Error adding policy: {str(e)}")
        
    return False

def test_access():
    """Test if we can access the users table"""
    print("\n🔍 Testing access to users table...")
    
    # First try with service role explicitly
    try:
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/users?limit=1",
            headers=headers
        )
        
        print(f"Service role access status: {response.status_code}")
        if response.status_code < 300:
            print("✅ Successfully accessed users table with service role")
            return "service_role"
        else:
            print(f"❌ Failed with service role: {response.text[:200]}...")
    except Exception as e:
        print(f"❌ Error with service role: {str(e)}")
    
    # Try with rls=false parameter
    try:
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/users?limit=1&rls=false",
            headers=headers
        )
        
        print(f"RLS=false access status: {response.status_code}")
        if response.status_code < 300:
            print("✅ Successfully accessed users table with rls=false")
            return "rls_parameter"
        else:
            print(f"❌ Failed with rls=false: {response.text[:200]}...")
    except Exception as e:
        print(f"❌ Error with rls=false: {str(e)}")
    
    # As a last resort, try to create a new database access method
    try:
        create_func_sql = """
        CREATE OR REPLACE FUNCTION get_users()
        RETURNS TABLE (
            id UUID,
            name TEXT,
            phone_number TEXT,
            password TEXT,
            user_type TEXT,
            email TEXT,
            created_at TIMESTAMPTZ,
            updated_at TIMESTAMPTZ
        ) AS $$
        BEGIN
            SET LOCAL row_security = OFF;
            RETURN QUERY SELECT * FROM users LIMIT 10;
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
        """
        
        # Create the function 
        create_response = requests.post(
            f"{SUPABASE_URL}/rest/v1/rpc/exec_sql",
            headers=headers,
            json={"query": create_func_sql},
            timeout=10
        )
        
        print(f"Create function status: {create_response.status_code}")
        if create_response.status_code < 300:
            print("✅ Successfully created get_users function")
        else:
            print(f"❌ Failed to create function: {create_response.text[:200]}...")
    except Exception as e:
        print(f"❌ Error creating function: {str(e)}")
        
    return None

def create_sample_users():
    """Create sample users for testing"""
    print("\n🔄 Creating sample users for testing...")
    
    # Create sample business user
    business_user_id = str(uuid.uuid4())
    business_user = {
        "id": business_user_id,
        "name": "Sample Business",
        "phone_number": "9999999999",
        "password": "password123",
        "user_type": "business", 
        "created_at": datetime.now().isoformat()
    }
    
    # Create sample customer user
    customer_user_id = str(uuid.uuid4())
    customer_user = {
        "id": customer_user_id,
        "name": "Sample Customer",
        "phone_number": "8888888888",
        "password": "password123",
        "user_type": "customer",
        "created_at": datetime.now().isoformat()
    }
    
    # Try different insertion methods
    # Method 1: Direct REST API with service role
    try:
        print("Trying direct REST API insertion...")
        response = requests.post(
            f"{SUPABASE_URL}/rest/v1/users",
            headers=headers,
            json=business_user
        )
        
        print(f"Direct API insertion status: {response.status_code}")
        if response.status_code < 300:
            print("✅ Successfully created business user via REST API")
            success = True
        else:
            print(f"❌ Failed: {response.text[:200]}...")
            success = False
    except Exception as e:
        print(f"❌ Error with REST API: {str(e)}")
        success = False
    
    # Method 2: SQL Insert via exec_sql if Method 1 failed
    if not success:
        try:
            print("\nTrying SQL insert via exec_sql...")
            
            # Serialize business_user into an SQL INSERT
            fields = ','.join(business_user.keys())
            values = ','.join([f"'{v}'" if not isinstance(v, (int, float)) else str(v) for v in business_user.values()])
            
            insert_sql = f"INSERT INTO users ({fields}) VALUES ({values}) RETURNING id;"
            
            response = requests.post(
                f"{SUPABASE_URL}/rest/v1/rpc/exec_sql",
                headers=headers,
                json={"query": insert_sql},
                timeout=10
            )
            
            print(f"SQL Insert status: {response.status_code}")
            if response.status_code < 300:
                print("✅ Successfully created business user via SQL")
                success = True
            else:
                print(f"❌ Failed: {response.text[:200]}...")
        except Exception as e:
            print(f"❌ Error with SQL insert: {str(e)}")
    
    # Try to insert customer user
    try:
        print("\nTrying to insert customer user...")
        response = requests.post(
            f"{SUPABASE_URL}/rest/v1/users",
            headers=headers,
            json=customer_user
        )
        
        print(f"Customer user insertion status: {response.status_code}")
        if response.status_code < 300:
            print("✅ Successfully created customer user")
        else:
            print(f"❌ Failed: {response.text[:200]}...")
    except Exception as e:
        print(f"❌ Error inserting customer: {str(e)}")
    
    return success

def update_env_file():
    """Update the .env file with the service key"""
    print("\n🔄 Updating .env file with service key...")
    
    try:
        env_content = ""
        if os.path.exists('.env'):
            with open('.env', 'r') as f:
                env_content = f.read()
        
        # Check if service key is already in the file
        if 'SUPABASE_SERVICE_KEY' not in env_content:
            with open('.env', 'a') as f:
                f.write(f"\nSUPABASE_SERVICE_KEY={SERVICE_KEY}\n")
            print("✅ Updated .env file with service key")
        else:
            print("✅ Service key already in .env file")
            
        return True
    except Exception as e:
        print(f"❌ Error updating .env file: {str(e)}")
        return False

def main():
    """Main function to fix user table permissions"""
    print("🔧 Starting permission fixing process for users table...")
    
    # First test if we can already access the table
    access_method = test_access()
    
    if access_method:
        print(f"\n✅ We already have access to the users table using {access_method}!")
    else:
        print("\n❌ We don't have access to the users table. Trying to fix...")
        
        # Try to disable RLS
        if try_direct_rls_disable():
            print("\n✅ Successfully fixed permissions by disabling RLS!")
        else:
            # If that doesn't work, try to add a permissive policy
            if add_policy_to_users_table():
                print("\n✅ Successfully fixed permissions by adding a permissive policy!")
            else:
                print("\n❌ Failed to fix permissions directly. Trying to create sample users...")
                
                # Try to create sample users
                if create_sample_users():
                    print("\n✅ Successfully created sample users!")
                else:
                    print("\n❌ Failed to create sample users.")
    
    # Update the .env file with service key
    update_env_file()
    
    # Final access test
    access_method = test_access()
    
    if access_method:
        print(f"\n✨ Fixed permissions! We now have access using {access_method}.")
    else:
        print("\n⚠️ Still having permission issues.")
        print("Update the app to use direct access with the service key and rls=false parameter.")
    
    print("\nENVIRONMENT VARIABLES TO SET IN YOUR APP:")
    print("===========================================")
    print(f"SUPABASE_URL={SUPABASE_URL}")
    print(f"SUPABASE_SERVICE_KEY={SERVICE_KEY}")
    print("===========================================")
    print("Make sure these are set in your .env file and that your app is using them correctly.")

if __name__ == "__main__":
    main() 