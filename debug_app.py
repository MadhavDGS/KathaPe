#!/usr/bin/env python3
"""
Debug Flask application that helps diagnose deployment issues
"""
from flask import Flask, Response
import os
import sys
import inspect
import traceback
import json

app = Flask(__name__)

@app.route('/')
def index():
    return "KathaPe Debug App - Use /debug to see server information"

@app.route('/debug')
def debug():
    """Return debug info about the environment"""
    output = []

    def log(message):
        output.append(message)
    
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
                first_line = f.readline().strip()
            log(f"First line: {first_line}")
        else:
            log("app.py does not exist!")

        log("\n===== CHECKING FOR app/ DIRECTORY =====")
        if os.path.exists("app") and os.path.isdir("app"):
            log("app/ directory exists!")
            log("Contents:")
            for item in os.listdir("app"):
                log(f"  - {item}")
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
                for name, obj in inspect.getmembers(imported_app):
                    if str(type(obj)).find('Flask') != -1:
                        log(f"Found Flask object: {name}")
        except Exception as e:
            log(f"Error importing app: {e}")
            log(traceback.format_exc())

        log("\n===== ENVIRONMENT VARIABLES =====")
        env_vars = {}
        for key, value in os.environ.items():
            if key.startswith(('PYTHON', 'FLASK', 'GUNICORN', 'RENDER', 'PATH', 'PYTHONPATH')):
                env_vars[key] = value
        log(json.dumps(env_vars, indent=2))
        
    except Exception as e:
        log(f"Error in debug view: {str(e)}")
        log(traceback.format_exc())
    
    return Response('\n'.join(output), mimetype='text/plain')

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080))) 