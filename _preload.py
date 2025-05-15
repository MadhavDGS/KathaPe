"""
Preload file to ensure correct module paths
This helps avoid naming conflicts between app.py and app/
"""
import os
import sys

# Modify the import path to prioritize the current directory
# This ensures flask_app.py is found before app/
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Remove the app directory from the path if it exists
app_dir = os.path.join(current_dir, 'app')
if app_dir in sys.path:
    sys.path.remove(app_dir)

print("Preload: Modified Python path to prioritize main directory") 