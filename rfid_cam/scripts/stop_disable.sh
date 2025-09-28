#!/bin/bash

echo "Stopping and disabling RFID Camera System service..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run with sudo: sudo ./scripts/stop_disable.sh"
    exit 1
fi

# Stop the service
echo "Stopping rfid_cam service..."
systemctl stop rfid_cam || true

# Disable the service
echo "Disabling rfid_cam service..."
systemctl disable rfid_cam || true

# Show status
echo "Service status:"
systemctl status rfid_cam --no-pager || true

echo ""
echo "Service stopped and disabled."
echo ""
echo "To completely remove:"
echo "1. Remove service file: sudo rm /etc/systemd/system/rfid_cam.service"
echo "2. Remove logrotate config: sudo rm /etc/logrotate.d/rfid_cam"
echo "3. Reload systemd: sudo systemctl daemon-reload"