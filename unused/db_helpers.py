#!/usr/bin/env python3
"""
Helper functions for database operations in Katha
"""
import os
import uuid
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get Supabase URL and keys
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

def is_valid_uuid(value):
    """Check if a value is a valid UUID"""
    if not value:
        return False
    
    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, TypeError, AttributeError):
        return False

def safe_uuid(id_value):
    """Ensure a value is a valid UUID string or generate a new one"""
    if not id_value or not is_valid_uuid(id_value):
        print(f"WARNING: Invalid UUID {id_value}, generating new one")
        return str(uuid.uuid4())
    return str(id_value)

def execute_sql(sql_query, params=None, use_service_key=True):
    """
    Execute a SQL query directly using the Supabase API
    
    Args:
        sql_query: The SQL query to execute
        params: Dictionary of parameters to replace in the query
        use_service_key: Whether to use the service key for bypassing RLS
        
    Returns:
        The response from the API
    """
    # Process parameters to ensure UUIDs are valid
    if params:
        for key, value in params.items():
            if key.endswith('_id') and not is_valid_uuid(value):
                params[key] = safe_uuid(value)
    
    # Choose the appropriate key
    api_key = SUPABASE_SERVICE_KEY if use_service_key and SUPABASE_SERVICE_KEY else SUPABASE_KEY
    
    headers = {
        'apikey': api_key,
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    response = requests.post(
        f"{SUPABASE_URL}/rest/v1/rpc/execute",
        headers=headers,
        json={
            "query": sql_query,
            "params": params or {}
        }
    )
    
    # Check for errors
    if response.status_code >= 300:
        print(f"SQL Error: {response.status_code} - {response.text}")
        return None
    
    return response.json()

def get_customer_by_id(customer_id, business_id):
    """
    Get customer details by ID
    
    Args:
        customer_id: The customer ID
        business_id: The business ID
        
    Returns:
        Customer details or None if not found
    """
    # Validate UUIDs
    customer_id = safe_uuid(customer_id)
    business_id = safe_uuid(business_id)
    
    query = """
    SELECT c.*, cc.current_balance 
    FROM customers c
    JOIN customer_credits cc ON c.id = cc.customer_id
    WHERE c.id = :customer_id AND cc.business_id = :business_id
    """
    
    result = execute_sql(query, {
        'customer_id': customer_id,
        'business_id': business_id
    })
    
    return result[0] if result and len(result) > 0 else None

def get_business_by_id(business_id):
    """
    Get business details by ID
    
    Args:
        business_id: The business ID
        
    Returns:
        Business details or None if not found
    """
    # Validate UUID
    business_id = safe_uuid(business_id)
    
    query = """
    SELECT * FROM businesses WHERE id = :business_id
    """
    
    result = execute_sql(query, {
        'business_id': business_id
    })
    
    return result[0] if result and len(result) > 0 else None

def get_transactions(business_id, customer_id=None):
    """
    Get transactions for a business and optionally filtered by customer
    
    Args:
        business_id: The business ID
        customer_id: Optional customer ID to filter by
        
    Returns:
        List of transactions
    """
    # Validate UUIDs
    business_id = safe_uuid(business_id)
    
    if customer_id:
        customer_id = safe_uuid(customer_id)
        query = """
        SELECT * FROM transactions 
        WHERE business_id = :business_id AND customer_id = :customer_id
        ORDER BY created_at DESC
        """
        params = {
            'business_id': business_id,
            'customer_id': customer_id
        }
    else:
        query = """
        SELECT * FROM transactions 
        WHERE business_id = :business_id
        ORDER BY created_at DESC LIMIT 10
        """
        params = {
            'business_id': business_id
        }
    
    result = execute_sql(query, params)
    
    return result if result else [] 