#!/usr/bin/env python3
import os
import sys
import secrets

# Check if we're running as a script
if __name__ != "__main__":
    print("This file should be run as a script, not imported.")
    sys.exit(1)

# Use the provided Supabase information
print("Setting up Katha environment with the provided Supabase credentials...")

# Environment file path
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')

# Generate a secure secret key
secret_key = secrets.token_hex(24)

# Environment variable content with known credentials
env_content = f"""# Katha App Environment Variables
# Database Configuration
DB_HOST=db.ghbmfgomnqmffixfkdyp.supabase.co
DB_PORT=5432
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=postgres

# Supabase Configuration
SUPABASE_URL=https://ghbmfgomnqmffixfkdyp.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdoYm1mZ29tbnFtZmZpeGZrZHlwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDcxNDAxNTcsImV4cCI6MjA2MjcxNjE1N30.Fw750xiDWVPrl6ssr9p6AJTt--8zvnPoboxJiURvsOI

# Flask Configuration
SECRET_KEY={secret_key}
FLASK_ENV=development
"""

# Write the environment file
with open(env_path, 'w') as env_file:
    env_file.write(env_content)

print(f"Environment file created at: {env_path}")
print("Database connection using default Supabase password. If this doesn't work, run setup_env.py to enter your custom password.")
print("\nYou can now run the application with: python app.py") 