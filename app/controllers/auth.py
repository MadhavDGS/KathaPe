from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from app.utils.auth_utils import get_current_user, verify_password, hash_password
import random
import string
from datetime import datetime, timedelta
import postgrest.exceptions

bp = Blueprint('auth', __name__)

# Dictionary to store OTPs (in a real app, this would be in a database)
otp_storage = {}

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        flash('You are already logged in.', 'info')
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        login_type = request.form.get('login_type', 'phone_password')
        user_type = request.form.get('user_type', 'business')
        
        if login_type == 'phone_password':
            phone = request.form['phone']
            password = request.form['password']
            
            # DEMO ACCOUNT BYPASS - BUSINESS ACCOUNT ONLY
            # Check for demo business account
            if phone == '9876543210' and password == 'demo123' and user_type == 'business':
                # Set session directly for demo business account
                session['user_id'] = '11111111-1111-1111-1111-111111111111'  # Use the ID from the SQL sample data
                session['user_type'] = 'business'
                flash('Demo business login successful!', 'success')
                return redirect(url_for('main.dashboard'))
            
            try:
                # Direct authentication using admin_supabase to bypass RLS
                user_result = current_app.admin_supabase.table('users') \
                    .select('*') \
                    .eq('phone_number', phone) \
                    .eq('user_type', user_type) \
                    .execute()
                
                if user_result.data:
                    user = user_result.data[0]
                    # Verify password
                    if user and check_password_hash(user['password_hash'], password):
                        # Authentication successful, set session
                        session['user_id'] = user['id']
                        session['user_type'] = user['user_type']
                        
                        # If customer account, ensure customer data is properly synced
                        if user['user_type'] == 'customer':
                            try:
                                # Check if customer record exists
                                customer_check = current_app.admin_supabase.table('customers') \
                                    .select('id') \
                                    .eq('user_id', user['id']) \
                                    .execute()
                                
                                # If no customer record, create one
                                if not customer_check.data or len(customer_check.data) == 0:
                                    customer_data = {
                                        'user_id': user['id'],
                                        'name': user['name'],
                                        'phone_number': user['phone_number'],
                                        'email': user['email'] if 'email' in user else None
                                    }
                                    customer_result = current_app.admin_supabase.table('customers').insert(customer_data).execute()
                                    print(f"Created new customer record: {customer_result.data}")
                            except Exception as customer_sync_error:
                                print(f"Customer data sync error: {str(customer_sync_error)}")
                                # Continue login process even if sync fails
                        
                        flash('Login successful!', 'success')
                        if user['user_type'] == 'business':
                            return redirect(url_for('main.dashboard'))
                        else:
                            return redirect(url_for('main.customer_dashboard'))
                    else:
                        flash('Invalid password.', 'danger')
                else:
                    flash('User not found with the provided phone number.', 'danger')
                    
            except Exception as e:
                print(f"Login error: {str(e)}")
                flash('Login failed. Please try again.', 'danger')
    
    return render_template('auth/login.html')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        flash('You are already logged in.', 'info')
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        name = request.form['name']
        email = request.form.get('email', '').strip()
        phone = request.form['phone'].strip()
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        use_email_otp = 'use_email_otp' in request.form
        user_type = request.form.get('user_type', 'business')
        
        # Validate password
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('auth.register'))
        
        # DEMO ACCOUNT CREATION - FOR BUSINESS ONLY
        if name.startswith('Demo') and user_type == 'business':
            # Set demo login credentials for the business user
            flash('Demo business account created! You can log in with demo credentials.', 'success')
            flash('Login with phone: 9876543210, password: demo123', 'info')
            return redirect(url_for('auth.login'))
        
        # Try direct database operations with extensive error handling
        try:
            # First check if user exists
            existing_users = current_app.admin_supabase.table('users') \
                .select('id') \
                .eq('phone_number', phone) \
                .execute()
            
            if existing_users.data and len(existing_users.data) > 0:
                flash('Phone number already registered. Please use a different phone number.', 'danger')
                return redirect(url_for('auth.register'))
            
            # Check email uniqueness if provided
            if email:
                existing_email = current_app.admin_supabase.table('users') \
                    .select('id') \
                    .eq('email', email) \
                    .execute()
                
                if existing_email.data and len(existing_email.data) > 0:
                    flash('Email already registered. Please use a different email.', 'danger')
                    return redirect(url_for('auth.register'))
            
            # Generate a unique identifier for this registration to track
            reg_id = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
            print(f"Starting registration {reg_id} for {name}, phone: {phone}, type: {user_type}")
            
            # Hash the password
            hashed_password = hash_password(password)
            
            # Create the user with admin privileges to bypass RLS
            user_data = {
                'name': name,
                'phone_number': phone,
                'password_hash': hashed_password,
                'email': email if email else None,
                'user_type': user_type,
                'use_email_otp': use_email_otp
            }
            
            # Insert the user
            user_result = current_app.admin_supabase.table('users').insert(user_data).execute()
            
            if not user_result.data or len(user_result.data) == 0:
                print(f"Registration {reg_id} failed: No user data returned")
                flash('Registration failed. Please try again.', 'danger')
                return redirect(url_for('auth.register'))
            
            user_id = user_result.data[0]['id']
            print(f"Registration {reg_id}: User created with ID {user_id}")
            
            # Based on user type, create additional records
            if user_type == 'business':
                try:
                    # Generate PIN for business
                    pin = ''.join(random.choices(string.digits, k=6))
                    
                    # Create business
                    business_data = {
                        'user_id': user_id,
                        'name': f"{name}'s Business",
                        'description': 'My new business',
                        'access_pin': pin
                    }
                    
                    business_result = current_app.admin_supabase.table('businesses').insert(business_data).execute()
                    
                    if business_result.data and len(business_result.data) > 0:
                        business_id = business_result.data[0]['id']
                        print(f"Registration {reg_id}: Business created with ID {business_id}")
                        flash(f'Registration successful! Your business PIN is {pin}', 'success')
                    else:
                        print(f"Registration {reg_id}: Business creation failed")
                        flash('Registration partially successful, but business setup failed.', 'warning')
                except Exception as e:
                    print(f"Registration {reg_id}: Business creation error: {str(e)}")
                    flash('Registration completed but business setup encountered an error.', 'warning')
            
            elif user_type == 'customer':
                try:
                    # Create customer
                    customer_data = {
                        'user_id': user_id,
                        'name': name,
                        'phone_number': phone,
                        'email': email if email else None
                    }
                    
                    customer_result = current_app.admin_supabase.table('customers').insert(customer_data).execute()
                    print(f"Customer registration details: {customer_result.data}")
                    
                    if customer_result.data and len(customer_result.data) > 0:
                        customer_id = customer_result.data[0]['id']
                        print(f"Registration {reg_id}: Customer created with ID {customer_id}")
                        flash('Customer account registration successful!', 'success')
                    else:
                        print(f"Registration {reg_id}: Customer creation failed")
                        flash('Registration partially successful, but customer setup failed.', 'warning')
                except Exception as e:
                    print(f"Registration {reg_id}: Customer creation error: {str(e)}")
                    flash('Registration completed but customer setup encountered an error.', 'warning')
            
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            print(f"Registration error: {str(e)}")
            flash(f'Registration failed: {str(e)}', 'danger')
    
    return render_template('auth/register.html')

@bp.route('/request-otp', methods=['POST'])
def request_otp():
    if request.method == 'POST':
        email_or_phone = request.form['email_or_phone']
        user_type = request.form.get('user_type', 'business')
        
        # Check if it's an email or phone number
        is_email = '@' in email_or_phone
        
        # Query to find the user - Use admin_supabase to bypass RLS
        if is_email:
            result = current_app.admin_supabase.table('users') \
                .select('*') \
                .eq('email', email_or_phone) \
                .eq('user_type', user_type) \
                .execute()
        else:
            result = current_app.admin_supabase.table('users') \
                .select('*') \
                .eq('phone_number', email_or_phone) \
                .eq('user_type', user_type) \
                .execute()
        
        if not result.data:
            return jsonify({'success': False, 'message': f'No {user_type} account found with this email/phone'})
        
        user = result.data[0]
        
        # Generate OTP
        otp = ''.join(random.choices(string.digits, k=6))
        
        # Store OTP with expiration (10 minutes from now)
        expiration = datetime.now() + timedelta(minutes=10)
        otp_storage[email_or_phone] = {
            'otp': otp,
            'user_id': user['id'],
            'expires_at': expiration
        }
        
        # In a real app, send OTP via email or SMS
        # Here we just return it for demonstration
        return jsonify({
            'success': True, 
            'message': f'OTP sent to {email_or_phone}',
            'otp': otp  # In production, don't return the OTP!
        })
    
    return jsonify({'success': False, 'message': 'Invalid request'})

@bp.route('/verify-otp', methods=['POST'])
def verify_otp():
    if request.method == 'POST':
        email_or_phone = request.form['email_or_phone']
        otp = request.form['otp']
        
        # Check if OTP exists and is valid
        if email_or_phone not in otp_storage:
            return jsonify({'success': False, 'message': 'No OTP requested for this email/phone'})
        
        stored_data = otp_storage[email_or_phone]
        
        # Check if OTP is expired
        if datetime.now() > stored_data['expires_at']:
            del otp_storage[email_or_phone]  # Clean up expired OTP
            return jsonify({'success': False, 'message': 'OTP expired'})
        
        # Verify OTP
        if otp != stored_data['otp']:
            return jsonify({'success': False, 'message': 'Invalid OTP'})
        
        # OTP is valid, log the user in
        user_id = stored_data['user_id']
        
        # Get user details - Use admin_supabase to bypass RLS
        result = current_app.admin_supabase.table('users') \
            .select('*') \
            .eq('id', user_id) \
            .execute()
        
        if not result.data:
            return jsonify({'success': False, 'message': 'User not found'})
        
        user = result.data[0]
        
        # Set user in session
        session['user_id'] = user['id']
        session['user_type'] = user['user_type']
        
        # Clean up used OTP
        del otp_storage[email_or_phone]
        
        redirect_url = url_for('main.dashboard') if user['user_type'] == 'business' else url_for('main.customer_dashboard')
        return jsonify({
            'success': True, 
            'message': 'Login successful!',
            'redirect': redirect_url
        })
    
    return jsonify({'success': False, 'message': 'Invalid request'})

@bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        phone = request.form['phone']
        
        # Check if user exists - Use admin_supabase to bypass RLS
        result = current_app.admin_supabase.table('users') \
            .select('*') \
            .eq('phone_number', phone) \
            .execute()
        
        if not result.data:
            flash('No account found with this phone number.', 'danger')
            return redirect(url_for('auth.forgot_password'))
        
        user = result.data[0]
        
        # Generate password reset token (in a real app, store this securely)
        reset_token = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
        
        # In a real app, send reset link via SMS or email
        
        flash('If an account exists with this phone number, a password reset link has been sent.', 'info')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/forgot_password.html')

@bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))

@bp.route('/business/access', methods=['GET', 'POST'])
def business_access():
    if request.method == 'POST':
        access_pin = request.form.get('access_pin')
        
        # Check if the business with this PIN exists - Use admin_supabase to bypass RLS
        result = current_app.admin_supabase.table('businesses') \
            .select('*') \
            .eq('access_pin', access_pin) \
            .execute()
        
        if result.data:
            business = result.data[0]
            return redirect(url_for('main.business_scan', business_id=business['id']))
        else:
            flash('Invalid access PIN.', 'danger')
    
    return render_template('auth/business_access.html')

@bp.route('/verify-account')
def verify_account():
    """Debug route to check if a user has the proper associated records"""
    phone = request.args.get('phone')
    user_type = request.args.get('user_type', 'business')
    
    if not phone:
        return jsonify({
            'status': 'error',
            'message': 'Phone number is required'
        })
    
    # Get user by phone using admin_supabase to bypass RLS
    user_result = current_app.admin_supabase.table('users') \
        .select('*') \
        .eq('phone_number', phone) \
        .execute()
    
    if not user_result.data:
        return jsonify({
            'status': 'error',
            'message': 'User not found'
        })
    
    user = user_result.data[0]
    
    # Check for associated records
    if user['user_type'] == 'business':
        business_result = current_app.admin_supabase.table('businesses') \
            .select('*') \
            .eq('user_id', user['id']) \
            .execute()
        
        return jsonify({
            'status': 'success',
            'user': user,
            'has_business': bool(business_result.data),
            'business_data': business_result.data
        })
    
    elif user['user_type'] == 'customer':
        customer_result = current_app.admin_supabase.table('customers') \
            .select('*') \
            .eq('user_id', user['id']) \
            .execute()
        
        return jsonify({
            'status': 'success',
            'user': user,
            'has_customer': bool(customer_result.data),
            'customer_data': customer_result.data
        })
    
    return jsonify({
        'status': 'error',
        'message': 'Unknown user type'
    }) 