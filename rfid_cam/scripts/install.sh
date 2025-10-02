#!/bin/bash
set -e

echo "Installing RFID Camera System..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run with sudo: sudo ./scripts/install.sh"
    exit 1
fi

# Get the actual user who called sudo
REAL_USER=${SUDO_USER:-$USER}
REAL_HOME=$(getent passwd "$REAL_USER" | cut -d: -f6)

echo "Installing for user: $REAL_USER"
echo "User home directory: $REAL_HOME"

# Update package lists
echo "Updating package lists..."
apt update

# Install system dependencies
echo "Installing system dependencies..."
apt install -y \
    python3-picamera2 \
    libcamera-apps \
    rclone \
    python3-pip \
    python3-venv \
    logrotate \
    minicom

# Install Python dependencies
echo "Installing Python dependencies..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RFID_CAM_DIR="$(dirname "$SCRIPT_DIR")"
cd "$RFID_CAM_DIR"
echo "Working directory: $(pwd)"
pip install --break-system-packages -r requirements.txt

# Create log file with proper permissions
echo "Setting up log file..."
touch /var/log/rfid_cam.log
chown $REAL_USER:$REAL_USER /var/log/rfid_cam.log
chmod 640 /var/log/rfid_cam.log

# Create photo directory if it doesn't exist
echo "Creating photo directory..."
PHOTO_DIR="${REAL_HOME}/rfid_photos"
mkdir -p "$PHOTO_DIR"
chown $REAL_USER:$REAL_USER "$PHOTO_DIR"

# Add user to dialout group for serial access
echo "Adding user to dialout group..."
usermod -a -G dialout $REAL_USER

# Install systemd service
echo "Installing systemd service..."
cp systemd/rfid_cam.service /etc/systemd/system/
systemctl daemon-reload

# Install logrotate configuration
echo "Installing logrotate configuration..."
cp logrotate/rfid_cam /etc/logrotate.d/

# Make scripts executable
echo "Making scripts executable..."
chmod +x scripts/*.sh

# Enable camera interface if not already enabled
echo "Checking camera interface..."
if ! grep -q "^camera_auto_detect=1" /boot/firmware/config.txt; then
    echo "camera_auto_detect=1" >> /boot/firmware/config.txt
    echo "Camera interface enabled - reboot may be required"
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "Creating .env from template..."
    cp .env.example .env
    chown $REAL_USER:$REAL_USER .env
    echo "WARNING: Please edit .env with your configuration before starting the service"
fi

# Enable and start the service
echo "Enabling rfid_cam service..."
systemctl enable rfid_cam

echo ""
echo "Installation complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env with your configuration:"
echo "   nano .env"
echo ""
echo "2. Test the application:"
echo "   ./scripts/test_locally.sh"
echo ""
echo "3. Start the service:"
echo "   sudo systemctl start rfid_cam"
echo ""
echo "4. Check service status:"
echo "   sudo systemctl status rfid_cam"
echo ""
echo "5. View logs:"
echo "   journalctl -u rfid_cam -f"
echo ""

if groups $REAL_USER | grep -q dialout; then
    echo "Note: User already in dialout group"
else
    echo "Note: You may need to logout and login again for group changes to take effect"
fi