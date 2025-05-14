import os
import requests
import json

SUPABASE_URL = 'https://ghbmfgomnqmffixfkdyp.supabase.co'
SERVICE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdoYm1mZ29tbnFtZmZpeGZrZHlwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0NzE0MDE1NywiZXhwIjoyMDYyNzE2MTU3fQ.RnbSqdIM5A67NuKHDOTdpqpu6G2zKJfhMeQapGUI2kw'

headers = {
    'apikey': SERVICE_KEY,
    'Authorization': f'Bearer {SERVICE_KEY}',
    'Content-Type': 'application/json',
    'Prefer': 'return=minimal'
}

with open('simplified_schema.sql', 'r') as f:
    sql = f.read()

# Split the SQL into sections for easier execution
sections = sql.split("-- ====================================================================")

# Execute each section separately
for i, section in enumerate(sections[1:], 1):  # Skip the first empty section
    section_name = section.strip().split('\n')[0]
    print(f"Executing section {i}: {section_name}")
    
    # Prepare the query
    data = {
        "query": section
    }
    
    # Execute the query using the SQL endpoint
    response = requests.post(
        f'{SUPABASE_URL}/rest/v1/rpc/exec_sql',
        headers=headers,
        json=data
    )
    
    print(f'Response: {response.status_code}')
    print(response.text)
    
    # If the function doesn't exist, create it
    if response.status_code == 404:
        print("Creating SQL execution function...")
        
        create_func_sql = """
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
        
        # Execute the SQL directly
        direct_response = requests.post(
            f'{SUPABASE_URL}/sql',
            headers=headers,
            data=create_func_sql
        )
        
        print(f'Function creation response: {direct_response.status_code}')
        print(direct_response.text)
        
        # Try executing the section again
        response = requests.post(
            f'{SUPABASE_URL}/rest/v1/rpc/exec_sql',
            headers=headers,
            json=data
        )
        
        print(f'Response after function creation: {response.status_code}')
        print(response.text)

print("Schema execution completed!") 