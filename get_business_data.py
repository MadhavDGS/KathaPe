#!/usr/bin/env python
"""
KathaPe Business Data Checker

This script connects to your database and checks if it can retrieve business 
and customer data. It will print out what it finds to help diagnose issues.
"""

import os
import traceback
from datetime import datetime

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
    
    # Get one business
    business_response = client.table('businesses').select('*').limit(1).execute()
    
    if business_response.data:
        business = business_response.data[0]
        business_id = business['id']
        print(f"\n✅ Found business: {business['name']} (ID: {business_id})")
        
        # Get customers for this business
        print("\nLooking for customers...")
        customers_response = client.table('customer_credits').select('*').eq('business_id', business_id).execute()
        
        if customers_response.data:
            print(f"✅ Found {len(customers_response.data)} customers with credit relationships")
            
            # Get first customer details
            first_customer = customers_response.data[0]
            customer_id = first_customer['customer_id']
            
            # Get customer name
            customer_details = client.table('customers').select('name,phone_number').eq('id', customer_id).execute()
            
            if customer_details.data:
                print(f"  - Customer: {customer_details.data[0].get('name')} (Balance: {first_customer.get('current_balance')})")
            else:
                print(f"  - Customer ID {customer_id} (Balance: {first_customer.get('current_balance')})")
                
            # Get transaction history
            transactions = client.table('transactions').select('*').eq('business_id', business_id).limit(5).execute()
            
            if transactions.data:
                print(f"\n✅ Found {len(transactions.data)} transactions")
                print("  Recent transactions:")
                for tx in transactions.data[:3]:  # Show first 3
                    date = datetime.fromisoformat(tx['created_at'].replace('Z', '+00:00')).strftime('%Y-%m-%d')
                    print(f"  - {tx['transaction_type'].upper()}: {tx.get('amount')} ({date})")
            else:
                print("\n❌ No transactions found")
        else:
            print("❌ No customers found for this business")
    else:
        print("\n❌ No businesses found in the database")
        
except Exception as e:
    print(f"❌ ERROR: {str(e)}")
    traceback.print_exc()
    print("\nPossible solutions:")
    print("1. Check if your Supabase credentials are correct")
    print("2. Make sure the required tables exist in your database")
    print("3. Check network connectivity to Supabase") 