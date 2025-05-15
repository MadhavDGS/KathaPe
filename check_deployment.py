#!/usr/bin/env python
"""
Deployment check script for KathaPe
This script performs basic validation to ensure the app is ready for deployment
"""
import os
import sys
import traceback

def check_syntax(filename):
    """Check if the Python file has valid syntax"""
    print(f"Checking syntax of {filename}...")
    
    try:
        with open(filename, 'r') as f:
            compile(f.read(), filename, 'exec')
        print(f"✅ {filename} syntax is valid")
        return True
    except SyntaxError as e:
        line_num = e.lineno
        print(f"❌ Syntax error in {filename} at line {line_num}: {e}")
        
        # Show the problematic line and surrounding context
        try:
            with open(filename, 'r') as f:
                lines = f.readlines()
                
            start = max(0, line_num - 3)
            end = min(len(lines), line_num + 2)
            
            print("\nContext:")
            for i in range(start, end):
                line_marker = "→ " if i + 1 == line_num else "  "
                print(f"{line_marker}{i+1}: {lines[i].rstrip()}")
                
        except Exception as context_err:
            print(f"Could not show context: {context_err}")
            
        return False

def main():
    """Run all deployment checks"""
    print("🔍 Starting KathaPe deployment checks...")
    
    # List of critical files to check
    critical_files = ['flask_app.py', 'wsgi.py']
    
    all_valid = True
    for file in critical_files:
        if not check_syntax(file):
            all_valid = False
    
    if all_valid:
        print("\n✅ All critical files passed syntax check!")
        print("The application should now work on Render.")
        print("\nDeployment recommendations:")
        print("1. Set RENDER_EMERGENCY_LOGIN=true in environment variables for guaranteed login")
        print("2. Increase the worker timeout to at least 240 seconds in render.yaml")
        print("3. Reduce the number of workers to 2 to prevent resource exhaustion")
        return 0
    else:
        print("\n❌ Syntax errors found. Fix before deploying!")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 