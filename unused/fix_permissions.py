import os
import requests
from supabase import create_client

# Supabase credentials provided by user
SUPABASE_URL = "https://ghbmfgomnqmffixfkdyp.supabase.co"
SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdoYm1mZ29tbnFtZmZpeGZrZHlwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0NzE0MDE1NywiZXhwIjoyMDYyNzE2MTU3fQ.RnbSqdIM5A67NuKHDOTdpqpu6G2zKJfhMeQapGUI2kw"

# Initialize Supabase client with service role key
supabase = create_client(SUPABASE_URL, SERVICE_KEY)

print("Checking if tables exist...")
try:
    response = supabase.table('users').select('count(*)').execute()
    print(f"Users table response: {response}")
except Exception as e:
    print(f"Error checking users table: {str(e)}")

# Create users if they don't exist
print("\nCreating sample users...")
try:
    # Delete existing test users first if they exist
    supabase.table('users').delete().eq('phone_number', '1234567890').execute()
    supabase.table('users').delete().eq('phone_number', '0987654321').execute()
    
    # Create business user
    business_user = {
        'name': 'Sample Business',
        'phone_number': '1234567890',
        'password': 'password123',
        'user_type': 'business'
    }
    
    response = supabase.table('users').insert(business_user).execute()
    print(f"Created business user: {response.data if hasattr(response, 'data') else 'No data'}")

    # Create customer user
    customer_user = {
        'name': 'Sample Customer',
        'phone_number': '0987654321',
        'password': 'password123',
        'user_type': 'customer'
    }
    
    response = supabase.table('users').insert(customer_user).execute()
    print(f"Created customer user: {response.data if hasattr(response, 'data') else 'No data'}")

except Exception as e:
    print(f"Error creating users: {str(e)}")

print("\nScript completed. Now try logging in with:")
print("Business: Phone: 1234567890, Password: password123")
print("Customer: Phone: 0987654321, Password: password123") 