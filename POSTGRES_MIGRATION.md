# KathaPe PostgreSQL Migration Guide

This guide explains how KathaPe has been migrated from Supabase to direct PostgreSQL connections.

## Overview of Changes

The application has been updated to use direct PostgreSQL connections instead of Supabase for the following reasons:

1. Direct database control and management
2. Simplified deployment with Render PostgreSQL service
3. Improved performance by eliminating API middleware
4. Reduced dependencies

## Key Files Changed

1. `flask_app.py`: Modified to use psycopg2 instead of Supabase client
2. `render.yaml`: Updated to include PostgreSQL database configuration
3. `db_init.py`: Added to handle database schema initialization
4. `wsgi.py`: Created to initialize database on startup
5. `requirements.txt`: Updated to remove Supabase dependency

## Database Connection

The application now uses a connection pool for optimal performance:

```python
# PostgreSQL connection pool
db_pool = ThreadedConnectionPool(
    minconn=1,
    maxconn=10,
    dsn=database_url,
    cursor_factory=psycopg2.extras.DictCursor
)
```

## Database Schema

The database schema is created automatically through the `db_init.py` script, which creates the following tables:

- `users`: User accounts (both business and customer users)
- `businesses`: Business profiles
- `customers`: Customer profiles
- `customer_credits`: Credit relationships between businesses and customers
- `transactions`: Credit and payment transactions
- `reminders`: Payment reminders

## Configuration

The database URL is configured through the `DATABASE_URL` environment variable:

```
# External connection URL (from outside Render):
DATABASE_URL=postgresql://kathape_user:IVClGfm9MjHpORJFRuI9JuCQ0efZn8Fc@dpg-d0nf3q1r0fns738vf3q0-a.singapore-postgres.render.com/kathape

# Internal connection URL (within Render's network):
DATABASE_URL=postgresql://kathape_user:IVClGfm9MjHpORJFRuI9JuCQ0efZn8Fc@dpg-d0nf3q1r0fns738vf3q0-a/kathape
```

In Render, this is automatically configured through the database service.

## Local Development Setup

To set up for local development:

1. Install PostgreSQL locally
2. Create a database for the application
3. Set the DATABASE_URL environment variable
4. Run the application

Example:
```bash
# Install PostgreSQL (macOS)
brew install postgresql

# Start PostgreSQL
brew services start postgresql

# Create database
createdb kathape

# Set environment variable - local database
export DATABASE_URL=postgres://postgres:postgres@localhost:5432/kathape
# OR use the Render database directly
export DATABASE_URL="postgresql://kathape_user:IVClGfm9MjHpORJFRuI9JuCQ0efZn8Fc@dpg-d0nf3q1r0fns738vf3q0-a.singapore-postgres.render.com/kathape"

# Initialize database
python db_init.py

# Run application
python flask_app.py
```

## Direct Database Access

For direct database access using psql:

```bash
# Connect to the Render database
PGPASSWORD=IVClGfm9MjHpORJFRuI9JuCQ0efZn8Fc psql -h dpg-d0nf3q1r0fns738vf3q0-a.singapore-postgres.render.com -U kathape_user kathape
```

## Deployment on Render

The `render.yaml` file is configured to automatically set up both the web service and PostgreSQL database:

```yaml
services:
  - type: web
    name: kathape
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn wsgi:app
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: kathape-db
          property: connectionString

databases:
  - name: kathape-db
    databaseName: kathape
    user: kathape_admin
```

## Database Initialization

On Render, the database is automatically initialized through the `wsgi.py` file which calls the `db_init.py` script:

```python
if os.environ.get('RENDER', '').lower() in ('1', 'true'):
    from db_init import initialize_database
    initialize_database()
```

This ensures that the database schema is created before the application starts. 