#!/usr/bin/env python3
"""
Script to create a confirmed user directly in Supabase for Katha app
This is a workaround for email confirmation issues
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

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("Error: SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables must be set.")
    print("Please run setup_supabase.py first and make sure you enter the service role key.")
    sys.exit(1)

print("This script will create a pre-confirmed user in Supabase.")
print("This bypasses email confirmation requirements.")

# Get user details
email = input("Enter email for the new user: ")
password = input("Enter password: ")
name = input("Enter name: ")
phone = input("Enter phone number: ")
user_type = input("User type (business/customer): ").lower()

if user_type not in ['business', 'customer']:
    print("Invalid user type. Please enter 'business' or 'customer'.")
    sys.exit(1)

# Set up headers with the service role key
headers = {
    'apikey': SUPABASE_SERVICE_KEY,
    'Authorization': f'Bearer {SUPABASE_SERVICE_KEY}',
    'Content-Type': 'application/json'
}

# Generate IDs - generate them with our safe function to ensure validity
user_id = safe_uuid(str(uuid.uuid4()))
type_id = safe_uuid(str(uuid.uuid4()))  # For business or customer

try:
    # 1. Create user with Supabase Auth API
    print(f"Creating user {email}...")
    auth_response = requests.post(
        f"{SUPABASE_URL}/auth/v1/admin/users",
        headers=headers,
        json={
            "email": email,
            "password": password,
            "email_confirm": True,
            "user_metadata": {
                "name": name,
                "phone": phone,
                "user_type": user_type
            }
        }
    )
    
    if auth_response.status_code >= 400:
        print(f"Error creating user: {auth_response.status_code} - {auth_response.text}")
        sys.exit(1)
    
    # Get user ID from response
    auth_data = auth_response.json()
    user_id = safe_uuid(auth_data.get('id'))
    
    if not user_id:
        print("Error: Failed to get user ID from response")
        sys.exit(1)
    
    print(f"✅ User created with ID: {user_id}")
    
    # 2. Create user record in users table
    user_data = {
        'id': user_id,
        'name': name,
        'phone_number': phone,
        'email': email,
        'password_hash': password,  # Using the password as a hash for simplicity
        'user_type': user_type,
        'created_at': datetime.now().isoformat()
    }
    
    user_response = requests.post(
        f"{SUPABASE_URL}/rest/v1/users",
        headers=headers,
        json=user_data
    )
    
    if user_response.status_code >= 400:
        print(f"Warning: Could not create user record: {user_response.status_code} - {user_response.text}")
    else:
        print("✅ User record created in the users table")
    
    # 3. Create business or customer record
    if user_type == 'business':
        # Generate access pin
        access_pin = f"{int(datetime.now().timestamp()) % 10000:04d}"
        
        business_data = {
            'id': type_id,
            'user_id': user_id,
            'name': f"{name}'s Business",
            'description': 'Auto-created business account',
            'access_pin': access_pin
        }
        
        business_response = requests.post(
            f"{SUPABASE_URL}/rest/v1/businesses",
            headers=headers,
            json=business_data
        )
        
        if business_response.status_code >= 400:
            print(f"Warning: Could not create business record: {business_response.status_code} - {business_response.text}")
        else:
            print(f"✅ Business record created with access PIN: {access_pin}")
            
    elif user_type == 'customer':
        customer_data = {
            'id': type_id,
            'user_id': user_id,
            'name': name,
            'phone_number': phone,
            'email': email
        }
        
        customer_response = requests.post(
            f"{SUPABASE_URL}/rest/v1/customers",
            headers=headers,
            json=customer_data
        )
        
        if customer_response.status_code >= 400:
            print(f"Warning: Could not create customer record: {customer_response.status_code} - {customer_response.text}")
        else:
            print("✅ Customer record created")
    
    print("\n🎉 Success! User created and confirmed.")
    print(f"Login with email: {email} and your password")

except Exception as e:
    print(f"Error: {str(e)}")
    sys.exit(1) 