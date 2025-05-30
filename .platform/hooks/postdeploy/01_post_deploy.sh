#!/bin/bash
set -e

# This hook runs AFTER the application is deployed but BEFORE the Procfile command is initiated.
# It should primarily be used for final configuration, data migration, or other
# tasks that need to happen once your application code is in place,
# but NOT for starting the long-running web processes (FastAPI, Streamlit).

# Activate virtual environment
source /var/app/venv/*/bin/activate

# Create log directory if it doesn't exist
sudo mkdir -p /var/log/app
sudo chown -R webapp:webapp /var/log/app

# Make run_services.sh executable
chmod +x /var/app/current/run_services.sh

# Our services are started by the Procfile command: 'web: ./run_services.sh'
# So, no need to start them here.

echo "Post-deployment hook finished. Main web services will be started by Procfile."