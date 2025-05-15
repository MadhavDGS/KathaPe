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
        
        # Set sensible default values for the session in case DB operations fail
        user_id = str(uuid.uuid4())
        user_name = f"User {phone[-4:]}"
        
        try:
            # Try Supabase authentication with minimal field selection
            client = get_supabase_client()
            if not client:
                flash('Database connection error', 'error')
                return render_template('login.html')
            
            # Extra logging for Render
            if RENDER_DEPLOYMENT:
                print(f"RENDER: Starting user lookup for phone={phone}")
                start_time = time.time()
            
            # Directly execute query without timeout function for login
            try:
                # Use minimal fields for better performance
                user_response = client.table('users').select('id,name,password,user_type').eq('phone_number', phone).execute()
                
                if RENDER_DEPLOYMENT:
                    elapsed_time = time.time() - start_time
                    print(f"RENDER: User lookup completed in {elapsed_time:.2f} seconds")
                
                if not user_response or not user_response.data:
                    flash('Invalid credentials: User not found', 'error')
                    return render_template('login.html')
                
                user = user_response.data[0]
                user_id = user['id']
                print(f"DEBUG: Found user with ID {user_id}")
                
                # Verify password
                if user.get('password') != password:
                    flash('Invalid password', 'error')
                    return render_template('login.html')
                
                # Set session data
                session['user_id'] = user_id
                session['user_name'] = user.get('name', user_name)
                session['user_type'] = user_type
                session['phone_number'] = phone
                
                # For faster logins, don't query additional profile data now
                # We'll fetch it later when needed in the dashboard
                if user_type == 'business':
                    # Just store minimal ID to fetch details later
                    business_id = str(uuid.uuid4())
                    session['business_id'] = business_id
                    session['business_name'] = f"{user.get('name')}'s Business"
                    session['access_pin'] = f"{int(datetime.now().timestamp()) % 10000:04d}"
                    
                    flash('Login successful!', 'success')
                    return redirect(url_for('business_dashboard'))
                else:
                    # Just store minimal ID to fetch details later
                    customer_id = str(uuid.uuid4())
                    session['customer_id'] = customer_id
                    
                    flash('Login successful!', 'success')
                    return redirect(url_for('customer_dashboard'))
                
            except Exception as e:
                print(f"Database query error: {str(e)}")
                flash('Login failed. Database error.', 'error')
                return render_template('login.html')
                
        except Exception as e:
            print(f"DEBUG: Login error: {str(e)}")
            traceback.print_exc()
            flash('Login failed. Please try again.', 'error')
            return render_template('login.html')
    
    return render_template('login.html') 