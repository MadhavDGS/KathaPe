from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, jsonify
from app.utils.auth_utils import login_required, business_required, customer_required, get_current_user
import random
import string
import qrcode
import io
import base64
from datetime import datetime, timedelta

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    """Home page"""
    # Check if user is logged in
    user = get_current_user()
    if user:
        # Redirect to the appropriate dashboard based on user type
        if user['user_type'] == 'business':
            return redirect(url_for('main.dashboard'))
        elif user['user_type'] == 'customer':
            return redirect(url_for('main.customer_dashboard'))
    
    # If not logged in, show the main index page
    return render_template('main/index.html')

@bp.route('/dark')
def dark_test():
    """Guaranteed dark mode test page"""
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return render_template('guaranteed_dark.html', current_time=current_time)

@bp.route('/test-supabase')
def test_supabase():
    """Test if Supabase is working"""
    # Try to select something from Supabase
    try:
        result = current_app.supabase.table('users').select('count').execute()
        return jsonify({
            'status': 'success',
            'message': 'Supabase connection working!',
            'data': result.data
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@bp.route('/dashboard')
@business_required
def dashboard():
    user = get_current_user()
    
    # Special handling for demo business account
    if user and user['id'] == '11111111-1111-1111-1111-111111111111':
        # For demo account, create structured data for the template
        demo_businesses = [
            {
                'id': '33333333-3333-3333-3333-333333333333',
                'name': 'Demo Shop',
                'description': 'A demo shop for testing',
                'balance': '1000.00',
                'is_active': True
            }
        ]
        
        demo_transactions = [
            {
                'amount': '500.00',
                'type': 'credit',
                'description': 'Initial credit',
                'date': datetime.now().strftime("%Y-%m-%d %H:%M")
            }
        ]
        
        return render_template('main/dashboard.html', 
                              user=user, 
                              businesses=demo_businesses,
                              recent_transactions=demo_transactions)
    
    # Get businesses for the current user
    try:
        businesses_result = current_app.supabase.table('businesses') \
            .select('*') \
            .eq('user_id', user['id']) \
            .execute()
        
        # Format business data
        businesses = []
        if businesses_result.data:
            for business in businesses_result.data:
                businesses.append({
                    'id': business['id'],
                    'name': business['name'],
                    'description': business['description'] or '',
                    'balance': business.get('balance', '0.00'),
                    'is_active': True
                })
        
        # Get recent transactions for the user's businesses
        transactions = []
        if businesses:
            business_ids = [b['id'] for b in businesses]
            transactions_result = current_app.supabase.table('transactions') \
                .select('*') \
                .in_('business_id', business_ids) \
                .order('created_at', desc=True) \
                .limit(10) \
                .execute()
            
            if transactions_result.data:
                for tx in transactions_result.data:
                    transactions.append({
                        'amount': tx['amount'],
                        'type': tx['transaction_type'],
                        'description': tx['notes'] or '',
                        'date': tx['created_at']
                    })
        
        return render_template('main/dashboard.html', 
                              user=user, 
                              businesses=businesses,
                              recent_transactions=transactions)
    
    except Exception as e:
        print(f"Error fetching business data: {str(e)}")
        flash("Unable to fetch business data. Please try again later.", "danger")
        
        # Default empty state
        return render_template('main/dashboard.html', 
                              user=user, 
                              businesses=[],
                              recent_transactions=[])

@bp.route('/customer-dashboard')
@customer_required
def customer_dashboard():
    user = get_current_user()
    print(f"Customer dashboard - User ID: {user['id']}, Name: {user['name']}")
    
    # For all customer accounts, use admin_supabase to bypass RLS issues
    try:
        # Direct query to get customer and their credits with business information
        query = f"""
        SELECT 
            c.id as customer_id, 
            c.name as customer_name,
            cc.id as credit_id,
            cc.current_balance,
            cc.updated_at,
            b.id as business_id,
            b.name as business_name
        FROM 
            customers c
            JOIN customer_credits cc ON c.id = cc.customer_id
            JOIN businesses b ON cc.business_id = b.id
        WHERE 
            c.user_id = '{user['id']}'
        """
        
        # Execute direct query with admin privileges
        result = current_app.admin_supabase.sql(query).execute()
        print(f"Direct SQL query result: {result.data}")
        
        if result.data and len(result.data) > 0:
            # Process the results
            credit_records = []
            total_credit = 0
            
            for record in result.data:
                credit_amount = float(record.get('current_balance', 0))
                business_name = record.get('business_name', 'Unknown Business')
                last_updated = record.get('updated_at', datetime.now().strftime("%Y-%m-%d %H:%M"))
                
                credit_records.append({
                    'business_name': business_name,
                    'credit_amount': "{:.2f}".format(credit_amount),
                    'last_updated': last_updated
                })
                
                total_credit += credit_amount
            
            return render_template('main/customer_dashboard.html', 
                                  user=user, 
                                  customers=credit_records,
                                  total_credits="{:.2f}".format(total_credit))
        else:
            # Fallback to get/create customer record if no credits found
            customer_result = current_app.admin_supabase.table('customers') \
                .select('*') \
                .eq('user_id', user['id']) \
                .execute()
            
            if not customer_result.data or len(customer_result.data) == 0:
                # Create a new customer record
                customer_data = {
                    'name': user['name'],
                    'phone_number': user['phone_number'],
                    'user_id': user['id'],
                    'email': user.get('email', None)
                }
                
                try:
                    customer_insert = current_app.admin_supabase.table('customers').insert(customer_data).execute()
                    print(f"Created new customer record: {customer_insert.data}")
                    flash("Your account is set up. Add businesses by entering a business code.", "info")
                except Exception as e:
                    print(f"Error creating customer: {str(e)}")
            else:
                flash("You don't have any business credits yet. Add a business to get started.", "info")
    
    except Exception as e:
        print(f"Error in customer dashboard: {str(e)}")
        import traceback
        traceback.print_exc()
        flash("Unable to fetch your business data. Please try again later.", "danger")
    
    # Default empty state
    return render_template('main/customer_dashboard.html', 
                          user=user, 
                          customers=[],
                          total_credits="0.00")

@bp.route('/business')
@business_required
def business():
    user = get_current_user()
    
    # Get businesses for the current user
    result = current_app.supabase.table('businesses') \
        .select('*') \
        .eq('user_id', user['id']) \
        .execute()
    
    businesses = result.data
    
    return render_template('main/business.html', businesses=businesses)

@bp.route('/business/add', methods=['POST'])
@business_required
def add_business():
    user = get_current_user()
    
    name = request.form.get('name')
    description = request.form.get('description', '')
    
    # Generate a unique PIN
    while True:
        pin = ''.join(random.choices(string.digits, k=6))
        check = current_app.supabase.table('businesses') \
            .select('id') \
            .eq('access_pin', pin) \
            .execute()
        if not check.data:
            break
    
    # Create new business with correct field names matching the schema
    result = current_app.supabase.table('businesses') \
        .insert({
            'name': name,
            'description': description,
            'address': '',  # Empty default address
            'business_phone': '',  # Empty default phone 
            'business_email': '',  # Empty default email
            'access_pin': pin,
            'user_id': user['id']
        }) \
        .execute()
    
    if result.data:
        flash('Business added successfully!', 'success')
    else:
        flash('Failed to add business.', 'danger')
    
    return redirect(url_for('main.business'))

@bp.route('/business/<business_id>/qr')
@business_required
def business_qr(business_id):
    """Display business QR code"""
    user = get_current_user()
    
    # Get business details
    result = current_app.supabase.table('businesses') \
        .select('*') \
        .eq('id', business_id) \
        .eq('user_id', user['id']) \
        .execute()
    
    if not result.data:
        flash('Business not found.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    business = result.data[0]
    
    # Generate QR code
    qr_data = f"business:{business['id']}:{business['name']}:{business['access_pin']}"
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
    
    qr_code = f"data:image/png;base64,{img_str}"
    
    return render_template('main/business_qr.html', business=business, qr_code=qr_code)

@bp.route('/business/<business_id>/qr_image')
@business_required
def business_qr_image(business_id):
    """Return just the QR code image"""
    user = get_current_user()
    
    # Get business details
    result = current_app.supabase.table('businesses') \
        .select('*') \
        .eq('id', business_id) \
        .eq('user_id', user['id']) \
        .execute()
    
    if not result.data:
        return "Business not found", 404
    
    business = result.data[0]
    
    # Generate QR code
    qr_data = f"business:{business['id']}:{business['name']}:{business['access_pin']}"
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
    
    # Return image directly
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    buffered.seek(0)
    
    return current_app.response_class(buffered.getvalue(), mimetype='image/png')

@bp.route('/customer/view/<business_id>')
@business_required
def customer_view(business_id):
    """View customers for a specific business - business owners only"""
    user = get_current_user()
    
    # Get business details and verify ownership - use admin_supabase
    business_result = current_app.admin_supabase.table('businesses') \
        .select('*') \
        .eq('id', business_id) \
        .eq('user_id', user['id']) \
        .execute()
    
    if not business_result.data:
        flash('Business not found or you do not have permission to view it.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    business = business_result.data[0]
    
    # Get customers with credits for this business - use admin_supabase
    customers_result = current_app.admin_supabase.table('customer_credits') \
        .select('*, customers(*)') \
        .eq('business_id', business_id) \
        .execute()
    
    print(f"Customer credits query result: {customers_result.data}")
    
    customers = []
    if customers_result.data:
        for credit in customers_result.data:
            if credit['customers']:
                customer = credit['customers']
                customer['credit_amount'] = "{:.2f}".format(float(credit['current_balance']))
                customer['last_updated'] = credit['updated_at']
                customers.append(customer)
    
    return render_template('main/customer_view.html', business=business, customers=customers)

@bp.route('/customer/detail/<customer_id>')
@business_required
def customer_detail(customer_id):
    """View details of a specific customer - business owners only"""
    user = get_current_user()
    
    # Get customer details with business info - use admin_supabase
    customer_result = current_app.admin_supabase.table('customer_credits') \
        .select('*, customers(*), businesses(*)') \
        .eq('customer_id', customer_id) \
        .execute()
    
    print(f"Customer detail query result: {customer_result.data}")
    
    if not customer_result.data:
        flash('Customer not found.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    credit = customer_result.data[0]
    customer = credit['customers']
    business = credit['businesses']
    
    # Verify that the business belongs to the current user
    if business['user_id'] != user['id']:
        flash('You do not have permission to view this customer.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    customer['credit_amount'] = "{:.2f}".format(float(credit['current_balance']))
    
    # Get credit history - use admin_supabase
    history_result = current_app.admin_supabase.table('credit_history') \
        .select('*') \
        .eq('customer_credit_id', credit['id']) \
        .order('created_at', desc=True) \
        .execute()
    
    history = history_result.data
    
    return render_template('main/customer_detail.html', 
                          customer=customer, 
                          business=business, 
                          history=history)

@bp.route('/transaction/add', methods=['GET', 'POST'])
@business_required
def add_transaction():
    user = get_current_user()
    
    if request.method == 'POST':
        business_id = request.form.get('business_id')
        amount = float(request.form.get('amount'))
        transaction_type = request.form.get('type')
        description = request.form.get('description', '')
        
        # Check if business belongs to user
        business_result = current_app.supabase.table('businesses') \
            .select('*') \
            .eq('id', business_id) \
            .eq('user_id', user['id']) \
            .execute()
        
        if not business_result.data:
            flash('Business not found.', 'danger')
            return redirect(url_for('main.dashboard'))
        
        business = business_result.data[0]
        
        # Update business balance
        new_balance = business['balance']
        if transaction_type == 'credit':
            new_balance += amount
        else:
            new_balance -= amount
        
        # Create transaction
        transaction_result = current_app.supabase.table('transactions') \
            .insert({
                'business_id': business_id,
                'user_id': user['id'],
                'amount': amount,
                'type': transaction_type,
                'description': description,
                'date': datetime.utcnow().isoformat()
            }) \
            .execute()
        
        # Update business balance
        business_update = current_app.supabase.table('businesses') \
            .update({'balance': new_balance}) \
            .eq('id', business_id) \
            .execute()
        
        if transaction_result.data and business_update.data:
            flash('Transaction added successfully!', 'success')
            return redirect(url_for('main.dashboard'))
        else:
            flash('Failed to add transaction.', 'danger')
    
    # Get businesses for dropdown
    businesses_result = current_app.supabase.table('businesses') \
        .select('*') \
        .eq('user_id', user['id']) \
        .execute()
    
    return render_template('main/add_transaction.html', businesses=businesses_result.data)

@bp.route('/customer/add', methods=['GET', 'POST'])
@business_required
def add_customer():
    user = get_current_user()
    
    if request.method == 'POST':
        business_id = request.form.get('business_id')
        customer_name = request.form.get('customer_name')
        phone = request.form.get('phone')
        email = request.form.get('email', '').strip()
        address = request.form.get('address', '')
        notes = request.form.get('notes', '')
        initial_credit = float(request.form.get('initial_credit', 0))
        
        # Check if business belongs to user
        business_result = current_app.supabase.table('businesses') \
            .select('*') \
            .eq('id', business_id) \
            .eq('user_id', user['id']) \
            .execute()
        
        if not business_result.data:
            flash('Business not found or you do not have permission.', 'danger')
            return redirect(url_for('main.dashboard'))
        
        # Create customer data
        customer_data = {
            'name': customer_name,
            'phone_number': phone,
            'notes': notes
        }
        
        # Only add email and address if they're provided
        if email:
            customer_data['email'] = email
            
        if address:
            customer_data['address'] = address
        
        # Create customer
        customer_result = current_app.supabase.table('customers') \
            .insert(customer_data) \
            .execute()
        
        if customer_result.data:
            customer_id = customer_result.data[0]['id']
            
            # Create customer credit record
            credit_data = {
                'customer_id': customer_id,
                'business_id': business_id,
                'current_balance': initial_credit
            }
            
            credit_result = current_app.supabase.table('customer_credits') \
                .insert(credit_data) \
                .execute()
            
            # If initial credit is provided, add a transaction record
            if initial_credit > 0:
                transaction_data = {
                    'business_id': business_id,
                    'customer_id': customer_id,
                    'amount': initial_credit,
                    'transaction_type': 'credit',
                    'notes': 'Initial credit',
                    'created_by': user['id']
                }
                
                transaction_result = current_app.supabase.table('transactions') \
                    .insert(transaction_data) \
                    .execute()
            
            flash('Customer added successfully!', 'success')
            return redirect(url_for('main.customer_view', business_id=business_id))
        else:
            flash('Failed to add customer.', 'danger')
    
    # Get businesses for dropdown
    businesses_result = current_app.supabase.table('businesses') \
        .select('*') \
        .eq('user_id', user['id']) \
        .execute()
    
    return render_template('main/add_customer.html', businesses=businesses_result.data)

@bp.route('/test')
def test():
    """Test page to verify rendering is working"""
    from datetime import datetime
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return render_template('test.html', current_time=current_time)

@bp.route('/ultra')
def ultra_simple():
    """Ultra simple page with just inline styles"""
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return render_template('ultra_simple.html', current_time=current_time)

@bp.route('/dark-index')
def dark_index():
    """Dark themed index page with all inline styles"""
    return render_template('main/dark_index.html')

@bp.route('/customer/add-business')
@customer_required
def customer_add_business():
    """Customer adding a business by code or QR"""
    return render_template('main/add_business_code.html')

@bp.route('/customer/add-business', methods=['POST'])
@customer_required
def add_business_by_code():
    """Process adding a business by access code"""
    user = get_current_user()
    access_pin = request.form.get('access_pin')
    
    if not access_pin:
        flash('Business code is required.', 'danger')
        return redirect(url_for('main.customer_add_business'))

    try:
        # Step 1: Find the business with this PIN
        business_query = f"""
        SELECT id, name, description
        FROM businesses 
        WHERE access_pin = '{access_pin}'
        LIMIT 1
        """
        
        business_result = current_app.admin_supabase.sql(business_query).execute()
        print(f"Business query result: {business_result.data}")
        
        if not business_result.data or len(business_result.data) == 0:
            flash('Invalid business code.', 'danger')
            return redirect(url_for('main.customer_add_business'))
        
        business = business_result.data[0]
        business_id = business['id']
        business_name = business['name']
        
        # Step 2: Get or create customer record for this user
        customer_query = f"""
        SELECT id, name, phone_number
        FROM customers
        WHERE user_id = '{user['id']}'
        LIMIT 1
        """
        
        customer_result = current_app.admin_supabase.sql(customer_query).execute()
        print(f"Customer query result: {customer_result.data}")
        
        if not customer_result.data or len(customer_result.data) == 0:
            # No customer record exists - create one
            customer_data = {
                'name': user['name'],
                'phone_number': user['phone_number'],
                'user_id': user['id'],
                'email': user.get('email', None)
            }
            
            customer_insert = current_app.admin_supabase.table('customers').insert(customer_data).execute()
            print(f"Customer insert result: {customer_insert.data}")
            
            if not customer_insert.data or len(customer_insert.data) == 0:
                flash('Failed to create your customer profile. Please try again.', 'danger')
                return redirect(url_for('main.customer_add_business'))
                
            customer_id = customer_insert.data[0]['id']
        else:
            # Customer record exists
            customer_id = customer_result.data[0]['id']
        
        # Step 3: Check if relationship already exists
        relationship_query = f"""
        SELECT id 
        FROM customer_credits
        WHERE customer_id = '{customer_id}' AND business_id = '{business_id}'
        LIMIT 1
        """
        
        relationship_result = current_app.admin_supabase.sql(relationship_query).execute()
        print(f"Relationship check result: {relationship_result.data}")
        
        if relationship_result.data and len(relationship_result.data) > 0:
            flash('You already have access to this business.', 'info')
            return redirect(url_for('main.customer_dashboard'))
        
        # Step 4: Create the relationship
        credit_data = {
            'customer_id': customer_id,
            'business_id': business_id,
            'current_balance': 0
        }
        
        credit_insert = current_app.admin_supabase.table('customer_credits').insert(credit_data).execute()
        print(f"Credit insert result: {credit_insert.data}")
        
        if not credit_insert.data or len(credit_insert.data) == 0:
            flash('Failed to link business. Please try again.', 'danger')
            return redirect(url_for('main.customer_add_business'))
            
        flash(f'Successfully added {business_name} to your account.', 'success')
        return redirect(url_for('main.customer_dashboard'))
        
    except Exception as e:
        print(f"Error in add_business_by_code: {str(e)}")
        import traceback
        traceback.print_exc()
        flash('An error occurred. Please try again.', 'danger')
        return redirect(url_for('main.customer_add_business')) 