# Katha - Credit Management System

A Flask application for managing credit between businesses and customers, with WhatsApp integration for sending reminders.

## Setup Instructions

### 1. Database Setup (Supabase)

1. Create a Supabase account and project at [supabase.com](https://supabase.com)
2. Go to your Supabase project's SQL Editor
3. Copy and paste the contents of `db_enhancements.sql` into the SQL editor
4. Run the SQL to create the necessary tables and functions

### 2. Environment Configuration

Run the setup script to configure your environment variables:

```bash
python setup_env.py
```

You'll need:
- Your Supabase project ID (found in your project's API settings)
- Your Supabase database password

### 3. Install Dependencies

```bash
pip install flask requests psycopg2-binary python-dotenv
```

### 4. Run the Application

```bash
python app.py
```

The application will be available at `http://127.0.0.1:5000`

## Features

- Business & customer user management
- Credit and payment tracking
- Receipt uploads via media attachments
- WhatsApp integration for payment reminders
- Mobile-friendly UI with transaction history in chat format

## Application Structure

- `/templates` - HTML templates for the application
- `/static` - CSS, JavaScript, and uploaded files
- `app.py` - Main Flask application
- `db_enhancements.sql` - Database schema and functions

# Katha: Phone-Based Authentication

This repository contains the Katha application, featuring simplified phone-based authentication.

## Overview

Katha is a Flask application that uses Supabase as its database backend. The application has been updated to use phone numbers as the primary authentication method instead of email addresses.

## Setup Instructions

### 1. Supabase Setup

1. Log in to your Supabase dashboard at https://app.supabase.com/
2. Select your project
3. Go to the SQL Editor tab
4. Create a new query
5. Copy the entire content of the `update_auth_schema.sql` file
6. Paste it into the SQL Editor and run it

### 2. Environment Configuration

1. Copy the `env_example` file to `.env`
2. Update the Supabase credentials and other settings
3. Set `AUTO_CREATE_USERS=true` if you want users to be automatically created when they attempt to log in

```
cp env_example .env
nano .env  # Edit with your credentials
```

### 3. Application Deployment

1. Install dependencies:
```
pip install -r requirements.txt
```

2. Run the application:
```
python app.py
```

3. Access the application at http://127.0.0.1:5002

## Key Features

### Phone-Based Authentication

- Users register and log in using their phone number and password
- No email verification required
- Simplified, streamlined user experience

### Auto-User Creation (Optional)

- With `AUTO_CREATE_USERS=true`, new users are automatically created on login attempt
- Useful for rapid onboarding without requiring separate registration

### Database Integration

- Direct database authentication instead of Supabase Auth
- SQL triggers automatically create associated profiles
- Safe UUID handling prevents database errors

## Architecture

The application uses:
- Flask for the web framework
- Supabase PostgreSQL for the database
- Database triggers for automatic record creation
- Direct password verification for authentication

## Troubleshooting

If you encounter login issues:
1. Check the application logs for debug information
2. Verify that all SQL scripts have been run successfully
3. Ensure database credentials are correct in the `.env` file
4. Check user records directly in the Supabase dashboard 