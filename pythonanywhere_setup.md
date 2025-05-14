# Deploying KathaPe to PythonAnywhere

This guide will walk you through deploying your KathaPe Flask application to PythonAnywhere.

## Step 1: Create a PythonAnywhere Account

1. Go to [PythonAnywhere.com](https://www.pythonanywhere.com) and sign up for an account
2. The free tier is sufficient for testing, but you may need a paid plan for production use

## Step 2: Upload Your Code

### Option 1: Using Git

1. Log in to your PythonAnywhere dashboard
2. Open a Bash console from the Dashboard
3. Clone your repository:
   ```bash
   git clone https://github.com/yourusername/KathaPe.git
   ```

### Option 2: Manual Upload

1. Create a zip archive of your project
2. In your PythonAnywhere dashboard, go to the "Files" tab
3. Upload the zip file
4. Open a Bash console and unzip it:
   ```bash
   unzip KathaPe.zip -d KathaPe
   ```

## Step 3: Set Up a Virtual Environment

1. Open a Bash console
2. Navigate to your project directory:
   ```bash
   cd KathaPe
   ```
3. Create a virtual environment:
   ```bash
   python -m venv venv
   ```
4. Activate the virtual environment:
   ```bash
   source venv/bin/activate
   ```
5. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Step 4: Configure the Web App

1. Go to the "Web" tab in your PythonAnywhere dashboard
2. Click "Add a new web app"
3. Choose "Manual configuration"
4. Select the Python version (Python 3.10 recommended)
5. Enter the path to your project (e.g., `/home/yourusername/KathaPe`)

## Step 5: Set Up the WSGI File

1. In the Web tab, scroll down to the "Code" section
2. Click on the WSGI configuration file link (e.g., `/var/www/yourusername_pythonanywhere_com_wsgi.py`)
3. Replace the contents with:

```python
import sys

# Add your project directory to the Python path
path = '/home/yourusername/KathaPe'
if path not in sys.path:
    sys.path.append(path)

# Import the Flask application
from app import app as application
```

4. Save the file

## Step 6: Configure Static Files

1. In the Web tab, scroll down to "Static files"
2. Add these mappings:
   - URL: `/static/` → Directory: `/home/yourusername/KathaPe/static/`
   - URL: `/static/uploads/` → Directory: `/home/yourusername/KathaPe/static/uploads/`
   - URL: `/static/qr_codes/` → Directory: `/home/yourusername/KathaPe/static/qr_codes/`

## Step 7: Set Environment Variables

1. In the Web tab, scroll down to "Environment variables"
2. Add the following variables:
   - `SUPABASE_URL`: Your Supabase URL
   - `SUPABASE_KEY`: Your Supabase key
   - `SUPABASE_SERVICE_KEY`: Your Supabase service key
   - `SECRET_KEY`: A random string for Flask session security
   - `UPLOAD_FOLDER`: `/home/yourusername/KathaPe/static/uploads`

## Step 8: Create Required Directories

1. Open a Bash console
2. Create required directories:
   ```bash
   mkdir -p ~/KathaPe/static/uploads
   mkdir -p ~/KathaPe/static/qr_codes
   mkdir -p ~/KathaPe/static/images
   ```

## Step 9: Restart Your Web App

1. In the Web tab, click the "Reload" button for your web app
2. Check the error log if there are any issues

## Troubleshooting

### Common Issues:

1. **ModuleNotFoundError**: Check if all dependencies are installed in your virtual environment
   ```bash
   source ~/KathaPe/venv/bin/activate
   pip install -r ~/KathaPe/requirements.txt
   ```

2. **Permission Errors**: Ensure directories have proper permissions
   ```bash
   chmod -R 755 ~/KathaPe/static
   ```

3. **Supabase Connection Issues**: PythonAnywhere free tier has outbound network restrictions. Consider:
   - Using a paid PythonAnywhere account
   - Relying on the mock data system for demonstration

4. **Worker Timeout**: Use the fallback mechanisms and proper timeout handling implemented in the app

### Checking Logs:

1. In the Web tab, click on the "Error log" link
2. Review any error messages

## Final Notes

- The app is designed to work with or without Supabase connectivity
- If Supabase connection fails, it will automatically fall back to the mock data system
- Test the application thoroughly after deployment
- Update the domain settings in the Web tab if you have a custom domain 