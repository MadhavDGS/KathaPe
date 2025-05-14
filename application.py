#!/usr/bin/env python3
"""
Simple application module that imports the Flask app
"""

# Import directly from app.py
from app import app as application

# For gunicorn
app = application

if __name__ == "__main__":
    app.run() 