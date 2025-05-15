"""
WSGI entry point for the Flask application
This avoids the naming conflict between the module and the Flask instance
"""
import os
import sys

# Ensure the current directory is in the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the Flask app instance
import app as app_module
application = app_module.app

# For gunicorn
app = application

# This allows direct execution of this file
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000))) 