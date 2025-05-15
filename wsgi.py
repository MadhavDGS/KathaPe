"""
WSGI entry point for the Flask application
This avoids the naming conflict between the module and the Flask instance
"""
import os
import sys

# Run preload to fix path issues
import _preload

# Ensure the current directory is in the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the Flask app directly - use flask_app to avoid name conflict with app/ directory
from flask_app import app

# For gunicorn
application = app

# This allows direct execution of this file
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000))) 