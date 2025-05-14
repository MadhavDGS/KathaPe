#!/usr/bin/env python3
"""
Debug script that prints information about the directory structure and environment
"""
import os
import sys
import inspect

print("===== PYTHON PATHS =====")
for p in sys.path:
    print(f"Path: {p}")

print("\n===== CURRENT DIRECTORY =====")
print(f"Current directory: {os.getcwd()}")

print("\n===== DIRECTORY CONTENTS =====")
for item in os.listdir('.'):
    if os.path.isdir(item):
        print(f"DIR: {item}/")
    else:
        print(f"FILE: {item}")

print("\n===== CHECKING FOR app.py =====")
if os.path.exists("app.py"):
    print("app.py exists!")
    with open("app.py", "r") as f:
        first_line = f.readline().strip()
    print(f"First line: {first_line}")
else:
    print("app.py does not exist!")

print("\n===== CHECKING FOR app/ DIRECTORY =====")
if os.path.exists("app") and os.path.isdir("app"):
    print("app/ directory exists!")
    print("Contents:")
    for item in os.listdir("app"):
        print(f"  - {item}")
else:
    print("app/ directory does not exist!")

print("\n===== ATTEMPTING IMPORT =====")
try:
    import app
    print("Successfully imported app")
    print(f"app.__file__: {app.__file__}")
    
    # Try to access the Flask app instance
    if hasattr(app, 'app'):
        print("app.app exists!")
        print(f"Type: {type(app.app)}")
    else:
        print("app.app does not exist!")
        
        # Try to find Flask instances
        for name, obj in inspect.getmembers(app):
            if str(type(obj)).find('Flask') != -1:
                print(f"Found Flask object: {name}")
except Exception as e:
    print(f"Error importing app: {e}")

print("\n===== ENVIRONMENT VARIABLES =====")
for key, value in os.environ.items():
    if key.startswith(('PYTHON', 'FLASK', 'GUNICORN', 'PATH', 'PYTHONPATH')):
        print(f"{key}={value}")

if __name__ == "__main__":
    print("\nThis script can be run directly for local debugging") 