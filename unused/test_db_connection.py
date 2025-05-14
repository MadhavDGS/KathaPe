#!/usr/bin/env python3
import os
import sys
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Function to test database connection
def test_db_connection():
    print("Testing database connection...")
    
    try:
        # Get database credentials from environment
        db_host = os.getenv('DB_HOST', 'db.ghbmfgomnqmffixfkdyp.supabase.co')
        db_port = os.getenv('DB_PORT', '5432')
        db_name = os.getenv('DB_NAME', 'postgres')
        db_user = os.getenv('DB_USER', 'postgres')
        db_password = os.getenv('DB_PASSWORD', 'postgres')
        
        # Connect to the database
        print(f"Connecting to PostgreSQL database at {db_host}:{db_port}...")
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            dbname=db_name,
            user=db_user,
            password=db_password
        )
        
        # Create a cursor
        cursor = conn.cursor()
        
        # Check connection by executing a simple query
        cursor.execute("SELECT version();")
        db_version = cursor.fetchone()
        
        print(f"Successfully connected to the database!")
        print(f"PostgreSQL version: {db_version[0]}")
        
        # Try to fetch users table info if it exists
        try:
            cursor.execute("SELECT COUNT(*) FROM users;")
            user_count = cursor.fetchone()[0]
            print(f"Found {user_count} users in the database.")
        except Exception as e:
            print(f"Could not query users table: {str(e)}")
        
        # Close communication
        cursor.close()
        conn.close()
        
        return True
    
    except Exception as e:
        print(f"Error connecting to the database: {str(e)}")
        print("\nPossible solutions:")
        print("1. Make sure your database password is correct")
        print("2. Check if your IP is whitelisted in Supabase")
        print("3. Verify that the database service is running")
        print("4. Run the setup_env.py script to update credentials")
        
        return False

if __name__ == "__main__":
    test_db_connection() 