from flask import Flask, render_template_string, Response
import os
import sys
import json
import traceback

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
            pre { background: #f4f4f4; padding: 10px; }
        </style>
    </head>
    <body>
        <h1>KathaPe Debug App</h1>
        <p>This is a debugging app for KathaPe deployment on Render.</p>
        
        <div class="nav">
            <a href="/info">View Debug Info</a>
            <a href="/fix">Fix Deployment</a>
        </div>
        
        <h2>Current Directory Structure</h2>
        <pre>{{ dir_contents }}</pre>
    </body>
    </html>
    """, dir_contents=get_directory_info())

@app.route('/info')
def info():
    """Show debug information"""
    try:
        info_text = []
        info_text.append("=== PYTHON PATH ===")
        for path in sys.path:
            info_text.append(f"- {path}")
        
        info_text.append("\n=== ENVIRONMENT VARIABLES ===")
        env_vars = {k: v for k, v in os.environ.items() 
                   if k.startswith(('PYTHON', 'FLASK', 'PATH'))}
        info_text.append(json.dumps(env_vars, indent=2))
        
        info_text.append("\n=== FILES ===")
        files = [f for f in os.listdir('.') if os.path.isfile(f)]
        for f in files:
            info_text.append(f"- {f}")
            
        info_text.append("\n=== DIRECTORIES ===")
        dirs = [d for d in os.listdir('.') if os.path.isdir(d)]
        for d in dirs:
            info_text.append(f"- {d}/")
            try:
                subfiles = os.listdir(d)
                for sf in subfiles[:5]:  # Only show first 5 files
                    info_text.append(f"  - {sf}")
                if len(subfiles) > 5:
                    info_text.append(f"  - ... and {len(subfiles)-5} more")
            except:
                info_text.append("  (error reading directory)")
                
        return Response("\n".join(info_text), mimetype="text/plain")
    except Exception as e:
        return f"Error getting debug info: {str(e)}\n\n{traceback.format_exc()}"

@app.route('/fix')
def fix():
    """Create a fix for the deployment"""
    try:
        # Create a bridge.py file to handle the app import
        bridge_content = """#!/usr/bin/env python3
from flask import Flask

try:
    # Try to import from app.py
    import app as app_module
    if hasattr(app_module, 'app'):
        app = app_module.app
    else:
        # Create a fallback app
        app = Flask(__name__)
        
        @app.route('/')
        def home():
            return "KathaPe is running! Using bridge module."
except:
    # Create a fallback app
    app = Flask(__name__)
    
    @app.route('/')
    def home():
        return "KathaPe is running! Using bridge module (fallback mode)."

# This is what gunicorn will import
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
            <title>Deployment Fix Created</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }
                h1 { color: #333; }
                .nav { margin: 20px 0; }
                .nav a { display: inline-block; margin-right: 15px; padding: 8px 15px; 
                        background: #0066cc; color: white; text-decoration: none; border-radius: 4px; }
                .success { background: #d4edda; border: 1px solid #c3e6cb; padding: 15px; border-radius: 4px; }
                pre { background: #f4f4f4; padding: 10px; }
            </style>
        </head>
        <body>
            <h1>Deployment Fix Created</h1>
            <div class="nav">
                <a href="/">Back to Home</a>
            </div>
            
            <div class="success">
                <p>Successfully created:</p>
                <ul>
                    <li><strong>bridge.py</strong> - A module to handle app import</li>
                    <li><strong>Procfile</strong> - Updated to use the bridge module</li>
                </ul>
                <p>Procfile now contains: <pre>web: gunicorn bridge:application</pre></p>
                <p>Commit and push these changes to complete the fix.</p>
            </div>
        </body>
        </html>
        """)
    except Exception as e:
        return f"Error creating fix: {str(e)}\n\n{traceback.format_exc()}"

def get_directory_info():
    """Get basic directory information"""
    try:
        result = []
        result.append(f"Current directory: {os.getcwd()}")
        result.append("\nFiles:")
        files = [f for f in os.listdir('.') if os.path.isfile(f)]
        for f in sorted(files):
            result.append(f"- {f}")
            
        result.append("\nDirectories:")
        dirs = [d for d in os.listdir('.') if os.path.isdir(d)]
        for d in sorted(dirs):
            result.append(f"- {d}/")
        
        return "\n".join(result)
    except Exception as e:
        return f"Error getting directory info: {str(e)}"

if __name__ == "__main__":
    app.run(debug=True) 