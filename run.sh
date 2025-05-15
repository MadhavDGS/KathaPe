#!/bin/bash
# Simple script to launch the Flask app with gunicorn
echo "Starting Flask application..."
gunicorn wsgi:app --workers=1 --threads=2 --timeout=60 