import os
import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv
import logging
import time

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Hardcoded database connection URLs
# Internal URL (for use within Render's network):
DATABASE_URL = 'postgresql://kathape_user:IVClGfm9MjHpORJFRuI9JuCQ0efZn8Fc@dpg-d0nf3q1r0fns738vf3q0-a/kathape'
# External URL (for use outside Render's network):
EXTERNAL_DATABASE_URL = 'postgresql://kathape_user:IVClGfm9MjHpORJFRuI9JuCQ0efZn8Fc@dpg-d0nf3q1r0fns738vf3q0-a.singapore-postgres.render.com/kathape'

def connect_to_postgres():
    """Connect to PostgreSQL server"""
    try:
        # Try internal URL first
        database_url = os.environ.get('DATABASE_URL', DATABASE_URL)
        
        logger.info(f"Connecting to PostgreSQL database...")
        try:
            conn = psycopg2.connect(database_url)
        except psycopg2.OperationalError:
            # If internal connection fails, try external URL
            logger.info("Internal database connection failed, trying external URL...")
            conn = psycopg2.connect(EXTERNAL_DATABASE_URL)
            
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        logger.info("Connected to PostgreSQL database")
        return conn
    except Exception as e:
        logger.error(f"Error connecting to PostgreSQL: {str(e)}")
        raise

def initialize_database():
    """Initialize the database with required tables"""
    conn = None
    try:
        # Connect to database
        conn = connect_to_postgres()
        cursor = conn.cursor()
        
        # Create users table
        logger.info("Creating users table...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            phone_number VARCHAR(20) UNIQUE NOT NULL,
            email VARCHAR(255),
            user_type VARCHAR(20) NOT NULL,
            password VARCHAR(255) NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
        """)
        
        # Create businesses table
        logger.info("Creating businesses table...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS businesses (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id),
            name VARCHAR(255) NOT NULL,
            description TEXT,
            address TEXT,
            phone VARCHAR(20),
            email VARCHAR(255),
            access_pin VARCHAR(10),
            profile_photo_url TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
        """)
        
        # Create customers table
        logger.info("Creating customers table...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id),
            name VARCHAR(255) NOT NULL,
            phone_number VARCHAR(20) NOT NULL,
            whatsapp_number VARCHAR(20),
            email VARCHAR(255),
            address TEXT,
            notes TEXT,
            profile_photo_url TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
        """)
        
        # Create customer_credits table
        logger.info("Creating customer_credits table...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS customer_credits (
            id UUID PRIMARY KEY,
            business_id UUID NOT NULL REFERENCES businesses(id),
            customer_id UUID NOT NULL REFERENCES customers(id),
            current_balance DECIMAL(12,2) NOT NULL DEFAULT 0,
            last_reminder_date TIMESTAMP,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
            UNIQUE(business_id, customer_id)
        );
        """)
        
        # Create transactions table
        logger.info("Creating transactions table...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id UUID PRIMARY KEY,
            business_id UUID NOT NULL REFERENCES businesses(id),
            customer_id UUID NOT NULL REFERENCES customers(id),
            amount DECIMAL(12,2) NOT NULL,
            transaction_type VARCHAR(20) NOT NULL,
            notes TEXT,
            media_url TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            created_by UUID NOT NULL REFERENCES users(id)
        );
        """)
        
        # Create reminders table
        logger.info("Creating reminders table...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id UUID PRIMARY KEY,
            business_id UUID NOT NULL REFERENCES businesses(id),
            customer_id UUID NOT NULL REFERENCES customers(id),
            sent_at TIMESTAMP NOT NULL DEFAULT NOW(),
            sent_by UUID NOT NULL REFERENCES users(id),
            reminder_type VARCHAR(20) NOT NULL,
            message TEXT,
            status VARCHAR(20) DEFAULT 'sent'
        );
        """)
        
        # Create indexes for performance
        logger.info("Creating indexes...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone_number);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_businesses_user ON businesses(user_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_customers_user ON customers(user_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_credits_business ON customer_credits(business_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_credits_customer ON customer_credits(customer_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_business ON transactions(business_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_customer ON transactions(customer_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON transactions(created_at);")
        
        # Create triggers to update balances on transactions
        logger.info("Creating triggers...")
        cursor.execute("""
        CREATE OR REPLACE FUNCTION update_credit_balance() RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.transaction_type = 'credit' THEN
                UPDATE customer_credits
                SET current_balance = current_balance + NEW.amount,
                    updated_at = NOW()
                WHERE business_id = NEW.business_id AND customer_id = NEW.customer_id;
            ELSIF NEW.transaction_type = 'payment' THEN
                UPDATE customer_credits
                SET current_balance = current_balance - NEW.amount,
                    updated_at = NOW()
                WHERE business_id = NEW.business_id AND customer_id = NEW.customer_id;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """)
        
        cursor.execute("""
        DROP TRIGGER IF EXISTS trg_update_balance ON transactions;
        """)
        
        cursor.execute("""
        CREATE TRIGGER trg_update_balance
        AFTER INSERT ON transactions
        FOR EACH ROW
        EXECUTE FUNCTION update_credit_balance();
        """)
        
        # Add a trigger to create profiles when users are created
        cursor.execute("""
        CREATE OR REPLACE FUNCTION create_user_profile() RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.user_type = 'business' THEN
                INSERT INTO businesses (id, user_id, name, description, access_pin, created_at)
                VALUES (gen_random_uuid(), NEW.id, NEW.name || '''s Business', 'Auto-created business', 
                        LPAD(FLOOR(RANDOM() * 10000)::TEXT, 4, '0'), NOW());
            ELSIF NEW.user_type = 'customer' THEN
                INSERT INTO customers (id, user_id, name, phone_number, created_at)
                VALUES (gen_random_uuid(), NEW.id, NEW.name, NEW.phone_number, NOW());
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """)
        
        cursor.execute("""
        DROP TRIGGER IF EXISTS trg_create_profile ON users;
        """)
        
        cursor.execute("""
        CREATE TRIGGER trg_create_profile
        AFTER INSERT ON users
        FOR EACH ROW
        EXECUTE FUNCTION create_user_profile();
        """)
        
        # Add sample data if table is empty
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        
        if user_count == 0:
            logger.info("Adding sample data...")
            # Add sample admin user
            cursor.execute("""
            INSERT INTO users (id, name, phone_number, user_type, password, created_at)
            VALUES ('00000000-0000-0000-0000-000000000001', 'Admin User', '1234567890', 'business', 'admin123', NOW());
            """)
            
            # Business will be created by trigger
            cursor.execute("SELECT id FROM businesses WHERE user_id = '00000000-0000-0000-0000-000000000001'")
            business_id = cursor.fetchone()[0]
            
            # Add a sample customer
            cursor.execute("""
            INSERT INTO users (id, name, phone_number, user_type, password, created_at)
            VALUES ('00000000-0000-0000-0000-000000000002', 'Sample Customer', '0987654321', 'customer', 'customer123', NOW());
            """)
            
            # Customer will be created by trigger
            cursor.execute("SELECT id FROM customers WHERE user_id = '00000000-0000-0000-0000-000000000002'")
            customer_id = cursor.fetchone()[0]
            
            # Create credit relationship
            cursor.execute("""
            INSERT INTO customer_credits (id, business_id, customer_id, current_balance, created_at, updated_at)
            VALUES (gen_random_uuid(), %s, %s, 0, NOW(), NOW());
            """, (business_id, customer_id))
            
            # Add a sample transaction
            cursor.execute("""
            INSERT INTO transactions (id, business_id, customer_id, amount, transaction_type, notes, created_at, created_by)
            VALUES (gen_random_uuid(), %s, %s, 100.00, 'credit', 'Initial credit', NOW(), '00000000-0000-0000-0000-000000000001');
            """, (business_id, customer_id))
        
        logger.info("Database initialization completed successfully!")
        
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    try:
        logger.info("Starting database initialization...")
        initialize_database()
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
    finally:
        logger.info("Database initialization process completed.") 