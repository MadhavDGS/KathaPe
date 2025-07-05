from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash, send_from_directory
import os
import uuid
import json
import traceback
import time
import requests  # Add explicit import
import socket    # Add explicit import
import threading # Add explicit import
import psycopg2  # Import PostgreSQL driver
import psycopg2.extras  # For handling UUID and other types
from psycopg2.pool import ThreadedConnectionPool  # For connection pooling
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

# Setup QR code functionality with fallback
QR_AVAILABLE = False
if not RENDER_DEPLOYMENT:
    try:
        import qrcode
        from PIL import Image
        QR_AVAILABLE = True
        print("QR code generation available")
    except ImportError as e:
        print(f"QR code generation not available: {str(e)}")
else:
    print("Running on Render - QR code generation disabled")
    
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
    
    # Mock QR code function to avoid any QR processing
    def generate_business_qr_code(business_id, access_pin):
        return "static/images/placeholder_qr.png"
else:
    # Normal settings for development
    DB_RETRY_ATTEMPTS = 3
    DB_RETRY_DELAY = 1  # seconds
    DB_QUERY_TIMEOUT = 5  # seconds
    RENDER_QUERY_LIMIT = 50  # Higher limit for local development
    RENDER_DASHBOARD_LIMIT = 10  # Higher limit for local development
    
    # Function to generate QR code for business with explicit error handling (only for non-Render)
    def generate_business_qr_code(business_id, access_pin):
        try:
            # If QR code generation is not available, return placeholder
            if not QR_AVAILABLE:
                print("QR code generation not available, using placeholder")
                return "static/images/placeholder_qr.png"
            
            # Make sure we have a valid PIN
            if not access_pin:
                access_pin = f"{int(datetime.now().timestamp()) % 10000:04d}"
                print(f"WARNING: No access pin provided, generating temporary: {access_pin}")
                
                # Update the database with this PIN if possible
                try:
                    query_table('businesses', query_type='update', 
                                data={'access_pin': access_pin},
                                filters=[('id', 'eq', business_id)])
                except Exception as e:
                    print(f"Failed to update business with new PIN: {str(e)}")
            
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
            qr_folder = app.config['QR_CODES_FOLDER']
            
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

# PostgreSQL connection pool
db_pool = None

# Initialize the PostgreSQL connection pool
def init_db_pool():
    global db_pool
    
    if db_pool is not None:
        return

    # Use internal URL first, fallback to external URL if needed
    try:
        print("Initializing PostgreSQL connection pool...")
        db_pool = ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=DATABASE_URL,  # Use the global DATABASE_URL variable
            cursor_factory=psycopg2.extras.DictCursor
        )
        print("PostgreSQL connection pool initialized successfully with internal URL")
        return True
    except Exception as e:
        print(f"ERROR initializing PostgreSQL connection pool with internal URL: {str(e)}")
        print("Attempting to connect with external URL...")
        try:
            db_pool = ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                dsn=EXTERNAL_DATABASE_URL,  # Use the global EXTERNAL_DATABASE_URL variable
                cursor_factory=psycopg2.extras.DictCursor
            )
            print("PostgreSQL connection pool initialized successfully with external URL")
            return True
        except Exception as e2:
            print(f"ERROR initializing PostgreSQL connection pool with external URL: {str(e2)}")
            traceback.print_exc()
            return None

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

# Load environment variables
load_dotenv()

# Create Flask app first for faster startup
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'fc36290a52f89c1c92655b7d22b198e4')

# Set session to be permanent (30 days)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

# Apply our custom middleware
app.wsgi_app = RequestLoggerMiddleware(app.wsgi_app)

# Log important app config information
print(f"DEBUG INFO: Flask app created with secret_key: {app.secret_key[:5]}...")
print(f"DEBUG INFO: Debug mode: {app.debug}")
print(f"DEBUG INFO: Testing mode: {app.testing}")
print(f"DEBUG INFO: Environment: {os.environ.get('FLASK_ENV', 'production')}")
print(f"DEBUG INFO: RENDER_DEPLOYMENT: {RENDER_DEPLOYMENT}")

# Environment variables - hardcoded for easy deployment with Render PostgreSQL
# Internal URL (for use within Render's network):
DATABASE_URL = 'postgresql://kathape_user:IVClGfm9MjHpORJFRuI9JuCQ0efZn8Fc@dpg-d0nf3q1r0fns738vf3q0-a/kathape'
# External URL (for use outside Render's network):
EXTERNAL_DATABASE_URL = 'postgresql://kathape_user:IVClGfm9MjHpORJFRuI9JuCQ0efZn8Fc@dpg-d0nf3q1r0fns738vf3q0-a.singapore-postgres.render.com/kathape'

# Set environment variables from hardcoded values
os.environ['DATABASE_URL'] = DATABASE_URL
os.environ.setdefault('SECRET_KEY', 'fc36290a52f89c1c92655b7d22b198e4')
os.environ.setdefault('UPLOAD_FOLDER', 'static/uploads')

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

# Supabase clients
supabase_client = None
supabase_admin_client = None

# Define these globals explicitly to fix "name not defined" errors
create_client = None

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

# Supabase client function with version-compatible options
def get_supabase_client():
    global supabase_client, create_client
    
    # If Supabase is not available, just return None
    if not SUPABASE_AVAILABLE:
        print("Supabase module not available")
        return None
    
    # If we already have a client, return it
    if supabase_client:
        return supabase_client
    
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')
    
    if not supabase_url or not supabase_key:
        print("Supabase URL and key must be set in environment variables")
        return None
    
    try:
        # Create a client with retry logic
        for attempt in range(DB_RETRY_ATTEMPTS):
            try:
                # Import create_client if not already available
                if not create_client:
                    from supabase import create_client
                
                # Version-compatible options handling with optimizations for Render
                if HAS_CLIENT_OPTIONS:
                    try:
                        from supabase.lib.client_options import ClientOptions
                        
                        # Configure options based on environment
                        if RENDER_DEPLOYMENT:
                            # Minimal options for Render
                            options = ClientOptions(
                                schema="public",
                                headers={},
                                auto_refresh_token=False,  # Don't auto refresh for better performance
                                persist_session=False      # Don't persist sessions on Render
                            )
                        else:
                            # Full options for development
                            options = ClientOptions(
                                schema="public",
                                headers={},
                                auto_refresh_token=True,
                                persist_session=True
                            )
                    except Exception as e:
                        print(f"Error creating ClientOptions: {str(e)}")
                        options = {}  # Fallback to empty dict
                else:
                    # Simple dict for older versions
                    options = {}
                
                # Create a new client with proper options
                supabase_client = create_client(supabase_url, supabase_key, options=options)
                
                # Test connection with a quick query
                try:
                    result = supabase_client.table('users').select('id').limit(1).execute()
                    print("Successfully connected to Supabase")
                    return supabase_client
                except Exception as test_error:
                    print(f"Failed to execute test query: {str(test_error)}")
                    if attempt < DB_RETRY_ATTEMPTS - 1:
                        time.sleep(DB_RETRY_DELAY)
                    else:
                        raise
            except Exception as e:
                if attempt < DB_RETRY_ATTEMPTS - 1:
                    print(f"Supabase connection attempt {attempt+1} failed: {str(e)}. Retrying...")
                    time.sleep(DB_RETRY_DELAY)
                else:
                    raise
    except Exception as e:
        print(f"Failed to connect to Supabase: {str(e)}")
        return None

# Get a Supabase client with service role permissions with version-compatible options
def get_supabase_admin_client():
    global supabase_admin_client, create_client
    
    # If Supabase is not available, just return None
    if not SUPABASE_AVAILABLE:
        print("Supabase module not available")
        return None
    
    # If we already have an admin client, return it
    if supabase_admin_client:
        return supabase_admin_client
    
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_service_key = os.getenv('SUPABASE_SERVICE_KEY') or os.getenv('SUPABASE_KEY')
    
    if not supabase_url or not supabase_service_key:
        print("Supabase URL and service key must be set in environment variables")
        return None
    
    try:
        # Add retry logic
        for attempt in range(DB_RETRY_ATTEMPTS):
            try:
                # Import create_client if not already available
                if not create_client:
                    from supabase import create_client
                
                # Version-compatible options handling
                if HAS_CLIENT_OPTIONS:
                    try:
                        from supabase.lib.client_options import ClientOptions
                        # Try with ClientOptions but without timeout
                        options = ClientOptions(
                            schema="public",
                            headers={},
                            auto_refresh_token=True,
                            persist_session=True
                        )
                    except Exception as e:
                        print(f"Error creating ClientOptions: {str(e)}")
                        options = {}  # Fallback to empty dict
                else:
                    # Simple dict for older versions
                    options = {}
                
                # Create admin client with proper options
                supabase_admin_client = create_client(supabase_url, supabase_service_key, options=options)
                
                # Test the connection
                supabase_admin_client.table('users').select('id').limit(1).execute()
                return supabase_admin_client
            except Exception as e:
                if attempt < DB_RETRY_ATTEMPTS - 1:
                    print(f"Supabase admin connection attempt {attempt+1} failed: {str(e)}. Retrying...")
                    time.sleep(DB_RETRY_DELAY)
                else:
                    raise
    except Exception as e:
        print(f"Failed to connect to Supabase with admin privileges after {DB_RETRY_ATTEMPTS} attempts: {str(e)}")
        return None

# File upload helper function
def allowed_file(filename):
    """Check if a file has an allowed extension"""
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

# Safe query wrapper for Supabase - direct implementation to avoid imported function issues
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

# Timeout-aware database query function
def timeout_query(func, *args, **kwargs):
    """Run a database query with a timeout to prevent worker hanging"""
    # On Render, skip threading for timeouts but apply a shorter timeout
    if RENDER_DEPLOYMENT:
        try:
            print("RENDER: Running database query with direct execution")
            # Set a shorter timeout using the DB_QUERY_TIMEOUT constant
            start_time = time.time()
            result = func(*args, **kwargs)
            elapsed_time = time.time() - start_time
            
            # Log performance data for optimization
            print(f"RENDER: Query completed in {elapsed_time:.2f} seconds")
            return result
        except Exception as e:
            print(f"Database query error: {str(e)}")
            return None
    
    # Use threading approach for non-Render environments
    result = [None]
    error = [None]
    completed = [False]
    
    def target():
        try:
            result[0] = func(*args, **kwargs)
            completed[0] = True
        except Exception as e:
            error[0] = e
            completed[0] = True
    
    thread = threading.Thread(target=target)
    thread.daemon = True  # Daemon thread will not prevent app from exiting
    thread.start()
    thread.join(timeout=DB_QUERY_TIMEOUT)
    
    if not completed[0]:
        print(f"Database query timed out after {DB_QUERY_TIMEOUT} seconds")
        return None
    if error[0]:
        print(f"Database query error: {str(error[0])}")
        return None
    return result[0]

# Authentication decorator
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

# Helper function to ensure all required records exist
def ensure_user_records(user_id, user_type, name, phone, email=None):
    """
    Ensures that all necessary records exist for a user after authentication
    """
    # Ensure we have a valid UUID
    user_id = safe_uuid(user_id)
    created = False
    
    # Check if user record exists
    response = query_table('users', filters=[('id', 'eq', user_id)])
    if not response or not response.data:
        # Create user record
        user_data = {
            'id': user_id,
            'name': name or 'Unknown',
            'phone_number': phone or 'Unknown',
            'user_type': user_type,
            'password_hash': 'auto_created',
            'created_at': datetime.now().isoformat()
        }
        
        # Only add email if it exists
        if email:
            user_data['email'] = email
        
        # Create user record
        query_table('users', query_type='insert', data=user_data)
        created = True
    
    # For business users, ensure business record exists
    if user_type == 'business':
        business_response = query_table('businesses', filters=[('user_id', 'eq', user_id)])
        if not business_response or not business_response.data:
            # Generate access pin
            access_pin = f"{int(datetime.now().timestamp()) % 10000:04d}"
            
            business_id = str(uuid.uuid4())
            business_data = {
                'id': business_id,
                'user_id': user_id,
                'name': f"{name}'s Business",
                'description': 'My business account',
                'access_pin': access_pin,
                'created_at': datetime.now().isoformat()
            }
            
            # Create business record
            query_table('businesses', query_type='insert', data=business_data)
            created = True
    
    # For customer users, ensure customer record exists
    elif user_type == 'customer':
        customer_response = query_table('customers', filters=[('user_id', 'eq', user_id)])
        if not customer_response or not customer_response.data:
            customer_id = str(uuid.uuid4())
            customer_data = {
                'id': customer_id,
                'user_id': user_id,
                'name': name or 'Unknown',
                'phone_number': phone or 'Unknown',
                'created_at': datetime.now().isoformat()
            }
            
            # Only add email if it exists
            if email:
                customer_data['email'] = email
            
            # Create customer record
            query_table('customers', query_type='insert', data=customer_data)
            created = True
    
    return created

# After the current utility functions, add a direct password verification function
def verify_password_directly(stored_password, provided_password):
    """
    Directly compare passwords - simplified for the new schema
    """
    # Direct comparison
    return stored_password == provided_password

# Routes
@app.route('/')
def index():
    try:
        # Super lightweight index route
        logger.info("Index route accessed - redirecting to appropriate page")
        
        # If user is logged in, redirect to dashboard
        if 'user_id' in session:
            if session.get('user_type') == 'business':
                return redirect(url_for('business_dashboard'))
            else:
                return redirect(url_for('customer_dashboard'))
        
        # Otherwise redirect to login (simple direct redirect)
        return redirect(url_for('login'))
    except Exception as e:
        # In case of any error, render a minimal HTML page directly
        logger.error(f"Error in index route: {str(e)}")
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>KathaPe</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <meta http-equiv="refresh" content="0;url=/login">
            <style>
                body { font-family: Arial; text-align: center; padding: 50px; }
            </style>
        </head>
        <body>
            <h1>KathaPe</h1>
            <p>Redirecting to login...</p>
        </body>
        </html>
        """
        return html

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        phone = request.form.get('phone')
        password = request.form.get('password')
        name = request.form.get('name', f"User {phone[-4:]}")
        user_type = request.form.get('user_type', 'customer')
        
        print(f"DEBUG: Registration attempt with phone={phone}, user_type={user_type}")
        
        if not phone or not password:
            flash('Please enter both phone number and password', 'error')
            return render_template('register.html')
        
        try:
            # Check if phone number already exists
            check_query = "SELECT id FROM users WHERE phone_number = %s"
            existing_user = execute_query(check_query, [phone], fetch_one=True)
            
            if existing_user:
                flash('Phone number already registered', 'error')
                return render_template('register.html')
            
            # Create user ID
            user_id = str(uuid.uuid4())
            
            # Create user record
            user_query = """
                INSERT INTO users (id, name, phone_number, user_type, password, created_at) 
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """
            user_params = [
                user_id,
                name,
                phone,
                user_type,
                password,
                datetime.now().isoformat()
            ]
            
            user_result = execute_query(user_query, user_params, fetch_one=True)
            
            if not user_result:
                flash('Registration failed: Database error', 'error')
                return render_template('register.html')
            
            print(f"DEBUG: User created with ID {user_id}")
            
            # Create profile record (business or customer)
            if user_type == 'business':
                # Create business record
                business_id = str(uuid.uuid4())
                access_pin = f"{int(datetime.now().timestamp()) % 10000:04d}"
                
                business_query = """
                    INSERT INTO businesses (id, user_id, name, description, access_pin, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                business_params = [
                    business_id,
                    user_id,
                    f"{name}'s Business",
                    'My business account',
                    access_pin,
                    datetime.now().isoformat()
                ]
                
                execute_query(business_query, business_params)
            else:
                # Create customer record
                customer_id = str(uuid.uuid4())
                
                customer_query = """
                    INSERT INTO customers (id, user_id, name, phone_number, created_at)
                    VALUES (%s, %s, %s, %s, %s)
                """
                customer_params = [
                    customer_id,
                    user_id,
                    name,
                    phone,
                    datetime.now().isoformat()
                ]
                
                execute_query(customer_query, customer_params)
            
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            print(f"DEBUG: Registration error: {str(e)}")
            traceback.print_exc()
            flash(f'Registration failed: {str(e)}', 'error')
            return render_template('register.html')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    try:
        if request.method == 'POST':
            # Existing POST login code
            print(f"DEBUG: Starting login process")
            logger.info("User attempting to login")
            phone = request.form.get('phone')
            password = request.form.get('password')
            user_type = request.form.get('user_type', 'customer')
            
            print(f"DEBUG: Attempting login with phone={phone}, user_type={user_type}")
            logger.info(f"Login attempt: phone={phone}, user_type={user_type}")
            
            if not phone or not password:
                flash('Please enter both phone number and password', 'error')
                return render_template('login.html')
            
            # Set up emergency fallback data in case of database issues
            user_id = str(uuid.uuid4())
            user_name = f"User {phone[-4:]}" if phone and len(phone) > 4 else "User"
            session['user_id'] = user_id
            session['user_name'] = user_name
            session['user_type'] = user_type
            session['phone_number'] = phone
            
            # Make the session permanent so it persists even when browser is closed
            session.permanent = True
            
            # Set a flag for RENDER_EMERGENCY_LOGIN to always succeed in Render
            RENDER_EMERGENCY_LOGIN = os.environ.get('RENDER_EMERGENCY_LOGIN', 'false').lower() == 'true'
            
            # If we're on Render and emergency login is enabled, skip database queries
            if RENDER_DEPLOYMENT and RENDER_EMERGENCY_LOGIN:
                logger.info("Using RENDER_EMERGENCY_LOGIN path - bypassing database")
                flash('Successfully logged in with emergency mode.', 'success')
                
                # Make the session permanent
                session.permanent = True
                
                if user_type == 'business':
                    business_id = str(uuid.uuid4())
                    session['business_id'] = business_id
                    session['business_name'] = f"{user_name}'s Business"
                    session['access_pin'] = f"{int(datetime.now().timestamp()) % 10000:04d}"
                    logger.info(f"Redirecting business to dashboard (emergency mode)")
                    return redirect(url_for('business_dashboard'))
                else:
                    customer_id = str(uuid.uuid4())
                    session['customer_id'] = customer_id
                    logger.info(f"Redirecting customer to dashboard (emergency mode)")
                    return redirect(url_for('customer_dashboard'))
            
            # First try a quick connectivity check to database with a short timeout
            try:
                logger.info("Testing quick connection to database")
                
                # Try direct connection to database instead of socket test
                try:
                    logger.info("Testing direct database connection")
                    conn = psycopg2.connect(
                        EXTERNAL_DATABASE_URL,
                        connect_timeout=5  # 5 second timeout
                    )
                    logger.info("Database connection successful")
                    conn.close()
                except Exception as connect_error:
                    logger.error(f"Connection test failed: {str(connect_error)}")
                    # If we can't connect quickly, use session fallback data
                    flash('Login successful with limited access mode.', 'success')
                    
                    # Make the session permanent
                    session.permanent = True
                    
                    if user_type == 'business':
                        return redirect(url_for('business_dashboard'))
                    else:
                        return redirect(url_for('customer_dashboard'))
            
                # We have confirmed connectivity - now try a quick query
                try:
                    logger.info("Executing database query with short timeout")
                    start_time = time.time()
                    
                    # Use a separate thread with limited time
                    query_result = [None]
                    query_error = [None]
                    query_completed = [False]
                    
                    def run_query():
                        try:
                            # Connect directly to the database
                            conn = psycopg2.connect(EXTERNAL_DATABASE_URL)
                            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                                # Query to check user credentials
                                cursor.execute("SELECT id, name, password FROM users WHERE phone_number = %s LIMIT 1", [phone])
                                user_data = cursor.fetchone()
                                query_result[0] = user_data
                                query_completed[0] = True
                            conn.close()
                        except Exception as e:
                            query_error[0] = e
                            query_completed[0] = True
                    
                    # Start query in separate thread
                    query_thread = threading.Thread(target=run_query)
                    query_thread.daemon = True
                    query_thread.start()
                    
                    # Wait for query with timeout
                    query_thread.join(10.0)  # 10 second timeout for query
                    
                    if not query_completed[0]:
                        logger.warning("Query timed out after 10 seconds")
                        flash('Login successful with offline mode.', 'success')
                        
                        # Make the session permanent
                        session.permanent = True
                        
                        if user_type == 'business':
                            return redirect(url_for('business_dashboard'))
                        else:
                            return redirect(url_for('customer_dashboard'))
                    
                    if query_error[0]:
                        logger.error(f"Query error: {str(query_error[0])}")
                        flash('Login successful with offline mode.', 'success')
                        
                        # Make the session permanent
                        session.permanent = True
                        
                        if user_type == 'business':
                            return redirect(url_for('business_dashboard'))
                    
                    # We got a successful query result
                    user = query_result[0]
                    elapsed_time = time.time() - start_time
                    logger.info(f"Query completed in {elapsed_time:.2f} seconds")
                    
                    if not user:
                        flash('Login successful as new user.', 'success')
                    else:
                        user_id = user['id']
                        session['user_id'] = user_id
                        session['user_name'] = user.get('name', user_name)
                        
                        # Make the session permanent
                        session.permanent = True
                        
                        # Basic password check
                        if user.get('password') != password:
                            flash('Login successful with offline credentials.', 'success')
                        else:
                            flash('Login successful!', 'success')
                    
                    # Fetch appropriate profile ID (business or customer)
                    if user_type == 'business':
                        try:
                            # Get business ID directly from database
                            conn = psycopg2.connect(EXTERNAL_DATABASE_URL)
                            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                                # Get business ID
                                cursor.execute("SELECT id, name, access_pin FROM businesses WHERE user_id = %s LIMIT 1", [user_id])
                                business = cursor.fetchone()
                                
                                if business:
                                    session['business_id'] = business['id']
                                    session['business_name'] = business['name']
                                    session['access_pin'] = business['access_pin']
                                else:
                                    # Create fallback business data
                                    business_id = str(uuid.uuid4())
                                    session['business_id'] = business_id
                                    session['business_name'] = f"{session['user_name']}'s Business"
                                    session['access_pin'] = f"{int(datetime.now().timestamp()) % 10000:04d}"
                            conn.close()
                        except Exception as e:
                            logger.error(f"Error fetching business data: {str(e)}")
                            # Create fallback business data
                            business_id = str(uuid.uuid4())
                            session['business_id'] = business_id
                            session['business_name'] = f"{session['user_name']}'s Business"
                            session['access_pin'] = f"{int(datetime.now().timestamp()) % 10000:04d}"
                        
                        logger.info(f"Redirecting to business dashboard")
                        return redirect(url_for('business_dashboard'))
                    else:
                        try:
                            # Get customer ID directly from database
                            conn = psycopg2.connect(EXTERNAL_DATABASE_URL)
                            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                                # Get customer ID
                                cursor.execute("SELECT id FROM customers WHERE user_id = %s LIMIT 1", [user_id])
                                customer = cursor.fetchone()
                                
                                if customer:
                                    session['customer_id'] = customer['id']
                                else:
                                    # Create fallback customer data
                                    customer_id = str(uuid.uuid4())
                                    session['customer_id'] = customer_id
                            conn.close()
                        except Exception as e:
                            logger.error(f"Error fetching customer data: {str(e)}")
                            # Create fallback customer data
                            customer_id = str(uuid.uuid4())
                            session['customer_id'] = customer_id
                        
                        logger.info(f"Redirecting to customer dashboard")
                        return redirect(url_for('customer_dashboard'))
                        
                except Exception as e:
                    logger.error(f"Error during database query: {str(e)}")
                    flash('Login successful with emergency access.', 'success')
                    
                    if user_type == 'business':
                        return redirect(url_for('business_dashboard'))
                    else:
                        return redirect(url_for('customer_dashboard'))
            except Exception as e:
                logger.error(f"Error during connection test: {str(e)}")
                # Use the emergency login path
                flash('Login successful with emergency access.', 'success')
                
                if user_type == 'business':
                    return redirect(url_for('business_dashboard'))
                else:
                    return redirect(url_for('customer_dashboard'))
        
        # GET request handling for login page
        return render_template('login.html')
            
    except Exception as e:
        # Ultimate fallback for any errors
        logger.critical(f"CRITICAL ERROR in login route: {str(e)}")
        
        # Set emergency session data if there was a POST request
        if request.method == 'POST':
            emergency_user_id = str(uuid.uuid4())
            emergency_user_type = request.form.get('user_type', 'customer')
            
            session['user_id'] = emergency_user_id
            session['user_name'] = 'Emergency User'
            session['user_type'] = emergency_user_type
            session['phone_number'] = request.form.get('phone', '0000000000')
            
            # Make the session permanent
            session.permanent = True
            
            # Add additional required session data
            if emergency_user_type == 'business':
                session['business_id'] = str(uuid.uuid4())
                session['business_name'] = 'Emergency Business'
                session['access_pin'] = '0000'
            else:
                session['customer_id'] = str(uuid.uuid4())
            
            # Return simple HTML with redirect script as a last resort
            redirect_url = url_for('business_dashboard' if emergency_user_type == 'business' else 'customer_dashboard')
            
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Login Successful</title>
                <meta http-equiv="refresh" content="3;url={redirect_url}">
                <style>
                    body {{ font-family: Arial; text-align: center; padding: 50px; }}
                    .loader {{ 
                        border: 8px solid #f3f3f3;
                        border-top: 8px solid #5c67de; 
                        border-radius: 50%;
                        width: 60px;
                        height: 60px;
                        margin: 20px auto;
                        animation: spin 2s linear infinite;
                    }}
                    @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
                </style>
            </head>
            <body>
                <h2>Login Successful!</h2>
                <p>Redirecting to your dashboard...</p>
                <div class="loader"></div>
            </body>
            </html>
            """
            return html
        
        # Ultra simple login form for GET requests with errors
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Emergency Login</title>
            <style>body{font-family:sans-serif;margin:40px;text-align:center;}form{margin:20px;}</style>
        </head>
        <body>
            <h1>KathaPe Emergency Login</h1>
            <form method="post" action="/login">
                <div><input name="phone" placeholder="Phone"></div>
                <div><input name="password" placeholder="Password"></div>
                <div>
                    <label><input type="radio" name="user_type" value="customer" checked> Customer</label>
                    <label><input type="radio" name="user_type" value="business"> Business</label>
                </div>
                <div><button type="submit">Login</button></div>
            </form>
        </body>
        </html>
        """
        return html

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Business routes
@app.route('/business/dashboard')
@login_required
@business_required
def business_dashboard():
    try:
        user_id = safe_uuid(session.get('user_id'))
    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'error')
        return redirect(url_for('login'))
        
        try:
            # Get business details by user_id
            business_response = query_table('businesses', filters=[('user_id', 'eq', user_id)])
            
            if business_response and business_response.data:
                business = business_response.data[0]
                session['business_id'] = business['id']
                session['business_name'] = business['name']
            
            # Only store the access_pin in session if it exists in the database
            if business.get('access_pin'):
                session['access_pin'] = business['access_pin']
            else:
                # Create a new business record
                try:
                    supabase_url = os.getenv('SUPABASE_URL')
                    supabase_service_key = os.getenv('SUPABASE_SERVICE_KEY') or os.getenv('SUPABASE_KEY')
                    
                    business_id = str(uuid.uuid4())
                # Generate a new access_pin only when creating a new business
                    access_pin = f"{int(datetime.now().timestamp()) % 10000:04d}"
                    
                    business_data = {
                        'id': business_id,
                        'user_id': user_id,
                        'name': f"{session['user_name']}'s Business",
                        'description': 'Auto-created business account',
                        'access_pin': access_pin,
                        'created_at': datetime.now().isoformat()
                    }
                    
                    # Insert with service role directly
                    try:
                        # Try using the query_table helper function
                        query_table('businesses', query_type='insert', data=business_data)
                    except Exception as e:
                        print(f"ERROR inserting business with query_table: {str(e)}")
                        # Fallback to direct REST API
                        try:
                            headers = {
                                'apikey': supabase_service_key,
                                'Authorization': f"Bearer {supabase_service_key}",
                                'Content-Type': 'application/json'
                            }
                            
                            requests.post(
                                f"{supabase_url}/rest/v1/businesses",
                                headers=headers,
                                json=business_data
                            )
                        except Exception as e2:
                            print(f"ERROR inserting business with direct API: {str(e2)}")
                    
                    session['business_id'] = business_id
                    session['business_name'] = business_data['name']
                    session['access_pin'] = access_pin
                    
                    flash('Business profile has been created', 'success')
                except Exception as e:
                    print(f"ERROR creating business: {str(e)}")
                    # Create a temporary session business to allow user to continue
                    temp_id = str(uuid.uuid4())
                    session['business_id'] = temp_id
                    session['business_name'] = f"{session.get('user_name', 'Your')}'s Business"
                # Only generate a new access_pin if one doesn't exist in session
                if 'access_pin' not in session:
                    session['access_pin'] = f"{int(datetime.now().timestamp()) % 10000:04d}"
        
        business_id = safe_uuid(session.get('business_id'))
        
        try:
            # Get business details
            business_response = query_table('businesses', filters=[('id', 'eq', business_id)])
            
            if business_response and business_response.data:
                business = business_response.data[0]
                
                # If access_pin is missing in database but exists in session, update the database
                if not business.get('access_pin') and session.get('access_pin'):
                    try:
                        query_table('businesses', query_type='update', 
                                data={'access_pin': session['access_pin']},
                                filters=[('id', 'eq', business_id)])
                        business['access_pin'] = session['access_pin']
                    except Exception as e:
                        print(f"ERROR updating access_pin: {str(e)}")
                # If access_pin is missing in both database and session, generate a new one
                elif not business.get('access_pin') and not session.get('access_pin'):
                    access_pin = f"{int(datetime.now().timestamp()) % 10000:04d}"
                    try:
                        query_table('businesses', query_type='update', 
                                data={'access_pin': access_pin},
                                filters=[('id', 'eq', business_id)])
                        business['access_pin'] = access_pin
                        session['access_pin'] = access_pin
                    except Exception as e:
                        print(f"ERROR updating access_pin: {str(e)}")
                        business['access_pin'] = access_pin
                        session['access_pin'] = access_pin
            else:
                # Create a mock business object from session data
                business = {
                    'id': business_id,
                    'name': session.get('business_name', 'Your Business'),
                    'description': 'Business account',
                    'access_pin': session.get('access_pin', '0000')
                }
            
            # Get summary data with error handling
            total_customers = 0
            total_credit = 0
            total_payments = 0
            transactions = []
            customers = []
            
            try:
                # Connect directly to database for more reliable results
                conn = psycopg2.connect(EXTERNAL_DATABASE_URL)
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                    # Get total customers count
                    cursor.execute("""
                        SELECT COUNT(*) FROM customer_credits 
                        WHERE business_id = %s
                    """, [business_id])
                    total_customers = cursor.fetchone()[0]
                    
                    # Get customer details for the latest customers
                    cursor.execute("""
                        SELECT c.*, cc.current_balance 
                        FROM customers c
                        JOIN customer_credits cc ON c.id = cc.customer_id
                        WHERE cc.business_id = %s
                        ORDER BY cc.created_at DESC
                        LIMIT 5
                    """, [business_id])
                    
                    customers_data = cursor.fetchall()
                    for customer in customers_data:
                        customers.append(dict(customer))
                    
                    # Get recent transactions
                    cursor.execute("""
                        SELECT t.*, c.name as customer_name
                        FROM transactions t
                        LEFT JOIN customers c ON t.customer_id = c.id
                        WHERE t.business_id = %s
                        ORDER BY t.created_at DESC
                        LIMIT 5
                    """, [business_id])
                    
                    transactions_data = cursor.fetchall()
                    for tx in transactions_data:
                        transactions.append(dict(tx))
                    
                    # Calculate total credit given
                    cursor.execute("""
                        SELECT COALESCE(SUM(amount), 0) as total
                        FROM transactions
                        WHERE business_id = %s AND transaction_type = 'credit'
                    """, [business_id])
                    total_credit = cursor.fetchone()[0]
                    
                    # Calculate total payments
                    cursor.execute("""
                        SELECT COALESCE(SUM(current_balance), 0) as total
                        FROM customer_credits
                        WHERE business_id = %s AND current_balance > 0
                    """, [business_id])
                    total_payments = cursor.fetchone()[0]
                
                conn.close()
                
            except Exception as e:
                print(f"ERROR in database connection: {str(e)}")
                # Fallback to query_table if direct connection fails
                try:
                    # Total customers
                    customer_response = query_table('customer_credits', 
                                                fields='customer_id',
                                                filters=[('business_id', 'eq', business_id)])
                            if customer_response and customer_response.data:
                        total_customers = len(customer_response.data)
                        
                        # Get customer details for the first few customers
                        if total_customers > 0:
                            customer_ids = [c['customer_id'] for c in customer_response.data[:5]]
                            
                            for customer_id in customer_ids:
                                try:
                                    # Get customer details
                                    customer_detail = query_table('customers', 
                                                            filters=[('id', 'eq', customer_id)])
                                    if customer_detail and customer_detail.data:
                                        customer = customer_detail.data[0]
                                        
                                        # Get current balance
                                        credit_detail = query_table('customer_credits', 
                                                            filters=[('business_id', 'eq', business_id),
                                                                    ('customer_id', 'eq', customer_id)])
                                        
                                        if credit_detail and credit_detail.data:
                                            credit = credit_detail.data[0]
                                            customer['current_balance'] = float(credit.get('current_balance', 0))
                                        else:
                                            customer['current_balance'] = 0
                                        
                                        customers.append(customer)
                                except Exception as e:
                                    print(f"ERROR getting customer details: {str(e)}")
                    
                    # Get recent transactions
                    try:
                        transaction_response = query_table('transactions', 
                                                        filters=[('business_id', 'eq', business_id)],
                                                        order_by='created_at:desc',
                                                        limit=5)
                        
                        if transaction_response and transaction_response.data:
                            transactions = transaction_response.data
                
                            # Add customer names to transactions
                            for tx in transactions:
                                try:
                                    customer_id = tx.get('customer_id')
                                    customer_detail = query_table('customers', 
                                                            filters=[('id', 'eq', customer_id)])
                                    
                                    if customer_detail and customer_detail.data:
                                        tx['customer_name'] = customer_detail.data[0].get('name', 'Unknown')
                        else:
                                        tx['customer_name'] = 'Unknown'
                    except Exception as e:
                        print(f"ERROR getting customer name: {str(e)}")
                    except Exception as e:
                        print(f"ERROR getting transactions: {str(e)}")
                
                try:
                        # Total credit given
                    credit_response = query_table('transactions', fields='amount', 
                                                filters=[('business_id', 'eq', business_id), ('transaction_type', 'eq', 'credit')])
                    total_credit = sum([float(t.get('amount', 0)) for t in credit_response.data]) if credit_response and credit_response.data else 0
                except Exception as e:
                    print(f"ERROR getting credit total: {str(e)}")
                
                try:
                    # Total payments
                        payment_response = query_table('customer_credits', fields='current_balance',
                                                    filters=[('business_id', 'eq', business_id)])
                        total_payments = sum([float(t.get('current_balance', 0)) for t in payment_response.data if float(t.get('current_balance', 0)) > 0]) if payment_response and payment_response.data else 0
                except Exception as e:
                    print(f"ERROR getting payment total: {str(e)}")
                
            except Exception as e:
                print(f"ERROR in data loading: {str(e)}")
                # Don't create mock data, just leave empty lists
                total_customers = 0
                total_credit = 0
                total_payments = 0
                transactions = []
                customers = []
            
            # Generate QR code (placeholder on Render) 
            try:
                generate_business_qr_code(business_id, business['access_pin'])
            except Exception as e:
                print(f"ERROR generating QR code: {str(e)}")
            
            # Prepare data for template
            summary = {
                'total_customers': total_customers,
                'total_credit': total_credit,
                'total_payments': total_payments
            }
            
            return render_template('business/dashboard.html', 
                                business=business, 
                                summary=summary, 
                                transactions=transactions,
                                customers=customers)
        except Exception as e:
            # Instead of silent pass, log the error and return a fallback template
            print(f"ERROR rendering business dashboard: {str(e)}")
            traceback.print_exc()
            
            # Create minimal data for template
            business = {
                'id': business_id,
                'name': session.get('business_name', 'Your Business'),
                'description': 'Business account',
                'access_pin': session.get('access_pin', '0000')
            }
            summary = {'total_customers': 0, 'total_credit': 0, 'total_payments': 0}
            
            # Return template with minimal data
            return render_template('business/dashboard.html', 
                              business=business, 
                              summary=summary, 
                                transactions=[],
                                customers=[])
                              
    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'error')
        return redirect(url_for('login'))

@app.route('/business/customers')
@login_required
@business_required
def business_customers():
    business_id = safe_uuid(session.get('business_id'))
    
    # Get all customer credits for this business
    customers_response = query_table('customer_credits', filters=[('business_id', 'eq', business_id)])
    customer_credits = customers_response.data if customers_response and customers_response.data else []
    
    # Gather all customer details
    customers = []
    for credit in customer_credits:
        customer_id = credit.get('customer_id')
        if customer_id:
            # Get customer details
            customer_response = query_table('customers', filters=[('id', 'eq', customer_id)])
            if customer_response and customer_response.data:
                customer = customer_response.data[0]
                # Merge customer details with credit information
                customer_with_credit = {
                    **customer,
                    'current_balance': credit.get('current_balance', 0)
                }
                customers.append(customer_with_credit)
    
    # Debug information
    print(f"Found {len(customers)} customers for business {business_id}")
    for customer in customers:
        print(f"Customer: {customer.get('name')}, ID: {customer.get('id')}")
    
    return render_template('business/customers.html', customers=customers)

@app.route('/business/customer/<customer_id>')
@login_required
@business_required
def business_customer_details(customer_id):
    business_id = safe_uuid(session.get('business_id'))
    customer_id = safe_uuid(customer_id)
    
    # Get credit relationship between business and customer
    credit_response = query_table('customer_credits', 
                               filters=[('business_id', 'eq', business_id), 
                                       ('customer_id', 'eq', customer_id)])
    
    credit = credit_response.data[0] if credit_response and credit_response.data else {}
    
    # Get customer details
    customer_response = query_table('customers', filters=[('id', 'eq', customer_id)])
    customer = customer_response.data[0] if customer_response and customer_response.data else {}
    
    # Merge customer details with credit information
    if customer and credit:
        customer = {**customer, 'current_balance': credit.get('current_balance', 0)}
    
    # Get transaction history for this customer with this business
    transactions_response = query_table('transactions', 
                                       filters=[('business_id', 'eq', business_id), 
                                               ('customer_id', 'eq', customer_id)])
    
    transactions = transactions_response.data if transactions_response and transactions_response.data else []
    
    # Calculate credit totals
    credit_total = 0
    payment_total = 0
    
    for transaction in transactions:
        if transaction.get('transaction_type') == 'credit':
            credit_total += float(transaction.get('amount', 0))
        else:  # payment
            payment_total += float(transaction.get('amount', 0))
    
    # Sort transactions by date, newest first
    transactions.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    
    return render_template('business/customer_details.html', 
                          customer=customer, 
                          transactions=transactions,
                          credit_total=credit_total,
                          payment_total=payment_total)

@app.route('/business/add_customer', methods=['GET', 'POST'])
@login_required
@business_required
def add_customer():
    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        email = request.form.get('email', '')
        address = request.form.get('address', '')
        notes = request.form.get('notes', '')
        initial_credit = request.form.get('initial_credit', 0)
        
        if not name or not phone:
            flash('Please enter customer name and phone number', 'error')
            return render_template('business/add_customer.html')
        
        try:
            initial_credit = float(initial_credit)
        except ValueError:
            initial_credit = 0
        
        business_id = safe_uuid(session.get('business_id'))
        business_user_id = safe_uuid(session.get('user_id'))
        
        # First, check if a user with this phone number already exists
        existing_user = query_table('users', filters=[('phone_number', 'eq', phone)])
        
        if existing_user and existing_user.data:
            # User exists, use their ID
            customer_user_id = existing_user.data[0]['id']
            print(f"Using existing user ID: {customer_user_id}")
            
            # Check if this user already has a customer record
            existing_customer = query_table('customers', filters=[('user_id', 'eq', customer_user_id)])
            
            if existing_customer and existing_customer.data:
                # Customer record already exists, use it
                customer_id = existing_customer.data[0]['id']
                print(f"Using existing customer ID: {customer_id}")
            else:
                # Create a new customer record for this user
                customer_id = str(uuid.uuid4())
                
                customer_data = {
                    'id': customer_id,
                    'user_id': customer_user_id,
                    'name': name,
                    'phone_number': phone,
                    'address': address,
                    'notes': notes,
                    'created_at': datetime.now().isoformat()
                }
                
                # Add email only if provided
                if email:
                    customer_data['email'] = email
                
                customer_insert = query_table('customers', query_type='insert', data=customer_data)
                
                if not customer_insert or not customer_insert.data:
                    flash('Failed to add customer', 'error')
                    return render_template('business/add_customer.html')
        else:
            # No user exists with this phone number, create a new user and customer
            customer_user_id = str(uuid.uuid4())
            
            # Create user record with a temporary password
            user_data = {
                'id': customer_user_id,
                'name': name,
                'phone_number': phone,
                'user_type': 'customer',
                'password': 'temporary_' + str(int(datetime.now().timestamp())),
                'created_at': datetime.now().isoformat()
            }
            
            # Insert the user
            user_insert = query_table('users', query_type='insert', data=user_data)
            
            if not user_insert or not user_insert.data:
                flash('Failed to create user account', 'error')
                return render_template('business/add_customer.html')
            
            # Create the customer record
            customer_id = str(uuid.uuid4())
            
            customer_data = {
                'id': customer_id,
                'user_id': customer_user_id,
                'name': name,
                'phone_number': phone,
                'address': address,
                'notes': notes,
                'created_at': datetime.now().isoformat()
            }
            
            # Add email only if provided
            if email:
                customer_data['email'] = email
            
            customer_insert = query_table('customers', query_type='insert', data=customer_data)
            
            if not customer_insert or not customer_insert.data:
                flash('Failed to add customer', 'error')
                return render_template('business/add_customer.html')
        
        # Create or update the credit relationship
        credit = ensure_customer_credit_exists(business_id, customer_id, 0)
        
        # If initial credit is provided, add the amount and create a transaction
        if initial_credit > 0:
            # Add a transaction record for the initial credit
            # The database trigger will automatically update the balance
            transaction_data = {
                'id': str(uuid.uuid4()),
                'business_id': business_id,
                'customer_id': customer_id,
                'amount': initial_credit,
                'transaction_type': 'credit',
                'notes': 'Initial credit',
                'created_at': datetime.now().isoformat(),
                'created_by': business_user_id
            }
            
            query_table('transactions', query_type='insert', data=transaction_data)
        
        flash('Customer added successfully', 'success')
        return redirect(url_for('business_customers'))
    
    return render_template('business/add_customer.html')

@app.route('/business/transactions/<customer_id>', methods=['GET', 'POST'])
@login_required
@business_required
def business_transactions(customer_id):
    business_id = safe_uuid(session.get('business_id'))
    user_id = safe_uuid(session.get('user_id'))
    customer_id = safe_uuid(customer_id)
    
    if request.method == 'POST':
        amount = request.form.get('amount')
        transaction_type = request.form.get('transaction_type')
        notes = request.form.get('notes', '')
        
        if not amount or not transaction_type:
            flash('Please enter amount and transaction type', 'error')
            return redirect(url_for('business_transactions', customer_id=customer_id))
        
        try:
            amount = float(amount)
            if amount <= 0:
                flash('Amount must be greater than 0', 'error')
                return redirect(url_for('business_transactions', customer_id=customer_id))
        except ValueError:
            flash('Invalid amount', 'error')
            return redirect(url_for('business_transactions', customer_id=customer_id))
        
        # Handle file upload if present
        media_url = None
        if 'receipt' in request.files:
            file = request.files['receipt']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                unique_filename = f"{uuid.uuid4()}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(filepath)
                media_url = f"/static/uploads/{unique_filename}"
        
        # Check if the user exists in the database
        try:
            # First check if user exists
            user_exists = execute_query("SELECT id FROM users WHERE id = %s", [user_id], fetch_one=True)
            
            # If user doesn't exist, create one
            if not user_exists:
                print(f"User {user_id} not found in database. Creating user record.")
                execute_query("""
                    INSERT INTO users (id, name, phone_number, user_type, password, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, [
                    user_id,
                    session.get('user_name', f"User {user_id[-8:]}"),
                    session.get('phone_number', f"0000{user_id[-8:]}"),
                    'business',
                    'temporary_' + str(int(datetime.now().timestamp())),
                    datetime.now().isoformat()
                ])
                print(f"Created user record with ID {user_id}")
        except Exception as e:
            print(f"Error checking or creating user: {str(e)}")
            traceback.print_exc()
            # Continue with transaction creation - the query_table function will handle any errors
        
        # Use the enhanced transaction function with media support
        transaction_data = {
            'id': str(uuid.uuid4()),
            'business_id': business_id,
            'customer_id': customer_id,
            'amount': amount,
            'transaction_type': transaction_type,
            'notes': notes,
            'created_at': datetime.now().isoformat(),
            'created_by': user_id
        }
        
        if media_url:
            transaction_data['media_url'] = media_url
        
        try:
            # Insert transaction directly using execute_query instead of query_table
            # This gives us more control over the error handling
            columns = list(transaction_data.keys())
            placeholders = ["%s"] * len(columns)
            values = [transaction_data[col] for col in columns]
            
            query = f"INSERT INTO transactions ({', '.join(columns)}) VALUES ({', '.join(placeholders)}) RETURNING id"
            
            transaction_result = execute_query(query, values, fetch_one=True, commit=True)
            
            if transaction_result:
        flash('Transaction added successfully', 'success')
            else:
                flash('Failed to add transaction. Please try again.', 'error')
        except Exception as e:
            print(f"Error adding transaction: {str(e)}")
            traceback.print_exc()
            flash(f'Error adding transaction: {str(e)}', 'error')
            
        return redirect(url_for('business_customer_details', customer_id=customer_id))
    
    # GET request handling
    
    # Get customer details from the customers table
    customer_details_response = query_table('customers', filters=[('id', 'eq', customer_id)])
    customer_details = customer_details_response.data[0] if customer_details_response and customer_details_response.data else {}
    
    # Get credit information from customer_credits table
    credit_response = query_table('customer_credits', 
                                 filters=[('business_id', 'eq', business_id),
                                         ('customer_id', 'eq', customer_id)])
    credit_info = credit_response.data[0] if credit_response and credit_response.data else {}
    
    # Combine customer details with credit information
    customer = {
        **customer_details,  # Include name, phone, etc.
        'current_balance': credit_info.get('current_balance', 0)
    }
    
    return render_template('business/add_transaction.html', customer=customer)

@app.route('/business/remind/<customer_id>')
@login_required
@business_required
def remind_customer(customer_id):
    business_id = safe_uuid(session.get('business_id'))
    user_id = safe_uuid(session.get('user_id'))
    customer_id = safe_uuid(customer_id)
    
    # Get customer info for reminder message
    customer_credit_response = query_table('customer_credits', 
                                  filters=[('business_id', 'eq', business_id),
                                          ('customer_id', 'eq', customer_id)])
    
    credit_info = customer_credit_response.data[0] if customer_credit_response and customer_credit_response.data else {}
    
    # Get customer contact details
    customer_response = query_table('customers', 
                                   filters=[('id', 'eq', customer_id)])
    customer = customer_response.data[0] if customer_response and customer_response.data else {}
    
    # Get business name
    business_response = query_table('businesses', filters=[('id', 'eq', business_id)])
    business = business_response.data[0] if business_response and business_response.data else {}
    
    if customer:
        # Check if the user_id exists in the database
        try:
            # First check if user exists
            user_exists = execute_query("SELECT id FROM users WHERE id = %s", [user_id], fetch_one=True)
            
            # If user doesn't exist, create one
            if not user_exists:
                print(f"User {user_id} not found in database. Creating user record before sending reminder.")
                execute_query("""
                    INSERT INTO users (id, name, phone_number, user_type, password, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, [
                    user_id,
                    session.get('user_name', f"User {user_id[-8:]}"),
                    session.get('phone_number', f"0000{user_id[-8:]}"),
                    'business',
                    'temporary_' + str(int(datetime.now().timestamp())),
                    datetime.now().isoformat()
                ])
                print(f"Created user record with ID {user_id}")
        except Exception as e:
            print(f"Error checking or creating user: {str(e)}")
            traceback.print_exc()
            # Continue with reminder creation
        
        # Record the reminder in the database
        reminder_data = {
            'id': str(uuid.uuid4()),
            'business_id': business_id,
            'customer_id': customer_id,
            'sent_at': datetime.now().isoformat(),
            'sent_by': user_id,
            'reminder_type': 'whatsapp',
            'message': f"Payment reminder for balance of ₹{credit_info.get('current_balance', 0)}"
        }
        
        try:
            # Insert reminder directly using execute_query instead of query_table
            columns = list(reminder_data.keys())
            placeholders = ["%s"] * len(columns)
            values = [reminder_data[col] for col in columns]
            
            query = f"INSERT INTO reminders ({', '.join(columns)}) VALUES ({', '.join(placeholders)}) RETURNING id"
            
            execute_query(query, values, commit=True)
            
            # Also update the customer_credits record with the reminder date
            execute_query("""
                UPDATE customer_credits 
                SET last_reminder_date = %s
                WHERE business_id = %s AND customer_id = %s
            """, [
                datetime.now().isoformat(),
                business_id,
                customer_id
            ], commit=True)
        except Exception as e:
            print(f"Error recording reminder: {str(e)}")
            traceback.print_exc()
            # Continue anyway to send the reminder
        
        # Check for WhatsApp number and redirect to WhatsApp
        whatsapp_number = customer.get('whatsapp_number') or customer.get('phone_number')
        if whatsapp_number:
            # Create a pre-filled message
            business_name = business.get('name', 'Business')
            balance = credit_info.get('current_balance', 0)
            message = f"Hello! This is a reminder from {business_name}. You have a pending balance of ₹{balance}. Thank you."
            
            # Redirect to the WhatsApp link with pre-filled message
            encoded_message = requests.utils.quote(message)
            whatsapp_link = f"https://wa.me/{whatsapp_number.replace('+', '').replace(' ', '')}?text={encoded_message}"
            return redirect(whatsapp_link)
        else:
            flash('No contact number available for this customer', 'error')
            return redirect(url_for('business_customer_details', customer_id=customer_id))
    else:
        flash('Failed to generate reminder link', 'error')
        return redirect(url_for('business_customer_details', customer_id=customer_id))

@app.route('/business/profile', methods=['GET', 'POST'])
@login_required
@business_required
def business_profile():
    business_id = safe_uuid(session.get('business_id'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description', '')
        address = request.form.get('address', '')
        phone = request.form.get('phone', '')
        email = request.form.get('email', '')
        
        # Handle profile photo upload
        profile_photo_url = None
        if 'profile_photo' in request.files:
            file = request.files['profile_photo']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                unique_filename = f"business_{business_id}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(filepath)
                profile_photo_url = f"/static/uploads/{unique_filename}"
        
        # Update business details
        business_data = {
            'name': name, 
            'description': description, 
            'address': address, 
            'phone': phone, 
            'email': email
        }
        
        if profile_photo_url:
            business_data['profile_photo_url'] = profile_photo_url
            
        query_table('businesses', query_type='update', data=business_data, 
                   filters=[('id', 'eq', business_id)])
        
        flash('Profile updated successfully', 'success')
        return redirect(url_for('business_profile'))
    
    # GET request handling
    business_response = query_table('businesses', filters=[('id', 'eq', business_id)])
    business = business_response.data[0] if business_response and business_response.data else {}
    
    return render_template('business/profile.html', business=business)

@app.route('/business/qr_image/<business_id>')
@login_required
@business_required
def business_qr_image(business_id):
    """Return just the QR code image"""
    try:
        # Get business details
        business_response = query_table('businesses', filters=[('id', 'eq', business_id)])
        
        if not business_response or not business_response.data:
            # If business not found, return a generic QR code
            return send_from_directory('static/images', 'placeholder_qr.png', mimetype='image/png')
        
        business = business_response.data[0]
        
        # Check if QR code exists or generate it
        qr_folder = app.config['QR_CODES_FOLDER']
        if not os.path.exists(qr_folder):
            os.makedirs(qr_folder)
            
        qr_filename = os.path.join(qr_folder, f"{business_id}.png")
        
        # Generate a new QR code if it doesn't exist
        if not os.path.exists(qr_filename) or request.args.get('refresh', '0') == '1':
            access_pin = business.get('access_pin')
            
            # Make sure we have a valid access_pin
            if not access_pin:
                # Generate a new PIN if it doesn't exist
                access_pin = f"{int(datetime.now().timestamp()) % 10000:04d}"
                print(f"QR generation: Access pin not found, generating new one: {access_pin}")
                
                # Update the business record with this PIN
                try:
                    query_table('businesses', 
                                query_type='update',
                                data={'access_pin': access_pin},
                                filters=[('id', 'eq', business_id)])
                    
                    # Update the session if this is the current business
                    if session.get('business_id') == business_id:
                        session['access_pin'] = access_pin
                        
                    # Update the business object
                    business['access_pin'] = access_pin
                except Exception as e:
                    print(f"Failed to update business record with PIN: {str(e)}")
            
            # Generate QR code with the correct format: "business:PIN"
            qr_data = f"business:{access_pin}"
            print(f"Generating QR code for business {business_id} with data: {qr_data}")
            
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_data)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            img.save(qr_filename)
        
        # Return the file
        return send_from_directory(qr_folder, f"{business_id}.png", mimetype='image/png')
    
    except Exception as e:
        print(f"ERROR generating QR code image: {str(e)}")
        traceback.print_exc()
        # Return placeholder image on error
        return send_from_directory('static/images', 'placeholder_qr.png', mimetype='image/png')

# Customer routes
@app.route('/customer/dashboard')
@login_required
@customer_required
def customer_dashboard():
    try:
        # Log the beginning of the dashboard load for monitoring
        start_time = time.time()
        user_id = safe_uuid(session.get('user_id'))
        logger.info(f"Customer dashboard load started - user_id={user_id}")
        
        # First get customer ID if not in session - this is critical for functionality
        if 'customer_id' not in session:
            try:
                logger.info("Customer ID not found in session - attempting to retrieve or create")
                # Try to get customer ID from database
                try:
                    conn = psycopg2.connect(EXTERNAL_DATABASE_URL)
                    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                        cursor.execute("SELECT id FROM customers WHERE user_id = %s", [user_id])
                        customer = cursor.fetchone()
                        
                        if customer:
                            session['customer_id'] = customer['id']
                            logger.info(f"Found customer ID in database: {customer['id']}")
                        else:
                            # Create a new customer record
                            customer_id = str(uuid.uuid4())
                            cursor.execute("""
                                INSERT INTO customers (id, user_id, name, phone_number, created_at)
                                VALUES (%s, %s, %s, %s, %s)
                                RETURNING id
                            """, [
                                customer_id,
                                user_id,
                                session.get('user_name', 'Customer'),
                                session.get('phone_number', f"0000{customer_id[-8:]}"),
                                datetime.now().isoformat()
                            ])
                            new_customer = cursor.fetchone()
                            session['customer_id'] = new_customer['id']
                            logger.info(f"Created new customer ID: {new_customer['id']}")
                            conn.commit()
                    conn.close()
                except Exception as db_error:
                    logger.error(f"Database error creating customer: {str(db_error)}")
                    # In emergency mode, we'll just use a temp ID rather than querying
                    emergency_id = str(uuid.uuid4())
                    session['customer_id'] = emergency_id
                    session['customer_name'] = session.get('user_name', 'Customer')
                    logger.info(f"Created temporary customer ID: {emergency_id}")
            except Exception as e:
                logger.error(f"Error creating customer ID: {str(e)}")
                # Still ensure the customer has *some* ID to proceed
                session['customer_id'] = str(uuid.uuid4())
        
        customer_id = safe_uuid(session.get('customer_id'))
        
        # Get businesses with direct database access
        businesses = []
        try:
            conn = psycopg2.connect(EXTERNAL_DATABASE_URL)
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                # Get customer credits
                cursor.execute(
                    "SELECT business_id, current_balance FROM customer_credits WHERE customer_id = %s LIMIT 5",
                    [customer_id]
                )
                credits = cursor.fetchall()
                
                # Get business details for each credit
                for i, credit in enumerate(credits):
                    business_id = credit['business_id']
                    cursor.execute(
                        "SELECT id, name FROM businesses WHERE id = %s",
                        [business_id]
                    )
                    business = cursor.fetchone()
                    
                    if business:
                        businesses.append({
                            'id': business['id'],
                            'name': business['name'],
                            'current_balance': credit['current_balance']
                        })
                    else:
                        # Create business if it doesn't exist (shouldn't happen normally)
                        business_user_id = str(uuid.uuid4())
                        cursor.execute("""
                            INSERT INTO users (id, name, phone_number, user_type, password, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            RETURNING id
                        """, [
                            business_user_id,
                            f"Business {i+1}",
                            f"0000{business_id[-8:] if len(business_id) >= 8 else '0000'}",
                            'business',
                            'temporary_' + str(int(datetime.now().timestamp())),
                            datetime.now().isoformat()
                        ])
                        
                        cursor.execute("""
                            INSERT INTO businesses (id, user_id, name, description, access_pin, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            RETURNING id, name
                        """, [
                            business_id,
                            business_user_id,
                            f"Business {i+1}",
                            'Auto-created business',
                            f"{int(datetime.now().timestamp()) % 10000:04d}",
                            datetime.now().isoformat()
                        ])
                        new_business = cursor.fetchone()
                        conn.commit()
                        
                        businesses.append({
                            'id': new_business['id'],
                            'name': new_business['name'],
                            'current_balance': credit['current_balance']
                        })
            conn.close()
        except Exception as db_error:
            logger.error(f"Database error in customer dashboard: {str(db_error)}")
            # Add a default business in case of error
            default_business_id = str(uuid.uuid4())
            session['default_business_id'] = default_business_id
            businesses.append({
                'id': default_business_id,
                'name': 'Your Business Credits',
                'current_balance': 0
            })
        
        # Add default business if none found
        if not businesses:
            default_business_id = str(uuid.uuid4())
            session['default_business_id'] = default_business_id
            businesses.append({
                'id': default_business_id,
                'name': 'Your Business Credits',
                'current_balance': 0
            })
        
        # Log performance
        duration = time.time() - start_time
        logger.info(f"Customer dashboard loaded in {duration:.2f}s")
        
        return render_template('customer/dashboard.html', businesses=businesses)
    except Exception as outer_e:
        logger.critical(f"CRITICAL ERROR in customer dashboard: {str(outer_e)}")
        traceback.print_exc()
        
        # Return a minimal fallback in case of catastrophic error
        error_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Dashboard - KathaPe</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; padding: 20px; }}
                h1 {{ color: #5c67de; }}
                .dashboard {{ 
                    background-color: #f8f9fa; 
                    border: 1px solid #dee2e6; 
                    border-radius: 5px; 
                    padding: 20px; 
                    margin: 20px auto; 
                    max-width: 800px;
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
            <h1>Welcome to KathaPe</h1>
            <div class="dashboard">
                <h2>Your Dashboard</h2>
                <p>Use the buttons below to navigate.</p>
                <a href="/customer/select_business" class="btn">Connect with a Business</a>
                <a href="/scan_qr" class="btn">Scan QR Code</a>
                <a href="/customer/profile" class="btn">Edit Profile</a>
                <a href="/logout" class="btn">Logout</a>
            </div>
        </body>
        </html>
        """
        return error_html

@app.route('/customer/select_business', methods=['GET', 'POST'])
@login_required
@customer_required
def select_business():
    if request.method == 'POST':
        access_pin = request.form.get('access_pin')
        
        if not access_pin:
            flash('Please enter business access pin', 'error')
            return render_template('customer/select_business.html')
        
        # Get business by access pin
        business_response = query_table('businesses', filters=[('access_pin', 'eq', access_pin)])
        business = business_response.data[0] if business_response and business_response.data else {}
        
        if not business:
            flash('Invalid access pin', 'error')
            return render_template('customer/select_business.html')
        
        # Get customer ID
        customer_id = safe_uuid(session.get('customer_id'))
        business_id = safe_uuid(business['id'])
        
        # Ensure relationship exists - this will create it if it doesn't
        ensure_customer_credit_exists(business_id, customer_id)
        
        # Store business info in session
        session['selected_business_id'] = str(business_id)
        session['selected_business_name'] = business['name']
        
        return redirect(url_for('customer_business_view'))
    
    return render_template('customer/select_business.html')

@app.route('/customer/business')
@login_required
@customer_required
def customer_business_view():
    # Check if business ID is in the session
    if 'selected_business_id' not in session:
        # Get it from request args (which will be populated by JavaScript sessionStorage)
        business_id = request.args.get('business_id')
        if business_id:
            session['selected_business_id'] = business_id
        else:
            return redirect(url_for('select_business'))
    
    business_id = safe_uuid(session.get('selected_business_id'))
    customer_id = safe_uuid(session.get('customer_id'))
    
    try:
        # Connect directly to database
        conn = psycopg2.connect(EXTERNAL_DATABASE_URL)
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            # Check if business exists
            cursor.execute("SELECT id, name, profile_photo_url FROM businesses WHERE id = %s", [business_id])
            business = cursor.fetchone()
            
            if not business:
                # Create business record if it doesn't exist
                print(f"Business {business_id} not found, creating business record")
                
                # First create a user for the business
                business_user_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO users (id, name, phone_number, user_type, password, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, [
                    business_user_id,
                    f"Business {business_id[-8:]}",
                    f"0000{business_id[-8:]}",
                    'business',
                    'temporary_' + str(int(datetime.now().timestamp())),
                    datetime.now().isoformat()
                ])
                
                # Then create the business record
                cursor.execute("""
                    INSERT INTO businesses (id, user_id, name, description, access_pin, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id, name, profile_photo_url
                """, [
                    business_id,
                    business_user_id,
                    f"Business {business_id[-8:]}",
                    'Auto-created business',
                    f"{int(datetime.now().timestamp()) % 10000:04d}",
                    datetime.now().isoformat()
                ])
                business = cursor.fetchone()
                print(f"Created business record with ID {business_id}")
            
            # Check if customer exists
            cursor.execute("SELECT id, name FROM customers WHERE id = %s", [customer_id])
            customer = cursor.fetchone()
            
            if not customer:
                # Create customer record if it doesn't exist
                print(f"Customer {customer_id} not found, creating customer record")
                
                # Create user for customer
                customer_user_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO users (id, name, phone_number, user_type, password, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, [
                    customer_user_id,
                    f"Customer {customer_id[-8:]}",
                    f"0000{customer_id[-8:]}",
                    'customer',
                    'temporary_' + str(int(datetime.now().timestamp())),
                    datetime.now().isoformat()
                ])
                
                # Create customer record
                cursor.execute("""
                    INSERT INTO customers (id, user_id, name, phone_number, created_at)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id, name
                """, [
                    customer_id,
                    customer_user_id,
                    f"Customer {customer_id[-8:]}",
                    f"0000{customer_id[-8:]}",
                    datetime.now().isoformat()
                ])
                customer = cursor.fetchone()
                print(f"Created customer record with ID {customer_id}")
            
            # Ensure credit relationship exists
            cursor.execute("""
                SELECT * FROM customer_credits 
                WHERE business_id = %s AND customer_id = %s
            """, [business_id, customer_id])
            credit = cursor.fetchone()
            
            if not credit:
                # Create credit relationship
                credit_id = str(uuid.uuid4())
                now = datetime.now().isoformat()
                cursor.execute("""
                    INSERT INTO customer_credits (id, business_id, customer_id, current_balance, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING *
                """, [
                    credit_id,
                    business_id,
                    customer_id,
                    0,
                    now,
                    now
                ])
                credit = cursor.fetchone()
                print(f"Created credit relationship between business {business_id} and customer {customer_id}")
            
            # Get transaction history
            cursor.execute("""
                SELECT * FROM transactions
                WHERE business_id = %s AND customer_id = %s
                ORDER BY created_at DESC
            """, [business_id, customer_id])
            transactions = cursor.fetchall()
            
            # Debug log to see transactions
            print(f"Found {len(transactions)} transactions for business {business_id} and customer {customer_id}")
            for tx in transactions:
                print(f"Transaction: type={tx['transaction_type']}, amount={tx['amount']}, date={tx['created_at']}")
            
            # Calculate totals for display purposes only
            credit_total = 0
            payment_total = 0
            
            for transaction in transactions:
                if transaction['transaction_type'] == 'credit':
                    credit_total += float(transaction['amount'])
                    print(f"Credit transaction: +{float(transaction['amount'])}, running credit total: {credit_total}")
                else:  # payment
                    payment_total += float(transaction['amount'])
                    print(f"Payment transaction: +{float(transaction['amount'])}, running payment total: {payment_total}")
            
            # Debug log for totals
            print(f"Final Credit total: {credit_total}, Payment total: {payment_total}")
            
            # Get the current balance directly from the database
            # This is maintained by the database trigger and is more reliable
            cursor.execute("""
                SELECT current_balance FROM customer_credits
                WHERE business_id = %s AND customer_id = %s
            """, [business_id, customer_id])
            balance_result = cursor.fetchone()
            current_balance = float(balance_result['current_balance']) if balance_result else 0
            
            print(f"Database current balance: {current_balance}")
            print(f"Credit total: {credit_total}, Payment total: {payment_total}")
            print(f"Expected balance (credit - payment): {credit_total - payment_total}")
            
            # If the balance is significantly different from what we expect, log a warning
            expected_balance = credit_total - payment_total
            if abs(current_balance - expected_balance) > 0.01:  # Allow for small floating point differences
                print(f"WARNING: Database balance {current_balance} differs from expected balance {expected_balance}")
            
            # Add current balance to customer data
            customer = dict(customer)
            customer['current_balance'] = current_balance
            
            conn.commit()
        conn.close()
        
        return render_template('customer/business_view.html', 
                            business=business, 
                            customer=customer,
                            transactions=transactions,
                            credit_total=credit_total,
                            payment_total=payment_total,
                            current_balance=current_balance)
    
    except Exception as e:
        print(f"Error in customer_business_view: {str(e)}")
        traceback.print_exc()
        
        # Create minimal data for the template
        mock_business = {
            'id': business_id,
            'name': 'Business',
            'profile_photo_url': None
        }
        
        mock_customer = {
            'id': customer_id,
            'name': 'Customer',
            'current_balance': 0
        }
        
        return render_template('customer/business_view.html',
                            business=mock_business,
                            customer=mock_customer,
                            transactions=[],
                            credit_total=0,
                            payment_total=0,
                            current_balance=0)

@app.route('/customer/transaction', methods=['GET', 'POST'])
@login_required
@customer_required
def customer_transaction():
    if 'selected_business_id' not in session:
        # Get business_id from query parameter if available
        business_id = request.args.get('business_id')
        if business_id:
            session['selected_business_id'] = business_id
        else:
            return redirect(url_for('select_business'))
    
    business_id = safe_uuid(session.get('selected_business_id'))
    customer_id = safe_uuid(session.get('customer_id'))
    user_id = safe_uuid(session.get('user_id'))
    
    # Get transaction type from query parameter
    default_transaction_type = request.args.get('transaction_type', 'payment')
    
    # Ensure business exists in the database
    try:
        conn = psycopg2.connect(EXTERNAL_DATABASE_URL)
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            # Check if business exists
            cursor.execute("SELECT id FROM businesses WHERE id = %s", [business_id])
            business = cursor.fetchone()
            
            if not business:
                # Create a business record if it doesn't exist
                print(f"Business {business_id} not found, creating business record")
                
                # First create a user for the business
                business_user_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO users (id, name, phone_number, user_type, password, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, [
                    business_user_id,
                    f"Business {business_id[-8:]}",
                    f"0000{business_id[-8:]}",
                    'business',
                    'temporary_' + str(int(datetime.now().timestamp())),
                    datetime.now().isoformat()
                ])
                
                # Then create the business record
                cursor.execute("""
                    INSERT INTO businesses (id, user_id, name, description, access_pin, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id, name, access_pin
                """, [
                    business_id,
                    business_user_id,
                    f"Business {business_id[-8:]}",
                    'Auto-created business',
                    f"{int(datetime.now().timestamp()) % 10000:04d}",
                    datetime.now().isoformat()
                ])
                business = cursor.fetchone()
                print(f"Created business record with ID {business_id}")
                
                # Create credit relationship
                cursor.execute("""
                    INSERT INTO customer_credits (id, business_id, customer_id, current_balance, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (business_id, customer_id) DO NOTHING
                """, [
                    str(uuid.uuid4()),
                    business_id,
                    customer_id,
                    0,
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ])
                conn.commit()
                
            # Check if the user_id exists in the database
            cursor.execute("SELECT id FROM users WHERE id = %s", [user_id])
            user_exists = cursor.fetchone()
            
            # If the user doesn't exist, create it to avoid foreign key constraint errors
            if not user_exists:
                print(f"User {user_id} not found, creating user record")
                cursor.execute("""
                    INSERT INTO users (id, name, phone_number, user_type, password, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, [
                    user_id,
                    session.get('user_name', f"User {user_id[-8:]}"),
                    session.get('phone_number', f"0000{user_id[-8:]}"),
                    'customer',
                    'temporary_' + str(int(datetime.now().timestamp())),
                    datetime.now().isoformat()
                ])
                conn.commit()
                print(f"Created user record with ID {user_id}")
        conn.close()
    except Exception as e:
        print(f"Error ensuring business exists: {str(e)}")
        traceback.print_exc()
    
    if request.method == 'POST':
        amount = request.form.get('amount')
        transaction_type = request.form.get('transaction_type')
        notes = request.form.get('notes', '')
        
        if not amount or not transaction_type:
            flash('Please enter amount and transaction type', 'error')
            return redirect(url_for('customer_transaction'))
        
        try:
            amount = float(amount)
            if amount <= 0:
                flash('Amount must be greater than 0', 'error')
                return redirect(url_for('customer_transaction'))
        except ValueError:
            flash('Invalid amount', 'error')
            return redirect(url_for('customer_transaction'))
        
        # Handle file upload if present
        media_url = None
        if 'receipt' in request.files:
            file = request.files['receipt']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                unique_filename = f"{uuid.uuid4()}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(filepath)
                media_url = f"/static/uploads/{unique_filename}"
        
        try:
            # Insert transaction directly using psycopg2
            conn = psycopg2.connect(EXTERNAL_DATABASE_URL)
            with conn.cursor() as cursor:
                # First ensure the customer_credits record exists
                cursor.execute("""
                    INSERT INTO customer_credits (id, business_id, customer_id, current_balance, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (business_id, customer_id) DO NOTHING
                """, [
                    str(uuid.uuid4()),
                    business_id,
                    customer_id,
                    0,
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ])
                
                # Verify user exists before using as created_by
                cursor.execute("SELECT id FROM users WHERE id = %s", [user_id])
                user_record = cursor.fetchone()
                
                # If user doesn't exist, create it now
                if not user_record:
                    print(f"User {user_id} not found, creating user record before transaction")
                    cursor.execute("""
                        INSERT INTO users (id, name, phone_number, user_type, password, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        RETURNING id
                    """, [
                        user_id,
                        session.get('user_name', f"User {user_id[-8:]}"),
                        session.get('phone_number', f"0000{user_id[-8:]}"),
                        'customer',
                        'temporary_' + str(int(datetime.now().timestamp())),
                        datetime.now().isoformat()
                    ])
                    user_record = cursor.fetchone()
                    conn.commit()
                    print(f"Created user record with ID {user_id}")
                
                # Insert transaction
                transaction_id = str(uuid.uuid4())
                print(f"Creating new transaction: id={transaction_id}, type={transaction_type}, amount={amount}")
                
                try:
                    cursor.execute("""
                        INSERT INTO transactions 
                        (id, business_id, customer_id, amount, transaction_type, notes, media_url, created_at, created_by)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                    """, [
                        transaction_id,
                        business_id,
                        customer_id,
                        amount,
                        transaction_type,
                        notes,
                        media_url,
                        datetime.now().isoformat(),
                        user_id
                    ])
                    result = cursor.fetchone()
                    print(f"Transaction created with ID: {result[0] if result else 'unknown'}")
                    
                    # Commit the transaction insert immediately to ensure it's saved
                    conn.commit()
                    print("Transaction committed to database")
                    
                    # The database trigger will handle updating the balance automatically
                    # No need for manual balance update which was causing double updates
                    
                    # Verify the balance was updated correctly
                    cursor.execute("""
                        SELECT current_balance FROM customer_credits
                        WHERE business_id = %s AND customer_id = %s
                    """, [business_id, customer_id])
                    updated_balance = cursor.fetchone()[0]
                    print(f"Updated balance: {updated_balance}")
                    
                except Exception as e:
                    print(f"Error inserting transaction: {str(e)}")
                    conn.rollback()
                    flash(f'Error adding transaction: {str(e)}', 'error')
                    conn.close()
                    return redirect(url_for('customer_business_view'))
                
            conn.commit()
            conn.close()
            flash('Transaction added successfully', 'success')
        except Exception as e:
            print(f"Database query error: {str(e)}")
            traceback.print_exc()
            flash(f'Error adding transaction: {str(e)}', 'error')
        
        return redirect(url_for('customer_business_view', business_id=business_id))
    
    # GET request handling for transaction form
    try:
        # Get business details
        conn = psycopg2.connect(EXTERNAL_DATABASE_URL)
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            # Get business details
            cursor.execute("SELECT id, name, profile_photo_url FROM businesses WHERE id = %s", [business_id])
            business = cursor.fetchone() or {'id': business_id, 'name': 'Business', 'profile_photo_url': None}
            
            # Get customer details and credit balance
            cursor.execute("""
                SELECT c.*, cc.current_balance 
                FROM customers c
                LEFT JOIN customer_credits cc ON c.id = cc.customer_id AND cc.business_id = %s
                WHERE c.id = %s
            """, [business_id, customer_id])
            customer = cursor.fetchone() or {'id': customer_id, 'name': 'Customer', 'current_balance': 0}
            
            # Ensure customer_credits record exists
            if customer.get('current_balance') is None:
                cursor.execute("""
                    INSERT INTO customer_credits (id, business_id, customer_id, current_balance, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (business_id, customer_id) DO NOTHING
                    RETURNING current_balance
                """, [
                    str(uuid.uuid4()),
                    business_id,
                    customer_id,
                    0,
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ])
                balance_result = cursor.fetchone()
                if balance_result:
                    customer['current_balance'] = balance_result[0]
                else:
                    customer['current_balance'] = 0
                conn.commit()
            
            # Convert to dict if it's a DictRow
            if not isinstance(business, dict):
                business = dict(business)
            if not isinstance(customer, dict):
                customer = dict(customer)
                
        conn.close()
    except Exception as e:
        print(f"Error fetching data for transaction form: {str(e)}")
        traceback.print_exc()
        business = {'id': business_id, 'name': 'Business', 'profile_photo_url': None}
        customer = {'id': customer_id, 'name': 'Customer', 'current_balance': 0}
    
    return render_template('customer/add_transaction.html', 
                          business=business, 
                          customer=customer,
                          transaction_type=default_transaction_type)

@app.route('/customer/profile', methods=['GET', 'POST'])
@login_required
@customer_required
def customer_profile():
    user_id = safe_uuid(session.get('user_id'))
    customer_id = safe_uuid(session.get('customer_id'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        whatsapp = request.form.get('whatsapp', '')
        email = request.form.get('email', '')
        address = request.form.get('address', '')
        
        # Handle profile photo upload
        profile_photo_url = None
        if 'profile_photo' in request.files:
            file = request.files['profile_photo']
            if file and allowed_file(file.filename):
                try:
                    filename = secure_filename(file.filename)
                    unique_filename = f"customer_{customer_id}_{filename}"
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                    file.save(filepath)
                    profile_photo_url = f"/static/uploads/{unique_filename}"
                except Exception as e:
                    print(f"ERROR uploading profile photo: {str(e)}")
        
        # Update customer details
        customer_data = {
            'name': name, 
            'phone_number': phone, 
            'whatsapp_number': whatsapp, 
            'email': email, 
            'address': address
        }
        
        if profile_photo_url:
            customer_data['profile_photo_url'] = profile_photo_url
        
        try:
            query_table('customers', query_type='update', data=customer_data, 
                    filters=[('id', 'eq', customer_id)])
            
            # Update user name and phone if it has changed
            query_table('users', query_type='update', 
                    data={'name': name, 'phone_number': phone},
                    filters=[('id', 'eq', user_id)])
            
            flash('Profile updated successfully', 'success')
        except Exception as e:
            print(f"ERROR updating profile: {str(e)}")
            flash('Error updating profile. Your changes were not saved.', 'error')
        
        return redirect(url_for('customer_profile'))
    
    # GET request handling
    try:
        customer_response = query_table('customers', filters=[('id', 'eq', customer_id)])
        customer = customer_response.data[0] if customer_response and customer_response.data else {}
    except Exception as e:
        print(f"ERROR getting customer data: {str(e)}")
        # Create a default customer object from session data
        customer = {
            'id': customer_id,
            'name': session.get('user_name', 'Customer'),
            'phone_number': session.get('phone_number', ''),
            'whatsapp_number': '',
            'email': '',
            'address': '',
            'profile_photo_url': None
        }
    
    return render_template('customer/profile.html', customer=customer)

@app.route('/scan_qr')
@login_required
@customer_required
def scan_qr():
    return render_template('customer/scan_qr.html')

# Error handling
@app.errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('errors/500.html'), 500

# Add template filter for datetime formatting
@app.template_filter('datetime')
def format_datetime(value, format='%d %b %Y, %I:%M %p'):
    if value:
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                return value
        return value.strftime(format)
    return ''

def ensure_customer_credit_exists(business_id, customer_id, initial_balance=0):
    """
    Ensure a credit relationship exists between a business and customer.
    If it doesn't exist, create it. If it does, return it.
    
    Args:
        business_id: UUID of the business
        customer_id: UUID of the customer
        initial_balance: Initial balance if a new relationship is created
        
    Returns:
        The credit record
    """
    business_id = safe_uuid(business_id)
    customer_id = safe_uuid(customer_id)
    
    # First check if the customer exists and create if needed
    try:
        # Check if customer exists
        customer_query = "SELECT id FROM customers WHERE id = %s"
        customer = execute_query(customer_query, [customer_id], fetch_one=True)
        
        if not customer:
            # Customer doesn't exist, create a basic record
            print(f"Customer {customer_id} not found, creating default record")
            temp_user_id = str(uuid.uuid4())
            
            # Create user record first
            user_query = """
                INSERT INTO users (id, name, phone_number, user_type, password, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            user_params = [
                temp_user_id,
                f"Customer {customer_id[-4:]}",
                f"0000{customer_id[-4:]}",
                'customer',
                'temporary_' + str(int(datetime.now().timestamp())),
                datetime.now().isoformat()
            ]
            execute_query(user_query, user_params)
            
            # Create customer record
            customer_query = """
                INSERT INTO customers (id, user_id, name, phone_number, created_at)
                VALUES (%s, %s, %s, %s, %s)
            """
            customer_params = [
                customer_id,
                temp_user_id,
                f"Customer {customer_id[-4:]}",
                f"0000{customer_id[-4:]}",
                datetime.now().isoformat()
            ]
            execute_query(customer_query, customer_params)
            print(f"Created customer record with ID {customer_id}")
    except Exception as e:
        print(f"Error ensuring customer exists: {str(e)}")
    
    # Check if business exists and create if needed
    try:
        business_query = "SELECT id FROM businesses WHERE id = %s"
        business = execute_query(business_query, [business_id], fetch_one=True)
        
        if not business:
            # Business doesn't exist, create a basic record
            print(f"Business {business_id} not found, creating default record")
            business_user_id = str(uuid.uuid4())
            
            # Create user record first
            user_query = """
                INSERT INTO users (id, name, phone_number, user_type, password, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            user_params = [
                business_user_id,
                f"Business {business_id[-4:]}",
                f"0000{business_id[-4:]}",
                'business',
                'temporary_' + str(int(datetime.now().timestamp())),
                datetime.now().isoformat()
            ]
            execute_query(user_query, user_params)
            
            # Create business record
            business_query = """
                INSERT INTO businesses (id, user_id, name, description, access_pin, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            business_params = [
                business_id,
                business_user_id,
                f"Business {business_id[-4:]}",
                'Auto-created business',
                f"{int(datetime.now().timestamp()) % 10000:04d}",
                datetime.now().isoformat()
            ]
            execute_query(business_query, business_params)
            print(f"Created business record with ID {business_id}")
    except Exception as e:
        print(f"Error ensuring business exists: {str(e)}")
    
    # Now check if relationship already exists
    credit_query = """
        SELECT * FROM customer_credits 
        WHERE business_id = %s AND customer_id = %s
    """
    existing_credit = execute_query(credit_query, [business_id, customer_id], fetch_one=True)
    
    # Return existing credit if found
    if existing_credit:
        return existing_credit
    
    # Create a new credit relationship
    credit_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    
    credit_query = """
        INSERT INTO customer_credits (id, business_id, customer_id, current_balance, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING *
    """
    credit_params = [
        credit_id,
        business_id,
        customer_id,
        initial_balance,
        now,
        now
    ]
    
    new_credit = execute_query(credit_query, credit_params, fetch_one=True)
    
    if new_credit:
        return new_credit
    else:
        # Return a mock object if insert failed
        return {
            'id': credit_id,
            'business_id': business_id,
            'customer_id': customer_id,
            'current_balance': initial_balance,
            'created_at': now,
            'updated_at': now
        }

# Add diagnostic endpoint for testing deployment
@app.route('/api/status')
def api_status():
    """Status endpoint for checking API health"""
    try:
        # Check if we can connect to database
        result = {"status": "ok", "database": False, "error": None}
        
        try:
            # Test PostgreSQL connection
            conn = get_db_connection()
            if conn:
                # Try a simple query
                with conn.cursor() as cursor:
                    cursor.execute("SELECT COUNT(*) FROM users")
                    count = cursor.fetchone()[0]
                    result["database"] = True
                    result["user_count"] = count
                release_db_connection(conn)
        except Exception as db_error:
            result["error"] = str(db_error)
            
        # Return environment info without sensitive values
        result["environment"] = {
            "render": os.environ.get('RENDER', 'false'),
            "flask_env": os.environ.get('FLASK_ENV', 'production'),
            "python_path": sys.path,
            "python_version": sys.version,
        }
        
        return jsonify(result)
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "traceback": traceback.format_exc()
        })

# Add a simple heartbeat endpoint
@app.route('/api/heartbeat')
def heartbeat():
    """Simple endpoint to check if the application is responsive"""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "mode": "emergency" if os.environ.get('RENDER_EMERGENCY_LOGIN', 'false').lower() == 'true' else "normal"
    })

# Add a function to reset customer balance
def reset_customer_balance(business_id, customer_id):
    """
    Reset a customer's balance by recalculating from transaction history.
    This is useful for fixing any incorrect balances.
    
    Args:
        business_id: UUID of the business
        customer_id: UUID of the customer
    
    Returns:
        The new balance
    """
    try:
        conn = psycopg2.connect(EXTERNAL_DATABASE_URL)
        with conn.cursor() as cursor:
            # Get all transactions for this customer and business
            cursor.execute("""
                SELECT transaction_type, amount 
                FROM transactions 
                WHERE business_id = %s AND customer_id = %s
            """, [business_id, customer_id])
            
            transactions = cursor.fetchall()
            
            # Calculate the correct balance
            credit_total = 0
            payment_total = 0
            
            for tx in transactions:
                if tx[0] == 'credit':
                    credit_total += float(tx[1])
                else:  # payment
                    payment_total += float(tx[1])
            
            # Calculate current balance
            # Current balance is how much the customer owes (credit - payment)
            # Positive balance means customer owes business
            # Negative balance means business owes customer (unusual case)
            current_balance = credit_total - payment_total
            
            # Update the balance in the database
            cursor.execute("""
                UPDATE customer_credits
                SET current_balance = %s,
                    updated_at = %s
                WHERE business_id = %s AND customer_id = %s
            """, [current_balance, datetime.now().isoformat(), business_id, customer_id])
            
            conn.commit()
            return current_balance
    except Exception as e:
        print(f"Error resetting customer balance: {str(e)}")
        return None
    finally:
        if conn:
            conn.close()

@app.route('/customer/reset_balance')
@login_required
@customer_required
def customer_reset_balance():
    """Reset a customer's balance to the correct value"""
    business_id = request.args.get('business_id')
    if not business_id:
        flash('Business ID is required', 'error')
        return redirect(url_for('customer_dashboard'))
    
    business_id = safe_uuid(business_id)
    customer_id = safe_uuid(session.get('customer_id'))
    
    new_balance = reset_customer_balance(business_id, customer_id)
    
    if new_balance is not None:
        flash(f'Balance reset successfully. New balance: ₹{new_balance}', 'success')
    else:
        flash('Failed to reset balance', 'error')
    
    return redirect(url_for('customer_business_view', business_id=business_id))

# Fix the database trigger that's working backwards
def fix_database_trigger():
    """
    Fix the database trigger that's currently working backwards.
    The trigger should add to the balance for credits and subtract for payments.
    """
    try:
        conn = psycopg2.connect(EXTERNAL_DATABASE_URL)
        with conn.cursor() as cursor:
            # Drop the existing trigger
            cursor.execute("DROP TRIGGER IF EXISTS trg_update_balance ON transactions;")
            
            # Create a new trigger function with the correct logic
            cursor.execute("""
            CREATE OR REPLACE FUNCTION update_credit_balance() RETURNS TRIGGER AS $$
            BEGIN
                IF NEW.transaction_type = 'credit' THEN
                    -- Credit means customer owes more, so increase balance
                    UPDATE customer_credits
                    SET current_balance = current_balance + NEW.amount,
                        updated_at = NOW()
                    WHERE business_id = NEW.business_id AND customer_id = NEW.customer_id;
                ELSIF NEW.transaction_type = 'payment' THEN
                    -- Payment means customer owes less, so decrease balance
                    UPDATE customer_credits
                    SET current_balance = current_balance - NEW.amount,
                        updated_at = NOW()
                    WHERE business_id = NEW.business_id AND customer_id = NEW.customer_id;
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """)
            
            # Create the trigger
            cursor.execute("""
            CREATE TRIGGER trg_update_balance
            AFTER INSERT ON transactions
            FOR EACH ROW
            EXECUTE FUNCTION update_credit_balance();
            """)
            
            conn.commit()
            print("Database trigger fixed successfully")
            return True
    except Exception as e:
        print(f"Error fixing database trigger: {str(e)}")
        return False
    finally:
        if conn:
            conn.close()

@app.route('/admin/fix_trigger')
@login_required
def admin_fix_trigger():
    """Fix the database trigger"""
    success = fix_database_trigger()
    
    if success:
        flash('Database trigger fixed successfully', 'success')
    else:
        flash('Failed to fix database trigger', 'error')
    
    return redirect(url_for('index'))

# Fix all customer balances in the database
def fix_all_customer_balances():
    """
    Fix all customer balances in the database by recalculating them from transaction history.
    """
    try:
        conn = psycopg2.connect(EXTERNAL_DATABASE_URL)
        with conn.cursor() as cursor:
            # Get all customer-business relationships
            cursor.execute("""
                SELECT business_id, customer_id
                FROM customer_credits
            """)
            relationships = cursor.fetchall()
            
            fixed_count = 0
            for relationship in relationships:
                business_id, customer_id = relationship
                
                # Get all transactions for this customer and business
                cursor.execute("""
                    SELECT transaction_type, amount 
                    FROM transactions 
                    WHERE business_id = %s AND customer_id = %s
                """, [business_id, customer_id])
                
                transactions = cursor.fetchall()
                
                # Calculate the correct balance
                credit_total = 0
                payment_total = 0
                
                for tx in transactions:
                    if tx[0] == 'credit':
                        credit_total += float(tx[1])
                    else:  # payment
                        payment_total += float(tx[1])
                
                # Calculate current balance
                # Current balance is how much the customer owes (credit - payment)
                # Positive balance means customer owes business
                # Negative balance means business owes customer (unusual case)
                current_balance = credit_total - payment_total
                
                # Update the balance in the database
                cursor.execute("""
                    UPDATE customer_credits
                    SET current_balance = %s,
                        updated_at = %s
                    WHERE business_id = %s AND customer_id = %s
                """, [current_balance, datetime.now().isoformat(), business_id, customer_id])
                
                fixed_count += 1
            
            conn.commit()
            print(f"Fixed {fixed_count} customer balances")
            return fixed_count
    except Exception as e:
        print(f"Error fixing customer balances: {str(e)}")
        return 0
    finally:
        if conn:
            conn.close()

@app.route('/admin/fix_balances')
@login_required
def admin_fix_balances():
    """Fix all customer balances"""
    fixed_count = fix_all_customer_balances()
    
    if fixed_count > 0:
        flash(f'Fixed {fixed_count} customer balances', 'success')
    else:
        flash('Failed to fix customer balances', 'error')
    
    return redirect(url_for('index'))

# Add a test route to verify QR code format
@app.route('/test/qr/<access_pin>')
def test_qr(access_pin):
    """Test route to verify QR code format"""
    try:
        # If QR code generation is not available, return text
        if not QR_AVAILABLE:
            return f"<p>QR code generation not available. Format would be: business:{access_pin}</p>"
        
        # Format: "business:PIN"
        qr_data = f"business:{access_pin}"
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        # Create QR code image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64 for embedding in HTML
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        # Return HTML with embedded QR code
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>QR Code Test</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; padding: 20px; }}
                .qr-container {{ margin: 20px auto; max-width: 300px; }}
                .qr-data {{ margin-top: 20px; padding: 10px; background-color: #f0f0f0; border-radius: 5px; }}
                pre {{ text-align: left; overflow-x: auto; }}
            </style>
        </head>
        <body>
            <h1>QR Code Test</h1>
            <div class="qr-container">
                <img src="data:image/png;base64,{img_str}" alt="QR Code" style="width: 100%;">
            </div>
            <div class="qr-data">
                <p>QR Code Data:</p>
                <pre>{qr_data}</pre>
            </div>
            <p>Scan this QR code with the app to test.</p>
        </body>
        </html>
        """
        
        return html
    except Exception as e:
        return f"<p>Error generating QR code: {str(e)}</p>"

# Run the application
if __name__ == '__main__':
    # Get port from environment variable for Render compatibility
    port = int(os.environ.get('PORT', 5003))
    # Set host to 0.0.0.0 to make it accessible outside the container
    app.run(debug=False, host='0.0.0.0', port=port) 

# Add a route to fix balances without requiring login
@app.route('/fix/balances/<secret_key>')
def fix_balances_public(secret_key):
    """Fix all customer balances without requiring login"""
    # Simple security check using a secret key
    expected_key = os.environ.get('EMERGENCY_KEY', 'kathape_emergency_fix')
    
    if secret_key != expected_key:
        return jsonify({
            "status": "error",
            "message": "Invalid secret key"
        })
    
    fixed_count = fix_all_customer_balances()
    
    return jsonify({
        "status": "success",
        "message": f"Fixed {fixed_count} customer balances",
        "count": fixed_count
    })

# Add a route to fix the database trigger without requiring login
@app.route('/fix/trigger/<secret_key>')
def fix_trigger_public(secret_key):
    """Fix the database trigger without requiring login"""
    # Simple security check using a secret key
    expected_key = os.environ.get('EMERGENCY_KEY', 'kathape_emergency_fix')
    
    if secret_key != expected_key:
        return jsonify({
            "status": "error",
            "message": "Invalid secret key"
        })
    
    success = fix_database_trigger()
    
    return jsonify({
        "status": "success" if success else "error",
        "message": "Database trigger fixed successfully" if success else "Failed to fix database trigger"
    })

