import os
import requests
from requests.exceptions import RequestException
import json
import time

# Supabase credentials - use environment variables if possible
SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://ghbmfgomnqmffixfkdyp.supabase.co')
SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdoYm1mZ29tbnFtZmZpeGZrZHlwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0NzE0MDE1NywiZXhwIjoyMDYyNzE2MTU3fQ.RnbSqdIM5A67NuKHDOTdpqpu6G2zKJfhMeQapGUI2kw')

def create_exec_sql_function():
    """
    Create the exec_sql function in the database
    This is a critical step to enable SQL fallbacks
    """
    print("Creating exec_sql function...")
    
    # Headers for API requests
    headers = {
        "apikey": SERVICE_KEY,
        "Authorization": f"Bearer {SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    
    # The exec_sql function definition
    # This is a PL/pgSQL function that will execute arbitrary SQL
    # It requires the service_role to work properly
    sql_function = """
    CREATE OR REPLACE FUNCTION exec_sql(query text)
    RETURNS json AS $$
    BEGIN
        EXECUTE query;
        RETURN json_build_object('status', 'success');
    EXCEPTION WHEN OTHERS THEN
        RETURN json_build_object('status', 'error', 'message', SQLERRM);
    END;
    $$ LANGUAGE plpgsql SECURITY DEFINER;
    
    -- Grant execution to authenticated users
    GRANT EXECUTE ON FUNCTION exec_sql TO authenticated;
    GRANT EXECUTE ON FUNCTION exec_sql TO anon;
    GRANT EXECUTE ON FUNCTION exec_sql TO service_role;
    """
    
    # Create a simpler function that just returns rows safely
    sql_getter = """
    CREATE OR REPLACE FUNCTION select_with_security(query text, params text[] DEFAULT NULL, row_security boolean DEFAULT TRUE)
    RETURNS json AS $$
    DECLARE
        result json;
    BEGIN
        IF row_security THEN
            -- Execute with RLS enabled
            EXECUTE query INTO result USING params;
        ELSE
            -- Execute with RLS disabled
            SET LOCAL row_security = off;
            EXECUTE query INTO result USING params;
            RESET row_security;
        END IF;
        RETURN result;
    EXCEPTION WHEN OTHERS THEN
        RETURN json_build_object('status', 'error', 'message', SQLERRM);
    END;
    $$ LANGUAGE plpgsql SECURITY DEFINER;
    
    -- Grant execution to authenticated users
    GRANT EXECUTE ON FUNCTION select_with_security TO authenticated;
    GRANT EXECUTE ON FUNCTION select_with_security TO anon;
    GRANT EXECUTE ON FUNCTION select_with_security TO service_role;
    """
    
    # Try different endpoints to create the function
    endpoints = [
        {"url": f"{SUPABASE_URL}/rest/v1/rpc/exec_sql", "description": "RPC exec_sql", "is_rpc": True},
        {"url": f"{SUPABASE_URL}/rest/v1/sql", "description": "REST SQL", "is_rpc": False},
        {"url": f"{SUPABASE_URL}/sql", "description": "Direct SQL", "is_rpc": False},
        {"url": f"{SUPABASE_URL}/pg/sql", "description": "PG SQL", "is_rpc": False}
    ]
    
    success = False
    
    for endpoint in endpoints:
        try:
            print(f"Trying {endpoint['description']} endpoint: {endpoint['url']}")
            
            if endpoint["is_rpc"]:
                # If endpoint is an RPC call to exec_sql (assuming it exists)
                response = requests.post(
                    endpoint["url"],
                    headers=headers,
                    json={"query": sql_function},
                    timeout=10
                )
            else:
                # Direct SQL endpoint
                response = requests.post(
                    endpoint["url"],
                    headers=headers,
                    json={"query": sql_function},
                    timeout=10
                )
                
            print(f"Status: {response.status_code}")
            
            if response.status_code < 300:
                print(f"✅ Successfully created exec_sql function using {endpoint['description']} endpoint!")
                success = True
                break
            else:
                print(f"❌ Failed with {endpoint['description']}: {response.text[:200]}")
        except RequestException as e:
            print(f"⚠️ Network error with {endpoint['description']}: {str(e)}")
        except Exception as e:
            print(f"⚠️ Error with {endpoint['description']}: {str(e)}")
    
    # If we haven't succeeded with exec_sql, try creating the select_with_security function
    if not success:
        print("\nTrying to create select_with_security function instead...")
        
        for endpoint in endpoints:
            try:
                print(f"Trying {endpoint['description']} endpoint: {endpoint['url']}")
                
                if endpoint["is_rpc"]:
                    # If endpoint is an RPC call to exec_sql (assuming it exists)
                    response = requests.post(
                        endpoint["url"],
                        headers=headers,
                        json={"query": sql_getter},
                        timeout=10
                    )
                else:
                    # Direct SQL endpoint
                    response = requests.post(
                        endpoint["url"],
                        headers=headers,
                        json={"query": sql_getter},
                        timeout=10
                    )
                    
                print(f"Status: {response.status_code}")
                
                if response.status_code < 300:
                    print(f"✅ Successfully created select_with_security function using {endpoint['description']} endpoint!")
                    success = True
                    break
                else:
                    print(f"❌ Failed with {endpoint['description']}: {response.text[:200]}")
            except RequestException as e:
                print(f"⚠️ Network error with {endpoint['description']}: {str(e)}")
            except Exception as e:
                print(f"⚠️ Error with {endpoint['description']}: {str(e)}")
    
    # Try to create the functions using direct REST API
    if not success:
        print("\nTrying to create functions via direct REST API...")
        
        try:
            # Try to call a REST API endpoint
            print("Checking what functions exist...")
            functions_url = f"{SUPABASE_URL}/rest/v1/rpc"
            response = requests.get(functions_url, headers=headers)
            
            print(f"Functions response status: {response.status_code}")
            if response.status_code < 300:
                print("Current functions:", response.text[:200])
        except Exception as e:
            print(f"Error checking functions: {str(e)}")
    
    if success:
        print("\n✅ Successfully created SQL function(s)!")
    else:
        print("\n❌ Failed to create SQL functions.")
        print("You may need to use the Supabase SQL editor directly.")

if __name__ == "__main__":
    create_exec_sql_function() 