import sys

# Add your project directory to the Python path
path = '/home/YOUR_PYTHONANYWHERE_USERNAME/KathaPe'
if path not in sys.path:
    sys.path.append(path)

# Import the Flask application
from app import app as application 