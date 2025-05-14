"""
Provides mock authentication functionality when the database is unavailable.
This module ensures the application remains functional even when Supabase connections fail.
"""
import os
import json
import uuid
from datetime import datetime
from functools import wraps
from flask import session, redirect, url_for, flash

# Mock user database in memory
# This will be used when Supabase permissions fail
MOCK_USERS = {
    # Sample business user
    "9999999999": {
        "id": str(uuid.uuid4()),
        "name": "Sample Business",
        "phone_number": "9999999999",
        "password": "password123",
        "user_type": "business",
        "created_at": datetime.now().isoformat()
    }
}

# Mock businesses for the business user
MOCK_BUSINESSES = {
    # Will use the business user's ID as key
}

# Mock customers for the customer user
MOCK_CUSTOMERS = {
    # Will use the customer user's ID as key
}

# Mock customer credits linking customers and businesses
MOCK_CUSTOMER_CREDITS = []

# Mock transactions
MOCK_TRANSACTIONS = []

def init_mock_data():
    """Initialize the mock data with proper relationships"""
    global MOCK_BUSINESSES, MOCK_CUSTOMERS, MOCK_CUSTOMER_CREDITS
    
    # Get user ID
    business_user_id = MOCK_USERS["9999999999"]["id"]
    
    # Create business record
    business_id = str(uuid.uuid4())
    MOCK_BUSINESSES[business_user_id] = {
        "id": business_id,
        "user_id": business_user_id,
        "name": "Sample Business Account",
        "description": "Mock business account",
        "access_pin": "1234",
        "created_at": datetime.now().isoformat()
    }

def save_mock_data():
    """
    Save mock data to a file so it persists between app restarts
    """
    try:
        mock_data = {
            "users": MOCK_USERS,
            "businesses": MOCK_BUSINESSES,
            "customers": MOCK_CUSTOMERS,
            "customer_credits": MOCK_CUSTOMER_CREDITS,
            "transactions": MOCK_TRANSACTIONS
        }
        
        with open('mock_data.json', 'w') as f:
            json.dump(mock_data, f, indent=2)
            
        return True
    except Exception as e:
        print(f"Error saving mock data: {str(e)}")
        return False

def load_mock_data():
    """
    Load mock data from file if it exists
    """
    global MOCK_USERS, MOCK_BUSINESSES, MOCK_CUSTOMERS, MOCK_CUSTOMER_CREDITS, MOCK_TRANSACTIONS
    
    try:
        if os.path.exists('mock_data.json'):
            with open('mock_data.json', 'r') as f:
                data = json.load(f)
                
                MOCK_USERS = data.get("users", MOCK_USERS)
                MOCK_BUSINESSES = data.get("businesses", MOCK_BUSINESSES)
                MOCK_CUSTOMERS = data.get("customers", MOCK_CUSTOMERS)
                MOCK_CUSTOMER_CREDITS = data.get("customer_credits", MOCK_CUSTOMER_CREDITS)
                MOCK_TRANSACTIONS = data.get("transactions", MOCK_TRANSACTIONS)
                
            return True
        return False
    except Exception as e:
        print(f"Error loading mock data: {str(e)}")
        return False

# Authentication functions
def mock_login(phone, password, user_type='customer'):
    """
    Attempt a mock login without using the database
    Returns (success, user_data) tuple
    """
    print(f"Mock login attempt for {phone} as {user_type}")
    
    # First check if this user exists in our mock database
    if phone in MOCK_USERS:
        user = MOCK_USERS[phone]
        
        # Verify password and user type
        if user['password'] == password and user['user_type'] == user_type:
            # Set session data
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_type'] = user_type
            session['phone_number'] = phone
            
            if user_type == 'business':
                # Get business data
                for business_id, business in MOCK_BUSINESSES.items():
                    if business['user_id'] == user['id']:
                        session['business_id'] = business['id']
                        session['business_name'] = business['name']
                        session['access_pin'] = business['access_pin']
                        break
                else:
                    # Create mock business if not found
                    business_id = str(uuid.uuid4())
                    session['business_id'] = business_id
                    session['business_name'] = f"{user['name']}'s Business"
                    session['access_pin'] = '1234'
            else:
                # Get customer data
                for customer_id, customer in MOCK_CUSTOMERS.items():
                    if customer['user_id'] == user['id']:
                        session['customer_id'] = customer['id']
                        break
                else:
                    # Create mock customer if not found
                    customer_id = str(uuid.uuid4())
                    session['customer_id'] = customer_id
            
            return True, user
    
    # Auto-create user if enabling demo mode
    if password == 'demo123' or phone.endswith('0000'):
        user_id = str(uuid.uuid4())
        user = {
            'id': user_id,
            'name': f"Demo {user_type.title()}",
            'phone_number': phone,
            'password': password,
            'user_type': user_type,
            'created_at': datetime.now().isoformat()
        }
        
        # Set session data
        session['user_id'] = user_id
        session['user_name'] = user['name']
        session['user_type'] = user_type
        session['phone_number'] = phone
        
        if user_type == 'business':
            business_id = str(uuid.uuid4())
            session['business_id'] = business_id
            session['business_name'] = f"{user['name']}'s Business"
            session['access_pin'] = '1234'
        else:
            customer_id = str(uuid.uuid4())
            session['customer_id'] = customer_id
        
        # Add to mock database
        MOCK_USERS[phone] = user
        return True, user
    
    # Finally, try any credentials with some dummy data for demo purposes
    if len(phone) >= 10 and password:
        # Create a temporary user just for this session
        user_id = str(uuid.uuid4())
        
        # Set session data
        session['user_id'] = user_id
        session['user_name'] = f"User {phone[-4:]}"
        session['user_type'] = user_type
        session['phone_number'] = phone
        
        if user_type == 'business':
            business_id = str(uuid.uuid4())
            session['business_id'] = business_id
            session['business_name'] = f"Business {phone[-4:]}"
            session['access_pin'] = f"{int(phone) % 10000:04d}" if phone.isdigit() else "1234"
        else:
            customer_id = str(uuid.uuid4())
            session['customer_id'] = customer_id
        
        # Create a temporary user for this session
        temp_user = {
            'id': user_id,
            'name': session['user_name'],
            'phone_number': phone,
            'user_type': user_type
        }
        
        return True, temp_user
    
    return False, None

def mock_register(phone, password, name, user_type='customer'):
    """
    Register a new user in the mock system
    Returns (success, message) tuple
    """
    if phone in MOCK_USERS:
        return False, "Phone number already registered"
    
    user_id = str(uuid.uuid4())
    user = {
        'id': user_id,
        'name': name or f"User {phone[-4:]}",
        'phone_number': phone,
        'password': password,
        'user_type': user_type,
        'created_at': datetime.now().isoformat()
    }
    
    MOCK_USERS[phone] = user
    
    if user_type == 'business':
        business_id = str(uuid.uuid4())
        MOCK_BUSINESSES[user_id] = {
            'id': business_id,
            'user_id': user_id,
            'name': f"{name}'s Business",
            'description': 'Auto-created business account',
            'access_pin': '1234',
            'created_at': datetime.now().isoformat()
        }
    else:
        customer_id = str(uuid.uuid4())
        MOCK_CUSTOMERS[user_id] = {
            'id': customer_id,
            'user_id': user_id,
            'name': name,
            'phone_number': phone,
            'created_at': datetime.now().isoformat()
        }
    
    return True, "User registered successfully"

# Mock database query functions
def mock_query_table(table_name, query_type='select', fields='*', filters=None, data=None):
    """
    Mock implementation of query_table function for when Supabase fails
    """
    # Response class with data attribute to match Supabase responses
    class MockResponse:
        def __init__(self, data):
            self.data = data
    
    try:
        # Handle select queries
        if query_type == 'select':
            results = []
            
            # Get data based on table name
            if table_name == 'users':
                all_users = list(MOCK_USERS.values())
                results = all_users
            elif table_name == 'businesses':
                all_businesses = list(MOCK_BUSINESSES.values())
                results = all_businesses
            elif table_name == 'customers':
                all_customers = list(MOCK_CUSTOMERS.values())
                results = all_customers
            elif table_name == 'customer_credits':
                results = MOCK_CUSTOMER_CREDITS
            elif table_name == 'transactions':
                results = MOCK_TRANSACTIONS
            
            # Apply filters if any
            if filters:
                filtered_results = []
                for item in results:
                    matches = True
                    for field, op, value in filters:
                        if field in item:
                            if op == 'eq' and item[field] != value:
                                matches = False
                            elif op == 'neq' and item[field] == value:
                                matches = False
                            # Add more operations as needed
                    
                    if matches:
                        filtered_results.append(item)
                
                results = filtered_results
            
            return MockResponse(results)
        
        # Handle insert queries
        elif query_type == 'insert':
            if not data:
                return MockResponse([])
            
            # Ensure ID is present
            if 'id' not in data:
                data['id'] = str(uuid.uuid4())
            
            # Insert into the correct "table"
            if table_name == 'users':
                MOCK_USERS[data['phone_number']] = data
            elif table_name == 'businesses':
                MOCK_BUSINESSES[data['user_id']] = data
            elif table_name == 'customers':
                MOCK_CUSTOMERS[data['user_id']] = data
            elif table_name == 'customer_credits':
                MOCK_CUSTOMER_CREDITS.append(data)
            elif table_name == 'transactions':
                MOCK_TRANSACTIONS.append(data)
                
                # Update customer credit balance
                for credit in MOCK_CUSTOMER_CREDITS:
                    if (credit['business_id'] == data['business_id'] and 
                        credit['customer_id'] == data['customer_id']):
                        if data['transaction_type'] == 'credit':
                            credit['current_balance'] = credit.get('current_balance', 0) + data['amount']
                        elif data['transaction_type'] == 'payment':
                            credit['current_balance'] = credit.get('current_balance', 0) - data['amount']
            
            # Save the updated mock data
            save_mock_data()
            
            return MockResponse([data])
        
        # Handle update queries
        elif query_type == 'update':
            updated_items = []
            
            # For each table type, find items matching filters and update
            if table_name == 'users':
                for phone, user in MOCK_USERS.items():
                    matches = True
                    if filters:
                        for field, op, value in filters:
                            if field in user:
                                if op == 'eq' and user[field] != value:
                                    matches = False
                    
                    if matches:
                        for key, value in data.items():
                            user[key] = value
                        updated_items.append(user)
            
            elif table_name == 'businesses':
                for user_id, business in MOCK_BUSINESSES.items():
                    matches = True
                    if filters:
                        for field, op, value in filters:
                            if field in business:
                                if op == 'eq' and business[field] != value:
                                    matches = False
                    
                    if matches:
                        for key, value in data.items():
                            business[key] = value
                        updated_items.append(business)
            
            elif table_name == 'customers':
                for user_id, customer in MOCK_CUSTOMERS.items():
                    matches = True
                    if filters:
                        for field, op, value in filters:
                            if field in customer:
                                if op == 'eq' and customer[field] != value:
                                    matches = False
                    
                    if matches:
                        for key, value in data.items():
                            customer[key] = value
                        updated_items.append(customer)
            
            elif table_name == 'customer_credits':
                for i, credit in enumerate(MOCK_CUSTOMER_CREDITS):
                    matches = True
                    if filters:
                        for field, op, value in filters:
                            if field in credit:
                                if op == 'eq' and credit[field] != value:
                                    matches = False
                    
                    if matches:
                        for key, value in data.items():
                            MOCK_CUSTOMER_CREDITS[i][key] = value
                        updated_items.append(MOCK_CUSTOMER_CREDITS[i])
            
            # Save the updated mock data
            save_mock_data()
            
            return MockResponse(updated_items)
            
        # Handle delete queries
        elif query_type == 'delete':
            deleted_items = []
            
            # Not implementing delete for simplicity
            # If needed, this would filter and remove items from the lists
            
            return MockResponse(deleted_items)
        
        else:
            print(f"Unsupported query type: {query_type}")
            return MockResponse([])
            
    except Exception as e:
        print(f"Error in mock_query_table: {str(e)}")
        return MockResponse([])

def ensure_unique_customer_credits():
    """
    Fix any duplicate customer_credits entries and ensure data structure is valid
    """
    global MOCK_CUSTOMER_CREDITS
    
    # Create a dictionary to track unique business+customer combinations
    unique_credits = {}
    cleaned_credits = []
    
    # Process each credit and keep only the latest one for each business+customer pair
    for credit in MOCK_CUSTOMER_CREDITS:
        # Skip if missing required fields
        if not credit.get('business_id') or not credit.get('customer_id'):
            continue
            
        # Create a key for this business+customer pair
        key = f"{credit['business_id']}_{credit['customer_id']}"
        
        # Ensure required fields have values
        if 'created_at' not in credit:
            credit['created_at'] = datetime.now().isoformat()
        if 'updated_at' not in credit:
            credit['updated_at'] = datetime.now().isoformat()
        if 'current_balance' not in credit:
            credit['current_balance'] = 0
        if 'id' not in credit:
            credit['id'] = str(uuid.uuid4())
            
        # If this is the first time we've seen this pair, or it's newer than what we've seen
        if key not in unique_credits or credit['updated_at'] > unique_credits[key]['updated_at']:
            unique_credits[key] = credit
    
    # Re-create the credits list with only unique entries
    MOCK_CUSTOMER_CREDITS = list(unique_credits.values())
    
    # Save the updated mock data
    save_mock_data()
    
    print(f"Fixed customer_credits list - now has {len(MOCK_CUSTOMER_CREDITS)} unique entries")
    return MOCK_CUSTOMER_CREDITS

# Initialize mock data if not already loaded
if not load_mock_data():
    init_mock_data()
    save_mock_data()

# Fix any data issues
ensure_unique_customer_credits()

# Print credentials for testing
print("\n============ MOCK CREDENTIALS FOR TESTING =============")
print("Business: Phone: 9999999999, Password: password123")
print("=========================================================\n") 