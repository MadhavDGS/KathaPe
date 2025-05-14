#!/usr/bin/env python3
"""
Script to directly create a test user in Supabase for the Katha app
This script bypasses the RLS restrictions by using the service role key
"""
import os
import sys
import uuid
import requests
from datetime import datetime
from dotenv import load_dotenv

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

# Set up headers with the service role key (if available) or the regular key
headers = {
    'apikey': SUPABASE_SERVICE_KEY or SUPABASE_KEY,
    'Authorization': f'Bearer {SUPABASE_SERVICE_KEY or SUPABASE_KEY}',
    'Content-Type': 'application/json',
    'Prefer': 'return=representation'
}

def create_business_user():
    # Generate unique IDs
    user_id = str(uuid.uuid4())
    business_id = str(uuid.uuid4())
    phone = input("Enter phone number: ")
    name = input("Enter name: ")
    password = input("Enter password: ")
    email = input("Enter email (leave blank to use phone@katha.app): ")
    access_pin = f"{int(datetime.now().timestamp()) % 10000:04d}"
    
    # Use default email if not provided
    if not email:
        email = f"{phone}@katha.app"
    
    # First create the auth user
    try:
        auth_data = {
            "email": email,
            "password": password,
            "email_confirm": True,
            "user_metadata": {
                "name": name,
                "phone": phone,
                "user_type": "business"
            }
        }
        
        # Try to create the user in auth
        auth_response = requests.post(
            f"{SUPABASE_URL}/auth/v1/admin/users",
            headers=headers,
            json=auth_data
        )
        
        # If successful, get the user ID
        if auth_response.status_code < 400:
            auth_result = auth_response.json()
            user_id = auth_result.get('id', user_id)
            print(f"Auth user created with ID: {user_id}")
        else:
            print(f"Note: Could not create auth user: {auth_response.status_code} - {auth_response.text}")
            print("Continuing with direct database creation...")
    except Exception as e:
        print(f"Note: Auth user creation failed: {str(e)}")
        print("Continuing with direct database creation...")
    
    # Create user record
    print("Creating user record...")
    user_data = {
        'id': user_id,
        'name': name,
        'phone_number': phone,
        'email': email,
        'password_hash': "direct_auth",  # We'll handle auth separately
        'user_type': 'business',
        'created_at': datetime.now().isoformat()
    }
    
    try:
        # Create user
        response = requests.post(
            f"{SUPABASE_URL}/rest/v1/users",
            headers=headers,
            json=user_data
        )
        
        if response.status_code >= 400:
            print(f"Error creating user: {response.status_code} - {response.text}")
            return
            
        # Create business record
        print("Creating business record...")
        business_data = {
            'id': business_id,
            'user_id': user_id,
            'name': f"{name}'s Business",
            'description': 'Test business account',
            'access_pin': access_pin,
            'created_at': datetime.now().isoformat()
        }
        
        response = requests.post(
            f"{SUPABASE_URL}/rest/v1/businesses",
            headers=headers,
            json=business_data
        )
        
        if response.status_code >= 400:
            print(f"Error creating business: {response.status_code} - {response.text}")
            return
            
        print(f"""
Test business user created successfully!
----------------------------------------
User ID: {user_id}
Business ID: {business_id}
Phone: {phone}
Name: {name}
Access PIN: {access_pin}
Email for login: {email}

To login, use:
- Email: {email}
- Phone: {phone}
- Password: {password}
- User Type: business
        """)
        
    except Exception as e:
        print(f"Error: {str(e)}")

def create_customer_user():
    # Generate unique IDs
    user_id = str(uuid.uuid4())
    customer_id = str(uuid.uuid4())
    phone = input("Enter phone number: ")
    name = input("Enter name: ")
    password = input("Enter password: ")
    email = input("Enter email (leave blank to use phone@katha.app): ")
    
    # Use default email if not provided
    if not email:
        email = f"{phone}@katha.app"
    
    # First create the auth user
    try:
        auth_data = {
            "email": email,
            "password": password,
            "email_confirm": True,
            "user_metadata": {
                "name": name,
                "phone": phone,
                "user_type": "customer"
            }
        }
        
        # Try to create the user in auth
        auth_response = requests.post(
            f"{SUPABASE_URL}/auth/v1/admin/users",
            headers=headers,
            json=auth_data
        )
        
        # If successful, get the user ID
        if auth_response.status_code < 400:
            auth_result = auth_response.json()
            user_id = auth_result.get('id', user_id)
            print(f"Auth user created with ID: {user_id}")
        else:
            print(f"Note: Could not create auth user: {auth_response.status_code} - {auth_response.text}")
            print("Continuing with direct database creation...")
    except Exception as e:
        print(f"Note: Auth user creation failed: {str(e)}")
        print("Continuing with direct database creation...")
    
    # Create user record
    print("Creating customer user record...")
    user_data = {
        'id': user_id,
        'name': name,
        'phone_number': phone,
        'email': email,
        'password_hash': "direct_auth",  # We'll handle auth separately
        'user_type': 'customer',
        'created_at': datetime.now().isoformat()
    }
    
    try:
        # Create user
        response = requests.post(
            f"{SUPABASE_URL}/rest/v1/users",
            headers=headers,
            json=user_data
        )
        
        if response.status_code >= 400:
            print(f"Error creating user: {response.status_code} - {response.text}")
            return
            
        # Create customer record
        print("Creating customer record...")
        customer_data = {
            'id': customer_id,
            'user_id': user_id,
            'name': name,
            'phone_number': phone,
            'email': email,
            'created_at': datetime.now().isoformat()
        }
        
        response = requests.post(
            f"{SUPABASE_URL}/rest/v1/customers",
            headers=headers,
            json=customer_data
        )
        
        if response.status_code >= 400:
            print(f"Error creating customer: {response.status_code} - {response.text}")
            return
            
        print(f"""
Test customer user created successfully!
----------------------------------------
User ID: {user_id}
Customer ID: {customer_id}
Phone: {phone}
Name: {name}
Email for login: {email}

To login, use:
- Email: {email}
- Phone: {phone}
- Password: {password}
- User Type: customer
        """)
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    print("Katha - Create Test User")
    print("------------------------")
    print("This script will create a test user directly in the Supabase database.")
    
    user_type = input("Create business or customer user? (b/c): ").lower()
    
    if user_type == 'b':
        create_business_user()
    elif user_type == 'c':
        create_customer_user()
    else:
        print("Invalid choice. Please enter 'b' for business or 'c' for customer.")
        sys.exit(1) 