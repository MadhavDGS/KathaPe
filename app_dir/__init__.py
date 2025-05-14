import os
from flask import Flask, send_from_directory
from dotenv import load_dotenv
from supabase import create_client, Client
import sys

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import app instance from the parent app.py file
from app import app

load_dotenv()

# Anon key for regular user operations
supabase_url = os.getenv('SUPABASE_URL', 'https://ghbmfgomnqmffixfkdyp.supabase.co')
supabase_key = os.getenv('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdoYm1mZ29tbnFtZmZpeGZrZHlwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDcxNDAxNTcsImV4cCI6MjA2MjcxNjE1N30.Fw750xiDWVPrl6ssr9p6AJTt--8zvnPoboxJiURvsOI')
supabase: Client = create_client(supabase_url, supabase_key)

# Service role key for admin operations that bypass RLS policies
# For a real app, you should use a real service_role key which we set to the same as anon key for now
service_role_key = os.getenv('SUPABASE_SERVICE_KEY', supabase_key)
admin_supabase: Client = create_client(supabase_url, service_role_key)

def create_app():
    app = Flask(__name__, static_folder='static', template_folder='templates')
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev')
    app.supabase = supabase
    app.admin_supabase = admin_supabase
    
    # Explicit route for serving static files
    @app.route('/static/<path:filename>')
    def serve_static(filename):
        return send_from_directory(os.path.join(app.root_path, 'static'), filename)
    
    # Register blueprints as before
    from app.controllers import main, auth
    app.register_blueprint(main.bp)
    app.register_blueprint(auth.bp, url_prefix='/auth')
    return app 

__all__ = ['app'] 