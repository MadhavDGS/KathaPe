#!/usr/bin/env python
"""
Script to check Supabase permissions using raw SQL.
This will help identify if your service role key has proper permissions.
"""

import os
from dotenv import load_dotenv
import requests
import json
import base64

# Load environment variables
load_dotenv()

# Get Supabase credentials
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_SERVICE_KEY')  # Use service role key for full access

if not supabase_url or not supabase_key:
    print("ERROR: Missing Supabase credentials in .env file")
    exit(1)

# Function to decode JWT and check role
def decode_jwt(token):
    try:
        # Split the token
        parts = token.split('.')
        if len(parts) != 3:
            return None
        
        # Get the payload part (second part)
        payload_base64 = parts[1]
        
        # Add padding if necessary
        padding = '=' * (4 - len(payload_base64) % 4) if len(payload_base64) % 4 != 0 else ''
        payload_base64 += padding
        
        # Decode base64
        payload_json = base64.b64decode(payload_base64.encode('utf-8')).decode('utf-8')
        payload = json.loads(payload_json)
        
        return payload
    except Exception as e:
        print(f"Error decoding JWT: {str(e)}")
        return None

# Decode the JWT and check role
payload = decode_jwt(supabase_key)
is_service_role = payload and payload.get('role') == 'service_role'

print(f"JWT Payload: {json.dumps(payload, indent=2)}")
print(f"Is service role: {is_service_role}")

# Set up headers for API request
headers = {
    'apikey': supabase_key,
    'Authorization': f'Bearer {supabase_key}',
    'Content-Type': 'application/json',
    'Prefer': 'return=representation'
}

# Function to execute a raw SQL query
def execute_sql(query):
    endpoint = f"{supabase_url}/rest/v1/rpc/execute_sql"
    payload = {'query': query}
    
    try:
        response = requests.post(endpoint, headers=headers, json=payload)
        if response.status_code != 200:
            print(f"Error executing query: {response.status_code} - {response.text}")
            return None
        return response.json()
    except Exception as e:
        print(f"Error executing query: {str(e)}")
        return None

# Try to create the execute_sql function if it doesn't exist
create_function_sql = """
CREATE OR REPLACE FUNCTION execute_sql(query text) RETURNS json AS $$
DECLARE
    result json;
BEGIN
    EXECUTE query INTO result;
    RETURN result;
EXCEPTION WHEN OTHERS THEN
    RETURN json_build_object('error', SQLERRM);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
"""

# First, try to directly create our SQL execution function
print("Attempting to create SQL execution function...")
endpoint = f"{supabase_url}/rest/v1/sql"
response = requests.post(endpoint, headers=headers, data=create_function_sql)
print(f"Response: {response.status_code} - {response.text}")

# If that fails, try to check if we can read tables directly
print("\nAttempting to query tables directly...")
try:
    # Try to query users table
    users_endpoint = f"{supabase_url}/rest/v1/users?select=*"
    users_response = requests.get(users_endpoint, headers=headers)
    print(f"Users table query: {users_response.status_code}")
    if users_response.status_code == 200:
        print(f"SUCCESS! Found {len(users_response.json())} users.")
    else:
        print(f"Error querying users: {users_response.text}")
    
    # Try to query schema information using pg_tables
    sql_endpoint = f"{supabase_url}/rest/v1/rpc/execute"
    payload = {
        "sql": "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
    }
    schema_response = requests.post(sql_endpoint, headers=headers, json=payload)
    print(f"Schema query: {schema_response.status_code}")
    if schema_response.status_code == 200:
        print(f"SUCCESS! Schema information: {schema_response.text}")
    else:
        print(f"Error querying schema: {schema_response.text}")

except Exception as e:
    print(f"Error querying tables: {str(e)}")

print("\n=== DIAGNOSTIC INFORMATION ===")
print(f"Supabase URL: {supabase_url}")
if payload:
    print(f"Key type: {'Service Role Key' if is_service_role else 'Anon Key'}")
    print(f"Role from JWT: {payload.get('role')}")
print(f"Key length: {len(supabase_key)} characters")
print("=== END DIAGNOSTIC INFORMATION ===")

print("\nSUGGESTED ACTIONS:")
print("1. Run the simplified_schema.sql script in Supabase SQL editor")
print("2. Verify you're using the service role key, not the anon key")
print("3. Check if your Supabase project has the correct permissions setup") 