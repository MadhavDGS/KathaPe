#!/usr/bin/env python3
"""
Script to test Supabase connection and database access
"""
import os
import sys
import uuid
import requests
import traceback
from dotenv import load_dotenv
from supabase import create_client, Client

# Import helper functions
try:
    from db_helpers import safe_uuid, is_valid_uuid
except ImportError:
    # Define fallback functions if db_helpers not available
    def is_valid_uuid(value):
        if not value:
            return False
        try:
            uuid.UUID(str(value))
            return True
        except (ValueError, TypeError, AttributeError):
            return False
    
    def safe_uuid(id_value):
        if not id_value or not is_valid_uuid(id_value):
            print(f"WARNING: Invalid UUID {id_value}, generating new one")
            return str(uuid.uuid4())
        return str(id_value)

# Load environment variables
load_dotenv()

# Get Supabase details from environment variables
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: SUPABASE_URL and SUPABASE_KEY environment variables must be set.")
    print("Please run setup_supabase.py first.")
    sys.exit(1)

print(f"Supabase URL: {SUPABASE_URL}")
print(f"Supabase Key: {SUPABASE_KEY[:10]}...{SUPABASE_KEY[-5:]}")
if SUPABASE_SERVICE_KEY:
    print(f"Supabase Service Key: {SUPABASE_SERVICE_KEY[:10]}...{SUPABASE_SERVICE_KEY[-5:]}")
else:
    print("Warning: No Supabase Service Key found")

# Test Supabase client connection
print("\n--- Testing Supabase Client Connection ---")
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    response = supabase.table('users').select('*').limit(1).execute()
    print(f"✅ Supabase client connection successful")
    print(f"Users found: {len(response.data)}")
except Exception as e:
    print(f"❌ Supabase client connection failed: {str(e)}")
    traceback.print_exc()

# Test UUID handling
print("\n--- Testing UUID Handling ---")
try:
    # Generate a test UUID
    test_uuid = str(uuid.uuid4())
    print(f"Valid UUID: {test_uuid} -> {is_valid_uuid(test_uuid)}")
    
    # Test invalid values
    invalid_values = [None, "", "not-a-uuid", 12345]
    for val in invalid_values:
        safe_val = safe_uuid(val)
        print(f"Invalid value: {val} -> safe UUID: {safe_val}")
        
    print("✅ UUID handling test completed")
except Exception as e:
    print(f"❌ UUID handling test failed: {str(e)}")
    traceback.print_exc()

# Test direct REST API access with regular key
print("\n--- Testing REST API Access (regular key) ---")
headers = {
    'apikey': SUPABASE_KEY,
    'Authorization': f'Bearer {SUPABASE_KEY}',
    'Content-Type': 'application/json'
}

try:
    response = requests.get(
        f"{SUPABASE_URL}/rest/v1/users?limit=1",
        headers=headers
    )
    
    if response.status_code < 300:
        print(f"✅ REST API access successful with regular key")
        data = response.json()
        print(f"Users found: {len(data)}")
    else:
        print(f"❌ REST API access failed with regular key: {response.status_code} - {response.text}")
except Exception as e:
    print(f"❌ REST API access failed with regular key: {str(e)}")
    traceback.print_exc()

# Test direct REST API access with service key
if SUPABASE_SERVICE_KEY:
    print("\n--- Testing REST API Access (service key) ---")
    service_headers = {
        'apikey': SUPABASE_SERVICE_KEY,
        'Authorization': f'Bearer {SUPABASE_SERVICE_KEY}',
        'Content-Type': 'application/json'
    }

    try:
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/users?limit=1",
            headers=service_headers
        )
        
        if response.status_code < 300:
            print(f"✅ REST API access successful with service key")
            data = response.json()
            print(f"Users found: {len(data)}")
        else:
            print(f"❌ REST API access failed with service key: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ REST API access failed with service key: {str(e)}")
        traceback.print_exc()

# Test Auth API
print("\n--- Testing Auth API ---")
auth_headers = {
    'apikey': SUPABASE_SERVICE_KEY or SUPABASE_KEY,
    'Authorization': f'Bearer {SUPABASE_SERVICE_KEY or SUPABASE_KEY}',
    'Content-Type': 'application/json'
}

try:
    response = requests.get(
        f"{SUPABASE_URL}/auth/v1/admin/users?limit=1", 
        headers=auth_headers
    )
    
    if response.status_code < 300:
        print(f"✅ Auth API access successful")
        data = response.json()
        print(f"Auth users found: {len(data) if isinstance(data, list) else 'Unknown format'}")
    else:
        print(f"❌ Auth API access failed: {response.status_code} - {response.text}")
except Exception as e:
    print(f"❌ Auth API access failed: {str(e)}")
    traceback.print_exc()

# Test UUID with database query
print("\n--- Testing UUID with Database Query ---")
try:
    # Use a dummy UUID that should not exist
    dummy_uuid = safe_uuid(str(uuid.uuid4()))
    
    response = supabase.table('users').select('*').eq('id', dummy_uuid).execute()
    print(f"✅ UUID query test successful")
    print(f"Users found with dummy UUID: {len(response.data)}")
    
    # Test with None UUID (this should use safe_uuid internally)
    try:
        response = supabase.table('users').select('*').eq('id', None).execute()
        print(f"❌ Query with None UUID did not raise error (should have been caught)")
    except Exception as e:
        print(f"✅ Query with None UUID raised error as expected: {str(e)}")
except Exception as e:
    print(f"❌ UUID query test failed: {str(e)}")
    traceback.print_exc()

print("\nTest completed. If all tests passed, your Supabase configuration is correct.")
print("If any tests failed, please check your Supabase credentials and permissions.")
print("\nRecommendation: If you're still encountering UUID errors, add the following SQL function to your database:")
print("""
-- Run this in the Supabase SQL editor:
CREATE OR REPLACE FUNCTION safe_uuid(text)
RETURNS uuid AS $$
BEGIN
    BEGIN
        RETURN $1::uuid;
    EXCEPTION WHEN OTHERS THEN
        RETURN uuid_generate_v4();
    END;
END;
$$ LANGUAGE plpgsql;
""") 