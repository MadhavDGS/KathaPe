import os
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables from .env file
load_dotenv()

# Get Supabase credentials from environment variables
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')
supabase_service_key = os.getenv('SUPABASE_SERVICE_KEY')

print("Supabase URL:", supabase_url)
print("Supabase Key:", supabase_key[:20] + "..." if supabase_key else None)
print("Supabase Service Key:", supabase_service_key[:20] + "..." if supabase_service_key else None)

# Print .env file contents
print("\nReading .env file directly:")
with open('.env', 'r') as f:
    print(f.read())

try:
    # Connect with anon key
    print("\nConnecting with anon key...")
    supabase = create_client(supabase_url, supabase_key)
    
    # Try to list tables
    print("Trying to list tables in the database...")
    tables_to_try = ['users', 'businesses', 'customers', 'customer_credits', 'transactions']
    
    for table in tables_to_try:
        try:
            print(f"\nTrying to access table: {table}")
            response = supabase.table(table).select('*').limit(1).execute()
            print(f"Success! Found {len(response.data)} records in the {table} table")
        except Exception as e:
            print(f"Error accessing {table}: {str(e)}")
    
    # Connect with service role key (admin)
    print("\nConnecting with service role key...")
    supabase_admin = create_client(supabase_url, supabase_service_key)
    
    # Try admin operations
    for table in tables_to_try:
        try:
            print(f"\nTrying to access table with service role: {table}")
            response = supabase_admin.table(table).select('*').limit(1).execute()
            print(f"Success! Found {len(response.data)} records in the {table} table")
            
            # Print schema
            if len(response.data) > 0:
                print(f"Schema of {table}: {list(response.data[0].keys())}")
        except Exception as e:
            print(f"Error accessing {table} with service role: {str(e)}")
            
except Exception as e:
    print(f"Error connecting to Supabase: {str(e)}")
    print("Please check your .env file and make sure your Supabase credentials are correct.") 