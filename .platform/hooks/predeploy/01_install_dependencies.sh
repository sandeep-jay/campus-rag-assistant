#!/bin/bash
set -e

# Install system dependencies
yum install -y python3-devel gcc nginx

# Set up Python environment
python3 -m venv /var/app/venv/
source /var/app/venv/bin/activate
pip install -r /var/app/staging/requirements.txt

# Set up directories and permissions
mkdir -p /var/log/app
chown -R webapp:webapp /var/app/staging /var/log/app