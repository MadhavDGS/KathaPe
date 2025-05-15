# KathaPe Data Fix Tools

This folder contains tools to help diagnose and fix data issues in your KathaPe app.

## Issues Fixed

The following issues have been fixed:

1. **Dark/Light Mode Toggle Interference**: The toggle button was interfering with the menu on mobile devices. This has been fixed by adjusting the CSS positioning and adding proper mobile menu adjustments.

2. **Sample Data Generation**: Added scripts to check for data issues and create sample test data.

## Tools Included

### 1. get_business_data.py

This script connects to your Supabase database and checks if it can retrieve business and customer data. It prints out diagnostic information to help identify connectivity or data issues.

To use:
```bash
python get_business_data.py
```

### 2. add_sample_data.py

This script adds sample data to your database for testing. It creates:
- 5 customers
- Credit relationships between customers and the business
- Sample transactions (both credit and payment types)

To use:
```bash
python add_sample_data.py
```

### 3. update_css.sh

This script simplifies updating just the CSS changes without affecting the Flask app files, which might have syntax issues.

To use:
```bash
./update_css.sh
```

## Credentials

The scripts use the updated Supabase credentials:

- URL: `https://ghbmfgomnqmffixfkdyp.supabase.co`
- Anon Key: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdoYm1mZ29tbnFtZmZpeGZrZHlwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDcxNDAxNTcsImV4cCI6MjA2MjcxNjE1N30.Fw750xiDWVPrl6ssr9p6AJTt--8zvnPoboxJiURvsOI`

## Next Steps

1. **Test Login**: The login should now work correctly with the sample data.
   - Username: One of the sample phone numbers (like '9876500001')
   - Password: 'sample123'
   
2. **Check Dashboard**: After login, you should see customers and transactions on the dashboard.

3. **Fix Flask App Syntax**: There are still syntax issues in the main `flask_app.py` file that need to be fixed. These scripts provide a workaround without needing to modify that file. 