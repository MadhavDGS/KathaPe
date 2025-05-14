#!/usr/bin/env python3
"""
Bridge module that specifically handles the app/ directory vs app.py conflict
"""
import os
import sys
import inspect
import importlib.util

print("Starting app_bridge.py...")

# The app.py file (not the app directory)
app_py_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.py')
print(f"Looking for app.py at: {app_py_path}")

if not os.path.exists(app_py_path):
    print(f"ERROR: {app_py_path} does not exist")
    from flask import Flask
    app = Flask(__name__)
    
    @app.route('/')
    def index():
        return "Error: app.py not found! This is a fallback app."
else:
    print(f"Found app.py at: {app_py_path}")
    
    # Load the app.py file directly using spec
    try:
        # Create a module spec
        spec = importlib.util.spec_from_file_location("app_py_module", app_py_path)
        app_py_module = importlib.util.module_from_spec(spec)
        
        # Execute the module
        spec.loader.exec_module(app_py_module)
        print("Successfully loaded app.py as a module")
        
        # Check for Flask app instance
        app = None
        for name, obj in inspect.getmembers(app_py_module):
            if str(type(obj)).find('Flask') != -1:
                print(f"Found Flask app instance: {name}")
                app = obj
                break
        
        if app is None:
            print("No Flask app instance found in app.py")
            # Create a fallback app
            from flask import Flask
            app = Flask(__name__)
            
            @app.route('/')
            def index():
                return "Error: No Flask app found in app.py! This is a fallback app."
        else:
            print(f"Successfully found app instance in app.py")
    except Exception as e:
        print(f"Error loading app.py: {str(e)}")
        # Create a fallback app
        from flask import Flask
        app = Flask(__name__)
        
        @app.route('/')
        def index():
            return f"Error loading app.py: {str(e)}"

# This is what gunicorn will import
application = app 