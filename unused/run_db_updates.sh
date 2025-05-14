#!/bin/bash

# Load environment variables from .env file if it exists
if [ -f ".env" ]; then
    source .env
fi

# Use environment variables or defaults
DB_HOST=${DB_HOST:-"db.ghbmfgomnqmffixfkdyp.supabase.co"}
DB_PORT=${DB_PORT:-"5432"}
DB_NAME=${DB_NAME:-"postgres"}
DB_USER=${DB_USER:-"postgres"}
DB_PASSWORD=${DB_PASSWORD:-"your-password-here"}

# Function to run SQL files
run_sql_file() {
    echo "Running $1..."
    PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -d $DB_NAME -U $DB_USER -f "$1"
    if [ $? -eq 0 ]; then
        echo "Successfully executed $1"
    else
        echo "Error executing $1"
        exit 1
    fi
}

# Run all SQL enhancement files
run_sql_file "db_init.sql"
run_sql_file "db_business_pin_enhancements.sql"
run_sql_file "db_enhanced_dashboard_function.sql"

echo "All database updates completed successfully!" 