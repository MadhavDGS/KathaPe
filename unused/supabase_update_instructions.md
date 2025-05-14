# Supabase Database Update Instructions

This guide explains how to update your Supabase database to support phone-based authentication for Katha application.

## Database Update Options

You have three options for updating your database:

### Option 1: Modify Existing Database (Recommended for Production)

Use this option if you want to preserve existing data while updating the schema to support phone-based authentication.

1. Log in to your Supabase dashboard at https://app.supabase.com/
2. Select your project
3. Go to the SQL Editor tab in the left navigation menu
4. Create a new query by clicking on "New Query"
5. Copy the entire content of the `update_auth_schema.sql` file
6. Paste it into the SQL Editor
7. Click "Run" to execute the queries

### Option 2: Complete Database Reset (Recommended for Development)

Use this option if you want to completely reset the database and start fresh. **WARNING: This will delete all existing data!**

This script handles dependent tables like `media_attachments` by dropping them before their dependencies.

1. Log in to your Supabase dashboard
2. Go to the SQL Editor
3. Create a new query
4. Copy the entire content of the `reset_database.sql` file
5. Paste it into the SQL Editor
6. Click "Run" to execute the queries

### Option 3: Simplified Reset using CASCADE (Fastest Method)

If you encounter dependency errors with Option 2, use this simpler approach that drops all tables with the CASCADE option.

1. Log in to your Supabase dashboard
2. Go to the SQL Editor
3. Create a new query
4. Copy the entire content of the `reset_database_cascade.sql` file
5. Paste it into the SQL Editor
6. Click "Run" to execute the queries

## What These Changes Do

The provided SQL scripts make several important changes to your database:

1. Updates the `users` table to use phone numbers as the primary identifier
2. Adds appropriate columns and constraints for phone-based authentication
3. Creates triggers to automatically create associated customer/business records
4. Adds a custom function for phone+password authentication
5. Creates a helpful view for calculating customer balances

## After Running the Script

After successfully running the script, your Supabase database will be aligned with the simplified authentication approach in your Flask application. Users will be able to register and log in using just their phone number and password.

## Important Notes

- The update script is designed to modify existing tables without losing data
- The reset scripts will completely remove all existing tables and recreate them
- The CASCADE option handles dependent tables automatically
- If any specific queries fail, check the table structure and adjust as needed
- These changes support the direct database authentication approach instead of relying on Supabase Auth

For any errors or issues, check your Supabase database logs or reach out for support. 