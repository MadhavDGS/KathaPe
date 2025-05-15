#!/bin/bash
# Simple script to launch the Flask app with gunicorn
echo "Starting Flask application..."
gunicorn wsgi:app 