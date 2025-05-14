# Simple wsgi file to import the app instance from the main app.py file
import os
import sys

# Ensure the current directory is in the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the Flask app instance
import app as app_module
application = app_module.app

# For gunicorn
app = application

if __name__ == "__main__":
    app.run() 