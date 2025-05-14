# Simplified Database Schema Instructions

This guide explains how to completely reset and rebuild your Supabase database with a simplified schema focused on phone-based authentication for the Katha application.

## Why Use This Approach

The simplified schema:
1. Uses a straightforward phone-based authentication system
2. Eliminates complex table dependencies
3. Removes unnecessary columns and simplifies data structures
4. Uses plaintext passwords for development simplicity (you can enhance security later)
5. Includes sample data to get started immediately
6. Properly sets up RLS (Row Level Security) policies for public access

## Step 1: Reset Your Database

1. **Log in to your Supabase dashboard** at https://app.supabase.com/
2. **Select your project**
3. **Go to the SQL Editor** tab in the left navigation menu
4. **Create a new query** by clicking on "New Query"
5. **Copy the entire content** of the `simplified_schema.sql` file
6. **Paste it into the SQL Editor**
7. **Review the script** - it will drop ALL existing data in your database
8. **Click "Run"** to execute the queries

## Step 2: Set Up Your Environment

1. **Run the environment setup script** to configure your Supabase credentials:
   ```
   python update_env.py
   ```

2. **Enter your Supabase credentials** when prompted:
   - Supabase URL
   - Supabase anon key
   - Supabase service role key (important for bypassing RLS)

   You can find these in your Supabase dashboard under Project Settings > API.

3. **Ensure all necessary directories exist**:
   ```
   mkdir -p static/uploads static/qr_codes
   ```

## Step 3: Run the Flask Application

1. **Start the Flask application**:
   ```
   python app.py
   ```

2. **Access the application** at http://127.0.0.1:5002

## What This Schema Does

1. **Drops everything** in the public schema and recreates it
2. **Creates a minimal set of tables**:
   - `users` - with phone-based authentication
   - `businesses` - for business profiles
   - `customers` - for customer profiles
   - `customer_credits` - tracks credit between businesses and customers
   - `transactions` - records payments and credits
3. **Sets up RLS policies** for public access to all tables
4. **Creates automated triggers** to maintain relationships
5. **Adds sample data** for testing

## Key Changes in the Application Code

1. **Using the service role key** to bypass RLS policies
2. **Direct password comparison** instead of hashed verification
3. **Simplified field names** in all database queries
4. **Auto-creation of profile records** if they don't exist

## Sample Login Credentials

The script creates two sample users:
- **Business User**: Phone: 1234567890, Password: password123
- **Customer User**: Phone: 0987654321, Password: password123

## Troubleshooting

If you encounter "permission denied" errors:
1. Make sure you're using the service role key (not the anon key)
2. Verify that the RLS policies are properly set up in your database
3. Check your application logs for detailed error messages
4. Restart the Flask application after updating the .env file 