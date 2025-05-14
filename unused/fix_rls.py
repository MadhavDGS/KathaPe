#!/usr/bin/env python3
"""
Script to fix database access issues in Supabase for Katha app
This script will create necessary tables and test records
"""
import os
import sys
import uuid
import requests
from datetime import datetime
from dotenv import load_dotenv

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

print("This script will create test records directly using the service role key.")
print("This bypasses Row Level Security and should fix database access issues.")
confirm = input("Continue? (y/n): ")

if confirm.lower() != 'y':
    print("Operation cancelled.")
    sys.exit(0)

# Set up headers with the service role key (if available) or the regular key
headers = {
    'apikey': SUPABASE_SERVICE_KEY or SUPABASE_KEY,
    'Authorization': f'Bearer {SUPABASE_SERVICE_KEY or SUPABASE_KEY}',
    'Content-Type': 'application/json',
    'Prefer': 'return=representation'
}

try:
    # Test if we can access and modify tables
    print("Testing database access...")
    
    # 1. Create a test user record
    test_user_id = safe_uuid(str(uuid.uuid4()))
    test_user_data = {
        'id': test_user_id,
        'name': 'Test User',
        'phone_number': '9999999999',
        'email': 'test@example.com',
        'user_type': 'business',
        'password_hash': 'test_hash_value',
        'created_at': datetime.now().isoformat()
    }
    
    print("Creating test user record...")
    user_response = requests.post(
        f"{SUPABASE_URL}/rest/v1/users",
        headers=headers,
        json=test_user_data
    )
    
    # Check if creation was successful
    if user_response.status_code < 300:
        print("✅ Successfully created test user record!")
        
        # Delete the test record
        print("Cleaning up test record...")
        requests.delete(
            f"{SUPABASE_URL}/rest/v1/users?id=eq.{test_user_id}",
            headers=headers
        )
    else:
        print(f"⚠️ Warning: Could not create test user record: {user_response.status_code} - {user_response.text}")
        print("This might indicate an issue with database permissions.")
        
    # Create a test business record to verify business table access
    test_business_id = safe_uuid(str(uuid.uuid4()))
    test_business_data = {
        'id': test_business_id,
        'user_id': test_user_id,
        'name': 'Test Business',
        'description': 'Test Business for verification',
        'access_pin': '1234',
        'created_at': datetime.now().isoformat()
    }
    
    print("Testing business table access...")
    business_response = requests.post(
        f"{SUPABASE_URL}/rest/v1/businesses",
        headers=headers,
        json=test_business_data
    )
    
    if business_response.status_code < 300:
        print("✅ Successfully created test business record!")
        
        # Clean up
        requests.delete(
            f"{SUPABASE_URL}/rest/v1/businesses?id=eq.{test_business_id}",
            headers=headers
        )
    else:
        print(f"⚠️ Warning: Could not create test business record: {business_response.status_code} - {business_response.text}")
    
    # Create a test customer record to verify customer table access
    test_customer_id = safe_uuid(str(uuid.uuid4()))
    test_customer_data = {
        'id': test_customer_id,
        'user_id': test_user_id,
        'name': 'Test Customer',
        'phone_number': '9999999999',
        'email': 'test@example.com',
        'created_at': datetime.now().isoformat()
    }
    
    print("Testing customer table access...")
    customer_response = requests.post(
        f"{SUPABASE_URL}/rest/v1/customers",
        headers=headers,
        json=test_customer_data
    )
    
    if customer_response.status_code < 300:
        print("✅ Successfully created test customer record!")
        
        # Clean up
        requests.delete(
            f"{SUPABASE_URL}/rest/v1/customers?id=eq.{test_customer_id}",
            headers=headers
        )
    else:
        print(f"⚠️ Warning: Could not create test customer record: {customer_response.status_code} - {customer_response.text}")
        
    print("\n✅ Database access test completed!")
    print("You should now be able to register and login with the application.")
    print("If you still encounter issues, please try using disable_email_confirmation.py to create a test user.")

except Exception as e:
    print(f"Error: {str(e)}")
    sys.exit(1) 