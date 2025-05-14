#!/usr/bin/env python3
import os
import sys
import secrets
from dotenv import load_dotenv
from supabase import create_client, Client

# Load existing environment variables if available
load_dotenv()

# Check if we're running as a script
if __name__ != "__main__":
    print("This file should be run as a script, not imported.")
    sys.exit(1)

# Supabase details from the provided information
supabase_url = "https://ghbmfgomnqmffixfkdyp.supabase.co"
supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdoYm1mZ29tbnFtZmZpeGZrZHlwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDcxNDAxNTcsImV4cCI6MjA2MjcxNjE1N30.Fw750xiDWVPrl6ssr9p6AJTt--8zvnPoboxJiURvsOI"
supabase_service_key = input("Enter your Supabase service role key (required to bypass RLS): ")

# Generate a secure secret key for Flask
secret_key = secrets.token_hex(24)

print("Setting up Katha with Supabase client...")

# Try to connect to Supabase to verify credentials
try:
    print("Testing Supabase connection...")
    supabase: Client = create_client(supabase_url, supabase_key)
    
    # Try a simple query to test the connection
    response = supabase.table('users').select("*").limit(1).execute()
    
    print("✅ Successfully connected to Supabase!")
    connection_successful = True
except Exception as e:
    print(f"❌ Failed to connect to Supabase: {e}")
    print("However, we'll still create the environment file.")
    connection_successful = False

# Environment file path
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')

# Environment variable content
env_content = f"""# Katha App Environment Variables
# Supabase Configuration
SUPABASE_URL={supabase_url}
SUPABASE_KEY={supabase_key}
SUPABASE_SERVICE_KEY={supabase_service_key}

# Flask Configuration
SECRET_KEY={secret_key}
FLASK_ENV=development
USE_SUPABASE_CLIENT=True
"""

# Write the environment file
with open(env_path, 'w') as env_file:
    env_file.write(env_content)

print(f"Environment file created at: {env_path}")

# Print next steps
print("\nNext steps:")
print("1. Install required dependencies: pip install supabase Flask python-dotenv")
print("2. Run the application: python app.py")

if not connection_successful:
    print("\nWarning: Supabase connection test failed.")
    print("Possible reasons:")
    print("1. Network issues (check your internet connection)")
    print("2. API key may be incorrect or expired")
    print("3. Supabase project may be in maintenance mode")
    print("\nYou may need to update your Supabase URL and key if they have changed.") 