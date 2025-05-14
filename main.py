#!/usr/bin/env python3
"""
Main entry point for the KathaPe application
"""
import os
import sys

# Make sure we can find modules in the current directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import directly - the variable 'app' is defined in app.py
import app
application = app.app

# For gunicorn
app = application

if __name__ == "__main__":
    app.run() 