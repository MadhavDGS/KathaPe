"""
Main launcher script for KathaPe applications
Can run both business and customer apps simultaneously or separately
"""
import os
import sys
import threading
import subprocess
from multiprocessing import Process
import time

# Add paths for the separated apps
sys.path.append(os.path.join(os.path.dirname(__file__), 'business_app'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'customer_app'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'shared'))

def run_business_app():
    """Run the business Flask application"""
    try:
        print("Starting Business Flask App on port 5001...")
        os.environ['BUSINESS_PORT'] = '5001'
        
        # Change to business app directory and run
        os.chdir(os.path.join(os.path.dirname(__file__), 'business_app'))
        from app import business_app
        business_app.run(debug=False, host='0.0.0.0', port=5001, threaded=True)
    except Exception as e:
        print(f"Error running business app: {str(e)}")

def run_customer_app():
    """Run the customer Flask application"""
    try:
        print("Starting Customer Flask App on port 5002...")
        os.environ['CUSTOMER_PORT'] = '5002'
        
        # Change to customer app directory and run
        os.chdir(os.path.join(os.path.dirname(__file__), 'customer_app'))
        from app import customer_app
        customer_app.run(debug=False, host='0.0.0.0', port=5002, threaded=True)
    except Exception as e:
        print(f"Error running customer app: {str(e)}")

def run_both_apps():
    """Run both applications in separate processes"""
    print("Starting KathaPe Applications...")
    print("Business app will be available at: http://localhost:5001")
    print("Customer app will be available at: http://localhost:5002")
    print("Press Ctrl+C to stop both applications")
    
    # Create processes for both apps
    business_process = Process(target=run_business_app)
    customer_process = Process(target=run_customer_app)
    
    try:
        # Start both processes
        business_process.start()
        time.sleep(2)  # Give business app time to start
        customer_process.start()
        
        # Wait for both processes
        business_process.join()
        customer_process.join()
        
    except KeyboardInterrupt:
        print("\nShutting down applications...")
        business_process.terminate()
        customer_process.terminate()
        business_process.join()
        customer_process.join()
        print("Applications stopped.")

def main():
    """Main function to handle command line arguments"""
    if len(sys.argv) > 1:
        app_type = sys.argv[1].lower()
        
        if app_type == 'business':
            print("Running Business App only...")
            run_business_app()
        elif app_type == 'customer':
            print("Running Customer App only...")
            run_customer_app()
        elif app_type == 'both' or app_type == 'all':
            run_both_apps()
        else:
            print("Usage:")
            print("  python main.py business    - Run business app only")
            print("  python main.py customer    - Run customer app only") 
            print("  python main.py both        - Run both apps")
            print("  python main.py             - Run both apps (default)")
    else:
        # Default: run both apps
        run_both_apps()

if __name__ == '__main__':
    main()
