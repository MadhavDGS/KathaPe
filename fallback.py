#!/usr/bin/env python3
"""
Standalone Flask application for Render deployment
"""
from flask import Flask, render_template

# Create the Flask application
app = Flask(__name__)

@app.route('/')
def home():
    return "KathaPe is running! This is a fallback application."

@app.route('/health')
def health():
    return "OK"

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080) 