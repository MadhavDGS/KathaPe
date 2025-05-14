from flask import session, current_app, redirect, url_for, flash
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps

def get_current_user():
    """Get the current user from the session"""
    if 'user_id' in session:
        # Special handling for demo accounts
        if session['user_id'] == '11111111-1111-1111-1111-111111111111':
            # Demo business owner
            return {
                'id': '11111111-1111-1111-1111-111111111111',
                'name': 'Demo Business Owner',
                'phone_number': '9876543210',
                'email': 'business@example.com',
                'user_type': 'business'
            }
        elif session['user_id'] == '22222222-2222-2222-2222-222222222222':
            # Demo customer
            return {
                'id': '22222222-2222-2222-2222-222222222222',
                'name': 'Demo Customer',
                'phone_number': '9876543211',
                'email': 'customer@example.com',
                'user_type': 'customer'
            }
        
        # Regular user lookup from database using admin_supabase to bypass RLS
        user = current_app.admin_supabase.table('users').select('*').eq('id', session['user_id']).execute()
        if user.data:
            return user.data[0]
    return None

def login_required(f):
    """Decorator to require login for a route"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def business_required(f):
    """Decorator to require business owner login for a route"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        
        user = get_current_user()
        if not user or user['user_type'] != 'business':
            flash('This page is for business owners only.', 'warning')
            return redirect(url_for('main.index'))
        
        return f(*args, **kwargs)
    return decorated_function

def customer_required(f):
    """Decorator to require customer login for a route"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        
        user = get_current_user()
        if not user or user['user_type'] != 'customer':
            flash('This page is for customers only.', 'warning')
            return redirect(url_for('main.index'))
        
        return f(*args, **kwargs)
    return decorated_function

def verify_password(stored_hash, password):
    """Verify a password against a hash"""
    try:
        print(f"Verifying password. Hash method: {stored_hash.split('$')[0] if '$' in stored_hash else 'unknown'}")
        return check_password_hash(stored_hash, password)
    except Exception as e:
        print(f"Error verifying password: {str(e)}")
        return False

def hash_password(password):
    """Hash a password"""
    # Use the stronger pbkdf2:sha256 method with 8 iterations for consistent hashing
    return generate_password_hash(password, method='pbkdf2:sha256', salt_length=8) 