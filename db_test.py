import psycopg2
import sys
import traceback
import time

# Hardcoded database connection URLs
# Internal URL (for use within Render's network):
DATABASE_URL = 'postgresql://kathape_user:IVClGfm9MjHpORJFRuI9JuCQ0efZn8Fc@dpg-d0nf3q1r0fns738vf3q0-a/kathape'
# External URL (for use outside Render's network):
EXTERNAL_DATABASE_URL = 'postgresql://kathape_user:IVClGfm9MjHpORJFRuI9JuCQ0efZn8Fc@dpg-d0nf3q1r0fns738vf3q0-a.singapore-postgres.render.com/kathape'

def test_db_connection():
    """Test connection to the database"""
    print("Testing database connection...")
    
    # Try internal URL first
    print(f"Trying internal URL connection...")
    try:
        start_time = time.time()
        conn = psycopg2.connect(DATABASE_URL)
        
        with conn.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            
        print(f"✅ Connected successfully to internal URL in {time.time() - start_time:.2f}s")
        print(f"PostgreSQL version: {version}")
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Internal URL connection failed: {str(e)}")
    
    # Try external URL next
    print(f"\nTrying external URL connection...")
    try:
        start_time = time.time()
        conn = psycopg2.connect(EXTERNAL_DATABASE_URL)
        
        with conn.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            
        print(f"✅ Connected successfully to external URL in {time.time() - start_time:.2f}s")
        print(f"PostgreSQL version: {version}")
        conn.close()
        return True
    except Exception as e:
        print(f"❌ External URL connection failed: {str(e)}")
        traceback.print_exc()
        return False

def check_tables():
    """Check existing tables in the database"""
    try:
        # Use external URL as it's more likely to work outside Render
        conn = psycopg2.connect(EXTERNAL_DATABASE_URL)
        
        # Get list of tables
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)
            tables = cursor.fetchall()
        
        print(f"\nFound {len(tables)} tables in the database:")
        
        # Check count for each table with a new cursor each time
        for table in tables:
            with conn.cursor() as cursor:
                cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
                count = cursor.fetchone()[0]
                print(f"  - {table[0]}: {count} records")
            
        conn.close()
    except Exception as e:
        print(f"❌ Error checking tables: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    print("🔄 KathaPe Database Connection Test")
    print("===================================")
    
    if test_db_connection():
        print("\n✅ Database connection test passed!")
        check_tables()
        print("\nTest completed successfully.")
        sys.exit(0)
    else:
        print("\n❌ Database connection test failed!")
        print("\nPlease check your database credentials and network connectivity.")
        sys.exit(1) 