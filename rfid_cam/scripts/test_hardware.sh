#!/bin/bash
set -e

echo "========================================="
echo "Pet Chip Reader - Hardware Connection Test"
echo "========================================="
echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $2"
    else
        echo -e "${RED}✗${NC} $2"
    fi
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Check if running on Raspberry Pi
echo "1. System Check"
echo "---------------"

if grep -q "Raspberry Pi" /proc/cpuinfo; then
    print_status 0 "Running on Raspberry Pi"
    PI_MODEL=$(grep "Model" /proc/cpuinfo | cut -d: -f2 | xargs)
    print_info "Model: $PI_MODEL"
else
    print_status 1 "Not running on Raspberry Pi (this may cause issues)"
fi

# Check OS version
OS_VERSION=$(cat /etc/os-release | grep PRETTY_NAME | cut -d'"' -f2)
print_info "OS: $OS_VERSION"

echo

# Check for required system packages
echo "2. System Dependencies"
echo "---------------------"

packages=("python3-picamera2" "libcamera-apps" "rclone" "python3-pip")
for package in "${packages[@]}"; do
    if dpkg -l | grep -q "^ii  $package "; then
        print_status 0 "$package installed"
    else
        print_status 1 "$package NOT installed"
        echo "  Run: sudo apt install $package"
    fi
done

echo

# Check camera interface
echo "3. Camera Interface"
echo "------------------"

if grep -q "^camera_auto_detect=1" /boot/firmware/config.txt 2>/dev/null || grep -q "^camera_auto_detect=1" /boot/config.txt 2>/dev/null; then
    print_status 0 "Camera interface enabled in config"
else
    print_status 1 "Camera interface not enabled"
    echo "  Run: sudo raspi-config -> Interface Options -> Camera -> Enable"
fi

echo

# Test camera detection
echo "4. Camera Detection"
echo "------------------"

if command -v rpicam-hello >/dev/null 2>&1; then
    print_info "Detecting cameras..."
    CAMERA_OUTPUT=$(timeout 10s rpicam-hello --list-cameras 2>/dev/null || echo "timeout")
    
    if echo "$CAMERA_OUTPUT" | grep -q "Available cameras"; then
        CAMERA_COUNT=$(echo "$CAMERA_OUTPUT" | grep -c "^\s*[0-9]" || echo "0")
        if [ "$CAMERA_COUNT" -ge 2 ]; then
            print_status 0 "Found $CAMERA_COUNT cameras (need 2)"
            echo "$CAMERA_OUTPUT" | grep "^\s*[0-9]" | while read line; do
                print_info "  $line"
            done
        elif [ "$CAMERA_COUNT" -eq 1 ]; then
            print_status 1 "Found only 1 camera (need 2)"
            echo "$CAMERA_OUTPUT" | grep "^\s*[0-9]" | while read line; do
                print_info "  $line"
            done
        else
            print_status 1 "No cameras detected"
        fi
    else
        print_status 1 "Camera detection failed or timed out"
        print_warning "Try: sudo reboot (if cameras were just connected)"
    fi
else
    print_status 1 "rpicam-hello not found"
fi

echo

# Test serial ports
echo "5. Serial Port Detection"
echo "-----------------------"

if ls /dev/ttyUSB* >/dev/null 2>&1; then
    print_status 0 "USB serial ports detected:"
    for port in /dev/ttyUSB*; do
        if [ -c "$port" ]; then
            print_info "  $port"
            # Check permissions
            if [ -r "$port" ] && [ -w "$port" ]; then
                print_status 0 "  $port is readable/writable"
            else
                print_status 1 "  $port permission denied"
                print_warning "  Add user to dialout group: sudo usermod -a -G dialout $USER"
            fi
        fi
    done
else
    print_status 1 "No USB serial ports found (/dev/ttyUSB*)"
    print_warning "Check USB-RS485 adapter connection"
fi

echo

# Check user groups
echo "6. User Permissions"
echo "------------------"

if groups $USER | grep -q dialout; then
    print_status 0 "User $USER is in dialout group"
else
    print_status 1 "User $USER is NOT in dialout group"
    echo "  Run: sudo usermod -a -G dialout $USER"
    echo "  Then logout and login again"
fi

echo

# Check Python environment
echo "7. Python Environment"
echo "---------------------"

PYTHON_VERSION=$(python3 --version)
print_info "Python version: $PYTHON_VERSION"

# Check if we're in the right directory
if [ -f "requirements.txt" ]; then
    print_status 0 "Found requirements.txt"
else
    print_status 1 "requirements.txt not found"
    print_warning "Run this script from the rfid_cam directory"
fi

# Test Python imports
print_info "Testing Python imports..."
python3 -c "
try:
    import serial
    print('✓ pyserial available')
except ImportError:
    print('✗ pyserial not available')

try:
    from dotenv import load_dotenv
    print('✓ python-dotenv available')
except ImportError:
    print('✗ python-dotenv not available')

try:
    from twilio.rest import Client
    print('✓ twilio available')
except ImportError:
    print('✗ twilio not available')

try:
    from picamera2 import Picamera2
    print('✓ picamera2 available')
except ImportError:
    print('✗ picamera2 not available (install via apt)')
"

echo

# Network connectivity test
echo "8. Network Connectivity"
echo "----------------------"

if ping -c 1 google.com >/dev/null 2>&1; then
    print_status 0 "Internet connectivity working"
else
    print_status 1 "Internet connectivity failed"
    print_warning "Check network connection (needed for uploads/notifications)"
fi

# Test DNS resolution for notification services
if nslookup smtp.gmail.com >/dev/null 2>&1; then
    print_status 0 "DNS resolution working (smtp.gmail.com)"
else
    print_status 1 "DNS resolution failed"
fi

echo

# Check log file permissions
echo "9. Log File Setup"
echo "----------------"

LOG_FILE="/var/log/rfid_cam.log"
if [ -f "$LOG_FILE" ]; then
    if [ -w "$LOG_FILE" ]; then
        print_status 0 "Log file writable: $LOG_FILE"
    else
        print_status 1 "Log file not writable: $LOG_FILE"
        echo "  Run: sudo chown $USER:$USER $LOG_FILE"
    fi
else
    print_status 1 "Log file does not exist: $LOG_FILE"
    echo "  Run: sudo touch $LOG_FILE && sudo chown $USER:$USER $LOG_FILE"
fi

echo

# Configuration file check
echo "10. Configuration"
echo "----------------"

if [ -f ".env" ]; then
    print_status 0 ".env file exists"
    
    # Check key settings
    if grep -q "^PORT=" .env; then
        PORT_VALUE=$(grep "^PORT=" .env | cut -d'=' -f2)
        print_info "Serial port configured: $PORT_VALUE"
    else
        print_warning "PORT not configured in .env"
    fi
    
    if grep -q "^PHOTO_DIR=" .env; then
        PHOTO_DIR=$(grep "^PHOTO_DIR=" .env | cut -d'=' -f2)
        if [ -d "$PHOTO_DIR" ]; then
            print_status 0 "Photo directory exists: $PHOTO_DIR"
        else
            print_status 1 "Photo directory does not exist: $PHOTO_DIR"
            echo "  Will be created automatically"
        fi
    fi
else
    print_status 1 ".env file not found"
    echo "  Run: cp .env.example .env && nano .env"
fi

echo

# Summary
echo "========================================="
echo "Hardware Test Summary"
echo "========================================="
echo

# Quick camera test if available
if command -v libcamera-still >/dev/null 2>&1 && [ "$CAMERA_COUNT" -ge 2 ]; then
    echo -e "${BLUE}Optional: Quick Camera Test${NC}"
    echo "Would you like to take test photos from both cameras? (y/n)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        print_info "Taking test photo from camera 0..."
        if timeout 10s libcamera-still --camera 0 -o test_cam0.jpg -t 2000 --width 640 --height 480 2>/dev/null; then
            print_status 0 "Camera 0 test photo: test_cam0.jpg"
        else
            print_status 1 "Camera 0 test failed"
        fi
        
        print_info "Taking test photo from camera 1..."
        if timeout 10s libcamera-still --camera 1 -o test_cam1.jpg -t 2000 --width 640 --height 480 2>/dev/null; then
            print_status 0 "Camera 1 test photo: test_cam1.jpg"
        else
            print_status 1 "Camera 1 test failed"
        fi
    fi
fi

echo
print_info "Next steps:"
echo "  1. Fix any issues marked with ✗"
echo "  2. Run: ./scripts/test_locally.sh (if all checks pass)"
echo "  3. If successful, start service: sudo systemctl start rfid_cam"
echo