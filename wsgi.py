"""
WSGI entry point for the Flask application
This avoids the naming conflict between the module and the Flask instance
"""
import os
import sys
import traceback

# Enable detailed error logging
os.environ['FLASK_ENV'] = os.environ.get('FLASK_ENV', 'production')
os.environ['PYTHONUNBUFFERED'] = '1'  # Ensure logs are flushed immediately

try:
    print("Starting WSGI initialization...")
    
    # Run preload to fix path issues
    import _preload
    
    # Ensure the current directory is in the path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    # Import the Flask app directly - use flask_app to avoid name conflict with app/ directory
    try:
        print("Importing Flask app...")
        from flask_app import app
        print("Flask app imported successfully")
    except Exception as flask_error:
        print(f"ERROR importing flask_app: {str(flask_error)}")
        traceback.print_exc()
        raise
    
    # For gunicorn
    application = app
    
    print("WSGI initialization completed successfully")

except Exception as e:
    print(f"CRITICAL ERROR in WSGI initialization: {str(e)}")
    traceback.print_exc()
    
    def application(environ, start_response):
        """Fallback application that returns an error message"""
        status = '500 Internal Server Error'
        headers = [('Content-type', 'text/html')]
        
        error_message = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Server Error</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; text-align: center; }}
                h1 {{ color: #d9534f; }}
                .error {{ background-color: #f2dede; border: 1px solid #ebccd1; color: #a94442; padding: 15px; 
                          margin: 20px 0; border-radius: 4px; text-align: left; }}
            </style>
        </head>
        <body>
            <h1>Application Error</h1>
            <p>The application could not start due to an error during initialization.</p>
            <div class="error">
                <strong>Error:</strong> {str(e)}
            </div>
            <p>Please check the server logs for more details.</p>
        </body>
        </html>
        """
        
        start_response(status, headers)
        return [error_message.encode('utf-8')]

# This allows direct execution of this file
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000))) 