import os
import subprocess

# Set environment variables
os.environ['SUPABASE_URL'] = 'https://ghbmfgomnqmffixfkdyp.supabase.co'
os.environ['SUPABASE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdoYm1mZ29tbnFtZmZpeGZrZHlwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDcxNDAxNTcsImV4cCI6MjA2MjcxNjE1N30.Fw750xiDWVPrl6ssr9p6AJTt--8zvnPoboxJiURvsOI'
os.environ['SUPABASE_SERVICE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdoYm1mZ29tbnFtZmZpeGZrZHlwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0NzE0MDE1NywiZXhwIjoyMDYyNzE2MTU3fQ.RnbSqdIM5A67NuKHDOTdpqpu6G2zKJfhMeQapGUI2kw'
os.environ['SECRET_KEY'] = 'flask_secret_key_123456789'
os.environ['DEBUG'] = 'true'
os.environ['PORT'] = '5003'
os.environ['AUTO_CREATE_USERS'] = 'true'
os.environ['UPLOAD_FOLDER'] = 'static/uploads'
os.environ['QR_CODES_FOLDER'] = 'static/qr_codes'

print("Environment variables set successfully!")

# Run the Flask app in a subprocess, passing the environment variables
subprocess.run(["python", "/Users/sreemadhav/SreeMadhav/Katha/app.py"]) 