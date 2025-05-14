#!/usr/bin/env python3
"""
Script to run the UUID fix SQL in Supabase
"""
import os
import sys
import requests
from dotenv import load_dotenv

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

print("This script will fix UUID handling in your Supabase database.")
print("It will create a safe_uuid function and fix any invalid UUIDs.")
confirm = input("Continue? (y/n): ")

if confirm.lower() != 'y':
    print("Operation cancelled.")
    sys.exit(0)

# Set up headers with the service role key
headers = {
    'apikey': SUPABASE_SERVICE_KEY,
    'Authorization': f'Bearer {SUPABASE_SERVICE_KEY}',
    'Content-Type': 'application/json'
}

# Read the SQL file
try:
    with open('fix_uuid_sql.sql', 'r') as f:
        sql_content = f.read()
except FileNotFoundError:
    print("Error: fix_uuid_sql.sql file not found.")
    print("Please make sure the file exists in the current directory.")
    sys.exit(1)

# Execute the SQL
try:
    print("Executing SQL fix...")
    
    response = requests.post(
        f"{SUPABASE_URL}/rest/v1/rpc/execute",
        headers=headers,
        json={
            "query": sql_content
        }
    )
    
    if response.status_code < 300:
        print("✅ UUID fix successfully applied!")
        try:
            result = response.json()
            print(f"Result: {result}")
        except:
            print("Result: (no JSON response)")
    else:
        print(f"⚠️ Warning: SQL execution returned status {response.status_code}")
        print(f"Response: {response.text}")
        
        # Try executing it as separate statements
        print("\nTrying to execute individual statements...")
        
        statements = sql_content.split(';')
        for i, stmt in enumerate(statements):
            if not stmt.strip():
                continue
                
            print(f"Executing statement {i+1}...")
            stmt_response = requests.post(
                f"{SUPABASE_URL}/rest/v1/rpc/execute",
                headers=headers,
                json={"query": stmt}
            )
            
            if stmt_response.status_code < 300:
                print(f"✅ Statement {i+1} executed successfully")
            else:
                print(f"⚠️ Statement {i+1} failed: {stmt_response.status_code} - {stmt_response.text}")
        
    print("\nUUID fix process completed.")
    print("You should now be able to use the application without UUID errors.")
    print("If you still encounter issues, please check the logs and database.")
    
except Exception as e:
    print(f"Error: {str(e)}")
    sys.exit(1) 