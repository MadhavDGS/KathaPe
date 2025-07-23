"""
Common utilities and configurations shared between customer and business Flask apps
"""
from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash, send_from_directory
import os
import uuid
import json
import traceback
import time
import requests
import socket
import threading
import psycopg2
import psycopg2.extras
from psycopg2.pool import ThreadedConnectionPool
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from functools import wraps
from dotenv import load_dotenv
import sys
import logging
import io
import base64
import qrcode
from PIL import Image

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Check if running on Render
RENDER_DEPLOYMENT = os.environ.get('RENDER', False)

# Environment variables - UPDATE THESE WITH YOUR NEW DATABASE URLs
# Internal URL (for use within Render's network):
DATABASE_URL = 'YOUR_NEW_INTERNAL_DATABASE_URL_HERE'
# External URL (for use outside Render's network):
EXTERNAL_DATABASE_URL = 'YOUR_NEW_EXTERNAL_DATABASE_URL_HERE'

# For local development, allow override via environment variables
DATABASE_URL = os.environ.get('DATABASE_URL', DATABASE_URL)
EXTERNAL_DATABASE_URL = os.environ.get('EXTERNAL_DATABASE_URL', EXTERNAL_DATABASE_URL)

# Set environment variables from hardcoded values only if not already set
os.environ.setdefault('DATABASE_URL', DATABASE_URL)
os.environ.setdefault('SECRET_KEY', 'fc36290a52f89c1c92655b7d22b198e4')
os.environ.setdefault('UPLOAD_FOLDER', 'static/uploads')

# On Render, configure optimized settings
if RENDER_DEPLOYMENT:
    print("RENDER MODE: Optimizing for improved performance")
    # Disable PIL completely to save memory
    Image = None
    qrcode = None
    
    # Aggressive performance settings for Render
    DB_RETRY_ATTEMPTS = 2
    DB_RETRY_DELAY = 1.0
    DB_QUERY_TIMEOUT = 30  # Increase timeout to prevent worker timeouts
    RENDER_QUERY_LIMIT = 10  # Limit number of results returned in queries
    RENDER_DASHBOARD_LIMIT = 5  # Limit items shown on dashboard
else:
    # Normal settings for development
    DB_RETRY_ATTEMPTS = 3
    DB_RETRY_DELAY = 1  # seconds
    DB_QUERY_TIMEOUT = 5  # seconds
    RENDER_QUERY_LIMIT = 50  # Higher limit for local development
    RENDER_DASHBOARD_LIMIT = 10  # Higher limit for local development

# Add request logging middleware
class RequestLoggerMiddleware:
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        request_time = time.time()
        path = environ.get('PATH_INFO', '')
        method = environ.get('REQUEST_METHOD', '')
        
        logger.info(f"REQUEST START: {method} {path}")
        
        def custom_start_response(status, headers, exc_info=None):
            duration = time.time() - request_time
            logger.info(f"REQUEST END: {method} {path} - Status: {status} - Duration: {duration:.3f}s")
            return start_response(status, headers, exc_info)
        
        try:
            return self.app(environ, custom_start_response)
        except Exception as e:
            logger.error(f"CRITICAL ERROR: {method} {path} - {str(e)}")
            logger.error(traceback.format_exc())
            custom_start_response('500 Internal Server Error', [('Content-Type', 'text/html')])
            error_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Error - KathaPe</title>
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    body {{ font-family: Arial, sans-serif; text-align: center; padding: 20px; }}
                    h1 {{ color: #e74c3c; }}
                    .error-box {{ 
                        background-color: #f8d7da; 
                        border: 1px solid #f5c6cb; 
                        border-radius: 5px; 
                        padding: 20px; 
                        margin: 20px auto; 
                        max-width: 800px;
                        text-align: left;
                        overflow: auto;
                    }}
                    .btn {{ 
                        display: inline-block; 
                        background-color: #5c67de; 
                        color: white; 
                        padding: 10px 20px; 
                        text-decoration: none; 
                        border-radius: 5px; 
                        margin-top: 20px; 
                    }}
                </style>
            </head>
            <body>
                <h1>Server Error</h1>
                <p>We encountered a problem processing your request.</p>
                <div class="error-box">
                    <strong>Error details:</strong><br>
                    {str(e)}
                    <hr>
                    <pre>{traceback.format_exc()}</pre>
                </div>
                <a href="/" class="btn">Go Back Home</a>
            </body>
            </html>
            """
            return [error_html.encode('utf-8')]

# PostgreSQL connection pool
db_pool = None

# Initialize the PostgreSQL connection pool
def init_db_pool():
    global db_pool
    
    if db_pool is not None:
        return True

    # For local development, don't fail if database is not available
    print("Initializing PostgreSQL connection pool...")
    
    # Try internal URL first, fallback to external URL if needed
    for db_url, url_type in [(DATABASE_URL, "internal"), (EXTERNAL_DATABASE_URL, "external")]:
        try:
            db_pool = ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                dsn=db_url,
                cursor_factory=psycopg2.extras.DictCursor
            )
            print(f"PostgreSQL connection pool initialized successfully with {url_type} URL")
            return True
        except Exception as e:
            print(f"ERROR initializing PostgreSQL connection pool with {url_type} URL: {str(e)}")
    
    # If we reach here, database connection failed
    print("WARNING: Could not connect to database. Application will run in limited mode.")
    print("Some features requiring database access will not be available.")
    return False

# Get a connection from the pool with retry
def get_db_connection():
    global db_pool
    
    if db_pool is None:
        if not init_db_pool():
            return None
    
    for attempt in range(DB_RETRY_ATTEMPTS):
        try:
            conn = db_pool.getconn()
            # Test connection
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            return conn
        except Exception as e:
            if attempt < DB_RETRY_ATTEMPTS - 1:
                print(f"Connection attempt {attempt+1} failed: {str(e)}. Retrying...")
                time.sleep(DB_RETRY_DELAY)
            else:
                print(f"Failed to get database connection after {DB_RETRY_ATTEMPTS} attempts: {str(e)}")
                return None

# Return a connection to the pool
def release_db_connection(conn):
    global db_pool
    if db_pool is not None and conn is not None:
        try:
            db_pool.putconn(conn)
        except Exception as e:
            print(f"Error returning connection to pool: {str(e)}")

# Execute database query with connection management
def execute_query(query, params=None, fetch_one=False, commit=True):
    conn = None
    try:
        conn = get_db_connection()
        if conn is None:
            print("ERROR: Failed to get database connection")
            return None
        
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            
            if commit:
                conn.commit()
                
            if cursor.description:
                if fetch_one:
                    return cursor.fetchone()
                else:
                    return cursor.fetchall()
            return None
    except Exception as e:
        print(f"Database query error: {str(e)}")
        if conn:
            conn.rollback()
        return None
    finally:
        if conn:
            release_db_connection(conn)

# Utility function to ensure valid UUIDs
def safe_uuid(id_value):
    """Ensure a value is a valid UUID string or generate a new one"""
    if not id_value:
        return str(uuid.uuid4())
    
    try:
        # Test if it's a valid UUID
        uuid.UUID(str(id_value))
        return str(id_value)
    except (ValueError, TypeError, AttributeError) as e:
        print(f"WARNING: Invalid UUID '{id_value}' - generating new UUID")
        return str(uuid.uuid4())

# Safe query wrapper for database operations
def query_table(table_name, query_type='select', fields='*', filters=None, data=None, limit=None):
    """
    Safely query a PostgreSQL table with proper error handling
    """
    try:
        # Handle different query types
        if query_type == 'select':
            # Build SELECT query
            query = f"SELECT {fields} FROM {table_name}"
            params = []
            
            # Apply filters
            if filters:
                where_conditions = []
                for field, op, value in filters:
                    if field.endswith('_id') and value:
                        value = safe_uuid(value)
                        
                    if op == 'eq':
                        where_conditions.append(f"{field} = %s")
                        params.append(value)
                    elif op == 'neq':
                        where_conditions.append(f"{field} != %s")
                        params.append(value)
                    # Add other operators as needed
                
                if where_conditions:
                    query += " WHERE " + " AND ".join(where_conditions)
            
            # Apply query limit only if explicitly provided
            if limit:
                query += f" LIMIT {limit}"
            
            # Execute query
            rows = execute_query(query, params)
            
            # Create a response class to match Supabase's structure
            class Response:
                def __init__(self, data):
                    self.data = data or []
            
            return Response(rows)
        
        elif query_type == 'insert':
            # Ensure UUID fields are valid
            if data and isinstance(data, dict):
                for key, value in data.items():
                    if key == 'id' or key.endswith('_id'):
                        data[key] = safe_uuid(value)
            
            if not data:
                return None
                
            # Build INSERT query
            columns = list(data.keys())
            placeholders = ["%s"] * len(columns)
            values = [data[col] for col in columns]
            
            query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({', '.join(placeholders)}) RETURNING *"
            
            # Execute query
            result = execute_query(query, values, commit=True)
            
            # Create a response class to match Supabase's structure
            class Response:
                def __init__(self, data):
                    self.data = data or []
            
            return Response(result)
            
        elif query_type == 'update':
            # Build UPDATE query
            if not data:
                return None
                
            set_parts = []
            values = []
            
            for key, value in data.items():
                if key == 'id' or key.endswith('_id'):
                    value = safe_uuid(value)
                
                set_parts.append(f"{key} = %s")
                values.append(value)
            
            query = f"UPDATE {table_name} SET {', '.join(set_parts)}"
            
            # Apply filters
            if filters:
                where_conditions = []
                for field, op, value in filters:
                    if field.endswith('_id'):
                        value = safe_uuid(value)
                        
                    if op == 'eq':
                        where_conditions.append(f"{field} = %s")
                        values.append(value)
                    # Add other operators as needed
                
                if where_conditions:
                    query += " WHERE " + " AND ".join(where_conditions)
            
            query += " RETURNING *"
            
            # Execute query
            result = execute_query(query, values, commit=True)
            
            # Create a response class to match Supabase's structure
            class Response:
                def __init__(self, data):
                    self.data = data or []
            
            return Response(result)
            
        elif query_type == 'delete':
            # Build DELETE query
            query = f"DELETE FROM {table_name}"
            params = []
            
            # Apply filters
            if filters:
                where_conditions = []
                for field, op, value in filters:
                    if field.endswith('_id'):
                        value = safe_uuid(value)
                        
                    if op == 'eq':
                        where_conditions.append(f"{field} = %s")
                        params.append(value)
                    # Add other operators as needed
                
                if where_conditions:
                    query += " WHERE " + " AND ".join(where_conditions)
            
            query += " RETURNING *"
            
            # Execute query
            result = execute_query(query, params, commit=True)
            
            # Create a response class to match Supabase's structure
            class Response:
                def __init__(self, data):
                    self.data = data or []
            
            return Response(result)
            
        else:
            print(f"ERROR: Invalid query type: {query_type}")
            
            # Create an empty response class to use as fallback
            class Response:
                def __init__(self):
                    self.data = []
            
            return Response()
        
    except Exception as e:
        print(f"Database query error: {str(e)}")
        traceback.print_exc()
        
        # Create an empty response class to use as fallback
        class Response:
            def __init__(self):
                self.data = []
        
        return Response()

# File upload helper function
def allowed_file(filename):
    """Check if a file has an allowed extension"""
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

# Authentication decorators
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def business_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('user_type') != 'business':
            flash('Access denied. Business account required.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def customer_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('user_type') != 'customer':
            flash('Access denied. Customer account required.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Function to generate QR code for business
def generate_business_qr_code(business_id, access_pin):
    if RENDER_DEPLOYMENT:
        return "static/images/placeholder_qr.png"
    
    try:
        # If QR code generation is not available, return placeholder
        try:
            import qrcode
            from PIL import Image
            QR_AVAILABLE = True
        except ImportError:
            print("QR code generation not available, using placeholder")
            return "static/images/placeholder_qr.png"
        
        # Make sure we have a valid PIN
        if not access_pin:
            access_pin = f"{int(datetime.now().timestamp()) % 10000:04d}"
            print(f"WARNING: No access pin provided, generating temporary: {access_pin}")
        
        # Format: "business:PIN" - this is what the scanner expects
        qr_data = f"business:{access_pin}"
        print(f"Generating QR code with data: {qr_data}")
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        qr_folder = 'static/qr_codes'
        
        # Ensure the directory exists
        if not os.path.exists(qr_folder):
            os.makedirs(qr_folder)
            
        qr_filename = os.path.join(qr_folder, f"{business_id}.png")
        img.save(qr_filename)
        return qr_filename
    except Exception as e:
        print(f"Error generating QR code: {str(e)}")
        # Return a default path that should exist
        return "static/images/placeholder_qr.png"

# Create Flask app with common configuration
def create_app(app_name='KathaPe'):
    # Load environment variables
    load_dotenv()
    
    app = Flask(app_name)
    app.secret_key = os.getenv('SECRET_KEY', 'fc36290a52f89c1c92655b7d22b198e4')
    
    # Set session to be permanent (30 days)
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
    
    # Apply our custom middleware
    app.wsgi_app = RequestLoggerMiddleware(app.wsgi_app)
    
    # Create folder structure
    upload_folder = os.getenv('UPLOAD_FOLDER', 'static/uploads')
    os.makedirs(upload_folder, exist_ok=True)
    qr_folder = 'static/qr_codes'
    os.makedirs(qr_folder, exist_ok=True)
    os.makedirs('static/images', exist_ok=True)
    
    # Set up file upload configuration
    app.config['UPLOAD_FOLDER'] = upload_folder
    app.config['QR_CODES_FOLDER'] = qr_folder
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload
    
    # Initialize database
    init_db_pool()
    
    return app

# Add template filter for datetime formatting
def format_datetime(value, format='%d %b %Y, %I:%M %p'):
    if isinstance(value, str):
        try:
            # Try to parse ISO format first
            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
            return dt.strftime(format)
        except:
            return value
    elif hasattr(value, 'strftime'):
        return value.strftime(format)
    else:
        return str(value)
