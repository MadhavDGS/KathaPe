#!/usr/bin/env python
"""
Simple test script to verify Supabase connection and schema.
"""

import os
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

# Get Supabase credentials
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_SERVICE_KEY')  # Use service role key for full access

if not supabase_url or not supabase_key:
    print("ERROR: Missing Supabase credentials in .env file")
    exit(1)

# Initialize Supabase client
print(f"Connecting to Supabase at {supabase_url}...")
supabase = create_client(supabase_url, supabase_key)

# Test connection
try:
    # Check users table
    print("\nChecking users table...")
    users_response = supabase.table('users').select('*').execute()
    print(f"Found {len(users_response.data)} users:")
    for idx, user in enumerate(users_response.data):
        print(f"  {idx+1}. ID: {user.get('id')}")
        print(f"     Name: {user.get('name')}")
        print(f"     Phone: {user.get('phone_number')}")
        print(f"     Type: {user.get('user_type')}")
        print(f"     Password: {user.get('password')}")
        print("")

    # Check businesses table
    print("\nChecking businesses table...")
    businesses_response = supabase.table('businesses').select('*').execute()
    print(f"Found {len(businesses_response.data)} businesses:")
    for idx, business in enumerate(businesses_response.data):
        print(f"  {idx+1}. ID: {business.get('id')}")
        print(f"     Name: {business.get('name')}")
        print(f"     User ID: {business.get('user_id')}")
        print(f"     Access PIN: {business.get('access_pin')}")
        print("")

    # Check customers table
    print("\nChecking customers table...")
    customers_response = supabase.table('customers').select('*').execute()
    print(f"Found {len(customers_response.data)} customers:")
    for idx, customer in enumerate(customers_response.data):
        print(f"  {idx+1}. ID: {customer.get('id')}")
        print(f"     Name: {customer.get('name')}")
        print(f"     User ID: {customer.get('user_id')}")
        print(f"     Phone: {customer.get('phone_number')}")
        print("")

    print("\nSuccessfully connected to Supabase and verified schema!")
    print("Your database setup appears to be working correctly.")

except Exception as e:
    print(f"ERROR: Failed to connect to Supabase: {str(e)}")
    exit(1) 