#!/usr/bin/env python3
"""
Minimal bridge module optimized for low-resource environments
"""
import os
import importlib.util
import time
print("Starting lightweight app_bridge.py...")

# The app.py file (not the app directory)
app_py_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.py')
print(f"Loading app.py from: {app_py_path}")

# First try to get the app directly from a pre-existing loaded module
try:
    from app import app
    application = app
    print("Loaded app from pre-imported module")
except Exception as e:
    print(f"Direct import failed: {str(e)}")
    
    # Load the app.py file manually as fallback
    try:
        # Create a module spec
        spec = importlib.util.spec_from_file_location("app_py_module", app_py_path)
        app_py_module = importlib.util.module_from_spec(spec)
        
        # Execute the module
        spec.loader.exec_module(app_py_module)
        print("Loaded app.py as a module")
        
        # Get the app instance
        app = app_py_module.app
        application = app
        print("Successfully found app instance")
    except Exception as e:
        print(f"Error loading app.py: {str(e)}")
        # Create a fallback app
        from flask import Flask
        app = Flask(__name__)
        application = app
        
        @app.route('/')
        def index():
            return "Error loading app - using minimal fallback"

print("App bridge initialization complete") 