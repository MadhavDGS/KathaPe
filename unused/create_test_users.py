import os
import requests
import json
import uuid
from datetime import datetime

# Supabase credentials
SUPABASE_URL = "https://ghbmfgomnqmffixfkdyp.supabase.co"
SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdoYm1mZ29tbnFtZmZpeGZrZHlwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0NzE0MDE1NywiZXhwIjoyMDYyNzE2MTU3fQ.RnbSqdIM5A67NuKHDOTdpqpu6G2zKJfhMeQapGUI2kw"

# Set up headers for REST API requests
headers = {
    "apikey": SERVICE_KEY,
    "Authorization": f"Bearer {SERVICE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

# Create a direct HTTP REST call to create users (bypass client library)
print("Creating test users directly via REST API...")

# First try to delete existing test users
try:
    response = requests.delete(
        f"{SUPABASE_URL}/rest/v1/users",
        headers=headers,
        params={"phone_number": "eq.1234567890"}
    )
    print(f"Deleted existing business user: {response.status_code}")
    
    response = requests.delete(
        f"{SUPABASE_URL}/rest/v1/users",
        headers=headers,
        params={"phone_number": "eq.0987654321"}
    )
    print(f"Deleted existing customer user: {response.status_code}")
except Exception as e:
    print(f"Error deleting users: {str(e)}")

# Create business user
business_user_id = str(uuid.uuid4())
business_user = {
    "id": business_user_id,
    "name": "Sample Business",
    "phone_number": "1234567890",
    "password": "password123",
    "user_type": "business",
    "created_at": datetime.now().isoformat()
}

try:
    response = requests.post(
        f"{SUPABASE_URL}/rest/v1/users",
        headers=headers,
        json=business_user
    )
    print(f"Created business user via REST: {response.status_code}")
    print(response.text)
    
    # If successful, create the business record
    if response.status_code < 300:
        business_id = str(uuid.uuid4())
        business = {
            "id": business_id,
            "user_id": business_user_id,
            "name": "Sample Business Account",
            "description": "Auto-created test business",
            "access_pin": "1234",
            "created_at": datetime.now().isoformat()
        }
        
        response = requests.post(
            f"{SUPABASE_URL}/rest/v1/businesses",
            headers=headers,
            json=business
        )
        print(f"Created business record: {response.status_code}")
        print(response.text)
except Exception as e:
    print(f"Error creating business user: {str(e)}")

# Create customer user
customer_user_id = str(uuid.uuid4())
customer_user = {
    "id": customer_user_id,
    "name": "Sample Customer",
    "phone_number": "0987654321",
    "password": "password123",
    "user_type": "customer",
    "created_at": datetime.now().isoformat()
}

try:
    response = requests.post(
        f"{SUPABASE_URL}/rest/v1/users",
        headers=headers,
        json=customer_user
    )
    print(f"Created customer user via REST: {response.status_code}")
    print(response.text)
    
    # If successful, create the customer record
    if response.status_code < 300:
        customer_id = str(uuid.uuid4())
        customer = {
            "id": customer_id,
            "user_id": customer_user_id,
            "name": "Sample Customer",
            "phone_number": "0987654321",
            "created_at": datetime.now().isoformat()
        }
        
        response = requests.post(
            f"{SUPABASE_URL}/rest/v1/customers",
            headers=headers,
            json=customer
        )
        print(f"Created customer record: {response.status_code}")
        print(response.text)
        
        # Create a relationship between customer and business
        if business_id:
            credit_id = str(uuid.uuid4())
            credit = {
                "id": credit_id,
                "business_id": business_id,
                "customer_id": customer_id,
                "current_balance": 500,
                "created_at": datetime.now().isoformat()
            }
            
            response = requests.post(
                f"{SUPABASE_URL}/rest/v1/customer_credits",
                headers=headers,
                json=credit
            )
            print(f"Created customer-business relationship: {response.status_code}")
            print(response.text)
except Exception as e:
    print(f"Error creating customer user: {str(e)}")

print("\nSetup complete. Try running the app now with:")
print("Business: Phone: 1234567890, Password: password123")
print("Customer: Phone: 0987654321, Password: password123") 