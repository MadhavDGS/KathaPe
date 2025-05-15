import os
import sys
import time

# Try importing Supabase to verify it's installed
try:
    from supabase import create_client, Client
    print("Supabase module is available")
except ImportError as e:
    print(f"ERROR: Supabase module not available: {str(e)}")
    sys.exit(1)

# Set environment variables
os.environ.setdefault('SUPABASE_URL', 'https://xhczvjwwmrvmcbwjxpxd.supabase.co')
os.environ.setdefault('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhoY3p2and3bXJ2bWNid2p4cHhkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MTM3MTQwNTgsImV4cCI6MjAyOTI5MDA1OH0.xnG-kIOiY4xbB3_QnTJtLXvwxU-fkW2RKlJw2WUoRE8')

def test_supabase_connection():
    """Test connection to Supabase"""
    try:
        print(f"Testing connection to Supabase...")
        
        # Get connection details
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')
        
        print(f"SUPABASE_URL: {supabase_url}")
        print(f"SUPABASE_KEY: {supabase_key[:10]}...")  # Only print part of the key for security
        
        # Try to create a client
        client = create_client(supabase_url, supabase_key)
        
        # Make a simple query to test connection
        start_time = time.time()
        print(f"Querying users table...")
        response = client.table('users').select('id').limit(1).execute()
        query_time = time.time() - start_time
        
        # Check response
        if response and response.data:
            print(f"✅ Connection successful! Query completed in {query_time:.2f} seconds")
            print(f"Found {len(response.data)} user records")
            return True
        else:
            print(f"⚠️ Connected but no data returned. Query completed in {query_time:.2f} seconds")
            return False
            
    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_supabase_connection()
    sys.exit(0 if success else 1) 