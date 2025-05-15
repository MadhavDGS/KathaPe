"""
WSGI entry point for the Flask application
This avoids the naming conflict between the module and the Flask instance
"""
import os
import sys
import traceback
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Enable detailed error logging
os.environ['FLASK_ENV'] = os.environ.get('FLASK_ENV', 'production')
os.environ['PYTHONUNBUFFERED'] = '1'  # Ensure logs are flushed immediately

try:
    print("Starting WSGI initialization...")
    logger.info("Starting WSGI initialization...")
    
    # Run preload to fix path issues
    try:
        import _preload
        logger.info("Preload module imported successfully")
    except ImportError:
        print("WARNING: _preload module not found, continuing without it")
        logger.warning("_preload module not found, continuing without it")
    except Exception as preload_error:
        print(f"ERROR importing _preload: {str(preload_error)}")
        logger.error(f"ERROR importing _preload: {str(preload_error)}")
        traceback.print_exc()
    
    # Ensure the current directory is in the path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    # Import the Flask app directly - use flask_app to avoid name conflict with app/ directory
    try:
        print("Importing Flask app...")
        logger.info("Importing Flask app...")
        from flask_app import app
        print("Flask app imported successfully")
        logger.info("Flask app imported successfully")
    except ImportError as import_error:
        error_msg = f"ERROR importing flask_app: {str(import_error)}"
        print(error_msg)
        logger.error(error_msg)
        traceback.print_exc()
        
        # Try to import app.py as fallback
        try:
            print("Trying to import app.py as fallback...")
            logger.info("Trying to import app.py as fallback...")
            from app import app
            print("Fallback app imported successfully")
            logger.info("Fallback app imported successfully")
        except ImportError as fallback_error:
            error_msg = f"ERROR importing fallback app: {str(fallback_error)}"
            print(error_msg)
            logger.error(error_msg)
            traceback.print_exc()
            
            # Create a simple error application as last resort
            from flask import Flask, make_response
            app = Flask(__name__)
            
            @app.route('/', defaults={'path': ''})
            @app.route('/<path:path>')
            def catch_all(path):
                error_html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Application Error</title>
                    <meta name="viewport" content="width=device-width, initial-scale=1">
                    <style>
                        body {{ font-family: Arial, sans-serif; text-align: center; padding: 20px; }}
                        h1 {{ color: #e74c3c; }}
                        .error-box {{ 
                            background-color: #f8d7da; 
                            border: 1px solid #f5c6cb; 
                            border-radius: 5px; 
                            padding: 20px; 
                            margin: 20px auto; 
                            max-width: 800px;
                            text-align: left;
                            overflow: auto;
                        }}
                    </style>
                </head>
                <body>
                    <h1>Application Error</h1>
                    <p>The application could not be started due to import errors.</p>
                    <div class="error-box">
                        <strong>Main import error:</strong><br>
                        {str(import_error)}
                        <hr>
                        <strong>Fallback import error:</strong><br>
                        {str(fallback_error)}
                    </div>
                </body>
                </html>
                """
                return make_response(error_html, 500)
    
    print("WSGI initialization completed successfully")
    logger.info("WSGI initialization completed successfully")
    
except Exception as e:
    print(f"CRITICAL ERROR in WSGI initialization: {str(e)}")
    logger.critical(f"CRITICAL ERROR in WSGI initialization: {str(e)}")
    traceback.print_exc()
    
    # Create a simple error application as last resort if we failed completely
    from flask import Flask, make_response
    app = Flask(__name__)
    
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def catch_all(path):
        error_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Critical Application Error</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; padding: 20px; }}
                h1 {{ color: #e74c3c; }}
                .error-box {{ 
                    background-color: #f8d7da; 
                    border: 1px solid #f5c6cb; 
                    border-radius: 5px; 
                    padding: 20px; 
                    margin: 20px auto; 
                    max-width: 800px;
                    text-align: left;
                    overflow: auto;
                }}
            </style>
        </head>
        <body>
            <h1>Critical Application Error</h1>
            <p>The application could not be started due to a critical error.</p>
            <div class="error-box">
                <strong>Error details:</strong><br>
                {str(e)}
                <hr>
                <pre>{traceback.format_exc()}</pre>
            </div>
        </body>
        </html>
        """
        return make_response(error_html, 500)

# This allows direct execution of this file
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000))) 