#!/usr/bin/env python
"""
This script helps you update your .env file with the proper Supabase credentials.
Run this script after setting up your simplified schema in Supabase.
"""

import os
import getpass
import uuid

# Check for existing .env file
env_file = '.env'
if os.path.exists(env_file):
    overwrite = input(f"The {env_file} file already exists. Overwrite? (y/n): ")
    if overwrite.lower() != 'y':
        print("Operation cancelled.")
        exit()

# Get Supabase credentials
print("\nYou'll need your Supabase project credentials.")
print("You can find these in your Supabase dashboard under Project Settings > API\n")

supabase_url = input("Enter your Supabase URL (e.g., https://abcdefg.supabase.co): ")
supabase_anon_key = input("Enter your Supabase anon key (public): ")
supabase_service_key = input("Enter your Supabase service role key (secret): ")

# Generate a random secret key for Flask
flask_secret_key = str(uuid.uuid4())

# Create .env file content
env_content = f"""# Supabase Connection Settings
SUPABASE_URL={supabase_url}
SUPABASE_KEY={supabase_anon_key}
SUPABASE_SERVICE_KEY={supabase_service_key}

# Flask Configuration
SECRET_KEY={flask_secret_key}
DEBUG=true
PORT=5002

# Application Configuration
AUTO_CREATE_USERS=true
UPLOAD_FOLDER=static/uploads
QR_CODES_FOLDER=static/qr_codes
"""

# Write to .env file
with open(env_file, 'w') as f:
    f.write(env_content)

print(f"\nCreated {env_file} file with your Supabase credentials.")
print("Now restart your Flask application for the changes to take effect.")
print("\nImportant: The service role key is used to bypass RLS policies.")
print("Make sure to keep your .env file secure and never commit it to version control.") 