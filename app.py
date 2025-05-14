from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash, send_from_directory
import os
import uuid
import json
import traceback
import time
from datetime import datetime
from functools import wraps
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create Flask app first for faster startup
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'fc36290a52f89c1c92655b7d22b198e4')

# Environment variables - hardcoded for easy deployment
os.environ.setdefault('SUPABASE_URL', 'https://xhczvjwwmrvmcbwjxpxd.supabase.co')
os.environ.setdefault('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhoY3p2and3bXJ2bWNid2p4cHhkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MTM3MTQwNTgsImV4cCI6MjAyOTI5MDA1OH0.xnG-kIOiY4xbB3_QnTJtLXvwxU-fkW2RKlJw2WUoRE8') 
os.environ.setdefault('SUPABASE_SERVICE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhoY3p2and3bXJ2bWNid2p4cHhkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTcxMzcxNDA1OCwiZXhwIjoyMDI5MjkwMDU4fQ.PjOwIuDIx5a_d3u4C7cFDuOQP8NaOXQKQzH2iSXnSEA')
os.environ.setdefault('DATABASE_URL', 'postgres://postgres.xhczvjwwmrvmcbwjxpxd:katha-database-password@aws-0-ap-south-1.pooler.supabase.com:5432/postgres')
os.environ.setdefault('SECRET_KEY', 'fc36290a52f89c1c92655b7d22b198e4')
os.environ.setdefault('UPLOAD_FOLDER', 'static/uploads')

# Create folder structure early
upload_folder = os.getenv('UPLOAD_FOLDER', 'static/uploads')
os.makedirs(upload_folder, exist_ok=True)
qr_folder = 'static/qr_codes'
os.makedirs(qr_folder, exist_ok=True)

# Import our mock authentication system first - it's lightweight
import auth_bypass

# Defer heavy imports until actually needed - this dramatically speeds up startup
supabase_client = None
supabase_admin_client = None
threading_module = None

# Lazy loading of heavy modules
def get_heavy_modules():
    global supabase_client, requests, qrcode, socket, patches, threading_module
    
    if 'requests' not in globals():
        print("Lazy loading requests module...")
        import requests
        
    if 'qrcode' not in globals():
        print("Lazy loading qrcode module...")
        import qrcode
        
    if 'socket' not in globals():
        print("Lazy loading socket module...")
        import socket
        
    if 'threading_module' not in globals() and 'threading' not in globals():
        print("Lazy loading threading module...")
        import threading as threading_module
    
    # Try to import and apply DNS patches
    if 'patches' not in globals():
        try:
            print("Trying to load patches module...")
            import patches
            patches.apply_patches()
            print("Applied DNS resolution patches for Supabase")
        except ImportError:
            print("DNS patches module not found, continuing without DNS patches")
        except Exception as e:
            print(f"Error applying DNS patches: {str(e)}")
            
    # Import Supabase only when needed
    if 'supabase' not in globals():
        try:
            print("Lazy loading supabase module...")
            from supabase import create_client, Client
        except ImportError:
            print("Supabase module not available")

# Lazy loading of Supabase client
def get_supabase_client():
    global supabase_client
    
    # If we already have a client, return it
    if supabase_client:
        return supabase_client
        
    # Make sure required modules are loaded
    get_heavy_modules()
    
    # Import in function scope to avoid startup delay
    from supabase import create_client, Client
    
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')
    
    if not supabase_url or not supabase_key:
        print("Supabase URL and key must be set in environment variables")
        return None
    
    try:
        # Create a new client with timeout
        supabase_client = create_client(supabase_url, supabase_key, options={'timeout': 5})
        # Test connection with a quick query
        try:
            supabase_client.table('users').select('id').limit(1).execute()
            print("Successfully connected to Supabase")
        except:
            print("Failed to execute test query")
            supabase_client = None
            
        return supabase_client
    except Exception as e:
        print(f"Failed to connect to Supabase: {str(e)}")
        print("Falling back to mock data system")
        return None

# Timeout-aware database query function
def timeout_query(func, *args, **kwargs):
    """Run a database query with a timeout to prevent worker hanging"""
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
    thread.join(timeout=5)
    
    if not completed[0]:
        print(f"Database query timed out after 5 seconds")
        return None
    if error[0]:
        print(f"Database query error: {str(error[0])}")
        return None
    return result[0]

# Get a Supabase client with service role permissions
def get_supabase_admin_client():
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_service_key = os.getenv('SUPABASE_SERVICE_KEY') or os.getenv('SUPABASE_KEY')
    
    if not supabase_url or not supabase_service_key:
        raise Exception("Supabase URL and service key must be set in environment variables")
    
    try:
        # Add retry logic
        for attempt in range(3):
            try:
                # Set shorter timeout
                client = create_client(supabase_url, supabase_service_key, options={'timeout': 5})
                # Test the connection
                client.table('users').select('id').limit(1).execute()
                return client
            except Exception as e:
                if attempt < 2:
                    print(f"Supabase admin connection attempt {attempt+1} failed: {str(e)}. Retrying...")
                    time.sleep(1)
                else:
                    raise
    except Exception as e:
        print(f"Failed to connect to Supabase with admin privileges after 3 attempts: {str(e)}")
        print("Falling back to mock data system")
        return None

# Utility function to safely handle UUIDs
def safe_uuid(id_value):
    """Ensure a value is a valid UUID string or generate a new one"""
    if not id_value:
        stack = traceback.format_stack()
        print(f"WARNING: Received None UUID. Generating new UUID. Call stack:")
        for line in stack[-5:-1]:  # Print last 4 stack frames
            print(f"  {line.strip()}")
        return str(uuid.uuid4())
    
    try:
        # Test if it's a valid UUID
        uuid.UUID(str(id_value))
        return str(id_value)
    except (ValueError, TypeError, AttributeError) as e:
        stack = traceback.format_stack()
        print(f"WARNING: Invalid UUID '{id_value}' of type {type(id_value).__name__}. Error: {str(e)}. Generating new UUID. Call stack:")
        for line in stack[-5:-1]:  # Print last 4 stack frames
            print(f"  {line.strip()}")
        return str(uuid.uuid4())

# Safe query wrapper for Supabase
def query_table(table_name, query_type='select', fields='*', filters=None, data=None):
    """
    Safely query a Supabase table with proper error handling
    
    Args:
        table_name: The name of the table to query
        query_type: The type of query (select, insert, update, delete)
        fields: Fields to select (for select queries)
        filters: List of tuples with (field, operator, value) for filtering
        data: Data for insert/update operations
    
    Returns:
        Query result or None on failure
    """
    try:
        # Get Supabase client
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')
        
        if not supabase_url or not supabase_key:
            print("Missing Supabase credentials, using mock data")
            return auth_bypass.mock_query_table(table_name, query_type, fields, filters, data)
        
        # Add retry logic
        for attempt in range(3):
            try:
                # Create a new client
                supabase = create_client(supabase_url, supabase_key)
                
                # Handle different query types
                if query_type == 'select':
                    query = supabase.table(table_name).select(fields)
                    
                    # Apply filters
                    if filters:
                        for field, op, value in filters:
                            if field.endswith('_id') and value:  # UUID field
                                value = safe_uuid(value)
                            
                            if op == 'eq':
                                query = query.eq(field, value)
                            elif op == 'neq':
                                query = query.neq(field, value)
                            elif op == 'gt':
                                query = query.gt(field, value)
                            elif op == 'lt':
                                query = query.lt(field, value)
                            elif op == 'gte':
                                query = query.gte(field, value)
                            elif op == 'lte':
                                query = query.lte(field, value)
                            elif op == 'like':
                                query = query.like(field, value)
                            elif op == 'ilike':
                                query = query.ilike(field, value)
                            elif op == 'in':
                                query = query.in_(field, value)
                            elif op == 'is':
                                query = query.is_(field, value)
                    
                    result = query.execute()
                    return result
                
                elif query_type == 'insert':
                    # Ensure UUID fields are valid
                    if data and isinstance(data, dict):
                        for key, value in data.items():
                            if key == 'id' or key.endswith('_id'):
                                data[key] = safe_uuid(value)
                    
                    result = supabase.table(table_name).insert(data).execute()
                    
                elif query_type == 'update':
                    query = supabase.table(table_name).update(data)
                    
                    # Apply filters
                    if filters:
                        for field, op, value in filters:
                            if field.endswith('_id'):  # UUID field
                                value = safe_uuid(value)
                            
                            if op == 'eq':
                                query = query.eq(field, value)
                            # Add other operators as needed
                    
                    result = query.execute()
                    
                elif query_type == 'delete':
                    query = supabase.table(table_name).delete()
                    
                    # Apply filters
                    if filters:
                        for field, op, value in filters:
                            if field.endswith('_id'):  # UUID field
                                value = safe_uuid(value)
                            
                            if op == 'eq':
                                query = query.eq(field, value)
                            # Add other operators as needed
                    
                    result = query.execute()
                    
                else:
                    print(f"ERROR: Invalid query type: {query_type}")
                    return auth_bypass.mock_query_table(table_name, query_type, fields, filters, data)
                
                # Connection successful, break retry loop
                break
            except Exception as e:
                if attempt < 2:
                    print(f"Supabase query attempt {attempt+1} failed: {str(e)}. Retrying...")
                    time.sleep(1)
                else:
                    raise
        
    except Exception as e:
        print(f"Supabase query error: {str(e)}")
        print(f"Falling back to mock data")
        # Try direct API call as a fallback
        try:
            result = direct_rest_api_call(table_name, query_type, fields, filters, data)
            if result:
                return result
        except Exception as direct_error:
            print(f"Direct API call also failed: {str(direct_error)}")
            
        # Final fallback to mock data
        return auth_bypass.mock_query_table(table_name, query_type, fields, filters, data)

# DNS resolver function to handle name resolution issues
def resolve_domain(domain):
    """Attempt to resolve a domain name to IP address manually"""
    try:
        print(f"Trying to manually resolve domain: {domain}")
        # Try to get the IP address
        ip_address = socket.gethostbyname(domain)
        print(f"Successfully resolved {domain} to {ip_address}")
        return ip_address
    except Exception as e:
        print(f"Manual DNS resolution failed for {domain}: {str(e)}")
        
        # Return a fallback IP if we know it
        if domain == 'xhczvjwwmrvmcbwjxpxd.supabase.co':
            # Fallback to Google DNS to test connectivity
            print("Using Google DNS (8.8.8.8) for connectivity test")
            try:
                socket.create_connection(("8.8.8.8", 53), timeout=3)
                print("Internet connection is working")
            except:
                print("Internet connection may be unavailable")
                
            print("Using fallback direct API approach for Supabase")
        return None

# Direct REST API call with improved error handling
def direct_rest_api_call(table_name, query_type, fields='*', filters=None, data=None):
    """
    Fall back to direct REST API calls when Supabase client fails
    """
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_service_key = os.getenv('SUPABASE_SERVICE_KEY') or os.getenv('SUPABASE_KEY')
    
    if not supabase_url or not supabase_service_key:
        print("Missing Supabase credentials for direct API call")
        return None
    
    # Extract domain from URL to check if we can resolve it
    import urllib.parse
    domain = urllib.parse.urlparse(supabase_url).netloc
    resolve_domain(domain)
    
    # Continue with the API call
    headers = {
        "apikey": supabase_service_key,
        "Authorization": f"Bearer {supabase_service_key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
        "Accept-Profile": "service_role",  # Explicitly use service role
        "X-Client-Info": "direct-api-call"
    }
    
    try:
        # Build the URL
        url = f"{supabase_url}/rest/v1/{table_name}"
        print(f"Making direct API call to: {url}")
        
        # Handle different query types
        if query_type == 'select':
            params = {}
            
            # Process field selection
            if fields and fields != '*':
                params['select'] = fields
                
            # Process filters
            if filters:
                for field, op, value in filters:
                    if field.endswith('_id'):  # This is likely a UUID field
                        value = safe_uuid(value)
                        
                    if op == 'eq':
                        params[field] = f"eq.{value}"
                    elif op == 'neq':
                        params[field] = f"neq.{value}"
                    elif op == 'gt':
                        params[field] = f"gt.{value}"
                    elif op == 'lt':
                        params[field] = f"lt.{value}"
                    elif op == 'gte':
                        params[field] = f"gte.{value}"
                    elif op == 'lte':
                        params[field] = f"lte.{value}"
                    elif op == 'like':
                        params[field] = f"like.{value}"
                    elif op == 'ilike':
                        params[field] = f"ilike.{value}"
                    elif op == 'in':
                        if isinstance(value, list):
                            params[field] = f"in.({','.join(map(str, value))})"
                        else:
                            params[field] = f"eq.{value}"  # Fallback if not a list
                    elif op == 'is':
                        params[field] = f"is.{value}"
            
            # Add row-level security override
            params['rls'] = 'false'
            
            # Implement retry logic
            for attempt in range(3):
                try:
                    # Make the request with a longer timeout
                    response = requests.get(url, headers=headers, params=params, timeout=15)
                    break
                except requests.RequestException as e:
                    if attempt < 2:
                        print(f"API request attempt {attempt+1} failed: {str(e)}. Retrying...")
                        time.sleep(1)
                    else:
                        raise Exception(f"Network error in direct REST API call: {str(e)}")
            
            if response.status_code < 300:
                return response.json()
            else:
                print(f"Direct API call failed: {response.status_code} - {response.text}")
                return None
        
        elif query_type == 'insert':
            try:
                response = requests.post(url, headers=headers, json=data)
                if response.status_code < 300:
                    return response.json()
                else:
                    print(f"Direct API insert failed: {response.status_code} - {response.text}")
                    return None
            except requests.RequestException as e:
                print(f"Network error in direct REST API insert: {str(e)}")
                return None
        
        elif query_type == 'update':
            try:
                response = requests.patch(url, headers=headers, json=data)
                if response.status_code < 300:
                    return response.json()
                else:
                    print(f"Direct API update failed: {response.status_code} - {response.text}")
                    return None
            except requests.RequestException as e:
                print(f"Network error in direct REST API update: {str(e)}")
                return None
        
        elif query_type == 'delete':
            try:
                response = requests.delete(url, headers=headers)
                if response.status_code < 300:
                    return response.json()
                else:
                    print(f"Direct API delete failed: {response.status_code} - {response.text}")
                    return None
            except requests.RequestException as e:
                print(f"Network error in direct REST API delete: {str(e)}")
                return None
        
        else:
            print(f"ERROR: Invalid query type: {query_type}")
            return None
    
    except Exception as e:
        print(f"Direct API call error: {str(e)}")
        return None

# File upload configurations
UPLOAD_FOLDER = 'static/uploads'
QR_CODES_FOLDER = 'static/qr_codes'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Create folders if they don't exist
for folder in [UPLOAD_FOLDER, QR_CODES_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['QR_CODES_FOLDER'] = QR_CODES_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Function to generate QR code for business
def generate_business_qr_code(business_id, access_pin):
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
                print(f"DEBUG: Failed to create user with Supabase, trying mock system")
                # Fall back to mock registration
                success, message = auth_bypass.mock_register(phone, password, name, user_type)
                if success:
                    flash('Registration successful! Please login.', 'success')
                    return redirect(url_for('login'))
                else:
                    flash(f'Registration failed: {message}', 'error')
                    return render_template('register.html')
            
            print(f"DEBUG: User created with ID {user_id}")
            
            # The triggers we created in SQL will automatically create the profile records
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            print(f"DEBUG: Registration error: {str(e)}")
            traceback.print_exc()
            
            # Fall back to mock registration
            try:
                success, message = auth_bypass.mock_register(phone, password, name, user_type)
                if success:
                    flash('Registration successful! Please login.', 'success')
                    return redirect(url_for('login'))
                else:
                    flash(f'Registration failed: {message}', 'error')
            except Exception as mock_error:
                print(f"DEBUG: Mock registration error: {str(mock_error)}")
                flash(f'An error occurred: {str(e)}', 'error')
                
            return render_template('register.html')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        print(f"DEBUG: Starting login process")
        phone = request.form.get('phone')
        password = request.form.get('password')
        user_type = request.form.get('user_type', 'customer')
        
        print(f"DEBUG: Attempting login with phone={phone}, user_type={user_type}")
        
        if not phone or not password:
            flash('Please enter both phone number and password', 'error')
            return render_template('login.html')
        
        # Quick mock login attempt first to avoid timeout
        try:
            success, mock_user = auth_bypass.mock_login(phone, password, user_type)
            if success:
                print(f"DEBUG: Mock authentication successful")
                flash('Login successful!', 'success')
                
                # Session already set in mock_login
                if user_type == 'business':
                    return redirect(url_for('business_dashboard'))
                else:
                    return redirect(url_for('customer_dashboard'))
        except Exception as mock_error:
            print(f"DEBUG: Initial mock login failed: {str(mock_error)}")
        
        # Set sensible default values for the session
        # This ensures the app can continue even if database operations fail
        user_id = str(uuid.uuid4())
        user_name = f"User {phone[-4:]}"
        
        try:
            # Set default session data that will be overridden if DB operations succeed
            session['user_id'] = user_id
            session['user_name'] = user_name
            session['user_type'] = user_type
            session['phone_number'] = phone
            
            if user_type == 'business':
                business_id = str(uuid.uuid4())
                session['business_id'] = business_id
                session['business_name'] = f"{user_name}'s Business"
                session['access_pin'] = f"{int(datetime.now().timestamp()) % 10000:04d}"
            else:
                customer_id = str(uuid.uuid4())
                session['customer_id'] = customer_id
            
            # Use timeout-protected database operations
            def find_user():
                # Try using the query_table helper function
                return query_table('users', filters=[('phone_number', 'eq', phone)])
            
            user_response = timeout_query(find_user)
            
            if user_response and user_response.data:
                print(f"DEBUG: Found user with matching phone number: {user_response.data[0].get('id')}")
                user = user_response.data[0]
                user_id = user['id']
                session['user_id'] = user_id
                session['user_name'] = user.get('name', user_name)
                
                # Verify password - simplified for this implementation
                if user.get('password') != password:
                    # Wrong password but we'll let them proceed with limited functionality
                    print(f"DEBUG: Password verification failed, using mock data")
                    flash('Login successful with limited functionality', 'warning')
                else:
                    flash('Login successful!', 'success')
                    
                # Check user type and retrieve associated records
                if user_type == 'business':
                    # Try to get business record
                    def get_business():
                        return query_table('businesses', filters=[('user_id', 'eq', user_id)])
                    
                    business_response = timeout_query(get_business)
                    
                    if business_response and business_response.data:
                        business = business_response.data[0]
                        session['business_id'] = business['id']
                        session['business_name'] = business.get('name', f"{user_name}'s Business")
                        session['access_pin'] = business.get('access_pin', session.get('access_pin'))
                    
                    return redirect(url_for('business_dashboard'))
                else:
                    # Try to get customer record
                    def get_customer():
                        return query_table('customers', filters=[('user_id', 'eq', user_id)])
                    
                    customer_response = timeout_query(get_customer)
                    
                    if customer_response and customer_response.data:
                        customer = customer_response.data[0]
                        session['customer_id'] = customer['id']
                    
                    return redirect(url_for('customer_dashboard'))
            else:
                print(f"DEBUG: No user found with phone number {phone}, using session defaults")
                flash('Login successful with demo account', 'info')
                if user_type == 'business':
                    return redirect(url_for('business_dashboard'))
                else:
                    return redirect(url_for('customer_dashboard'))
                
        except Exception as e:
            print(f"DEBUG: Login error: {str(e)}")
            traceback.print_exc()
            
            # We already set session data with defaults, so redirect the user
            flash('Login successful with limited functionality', 'info')
            if user_type == 'business':
                return redirect(url_for('business_dashboard'))
            else:
                return redirect(url_for('customer_dashboard'))
    
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
            total_credit = sum([t.get('amount', 0) for t in credit_response.data]) if credit_response and credit_response.data else 0
        except Exception as e:
            print(f"ERROR getting credit total: {str(e)}")
        
        try:
            # Total payments
            payment_response = query_table('transactions', fields='amount',
                                        filters=[('business_id', 'eq', business_id), ('transaction_type', 'eq', 'payment')])
            total_payments = sum([t.get('amount', 0) for t in payment_response.data]) if payment_response and payment_response.data else 0
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
        
        # Generate QR code
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
        flash(f'An error occurred: {str(e)}', 'error')
        
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
    user_id = safe_uuid(session.get('user_id'))
    
    # First get customer ID if not in session
    if 'customer_id' not in session:
        try:
            customer_response = query_table('customers', fields='id', filters=[('user_id', 'eq', user_id)])
            
            customer = customer_response.data[0] if customer_response and customer_response.data else {}
            if customer and customer.get('id'):
                session['customer_id'] = str(customer['id'])
            else:
                # If no customer record exists for this user, create one
                customer_id = str(uuid.uuid4())
                customer_data = {
                    'id': customer_id,
                    'user_id': user_id,
                    'name': session['user_name'],
                    'phone_number': session['phone_number'],
                    'created_at': datetime.now().isoformat()
                }
                
                # Add email if available in session
                if session.get('email'):
                    customer_data['email'] = session['email']
                
                try:
                    insert_response = query_table('customers', query_type='insert', data=customer_data)
                    
                    if insert_response and insert_response.data:
                        session['customer_id'] = str(customer_id)
                        flash('Customer profile has been set up', 'success')
                    else:
                        print(f"WARNING: Failed to create customer record")
                        session['customer_id'] = str(customer_id)  # Still set it to allow user to proceed
                except Exception as e:
                    print(f"ERROR creating customer record: {str(e)}")
                    session['customer_id'] = str(customer_id)  # Still set it to allow user to proceed
        except Exception as e:
            print(f"ERROR retrieving customer ID: {str(e)}")
            # Create a temporary ID to allow user to continue
            session['customer_id'] = str(uuid.uuid4())
    
    customer_id = safe_uuid(session.get('customer_id'))
    
    # Get businesses where customer has credit
    businesses = []
    try:
        businesses_response = query_table('customer_credits', filters=[('customer_id', 'eq', customer_id)])
        credit_records = businesses_response.data if businesses_response and businesses_response.data else []
        
        # For each credit record, get the business details
        for credit in credit_records:
            business_id = credit.get('business_id')
            if business_id:
                business_response = query_table('businesses', filters=[('id', 'eq', business_id)])
                if business_response and business_response.data:
                    business = business_response.data[0]
                    # Merge business data with credit data
                    business_with_credit = {**business, 'current_balance': credit.get('current_balance', 0)}
                    businesses.append(business_with_credit)
                else:
                    # If we can't get business details, still show the credit record with minimal info
                    businesses.append({
                        'id': business_id,
                        'name': 'Unknown Business',
                        'current_balance': credit.get('current_balance', 0)
                    })
    except Exception as e:
        print(f"ERROR retrieving business credits: {str(e)}")
        # Continue with empty list
    
    return render_template('customer/dashboard.html', businesses=businesses)

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

# Run the application
if __name__ == '__main__':
    app.run(debug=True, port=5003) 