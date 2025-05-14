#!/bin/bash

echo "Setting up Katha database..."

# Set your PostgreSQL connection details
DB_USER="postgres"
DB_NAME="postgres"
DB_HOST="localhost"
DB_PORT="5432" 

# You may need to adjust these based on your Supabase setup
# For local development with Supabase CLI, these should work

# Run the schema setup
echo "Creating schema and tables..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f supabase_setup_fixed.sql

# Run the helper functions
echo "Adding helper functions..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f supabase_helper_functions.sql

# Run the seed data
echo "Adding seed data..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f supabase_seed_data.sql

echo "Database setup complete!" 