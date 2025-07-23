import os
import psycopg2
import psycopg2.extras

# Test database connection
DATABASE_URL = "postgresql://kathape_database_user:Ht2wROzJ5M2VfxVXvJ3iO4L45Q9GC2Wb@dpg-d20j432li9vc73a35od0-a.singapore-postgres.render.com/kathape_database"

try:
    print("Testing database connection...")
    conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
    
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
        # Test basic query
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
        tables = cursor.fetchall()
        
        print("✅ Database connection successful!")
        print("📋 Available tables:")
        for table in tables:
            print(f"   - {table['table_name']}")
        
        # Test table structure
        cursor.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='users' ORDER BY ordinal_position")
        columns = cursor.fetchall()
        
        print("\n👤 Users table structure:")
        for col in columns:
            print(f"   - {col['column_name']}: {col['data_type']}")
    
    conn.close()
    print("\n🎉 Database is ready for your KathaPe apps!")
    
except Exception as e:
    print(f"❌ Database connection failed: {str(e)}")
