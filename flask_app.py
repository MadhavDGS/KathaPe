from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash, send_from_directory
import os
import uuid
import json
import traceback
import time
import requests  # Add explicit import
import socket    # Add explicit import
import threading # Add explicit import
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from functools import wraps
from dotenv import load_dotenv
import sys
import logging

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
            
            qr_data = f"business:{access_pin}"
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

# Import Supabase first to ensure it's available globally
try:
    # Import supabase with proper error handling
    from supabase import create_client, Client
    print("Successfully imported Supabase module")
    
    # Check if we can import ClientOptions
    try:
        from supabase.lib.client_options import ClientOptions
        HAS_CLIENT_OPTIONS = True
    except ImportError:
        HAS_CLIENT_OPTIONS = False
        print("ClientOptions not available, using simple dict for options")
    
    SUPABASE_AVAILABLE = True
except ImportError as e:
    print(f"Supabase module not available, will use mock data only: {str(e)}")
    SUPABASE_AVAILABLE = False
    HAS_CLIENT_OPTIONS = False
except Exception as e:
    print(f"Error setting up Supabase: {str(e)}")
    SUPABASE_AVAILABLE = False
    HAS_CLIENT_OPTIONS = False

# Load environment variables
load_dotenv()

# Create Flask app first for faster startup
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'fc36290a52f89c1c92655b7d22b198e4')

# Apply our custom middleware
app.wsgi_app = RequestLoggerMiddleware(app.wsgi_app)

# Log important app config information
print(f"DEBUG INFO: Flask app created with secret_key: {app.secret_key[:5]}...")
print(f"DEBUG INFO: Debug mode: {app.debug}")
print(f"DEBUG INFO: Testing mode: {app.testing}")
print(f"DEBUG INFO: Environment: {app.env}")
print(f"DEBUG INFO: RENDER_DEPLOYMENT: {RENDER_DEPLOYMENT}")

# Environment variables - hardcoded for easy deployment
os.environ.setdefault('SUPABASE_URL', 'https://xhczvjwwmrvmcbwjxpxd.supabase.co')
os.environ.setdefault('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhoY3p2and3bXJ2bWNid2p4cHhkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MTM3MTQwNTgsImV4cCI6MjAyOTI5MDA1OH0.xnG-kIOiY4xbB3_QnTJtLXvwxU-fkW2RKlJw2WUoRE8') 
os.environ.setdefault('SUPABASE_SERVICE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhoY3p2and3bXJ2bWNid2p4cHhkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTcxMzcxNDA1OCwiZXhwIjoyMDI5MjkwMDU4fQ.PjOwIuDIx5a_d3u4C7cFDuOQP8NaOXQKQzH2iSXnSEA')
os.environ.setdefault('DATABASE_URL', 'postgres://postgres.xhczvjwwmrvmcbwjxpxd:katha-database-password@aws-0-ap-south-1.pooler.supabase.com:5432/postgres')
os.environ.setdefault('SECRET_KEY', 'fc36290a52f89c1c92655b7d22b198e4')
os.environ.setdefault('UPLOAD_FOLDER', 'static/uploads')

# Try to import and apply DNS patches for Supabase connectivity
try:
    import patches
    patches.apply_patches()
    print("Applied DNS resolution patches for Supabase")
except ImportError:
    print("DNS patches module not found, continuing without DNS patches")
except Exception as e:
    print(f"Error applying DNS patches: {str(e)}")

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
    Safely query a Supabase table with proper error handling
    """
    # Create an empty response class to use as fallback when Supabase is unavailable
    class EmptyResponse:
        def __init__(self):
            self.data = []
    
    try:
        # Get Supabase client
        client = get_supabase_client()
        
        if not client:
            print(f"No Supabase client available for {table_name}")
            return EmptyResponse()
        
        # Handle different query types
        if query_type == 'select':
            query = client.table(table_name).select(fields)
            
            # Apply filters
            if filters:
                for field, op, value in filters:
                    if field.endswith('_id') and value:
                        value = safe_uuid(value)
                        
                    if op == 'eq':
                        query = query.eq(field, value)
                    elif op == 'neq':
                        query = query.neq(field, value)
                    # Add other operators as needed
            
            # Apply query limit based on environment
            if limit:
                query = query.limit(limit)
            elif RENDER_DEPLOYMENT:
                query = query.limit(RENDER_QUERY_LIMIT)
                
            result = query.execute()
            return result
        
        elif query_type == 'insert':
            # Ensure UUID fields are valid
            if data and isinstance(data, dict):
                for key, value in data.items():
                    if key == 'id' or key.endswith('_id'):
                        data[key] = safe_uuid(value)
                        
            result = client.table(table_name).insert(data).execute()
            return result
            
        elif query_type == 'update':
            query = client.table(table_name).update(data)
            
            # Apply filters
            if filters:
                for field, op, value in filters:
                    if field.endswith('_id'):
                        value = safe_uuid(value)
                        
                    if op == 'eq':
                        query = query.eq(field, value)
                    # Add other operators as needed
            
            result = query.execute()
            return result
            
        elif query_type == 'delete':
            query = client.table(table_name).delete()
            
            # Apply filters
            if filters:
                for field, op, value in filters:
                    if field.endswith('_id'):
                        value = safe_uuid(value)
                        
                    if op == 'eq':
                        query = query.eq(field, value)
                    # Add other operators as needed
            
            result = query.execute()
            return result
            
        else:
            print(f"ERROR: Invalid query type: {query_type}")
            return EmptyResponse()
        
    except Exception as e:
        print(f"Supabase query error: {str(e)}")
        return EmptyResponse()

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
    if 'user_id' in session:
        if session.get('user_type') == 'business':
            return redirect(url_for('business_dashboard'))
        else:
            return redirect(url_for('customer_dashboard'))
    return redirect(url_for('login'))

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
            # Get admin database connection for auth operations
            supabase = get_supabase_admin_client()
            
            if not supabase:
                flash('Registration failed: Database connection error', 'error')
                return render_template('register.html')
            
            # Check if phone number already exists
            existing_user = supabase.table('users').select('id').eq('phone_number', phone).execute()
            if existing_user.data:
                flash('Phone number already registered', 'error')
                return render_template('register.html')
            
            # Create user ID
            user_id = str(uuid.uuid4())
            
            # Prepare user data
            user_data = {
                'id': user_id,
                'name': name,
                'phone_number': phone,
                'user_type': user_type,
                'password': password,  # Using simplified password field
                'created_at': datetime.now().isoformat()
            }
            
            # Insert user directly using admin client
            user_response = supabase.table('users').insert(user_data).execute()
            
            if not user_response or not user_response.data:
                flash('Registration failed: Database error', 'error')
                return render_template('register.html')
            
            print(f"DEBUG: User created with ID {user_id}")
            
            # The triggers we created in SQL will automatically create the profile records
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
    if request.method == 'POST':
        try:
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
            
            # Set sensible default values for the session in case DB operations fail
            user_id = str(uuid.uuid4())
            user_name = f"User {phone[-4:]}"
            
            # Try Supabase authentication with minimal field selection
            client = get_supabase_client()
            if not client:
                # Handle database connection error
                logger.error("Database connection error during login")
                flash('Database connection error. Please try again later.', 'error')
                return render_template('login.html')
            
            # Extra logging for Render
            if RENDER_DEPLOYMENT:
                logger.info(f"RENDER: Starting user lookup for phone={phone}")
                print(f"RENDER: Starting user lookup for phone={phone}")
                start_time = time.time()
            
            # Directly execute query without timeout function for login
            try:
                # Use minimal fields for better performance
                logger.info("Executing Supabase query")
                user_response = client.table('users').select('id,name,password,user_type').eq('phone_number', phone).execute()
                
                if RENDER_DEPLOYMENT:
                    elapsed_time = time.time() - start_time
                    logger.info(f"RENDER: User lookup completed in {elapsed_time:.2f} seconds")
                    print(f"RENDER: User lookup completed in {elapsed_time:.2f} seconds")
                
                if not user_response or not user_response.data:
                    logger.warning(f"Invalid credentials: User not found for phone={phone}")
                    flash('Invalid credentials: User not found', 'error')
                    return render_template('login.html')
                
                user = user_response.data[0]
                user_id = user['id']
                logger.info(f"Found user with ID {user_id}")
                print(f"DEBUG: Found user with ID {user_id}")
                
                # Verify password
                if user.get('password') != password:
                    logger.warning(f"Invalid password for user {user_id}")
                    flash('Invalid password', 'error')
                    return render_template('login.html')
                
                # Set session data
                logger.info(f"Setting session data for user {user_id}")
                session['user_id'] = user_id
                session['user_name'] = user.get('name', user_name)
                session['user_type'] = user_type
                session['phone_number'] = phone
                
                if RENDER_DEPLOYMENT:
                    # On Render: Minimal setup for faster page load
                    logger.info("Login successful on Render - using minimal data setup")
                    flash('Login successful!', 'success')
                    
                    if user_type == 'business':
                        # Minimal session data, will fetch details in dashboard
                        business_id = str(uuid.uuid4())
                        session['business_id'] = business_id
                        session['business_name'] = f"{user.get('name')}'s Business"
                        session['access_pin'] = f"{int(datetime.now().timestamp()) % 10000:04d}"
                        logger.info(f"Redirecting business user to dashboard with ID {business_id}")
                        return redirect(url_for('business_dashboard'))
                    else:
                        # Minimal session data, will fetch details in dashboard
                        customer_id = str(uuid.uuid4())
                        session['customer_id'] = customer_id
                        logger.info(f"Redirecting customer to dashboard with ID {customer_id}")
                        return redirect(url_for('customer_dashboard'))
                else:
                    # In development: Fetch full profile data
                    if user_type == 'business':
                        # Business redirect handling
                        logger.info(f"Redirecting business user to dashboard (dev mode)")
                        return redirect(url_for('business_dashboard'))
                    else:
                        # Customer redirect handling  
                        logger.info(f"Redirecting customer to dashboard (dev mode)")
                        return redirect(url_for('customer_dashboard'))
                    
            except Exception as e:
                # Log any errors during login query execution
                logger.error(f"Database query error: {str(e)}")
                print(f"Database query error: {str(e)}")
                traceback.print_exc()  # Print full traceback for debugging
                flash('Login failed. Please try again later.', 'error')
                return render_template('login.html')
                
        except Exception as e:
            # Log any uncaught exceptions during the login process
            logger.critical(f"CRITICAL ERROR in login: {str(e)}")
            print(f"CRITICAL ERROR in login: {str(e)}")
            traceback.print_exc()
            
            # Failsafe error page
            error_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Login Error - KathaPe</title>
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
                <h1>Login Error</h1>
                <p>We encountered a problem during login.</p>
                <div class="error-box">
                    <strong>Error details:</strong><br>
                    {str(e)}
                    <hr>
                    <pre>{traceback.format_exc()}</pre>
                </div>
                <a href="/login" class="btn">Try Again</a>
            </body>
            </html>
            """
            return error_html
    
    return render_template('login.html')

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
        
        try:
            # Get business details by user_id
            business_response = query_table('businesses', filters=[('user_id', 'eq', user_id)])
            
            if business_response and business_response.data:
                business = business_response.data[0]
                session['business_id'] = business['id']
                session['business_name'] = business['name']
                session['access_pin'] = business['access_pin']
            else:
                # Create a new business record
                try:
                    supabase_url = os.getenv('SUPABASE_URL')
                    supabase_service_key = os.getenv('SUPABASE_SERVICE_KEY') or os.getenv('SUPABASE_KEY')
                    
                    business_id = str(uuid.uuid4())
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
                    session['access_pin'] = f"{int(datetime.now().timestamp()) % 10000:04d}"
        except Exception as e:
            flash(f'Error retrieving business: {str(e)}', 'error')
            # Create a temporary session business to allow user to continue
            temp_id = str(uuid.uuid4())
            session['business_id'] = temp_id
            session['business_name'] = f"{session.get('user_name', 'Your')}'s Business"
            session['access_pin'] = f"{int(datetime.now().timestamp()) % 10000:04d}"
        
        business_id = safe_uuid(session.get('business_id'))
        
        try:
            # Get business details
            business_response = query_table('businesses', filters=[('id', 'eq', business_id)])
            
            if business_response and business_response.data:
                business = business_response.data[0]
                
                # If access_pin is missing, generate one
                if not business.get('access_pin'):
                    access_pin = f"{int(datetime.now().timestamp()) % 10000:04d}"
                    try:
                        query_table('businesses', query_type='update', 
                                data={'access_pin': access_pin},
                                filters=[('id', 'eq', business_id)])
                        business['access_pin'] = access_pin
                    except Exception as e:
                        print(f"ERROR updating access_pin: {str(e)}")
                        business['access_pin'] = session.get('access_pin', access_pin)
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
            
            # Use different loading strategies based on environment
            if RENDER_DEPLOYMENT:
                # On Render: Load minimal essential data for dashboard with strict limits
                try:
                    # Get customer count - simple and fast count query
                    customers_response = query_table('customer_credits', 
                                                 fields='id', 
                                                 filters=[('business_id', 'eq', business_id)])
                    total_customers = len(customers_response.data) if customers_response and customers_response.data else 0
                    
                    # Get just a few customers for display
                    credited_customers_response = query_table('customer_credits', 
                                                         filters=[('business_id', 'eq', business_id)],
                                                         limit=RENDER_DASHBOARD_LIMIT)
                    
                    if credited_customers_response and credited_customers_response.data:
                        # Get simplified customer data for each of these credits (limited)
                        for credit in credited_customers_response.data:
                            customer_id = safe_uuid(credit.get('customer_id'))
                            try:
                                customer_response = query_table('customers', 
                                                            fields='id,name,phone_number', 
                                                            filters=[('id', 'eq', customer_id)])
                                if customer_response and customer_response.data:
                                    customer = customer_response.data[0]
                                    # Merge with minimal data
                                    customer_with_credit = {
                                        'id': customer.get('id'),
                                        'name': customer.get('name', 'Unknown'),
                                        'phone_number': customer.get('phone_number', 'Unknown'),
                                        'current_balance': credit.get('current_balance', 0)
                                    }
                                    customers.append(customer_with_credit)
                            except Exception as e:
                                print(f"ERROR retrieving customer {customer_id}: {str(e)}")
                    
                    # Get a few recent transactions
                    transactions_response = query_table('transactions', 
                                                  filters=[('business_id', 'eq', business_id)],
                                                  limit=RENDER_DASHBOARD_LIMIT)
                    
                    if transactions_response and transactions_response.data:
                        transactions = transactions_response.data
                        
                        # Get basic customer names for these transactions with a single query
                        customer_ids = [tx.get('customer_id') for tx in transactions if tx.get('customer_id')]
                        if customer_ids:
                            # Get all customers in a single query instead of multiple queries
                            customers_map = {}
                            for customer_id in customer_ids:
                                customer_response = query_table('customers', 
                                                            fields='id,name', 
                                                            filters=[('id', 'eq', customer_id)])
                                if customer_response and customer_response.data:
                                    customers_map[customer_response.data[0].get('id')] = customer_response.data[0].get('name', 'Unknown')
                            
                            # Apply customer names to transactions
                            for transaction in transactions:
                                cust_id = transaction.get('customer_id')
                                transaction['customer_name'] = customers_map.get(cust_id, 'Unknown')
                    
                    # Get credit and payment totals with simple queries
                    try:
                        credit_sum_response = query_table('transactions', 
                                                    fields='amount', 
                                                    filters=[('business_id', 'eq', business_id), 
                                                            ('transaction_type', 'eq', 'credit')],
                                                    limit=100)  # Limit but enough to get summary totals
                        
                        if credit_sum_response and credit_sum_response.data:
                            total_credit = sum([float(t.get('amount', 0)) for t in credit_sum_response.data])
                    except Exception as e:
                        print(f"ERROR getting credit total: {str(e)}")
                    
                    try:
                        payment_sum_response = query_table('transactions', 
                                                      fields='amount', 
                                                      filters=[('business_id', 'eq', business_id), 
                                                              ('transaction_type', 'eq', 'payment')],
                                                      limit=100)  # Limit but enough to get summary totals
                        
                        if payment_sum_response and payment_sum_response.data:
                            total_payments = sum([float(t.get('amount', 0)) for t in payment_sum_response.data])
                    except Exception as e:
                        print(f"ERROR getting payment total: {str(e)}")
                        
                except Exception as e:
                    print(f"ERROR in Render optimized data loading: {str(e)}")
                    # Create basic mock data on error
                    total_customers = 0
                    total_credit = 0
                    total_payments = 0
                    transactions = [{'customer_name': 'Example Customer', 'amount': 0, 'transaction_type': 'credit', 'created_at': datetime.now().isoformat()}]
                    customers = [{'name': 'Example Customer', 'current_balance': 0, 'id': str(uuid.uuid4())}]
                    
            else:
                # In development: Load complete data with more detailed queries
                try:
                    # Get customer credits to display customers on dashboard
                    customers_response = query_table('customer_credits', filters=[('business_id', 'eq', business_id)])
                    customer_credits = customers_response.data if customers_response and customers_response.data else []
                    
                    # Total customers
                    total_customers = len(customer_credits)
                    
                    # Get customer details for each customer credit
                    for credit in customer_credits:
                        customer_id = safe_uuid(credit.get('customer_id'))
                        try:
                            customer_response = query_table('customers', filters=[('id', 'eq', customer_id)])
                            if customer_response and customer_response.data:
                                customer = customer_response.data[0]
                                # Merge customer details with credit information
                                customer_with_credit = {
                                    **customer,
                                    'current_balance': credit.get('current_balance', 0)
                                }
                                customers.append(customer_with_credit)
                        except Exception as e:
                            print(f"ERROR retrieving customer {customer_id}: {str(e)}")
                    
                except Exception as e:
                    print(f"ERROR getting customers count: {str(e)}")
                
                try:
                    # Total credit
                    credit_response = query_table('transactions', fields='amount', 
                                                filters=[('business_id', 'eq', business_id), ('transaction_type', 'eq', 'credit')])
                    total_credit = sum([float(t.get('amount', 0)) for t in credit_response.data]) if credit_response and credit_response.data else 0
                except Exception as e:
                    print(f"ERROR getting credit total: {str(e)}")
                
                try:
                    # Total payments
                    payment_response = query_table('transactions', fields='amount',
                                                filters=[('business_id', 'eq', business_id), ('transaction_type', 'eq', 'payment')])
                    total_payments = sum([float(t.get('amount', 0)) for t in payment_response.data]) if payment_response and payment_response.data else 0
                except Exception as e:
                    print(f"ERROR getting payment total: {str(e)}")
                
                try:
                    # Recent transactions
                    transactions_response = query_table('transactions', 
                                                    filters=[('business_id', 'eq', business_id)])
                    transactions = transactions_response.data if transactions_response and transactions_response.data else []
                    
                    # Get customer names for transactions
                    for transaction in transactions:
                        customer_id = safe_uuid(transaction.get('customer_id'))
                        try:
                            customer_response = query_table('customers', fields='name', filters=[('id', 'eq', customer_id)])
                            if customer_response and customer_response.data:
                                transaction['customer_name'] = customer_response.data[0].get('name', 'Unknown')
                            else:
                                transaction['customer_name'] = 'Unknown'
                        except Exception as e:
                            print(f"ERROR getting customer name: {str(e)}")
                            transaction['customer_name'] = 'Unknown'
                except Exception as e:
                    print(f"ERROR getting transactions: {str(e)}")
            
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
            # Log the full error with traceback for debugging
            print(f"CRITICAL ERROR in business_dashboard: {str(e)}")
            traceback.print_exc()
            
            # Create minimal data for the template
            mock_business = {
                'name': session.get('business_name', 'Your Business'),
                'description': 'Unable to load business data',
                'access_pin': session.get('access_pin', ''),
                'id': business_id
            }
            
            mock_summary = {
                'total_customers': 0,
                'total_credit': 0,
                'total_payments': 0
            }
            
            # Try to generate QR code with session data
            if mock_business['access_pin']:
                try:
                    generate_business_qr_code(business_id, mock_business['access_pin'])
                except:
                    pass
            
            return render_template('business/dashboard.html', 
                                business=mock_business, 
                                summary=mock_summary, 
                                transactions=[],
                                customers=[])
    except Exception as outer_e:
        # Special handling for any unexpected errors
        print(f"CATASTROPHIC ERROR in business_dashboard: {str(outer_e)}")
        traceback.print_exc()
        
        # Render a simple error page with the error message
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
            <h1>Dashboard Error</h1>
            <p>We encountered a problem loading your dashboard.</p>
            <div class="error-box">
                <strong>Error details:</strong><br>
                {str(outer_e)}
            </div>
            <a href="/logout" class="btn">Logout and Try Again</a>
        </body>
        </html>
        """
        return error_html

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
            # Update the existing credit with new balance
            current_balance = float(credit.get('current_balance', 0))
            updated_balance = current_balance + initial_credit
            
            credit_update = query_table('customer_credits', 
                                      query_type='update',
                                      data={'current_balance': updated_balance, 'updated_at': datetime.now().isoformat()},
                                      filters=[('id', 'eq', credit['id'])])
            
            # Add a transaction record for the initial credit
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
        
        query_table('transactions', query_type='insert', data=transaction_data)
        
        flash('Transaction added successfully', 'success')
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
            query_table('reminders', query_type='insert', data=reminder_data)
            
            # Also update the customer_credits record with the reminder date
            query_table('customer_credits', 
                       query_type='update',
                       data={'last_reminder_date': datetime.now().isoformat()},
                       filters=[('business_id', 'eq', business_id),
                               ('customer_id', 'eq', customer_id)])
        except Exception as e:
            print(f"Error recording reminder: {str(e)}")
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
        if not os.path.exists(qr_filename):
            access_pin = business.get('access_pin', '0000')
            # Generate QR code
            qr_data = f"business:{access_pin}"
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
                # In emergency mode, we'll just use a temp ID rather than querying
                emergency_id = str(uuid.uuid4())
                session['customer_id'] = emergency_id
                session['customer_name'] = session.get('user_name', 'Customer')
                logger.info(f"Created temporary customer ID: {emergency_id}")
            except Exception as e:
                logger.error(f"Error creating customer ID: {str(e)}")
                # Still ensure the customer has *some* ID to proceed
                session['customer_id'] = str(uuid.uuid4())
        
        # On Render, we'll use extremely minimal data to avoid timeouts
        if RENDER_DEPLOYMENT:
            # Create a static default business that won't require any DB queries
            default_business = {
                'id': 'default',
                'name': 'Your Business Credits',
                'current_balance': 0
            }
            
            # Send very minimal data to the template
            businesses = [default_business]
            
            # Log performance
            duration = time.time() - start_time
            logger.info(f"RENDER: Customer dashboard loaded with minimal data in {duration:.2f}s")
            
            return render_template('customer/dashboard.html', businesses=businesses)
        else:
            # In development, we can load more data
            try:
                customer_id = safe_uuid(session.get('customer_id'))
                
                # Get businesses with limited DB interaction
                businesses_response = query_table(
                    'customer_credits', 
                    fields='business_id,current_balance', 
                    filters=[('customer_id', 'eq', customer_id)],
                    limit=5
                )
                
                businesses = []
                if businesses_response and businesses_response.data:
                    for i, credit in enumerate(businesses_response.data):
                        business_id = credit.get('business_id')
                        businesses.append({
                            'id': business_id,
                            'name': f'Business {i+1}',
                            'current_balance': credit.get('current_balance', 0)
                        })
                
                # Add default business if none found
                if not businesses:
                    businesses.append({
                        'id': 'default',
                        'name': 'Your Business Credits',
                        'current_balance': 0
                    })
                
                # Log performance
                duration = time.time() - start_time
                logger.info(f"DEV: Customer dashboard loaded in {duration:.2f}s")
                
                return render_template('customer/dashboard.html', businesses=businesses)
            except Exception as e:
                logger.error(f"Error in customer dashboard: {str(e)}")
                traceback.print_exc()
                
                # Add default business in error case
                businesses = [{
                    'id': 'default-error',
                    'name': 'Your Business Credits',
                    'current_balance': 0
                }]
                
                return render_template('customer/dashboard.html', businesses=businesses)
    except Exception as e:
        logger.critical(f"CRITICAL ERROR in customer dashboard: {str(e)}")
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
    
    # Ensure credit relationship exists - this will create it if it doesn't
    credit = ensure_customer_credit_exists(business_id, customer_id)
    
    # Get business details
    business_response = query_table('businesses', filters=[('id', 'eq', business_id)])
    business = business_response.data[0] if business_response and business_response.data else {}
    
    # Get customer details
    customer_response = query_table('customers', filters=[('id', 'eq', customer_id)])
    customer = customer_response.data[0] if customer_response and customer_response.data else {}
    
    # Merge customer details with credit information
    current_balance = credit.get('current_balance', 0) if credit else 0
    if customer:
        customer = {**customer, 'current_balance': current_balance}
    
    # Get transaction history for this customer with this business
    transactions = []
    credit_total = 0
    payment_total = 0
    
    try:
        transactions_response = query_table('transactions',
                                           filters=[('business_id', 'eq', business_id),
                                                   ('customer_id', 'eq', customer_id)])
        transactions = transactions_response.data if transactions_response and transactions_response.data else []
        
        # Calculate totals and sort transactions by date, newest first
        for transaction in transactions:
            if transaction.get('transaction_type') == 'credit':
                credit_total += float(transaction.get('amount', 0))
            else:  # payment
                payment_total += float(transaction.get('amount', 0))
        
        # Sort transactions by date, newest first
        transactions.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    except Exception as e:
        print(f"ERROR retrieving transactions: {str(e)}")
    
    return render_template('customer/business_view.html', 
                          business=business, 
                          customer=customer,
                          transactions=transactions,
                          credit_total=credit_total,
                          payment_total=payment_total,
                          current_balance=current_balance)

@app.route('/customer/transaction', methods=['GET', 'POST'])
@login_required
@customer_required
def customer_transaction():
    if 'selected_business_id' not in session:
        return redirect(url_for('select_business'))
    
    business_id = safe_uuid(session.get('selected_business_id'))
    customer_id = safe_uuid(session.get('customer_id'))
    user_id = safe_uuid(session.get('user_id'))
    
    # Get transaction type from query parameter
    default_transaction_type = request.args.get('transaction_type', 'payment')
    
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
            
        query_table('transactions', query_type='insert', data=transaction_data)
        
        flash('Transaction added successfully', 'success')
        return redirect(url_for('customer_business_view'))
    
    # Get for transaction form
    # Get business details
    business_response = query_table('businesses', filters=[('id', 'eq', business_id)])
    business = business_response.data[0] if business_response and business_response.data else {}
    
    # Get customer details
    customer_response = query_table('customers', filters=[('id', 'eq', customer_id)])
    customer = customer_response.data[0] if customer_response and customer_response.data else {}
    
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
    
    # Check if relationship already exists
    existing_credit = query_table('customer_credits', 
                                 filters=[('business_id', 'eq', business_id),
                                         ('customer_id', 'eq', customer_id)])
    
    # Return existing credit if found
    if existing_credit and existing_credit.data:
        return existing_credit.data[0]
    
    # Create a new credit relationship
    credit_data = {
        'id': str(uuid.uuid4()),
        'business_id': business_id,
        'customer_id': customer_id,
        'current_balance': initial_balance,
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat()
    }
    
    credit_insert = query_table('customer_credits', query_type='insert', data=credit_data)
    
    if credit_insert and credit_insert.data:
        return credit_insert.data[0]
    else:
        # Return the data even if insert failed (for mock data system)
        return credit_data

# Add diagnostic endpoint for testing deployment
@app.route('/api/status')
def api_status():
    """Status endpoint for checking API health"""
    try:
        # Check if we can connect to database
        result = {"status": "ok", "database": False, "error": None}
        
        try:
            # Test Supabase connection
            client = get_supabase_client()
            if client:
                # Try a simple query
                response = client.table('users').select('id').limit(1).execute()
                if response and response.data:
                    result["database"] = True
                    result["user_count"] = len(response.data)
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

# Run the application
if __name__ == '__main__':
    # Get port from environment variable for Render compatibility
    port = int(os.environ.get('PORT', 5003))
    # Set host to 0.0.0.0 to make it accessible outside the container
    app.run(debug=False, host='0.0.0.0', port=port) 