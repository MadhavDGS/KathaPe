#!/bin/bash
# Script to update the KathaPe deployment

echo "Checking syntax of key files..."
python check_deployment.py

if [ $? -ne 0 ]; then
    echo "❌ Syntax check failed. Please fix the errors before deploying."
    exit 1
fi

echo -e "\n🔄 Committing and pushing changes..."

# Add the files
git add flask_app.py wsgi.py check_deployment.py DEPLOYMENT.md update.sh

# Commit
git commit -m "Fix syntax error in flask_app.py and improve error handling"

# Push
echo "Pushing to repository..."
git push

echo -e "\n✅ Update complete! Your changes should now be deployed to Render."
echo "Check the deployment status at: https://dashboard.render.com"
echo ""
echo "Remember to set these environment variables on Render:"
echo "- RENDER_EMERGENCY_LOGIN=true"
echo "- FLASK_ENV=production"
echo ""
echo "Also consider updating the worker timeout in render.yaml to 240 seconds." 