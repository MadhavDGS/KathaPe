#!/usr/bin/env python
"""
Simple script to copy env_update to .env
"""

import os
import shutil

source_file = 'env_update'
target_file = '.env'

if not os.path.exists(source_file):
    print(f"ERROR: {source_file} does not exist")
    exit(1)

# Copy the file
shutil.copy2(source_file, target_file)
print(f"Successfully copied {source_file} to {target_file}")
print("Now restart your Flask application for the changes to take effect.") 