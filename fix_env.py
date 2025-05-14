#!/usr/bin/env python3

env_content = """# Katha Credit Management Application
# Environment Configuration

# Flask Secret Key (used for session encryption)
SECRET_KEY=652177888b9fce2db641304ad954bfc3912b391fb9d2a96b

# Supabase Configuration
SUPABASE_URL=https://ghbmfgomnqmffixfkdyp.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdoYm1mZ29tbnFtZmZpeGZrZHlwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDcxNDAxNTcsImV4cCI6MjA2MjcxNjE1N30.Fw750xiDWVPrl6ssr9p6AJTt--8zvnPoboxJiURvsOI
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdoYm1mZ29tbnFtZmZpeGZrZHlwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0NzE0MDE1NywiZXhwIjoyMDYyNzE2MTU3fQ.RnbSqdIM5A67NuKHDOTdpqpu6G2zKJfhMeQapGUI2kw

# Application Settings
FLASK_APP=app.py
FLASK_ENV=development
FLASK_DEBUG=1
PORT=5003
"""

with open('.env', 'w') as f:
    f.write(env_content)

print("Created .env file with correct Supabase credentials.") 