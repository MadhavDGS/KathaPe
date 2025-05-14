#!/usr/bin/env python3
"""
Debug Flask application that helps diagnose deployment issues
"""
from flask import Flask, Response, render_template_string, redirect
import os
import sys
import inspect
import traceback
import json
import re

app = Flask(__name__)

@app.route('/')
def index():
    return render_template_string("""
    <html>
    <head>
        <title>KathaPe Debug App</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }
            h1 { color: #333; }
            .nav { margin: 20px 0; }
            .nav a { display: inline-block; margin-right: 15px; padding: 8px 15px; 
                     background: #0066cc; color: white; text-decoration: none; border-radius: 4px; }
            .nav a:hover { background: #0055b3; }
        </style>
    </head>
    <body>
        <h1>KathaPe Debug App</h1>
        <p>This is a diagnostic application to help troubleshoot deployment issues.</p>
        
        <div class="nav">
            <a href="/debug">View Debug Info</a>
            <a href="/app_contents">View app.py Contents</a>
            <a href="/create_bridge">Create Bridge Module</a>
            <a href="/deploy_fallback">Deploy Fallback</a>
        </div>
        
        <p>First, check the <a href="/debug">debug information</a> to understand the environment.</p>
        <p>Then, you can try to fix the issue using one of the other options.</p>
    </body>
    </html>
    """)

@app.route('/debug')
def debug():
    """Return debug info about the environment"""
    output = []

    def log(message):
        output.append(str(message))
    
    try:
        log("===== PYTHON PATHS =====")
        for p in sys.path:
            log(f"Path: {p}")

        log("\n===== CURRENT DIRECTORY =====")
        log(f"Current directory: {os.getcwd()}")

        log("\n===== DIRECTORY CONTENTS =====")
        for item in os.listdir('.'):
            if os.path.isdir(item):
                log(f"DIR: {item}/")
            else:
                log(f"FILE: {item}")

        log("\n===== CHECKING FOR app.py =====")
        if os.path.exists("app.py"):
            log("app.py exists!")
            with open("app.py", "r") as f:
                first_lines = [f.readline().strip() for _ in range(50)]  # Read first 50 lines
            log(f"First lines: {first_lines[:10]}")
            
            # Search for Flask creation
            flask_pattern = re.compile(r'app\s*=\s*Flask\(')
            found = False
            line_number = 0
            
            with open("app.py", "r") as f:
                for i, line in enumerate(f):
                    if flask_pattern.search(line):
                        found = True
                        line_number = i + 1
                        log(f"Found Flask creation at line {line_number}: {line.strip()}")
                        break
            
            if not found:
                log("Could not find Flask app creation in app.py")
        else:
            log("app.py does not exist!")

        log("\n===== CHECKING FOR app/ DIRECTORY =====")
        if os.path.exists("app") and os.path.isdir("app"):
            log("app/ directory exists!")
            log("Contents:")
            for item in os.listdir("app"):
                log(f"  - {item}")
            
            # Check for __init__.py
            if os.path.exists("app/__init__.py"):
                log("app/__init__.py exists!")
                with open("app/__init__.py", "r") as f:
                    first_line = f.readline().strip()
                log(f"First line: {first_line}")
        else:
            log("app/ directory does not exist!")

        log("\n===== ATTEMPTING IMPORT =====")
        try:
            import app as imported_app
            log("Successfully imported app")
            log(f"app.__file__: {imported_app.__file__}")
            
            # Try to access the Flask app instance
            if hasattr(imported_app, 'app'):
                log("app.app exists!")
                log(f"Type: {type(imported_app.app)}")
            else:
                log("app.app does not exist!")
                
                # Try to find Flask instances
                flask_objects = []
                for name, obj in inspect.getmembers(imported_app):
                    obj_type = str(type(obj))
                    if 'Flask' in obj_type:
                        flask_objects.append(f"Found Flask object: {name}, type: {obj_type}")
                
                if flask_objects:
                    for obj in flask_objects:
                        log(obj)
                else:
                    log("No Flask objects found in module")
        except Exception as e:
            log(f"Error importing app: {e}")
            log(traceback.format_exc())

        log("\n===== ENVIRONMENT VARIABLES =====")
        env_vars = {}
        for key, value in sorted(os.environ.items()):
            if key.startswith(('PYTHON', 'FLASK', 'GUNICORN', 'RENDER', 'PATH', 'PYTHONPATH')):
                env_vars[key] = value
        log(json.dumps(env_vars, indent=2))
        
    except Exception as e:
        log(f"Error in debug view: {str(e)}")
        log(traceback.format_exc())
    
    return Response('\n'.join(output), mimetype='text/plain')

@app.route('/app_contents')
def app_contents():
    """View the contents of app.py"""
    if not os.path.exists("app.py"):
        return "app.py does not exist"
    
    try:
        with open("app.py", "r") as f:
            content = f.read()
        
        # Highlight Flask instance creation
        content_html = content.replace("app = Flask", "<b style='background:yellow'>app = Flask</b>")
        
        return render_template_string("""
        <html>
        <head>
            <title>app.py Contents</title>
            <style>
                body { font-family: monospace; margin: 20px; }
                pre { background: #f4f4f4; padding: 15px; overflow: auto; max-height: 800px; }
                .back { display: inline-block; margin: 20px 0; padding: 8px 15px; 
                       background: #0066cc; color: white; text-decoration: none; border-radius: 4px; }
            </style>
        </head>
        <body>
            <a class="back" href="/">Back to Home</a>
            <h1>Contents of app.py</h1>
            <pre>{{ content|safe }}</pre>
        </body>
        </html>
        """, content=content_html)
    except Exception as e:
        return f"Error reading app.py: {str(e)}"

@app.route('/create_bridge')
def create_bridge():
    """Create a bridge.py file that correctly imports the app"""
    try:
        bridge_content = """#!/usr/bin/env python3
\"\"\"
Bridge module to find and export the Flask app instance from app.py
\"\"\"
import os
import sys
import re
import inspect

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# First try direct import
try:
    import app as app_module
    
    # Check if app.app exists
    if hasattr(app_module, 'app'):
        app = app_module.app
        print("Successfully imported app.app directly")
    else:
        # Look for Flask instances in the module
        app = None
        for name, obj in inspect.getmembers(app_module):
            if str(type(obj)).find('Flask') != -1:
                print(f"Found Flask instance: {name}")
                app = obj
                break
                
        if app is None:
            raise ImportError("Could not find Flask app instance in app module")
except Exception as e:
    print(f"Error importing from app.py: {e}")
    
    # Try extracting the app from app.py directly
    try:
        # Check if app.py exists
        if not os.path.exists('app.py'):
            raise FileNotFoundError("app.py not found")
            
        # Read app.py
        with open('app.py', 'r') as f:
            app_py_content = f.read()
            
        # Execute app.py content with a custom namespace
        namespace = {}
        exec(app_py_content, namespace)
        
        # Find Flask instances in the namespace
        app = None
        for name, obj in namespace.items():
            if str(type(obj)).find('Flask') != -1:
                print(f"Found Flask instance in eval namespace: {name}")
                app = obj
                break
                
        if app is None:
            raise ImportError("Could not find Flask app instance in app.py")
    except Exception as e2:
        print(f"Error extracting app from app.py: {e2}")
        
        # Create a fallback app
        from flask import Flask
        app = Flask(__name__)
        
        @app.route('/')
        def home():
            return "KathaPe Fallback App - Bridge module had to create a new app"

# This is the variable that gunicorn will import
application = app
"""
        
        with open("bridge.py", "w") as f:
            f.write(bridge_content)
            
        # Update Procfile
        with open("Procfile", "w") as f:
            f.write("web: gunicorn bridge:application")
            
        return render_template_string("""
        <html>
        <head>
            <title>Bridge Module Created</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }
                h1 { color: #333; }
                .success { background: #d4edda; border: 1px solid #c3e6cb; padding: 15px; border-radius: 4px; }
                .back { display: inline-block; margin: 20px 0; padding: 8px 15px; 
                       background: #0066cc; color: white; text-decoration: none; border-radius: 4px; }
                pre { background: #f4f4f4; padding: 10px; }
            </style>
        </head>
        <body>
            <a class="back" href="/">Back to Home</a>
            <h1>Bridge Module Created</h1>
            <div class="success">
                <p>Successfully created bridge.py and updated Procfile.</p>
                <p>Procfile now contains: <pre>web: gunicorn bridge:application</pre></p>
                <p>Commit and push these changes to deploy with the bridge module.</p>
            </div>
        </body>
        </html>
        """)
    except Exception as e:
        return f"Error creating bridge module: {str(e)}"

@app.route('/deploy_fallback')
def deploy_fallback():
    """Switch to use a simple fallback app"""
    try:
        # Update Procfile to use fallback.py
        with open("Procfile", "w") as f:
            f.write("web: gunicorn fallback:app")
            
        return render_template_string("""
        <html>
        <head>
            <title>Deployed Fallback App</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }
                h1 { color: #333; }
                .success { background: #d4edda; border: 1px solid #c3e6cb; padding: 15px; border-radius: 4px; }
                .back { display: inline-block; margin: 20px 0; padding: 8px 15px; 
                       background: #0066cc; color: white; text-decoration: none; border-radius: 4px; }
            </style>
        </head>
        <body>
            <a class="back" href="/">Back to Home</a>
            <h1>Deployed Fallback App</h1>
            <div class="success">
                <p>Successfully updated Procfile to use the fallback app.</p>
                <p>Commit and push these changes to deploy the fallback app.</p>
            </div>
        </body>
        </html>
        """)
    except Exception as e:
        return f"Error deploying fallback: {str(e)}"

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080))) 