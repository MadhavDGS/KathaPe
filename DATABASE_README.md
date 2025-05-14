# Database Schema Updates

This document provides instructions for updating the database schema to ensure all required columns exist and relationships are properly maintained.

## Schema Changes

The file `db_schema_fix.sql` contains SQL queries to update the database schema with the following changes:

1. **Add missing columns to tables**:
   - Add `address`, `notes`, and `profile_photo_url` columns to the `customers` table
   - Add `updated_at`, `last_transaction_date`, and `last_reminder_date` columns to the `customer_credits` table
   - Add `created_by`, `media_url`, and `notes` columns to the `transactions` table

2. **Create consistency triggers**:
   - Automatically update the `updated_at` timestamp when records are modified
   - Ensure customer-business relationships are unique
   - Automatically create credit relationships when transactions are added

3. **Add transaction management**:
   - Create triggers to automatically update balance in `customer_credits` when transactions are added
   - Set up proper credit and payment accounting
   - Track last transaction date

4. **Add reminder tracking**:
   - Create a new `reminders` table to track all reminders sent
   - Automatic updating of `last_reminder_date` in customer credits
   - Record reminder history for analytics

## Database Structure

Here's the core database structure:

### users
- `id` (UUID): Primary key
- `name` (TEXT): User's name
- `phone_number` (TEXT): User's phone number
- `email` (TEXT): User's email (optional)
- `user_type` (TEXT): Either 'business' or 'customer'
- `password` (TEXT): Password for authentication
- `created_at` (TIMESTAMP): Creation timestamp

### businesses
- `id` (UUID): Primary key
- `user_id` (UUID): Foreign key to users table
- `name` (TEXT): Business name
- `description` (TEXT): Business description
- `access_pin` (TEXT): PIN for customers to connect
- `profile_photo_url` (TEXT): Profile photo URL
- `created_at` (TIMESTAMP): Creation timestamp

### customers
- `id` (UUID): Primary key
- `user_id` (UUID): Foreign key to users table
- `name` (TEXT): Customer name
- `phone_number` (TEXT): Customer phone
- `whatsapp_number` (TEXT): WhatsApp number for reminders
- `email` (TEXT): Customer email
- `address` (TEXT): Customer address
- `notes` (TEXT): Additional notes
- `profile_photo_url` (TEXT): Profile photo URL
- `created_at` (TIMESTAMP): Creation timestamp

### customer_credits
- `id` (UUID): Primary key
- `business_id` (UUID): Foreign key to businesses
- `customer_id` (UUID): Foreign key to customers
- `current_balance` (NUMERIC): Current credit balance
- `created_at` (TIMESTAMP): When relationship was created
- `updated_at` (TIMESTAMP): Last update timestamp
- `last_transaction_date` (TIMESTAMP): Date of last transaction
- `last_reminder_date` (TIMESTAMP): Date of last reminder sent

### transactions
- `id` (UUID): Primary key
- `business_id` (UUID): Foreign key to businesses
- `customer_id` (UUID): Foreign key to customers
- `amount` (NUMERIC): Transaction amount
- `transaction_type` (TEXT): 'credit' or 'payment'
- `notes` (TEXT): Transaction notes
- `media_url` (TEXT): Receipt image URL
- `created_at` (TIMESTAMP): Transaction timestamp
- `created_by` (UUID): User who created the transaction

### reminders
- `id` (UUID): Primary key
- `business_id` (UUID): Foreign key to businesses
- `customer_id` (UUID): Foreign key to customers
- `sent_at` (TIMESTAMP): When reminder was sent
- `sent_by` (UUID): User who sent the reminder
- `reminder_type` (TEXT): Reminder medium (e.g., 'whatsapp')
- `message` (TEXT): Reminder message content

## How to Apply Schema Changes

### Method 1: Using Supabase SQL Editor

1. Log in to your Supabase dashboard
2. Go to the SQL Editor
3. Copy the contents of `db_schema_fix.sql` and paste into the SQL Editor
4. Run the queries

### Method 2: Using the Command Line

If you have installed the Supabase CLI:

```bash
# Export your Supabase credentials
export SUPABASE_URL=your_supabase_url
export SUPABASE_KEY=your_supabase_key

# Run the SQL file against your Supabase instance
supabase db execute < db_schema_fix.sql
```

### Method 3: Using Python and psycopg2

```python
import psycopg2

# Replace with your Supabase PostgreSQL connection info
conn = psycopg2.connect(
    host="your_supabase_host",
    database="postgres",
    user="postgres",
    password="your_postgres_password"
)

# Open the SQL file
with open('db_schema_fix.sql', 'r') as f:
    sql = f.read()

# Execute the SQL
with conn.cursor() as cur:
    cur.execute(sql)
    conn.commit()

conn.close()
```

## Data Persistence

With these changes, the application will now:

1. Maintain a persistent relationship between customers and businesses
2. Properly handle customer data across multiple businesses
3. Ensure credit balances are accurately tracked and updated with every transaction
4. Keep transaction history complete and accurate
5. Track all reminder history for better customer management

After applying these changes, all relationships will persist between app restarts and will be properly maintained even if the same customer connects to multiple businesses. 