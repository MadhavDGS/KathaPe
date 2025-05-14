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
    },
    # Sample customer user
    "8888888888": {
        "id": str(uuid.uuid4()),
        "name": "Sample Customer",
        "phone_number": "8888888888", 
        "password": "password123",
        "user_type": "customer",
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
    
    # Get user IDs
    business_user_id = MOCK_USERS["9999999999"]["id"]
    customer_user_id = MOCK_USERS["8888888888"]["id"]
    
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
    
    # Create customer record
    customer_id = str(uuid.uuid4())
    MOCK_CUSTOMERS[customer_user_id] = {
        "id": customer_id,
        "user_id": customer_user_id,
        "name": "Sample Customer",
        "phone_number": "8888888888",
        "created_at": datetime.now().isoformat()
    }
    
    # Create relationship between business and customer
    MOCK_CUSTOMER_CREDITS.append({
        "id": str(uuid.uuid4()),
        "business_id": business_id,
        "customer_id": customer_id,
        "current_balance": 500,
        "created_at": datetime.now().isoformat()
    })

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
    Mock login function that uses the in-memory database
    """
    # Try to find user by phone
    user = MOCK_USERS.get(phone)
    
    # Check if user exists and password matches
    if user and user['password'] == password:
        # Set session data
        session['user_id'] = user['id']
        session['user_name'] = user['name']
        session['user_type'] = user['user_type']
        session['phone_number'] = phone
        
        # For business users, set business ID
        if user['user_type'] == 'business':
            business = MOCK_BUSINESSES.get(user['id'])
            if business:
                session['business_id'] = business['id']
                session['business_name'] = business['name']
                session['access_pin'] = business['access_pin']
        # For customer users, set customer ID
        elif user['user_type'] == 'customer':
            customer = MOCK_CUSTOMERS.get(user['id'])
            if customer:
                session['customer_id'] = customer['id']
                
        return True, user
    else:
        return False, None

def mock_register(phone, password, name, user_type='customer'):
    """
    Mock register function that uses the in-memory database
    """
    # Check if user already exists
    if phone in MOCK_USERS:
        return False, "Phone number already registered"
    
    # Create user ID
    user_id = str(uuid.uuid4())
    
    # Create user
    MOCK_USERS[phone] = {
        "id": user_id,
        "name": name,
        "phone_number": phone,
        "password": password,
        "user_type": user_type,
        "created_at": datetime.now().isoformat()
    }
    
    # Create profile based on user type
    if user_type == 'business':
        business_id = str(uuid.uuid4())
        MOCK_BUSINESSES[user_id] = {
            "id": business_id,
            "user_id": user_id,
            "name": f"{name}'s Business",
            "description": "Auto-created business account",
            "access_pin": "1234",
            "created_at": datetime.now().isoformat()
        }
    else:
        customer_id = str(uuid.uuid4())
        MOCK_CUSTOMERS[user_id] = {
            "id": customer_id,
            "user_id": user_id,
            "name": name,
            "phone_number": phone,
            "created_at": datetime.now().isoformat()
        }
    
    # Save the updated mock data
    save_mock_data()
    
    return True, "Registration successful"

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

# Initialize mock data if not already loaded
if not load_mock_data():
    init_mock_data()
    save_mock_data()

# Print credentials for testing
print("\n============ MOCK CREDENTIALS FOR TESTING =============")
print("Business: Phone: 9999999999, Password: password123")
print("Customer: Phone: 8888888888, Password: password123")
print("=========================================================\n") 