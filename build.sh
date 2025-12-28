#!/usr/bin/env bash
# build.sh - Render build script for IntentLink Backend
# Exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Create logs directory if it doesn't exist
mkdir -p logs

# Collect static files
python manage.py collectstatic --no-input

# Run database migrations
python manage.py migrate
