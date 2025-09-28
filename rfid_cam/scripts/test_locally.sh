#!/bin/bash

echo "Testing RFID Camera System locally..."

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "ERROR: .env file not found. Copy from .env.example and configure it first."
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "src/a04_dualcam_notify.py" ]; then
    echo "ERROR: Run this script from the rfid_cam directory"
    exit 1
fi

# Set PYTHONUNBUFFERED for immediate output
export PYTHONUNBUFFERED=1

echo "Starting application in foreground mode..."
echo "Press Ctrl+C to stop"
echo ""

# Run the application
python3 src/a04_dualcam_notify.py