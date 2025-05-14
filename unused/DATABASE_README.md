# Katha Database Setup

This README details the improved database setup for the Katha application.

## Overview

The database has been restructured to fix login/registration issues and improve overall functionality. The setup is now split into multiple files for better organization:

1. `supabase_setup_fixed.sql` - Core schema, tables, policies, and triggers
2. `supabase_helper_functions.sql` - Additional helper functions for data management
3. `supabase_seed_data.sql` - Demo data and customer/transaction management functions

## Key Improvements

### Extensions
- Added explicit creation of required extensions (uuid-ossp, pgcrypto)

### Authentication
- Fixed login_user function to properly verify passwords using pgcrypto
- Improved register_user function with better validation and error handling
- Added password hashing during registration

### Row-Level Security
- Enhanced policies for better access control
- Added policies for customers to view businesses they have credits with
- Fixed customer data access issues

### Data Management
- Added functions for customer search
- Added dashboard summary functions
- Added transactions that automatically update credit history
- Improved business and customer update functions

### Error Handling
- Better validation in all functions
- Descriptive error messages
- Proper customer and business relationship management

## Usage

### Setup

Run the database setup script:

```bash
./setup_database.sh
```

This will create the database schema, add helper functions, and populate demo data.

### Demo Accounts

The database includes demo accounts for testing:

**Business Account:**
- Phone: 9876543210
- Password: password123

**Customer Account:**
- Phone: 1234567890
- Password: password123

### Key Functions

#### Authentication
- `register_user(name, phone, password, email, user_type, use_email_otp)` - Register a new user
- `login_user(phone, password, user_type)` - Authenticate a user

#### Customer Management
- `add_customer_with_credit(business_id, name, phone, ...)` - Add a new customer to a business
- `get_customer_details(business_id, customer_id)` - Get detailed customer info
- `search_customers(business_id, search_text)` - Search customers by name/phone

#### Transactions
- `add_transaction(business_id, customer_id, amount, type, notes, created_by)` - Add a transaction

#### Business Management
- `get_business_dashboard(business_id)` - Get business summary and stats
- `update_business(business_id, name, description, ...)` - Update business details

## Database Structure

The database consists of the following main tables:

1. `users` - Authentication for both business owners and customers
2. `businesses` - Business profiles
3. `customers` - Customer profiles (with or without user accounts)
4. `customer_credits` - Credit balances for customers at each business
5. `transactions` - Transaction history (credits and payments)
6. `credit_history` - Detailed history of balance changes

## Additional Notes

- When a transaction is created, the customer credit balance is automatically updated
- Credit history is automatically generated
- Business owners can only see customers who have a relationship with their business
- Customers can only see their own data 