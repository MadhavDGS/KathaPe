#!/usr/bin/env python
"""
KathaPe Sample Data Generator

This script adds sample data to your database to help with testing and demonstrations.
"""

import os
import uuid
import traceback
from datetime import datetime, timedelta

try:
    # Import Supabase
    print("Importing Supabase...")
    from supabase import create_client, Client
    print("Supabase imported successfully")
    
    # Environment variables 
    SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://ghbmfgomnqmffixfkdyp.supabase.co')
    SUPABASE_KEY = os.environ.get('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdoYm1mZ29tbnFtZmZpeGZrZHlwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDcxNDAxNTcsImV4cCI6MjA2MjcxNjE1N30.Fw750xiDWVPrl6ssr9p6AJTt--8zvnPoboxJiURvsOI')
    
    # Create client
    print(f"Connecting to Supabase at {SUPABASE_URL}...")
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Test Connection
    test_result = client.table('users').select('id').limit(1).execute()
    print(f"Connection test successful! Found {len(test_result.data) if test_result.data else 0} users")
    
    # Get or create a business
    business_response = client.table('businesses').select('*').limit(1).execute()
    
    if business_response.data:
        business = business_response.data[0]
        business_id = business['id']
        print(f"Using existing business: {business['name']} (ID: {business_id})")
    else:
        # Create a business user
        business_user_id = str(uuid.uuid4())
        print(f"Creating new business user (ID: {business_user_id})...")
        
        user_data = {
            'id': business_user_id,
            'name': 'Sample Business Owner',
            'phone_number': '9876543210',
            'user_type': 'business',
            'password': 'sample123',
            'created_at': datetime.now().isoformat()
        }
        
        client.table('users').insert(user_data).execute()
        
        # Create a business
        business_id = str(uuid.uuid4())
        print(f"Creating new business (ID: {business_id})...")
        
        business_data = {
            'id': business_id,
            'user_id': business_user_id,
            'name': 'Sample Business',
            'description': 'A sample business for testing',
            'access_pin': '1234',
            'created_at': datetime.now().isoformat()
        }
        
        client.table('businesses').insert(business_data).execute()
        print("✅ Business created successfully")
    
    # Create customers with credit relationships and transactions
    num_customers = 5
    print(f"\nCreating {num_customers} test customers...")
    
    for i in range(1, num_customers + 1):
        # Create user
        customer_user_id = str(uuid.uuid4())
        user_data = {
            'id': customer_user_id,
            'name': f'Customer {i}',
            'phone_number': f'98765{i:05d}',
            'user_type': 'customer',
            'password': 'sample123',
            'created_at': datetime.now().isoformat()
        }
        
        client.table('users').insert(user_data).execute()
        
        # Create customer
        customer_id = str(uuid.uuid4())
        customer_data = {
            'id': customer_id,
            'user_id': customer_user_id,
            'name': f'Customer {i}',
            'phone_number': f'98765{i:05d}',
            'created_at': datetime.now().isoformat()
        }
        
        client.table('customers').insert(customer_data).execute()
        
        # Create credit relationship
        initial_balance = i * 1000
        credit_id = str(uuid.uuid4())
        credit_data = {
            'id': credit_id,
            'business_id': business_id,
            'customer_id': customer_id,
            'current_balance': initial_balance,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        client.table('customer_credits').insert(credit_data).execute()
        
        # Create some transactions
        print(f"  - Adding {i+2} transactions for Customer {i}...")
        
        # Credit transaction (larger amount)
        credit_tx_id = str(uuid.uuid4())
        credit_tx_data = {
            'id': credit_tx_id,
            'business_id': business_id,
            'customer_id': customer_id,
            'amount': initial_balance,
            'transaction_type': 'credit',
            'notes': f'Initial credit for Customer {i}',
            'created_at': (datetime.now() - timedelta(days=i*2)).isoformat(),
            'created_by': business_id
        }
        
        client.table('transactions').insert(credit_tx_data).execute()
        
        # Add some payment transactions (smaller amounts)
        for j in range(1, i+2):
            payment_tx_id = str(uuid.uuid4())
            payment_amount = 100 * j
            payment_tx_data = {
                'id': payment_tx_id,
                'business_id': business_id,
                'customer_id': customer_id,
                'amount': payment_amount,
                'transaction_type': 'payment',
                'notes': f'Payment {j} from Customer {i}',
                'created_at': (datetime.now() - timedelta(days=i-j)).isoformat(),
                'created_by': customer_user_id
            }
            
            client.table('transactions').insert(payment_tx_data).execute()
    
    print("\n✅ Sample data creation complete!")
    print("You should now be able to see customers and transactions on your dashboard.")
    
except Exception as e:
    print(f"❌ ERROR: {str(e)}")
    traceback.print_exc() 