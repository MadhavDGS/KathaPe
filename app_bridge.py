#!/usr/bin/env python3
"""
Bridge module that specifically handles the app/ directory vs app.py conflict
"""
import os
import sys
import inspect
import importlib.util
import time
import signal

print("Starting app_bridge.py...")

# Set up a timeout handler to prevent worker hangs during initialization
def timeout_handler(signum, frame):
    raise TimeoutError("Operation timed out")

# Try to import and apply DNS patches for Supabase connectivity
try:
    import patches
    patches.apply_patches()
    print("Applied DNS resolution patches for Supabase")
except ImportError:
    print("DNS patches module not found, continuing without DNS patches")
except Exception as e:
    print(f"Error applying DNS patches: {str(e)}")

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
        # Set a timeout for module loading to prevent worker hanging
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(10)  # 10 seconds timeout for loading
        
        # Create a module spec
        spec = importlib.util.spec_from_file_location("app_py_module", app_py_path)
        app_py_module = importlib.util.module_from_spec(spec)
        
        # Execute the module
        spec.loader.exec_module(app_py_module)
        print("Successfully loaded app.py as a module")
        
        # Reset the alarm
        signal.alarm(0)
        
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
            
            # Configure timeouts for the app
            try:
                if hasattr(app, 'config'):
                    app.config['TIMEOUT'] = 5
                    print("Set app timeout to 5 seconds")
            except Exception as config_error:
                print(f"Failed to configure timeouts: {str(config_error)}")
                
    except TimeoutError:
        print("Timeout while loading app.py - creating fallback app")
        from flask import Flask
        app = Flask(__name__)
        
        @app.route('/')
        def index():
            return "Timeout while loading app.py! This is a fallback app."
    except Exception as e:
        print(f"Error loading app.py: {str(e)}")
        # Create a fallback app
        from flask import Flask
        app = Flask(__name__)
        
        @app.route('/')
        def index():
            return f"Error loading app.py: {str(e)}"

# Configure the app's request handling
try:
    # Set gunicorn worker timeout
    if hasattr(app, 'config'):
        app.config['TIMEOUT'] = 25  # 25 seconds
        app.config['PREFERRED_URL_SCHEME'] = 'https'  # Ensure https for all URLs
except Exception as config_error:
    print(f"Failed to configure app: {str(config_error)}")

# This is what gunicorn will import
application = app 