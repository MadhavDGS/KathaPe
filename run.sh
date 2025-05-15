#!/bin/bash
# Simple script to launch the Flask app with gunicorn
echo "Starting Flask application..."
# Set PYTHONPATH to prioritize the main directory
export PYTHONPATH=$PWD:$PYTHONPATH
echo "PYTHONPATH set to: $PYTHONPATH"
gunicorn wsgi:app 