#!/usr/bin/env python3
import os
import getpass
import sys

def create_env_file():
    """Creates a .env file with the necessary environment variables."""
    env_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    
    # Check if .env file already exists
    if os.path.exists(env_file_path):
        overwrite = input("The .env file already exists. Overwrite it? (y/n): ").lower()
        if overwrite != 'y':
            print("Setup cancelled. Existing .env file not modified.")
            return False
    
    # Supabase details from the provided information
    supabase_host = "db.ghbmfgomnqmffixfkdyp.supabase.co"
    supabase_url = "https://ghbmfgomnqmffixfkdyp.supabase.co"
    supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdoYm1mZ29tbnFtZmZpeGZrZHlwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDcxNDAxNTcsImV4cCI6MjA2MjcxNjE1N30.Fw750xiDWVPrl6ssr9p6AJTt--8zvnPoboxJiURvsOI"
    
    # Get database password
    db_password = getpass.getpass("Enter your Supabase database password: ")
    
    # Generate a secret key if needed
    secret_key = os.urandom(24).hex()
    
    # Create the env file content
    env_content = f"""# Katha App Environment Variables
# Database Configuration
DB_HOST={supabase_host}
DB_PORT=5432
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD={db_password}

# Supabase Configuration
SUPABASE_URL={supabase_url}
SUPABASE_KEY={supabase_key}

# Flask Configuration
SECRET_KEY={secret_key}
FLASK_ENV=development
"""
    
    # Write the env file
    with open(env_file_path, 'w') as env_file:
        env_file.write(env_content)
    
    print(f"Environment variables have been set up in {env_file_path}")
    print("For security reasons, never commit this file to your repository.")
    return True

def update_gitignore():
    """Updates .gitignore to include .env file"""
    gitignore_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.gitignore')
    
    # Check if .gitignore exists
    if not os.path.exists(gitignore_path):
        # Create new .gitignore
        with open(gitignore_path, 'w') as gitignore_file:
            gitignore_file.write("# Katha App .gitignore\n")
            gitignore_file.write(".env\n")
            gitignore_file.write("__pycache__/\n")
            gitignore_file.write("*.py[cod]\n")
            gitignore_file.write("*$py.class\n")
            gitignore_file.write("venv/\n")
            gitignore_file.write(".venv/\n")
            gitignore_file.write(".DS_Store\n")
        print(f"Created new .gitignore file at {gitignore_path}")
        return
    
    # Check if .env is already in .gitignore
    with open(gitignore_path, 'r') as gitignore_file:
        content = gitignore_file.read()
    
    if ".env" not in content:
        with open(gitignore_path, 'a') as gitignore_file:
            gitignore_file.write("\n# Environment variables\n")
            gitignore_file.write(".env\n")
        print("Added .env to .gitignore")
    else:
        print(".env already in .gitignore")

def main():
    print("Katha App Environment Setup")
    print("===========================")
    print("This script will set up the necessary environment variables for your Katha application.")
    
    success = create_env_file()
    if success:
        update_gitignore()
        print("\nSetup complete!")
        print("You can now run your application using: python app.py")
    
if __name__ == "__main__":
    main() 