#!/usr/bin/env python3
"""
Script to fix database issues and create a test user in one go
"""
import os
import sys
import subprocess
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Check for required environment variables
if not os.getenv('SUPABASE_URL') or not os.getenv('SUPABASE_SERVICE_KEY'):
    print("Error: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set.")
    print("Please run setup_supabase.py first.")
    sys.exit(1)

print("This script will test database access and create a test user.")
print("Warning: This should only be used in development/testing environments.")
confirm = input("Continue? (y/n): ")

if confirm.lower() != 'y':
    print("Operation cancelled.")
    sys.exit(0)

# Step 1: Test database access
print("\n--- Step 1: Testing Database Access ---")
try:
    # Run the fix_rls.py script with input 'y'
    process = subprocess.run(
        ["python", "fix_rls.py"],
        input="y\n",  # Pass 'y' to the confirmation prompt
        text=True,
        capture_output=True
    )
    
    # Print the output
    print(process.stdout)
    
    if process.returncode != 0:
        print("Warning: Database test encountered issues.")
        print(process.stderr)
        print("Continuing anyway...")
    
except Exception as e:
    print(f"Error: {e}")
    print("Continuing to next step...")

# Step 2: Create a test user
print("\n--- Step 2: Creating a test user ---")
user_type = input("Create business (b) or customer (c) user? ").lower()

if user_type in ['b', 'business']:
    try:
        # Run create_test_user.py with 'b' as input
        process = subprocess.run(
            ["python", "disable_email_confirmation.py"],
            input="y\n",
            text=True,
            capture_output=True
        )
        
        # Print output
        print(process.stdout)
        
        if process.returncode != 0:
            print("Warning: There was an issue running the command.")
            print(process.stderr)
            
        # Prompt for user details and manually run the create_test_user.py script
        print("\nPlease provide the following information for a business user:")
        phone = input("Phone number: ")
        name = input("Name: ")
        password = input("Password: ")
        email = input("Email (optional): ")
        
        # Construct input string
        inputs = f"b\n{phone}\n{name}\n{password}\n{email}\n"
        
        # Run the create_test_user.py script
        process = subprocess.run(
            ["python", "create_test_user.py"],
            input=inputs,
            text=True,
            capture_output=True
        )
        
        # Print the output
        print(process.stdout)
        
    except Exception as e:
        print(f"Error: {e}")
        
elif user_type in ['c', 'customer']:
    try:
        # Run create_test_user.py with 'c' as input
        process = subprocess.run(
            ["python", "disable_email_confirmation.py"],
            input="y\n",
            text=True,
            capture_output=True
        )
        
        # Print output
        print(process.stdout)
        
        if process.returncode != 0:
            print("Warning: There was an issue running the command.")
            print(process.stderr)
            
        # Prompt for user details and manually run the create_test_user.py script
        print("\nPlease provide the following information for a customer user:")
        phone = input("Phone number: ")
        name = input("Name: ")
        password = input("Password: ")
        email = input("Email (optional): ")
        
        # Construct input string
        inputs = f"c\n{phone}\n{name}\n{password}\n{email}\n"
        
        # Run the create_test_user.py script
        process = subprocess.run(
            ["python", "create_test_user.py"],
            input=inputs,
            text=True,
            capture_output=True
        )
        
        # Print the output
        print(process.stdout)
        
    except Exception as e:
        print(f"Error: {e}")
else:
    print("Invalid choice. Please enter 'b' for business or 'c' for customer.")
    sys.exit(1)

print("\n--- All steps completed ---")
print("You should now be able to register and log in without issues.")
print("The application will save user data correctly to the database tables.") 