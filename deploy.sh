#!/bin/bash
cd "$(dirname "$0")"

if ! command -v pm2 &> /dev/null
then
    echo "PM2 could not be found. Please install it using: npm install -g pm2"
    exit 1
fi

echo "Starting AIGC Automation API..."
# Run the FastAPI server via uvicorn in the activated virtual environment
pm2 start venv/bin/uvicorn --name "aigc-api" -- src.main:app --host 0.0.0.0 --port 8000

echo "Service started in background."
pm2 status
