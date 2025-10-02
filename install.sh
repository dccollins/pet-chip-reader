#!/bin/bash
# =============================================================================
# RFID Pet Chip Reader - Complete Installation Script
# =============================================================================
# This script installs the AI-powered pet monitoring system with all dependencies
# Run with: curl -sSL https://raw.githubusercontent.com/your-repo/install.sh | bash
# Or: sudo ./install.sh

set -e
set -o pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_VERSION="2.0.0"
LOG_FILE="/tmp/rfid_install.log"
REQUIRED_SPACE_MB=2048  # 2GB minimum free space

# Functions
print_header() {
    echo -e "${BLUE}"
    echo "=================================================================="
    echo "   🐾 RFID Pet Chip Reader Installation Script v${SCRIPT_VERSION}"
    echo "=================================================================="
    echo -e "${NC}"
}

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] INFO: $1" >> "$LOG_FILE"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] WARN: $1" >> "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1" >> "$LOG_FILE"
    exit 1
}

check_prerequisites() {
    log_info "Checking system prerequisites..."
    
    # Check if running as root
    if [ "$EUID" -ne 0 ]; then
        log_error "Please run with sudo: sudo ./install.sh"
    fi
    
    # Get the actual user who called sudo
    REAL_USER=${SUDO_USER:-$USER}
    REAL_HOME=$(getent passwd "$REAL_USER" | cut -d: -f6)
    
    if [ -z "$REAL_USER" ] || [ "$REAL_USER" = "root" ]; then
        log_error "Cannot determine non-root user. Please run with sudo from a regular user account."
    fi
    
    log_info "Installing for user: $REAL_USER"
    log_info "User home directory: $REAL_HOME"
    
    # Check for existing installation
    SERVICE_EXISTS=false
    SERVICE_RUNNING=false
    
    if systemctl list-unit-files | grep -q "rfid_cam.service"; then
        SERVICE_EXISTS=true
        log_info "Found existing rfid_cam service"
        
        if systemctl is-active --quiet rfid_cam; then
            SERVICE_RUNNING=true
            log_warn "Service is currently running - will stop for safe installation"
        fi
    fi
    
    # Check if running on Raspberry Pi
    if ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
        log_warn "This doesn't appear to be a Raspberry Pi. Some features may not work."
    fi
    
    # Check available disk space
    AVAILABLE_SPACE=$(df / | awk 'NR==2 {print int($4/1024)}')
    if [ "$AVAILABLE_SPACE" -lt "$REQUIRED_SPACE_MB" ]; then
        log_error "Insufficient disk space. Need ${REQUIRED_SPACE_MB}MB, have ${AVAILABLE_SPACE}MB"
    fi
    
    # Check internet connectivity
    if ! ping -c 1 google.com &> /dev/null; then
        log_warn "Internet connectivity check failed. Installation may fail."
    fi
}

update_system() {
    log_info "Updating package lists..."
    if ! apt update >> "$LOG_FILE" 2>&1; then
        log_error "Failed to update package lists. Check internet connection."
    fi
    
    log_info "Upgrading critical system packages..."
    apt upgrade -y ca-certificates curl wget gnupg lsb-release >> "$LOG_FILE" 2>&1
}

install_system_dependencies() {
    log_info "Installing system dependencies..."
    
    # Core system packages
    local SYSTEM_PACKAGES=(
        # Python and development tools
        "python3"
        "python3-pip" 
        "python3-venv"
        "python3-dev"
        "python3-setuptools"
        "build-essential"
        
        # Camera and media
        "python3-picamera2"
        "libcamera-apps"
        "libcamera-dev"
        
        # Communication and networking
        "rclone"
        "curl"
        "wget"
        
        # System utilities
        "logrotate"
        "minicom"
        "screen"
        "htop"
        
        # Serial communication
        "setserial"
        
        # Image processing
        "libjpeg-dev"
        "zlib1g-dev"
        "libtiff5-dev"
        "libfreetype6-dev"
        "liblcms2-dev"
        "libwebp-dev"
        "libharfbuzz-dev"
        "libfribidi-dev"
    )
    
    for package in "${SYSTEM_PACKAGES[@]}"; do
        log_info "Installing $package..."
        if ! apt install -y "$package" >> "$LOG_FILE" 2>&1; then
            log_error "Failed to install $package"
        fi
    done
    
    log_info "System dependencies installed successfully"
}

install_python_dependencies() {
    log_info "Installing Python dependencies..."
    
    # Create requirements file with all dependencies
    cat > /tmp/rfid_requirements.txt << 'EOF'
# Core RFID system dependencies
pyserial>=3.5
python-dotenv>=1.0.0

# AI and image processing
requests>=2.28.0
Pillow>=9.0.0
piexif>=1.1.3

# Communication
twilio>=8.0.0

# GPS support (for future use)
pynmea2>=1.18.0

# Development and debugging
colorama>=0.4.0
EOF
    
    # Install Python packages with proper error handling
    if ! python3 -m pip install --break-system-packages -r /tmp/rfid_requirements.txt >> "$LOG_FILE" 2>&1; then
        log_warn "Pip install failed, trying alternative method..."
        
        # Try installing packages individually
        local PYTHON_PACKAGES=(
            "pyserial"
            "python-dotenv" 
            "requests"
            "Pillow"
            "piexif"
            "twilio"
            "pynmea2"
            "colorama"
        )
        
        for package in "${PYTHON_PACKAGES[@]}"; do
            log_info "Installing Python package: $package"
            python3 -m pip install --break-system-packages "$package" >> "$LOG_FILE" 2>&1 || log_warn "Failed to install $package"
        done
    fi
    
    log_info "Python dependencies installed successfully"
}

setup_project_structure() {
    log_info "Setting up project structure..."
    
    # Determine project directory
    if [ -f "./rfid_cam/src/single_camera_test.py" ]; then
        PROJECT_DIR=$(pwd)
        log_info "Found existing project at: $PROJECT_DIR"
    else
        log_error "Project files not found. Please run this script from the pet-chip-reader directory."
    fi
    
    cd "$PROJECT_DIR"
    
    # Set ownership for project files
    chown -R "$REAL_USER:$REAL_USER" .
    
    # Make scripts executable
    find . -name "*.sh" -exec chmod +x {} \;
    
    # Create necessary directories
    local DIRECTORIES=(
        "${REAL_HOME}/rfid_photos"
        "/var/log"
        "/etc/systemd/system"
        "/etc/logrotate.d"
    )
    
    for dir in "${DIRECTORIES[@]}"; do
        mkdir -p "$dir"
        log_info "Created directory: $dir"
    done
    
    # Set proper ownership
    chown "$REAL_USER:$REAL_USER" "${REAL_HOME}/rfid_photos"
}

backup_existing_installation() {
    if [ "$SERVICE_EXISTS" = true ]; then
        log_info "Creating backup of existing installation..."
        
        BACKUP_DIR="/tmp/rfid_backup_$(date +%Y%m%d_%H%M%S)"
        mkdir -p "$BACKUP_DIR"
        
        # Backup configuration
        if [ -f "rfid_cam/.env" ]; then
            cp "rfid_cam/.env" "$BACKUP_DIR/.env.backup"
            log_info "Backed up .env to $BACKUP_DIR"
        fi
        
        # Backup service file
        if [ -f "/etc/systemd/system/rfid_cam.service" ]; then
            cp "/etc/systemd/system/rfid_cam.service" "$BACKUP_DIR/rfid_cam.service.backup"
            log_info "Backed up service file to $BACKUP_DIR"
        fi
        
        # Backup logs (last 100 lines)
        if [ -f "/var/log/rfid_cam.log" ]; then
            tail -100 /var/log/rfid_cam.log > "$BACKUP_DIR/rfid_cam.log.backup"
            log_info "Backed up recent logs to $BACKUP_DIR"
        fi
        
        echo "BACKUP_DIR=$BACKUP_DIR" > /tmp/rfid_backup_location
        log_info "Backup location saved: $BACKUP_DIR"
    fi
}

stop_existing_service() {
    if [ "$SERVICE_RUNNING" = true ]; then
        log_info "Stopping existing rfid_cam service..."
        if systemctl stop rfid_cam; then
            log_info "Service stopped successfully"
            sleep 2  # Give it time to fully stop
        else
            log_warn "Failed to stop service gracefully, continuing anyway"
        fi
    fi
}

setup_configuration() {
    log_info "Setting up configuration files..."
    
    cd rfid_cam
    
    # Handle existing .env file
    if [ -f ".env" ]; then
        log_info "Found existing .env file - preserving configuration"
        # Validate existing .env has required new keys
        if ! grep -q "OPENAI_API_KEY" .env; then
            log_info "Adding new AI configuration options to .env"
            cat >> .env << 'EOF'

# AI Enhancement Settings (added by installer)
OPENAI_API_KEY=
ANIMAL_IDENTIFICATION=true
IMMEDIATE_NOTIFICATION=true
EOF
        fi
    elif [ -f ".env.example" ]; then
        cp .env.example .env
        chown "$REAL_USER:$REAL_USER" .env
        chmod 600 .env
        log_info "Created .env from template"
    else
        log_warn ".env.example not found, creating minimal .env"
        cat > .env << EOF
# Minimal RFID Camera System Configuration
PORT=/dev/ttyUSB1
BAUD=9600
POLL_INTERVAL=0.5
DEDUPE_SECONDS=2
PHOTO_DIR=${REAL_HOME}/rfid_photos
CAPTURE_ON_ANY=true
IMMEDIATE_NOTIFICATION=true
ANIMAL_IDENTIFICATION=true
OPENAI_API_KEY=
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASS=
ALERT_TO_EMAIL=
EOF
        chown "$REAL_USER:$REAL_USER" .env
        chmod 600 .env
    fi
}

setup_logging() {
    log_info "Setting up logging system..."
    
    # Create log file with proper permissions
    touch /var/log/rfid_cam.log
    chown "$REAL_USER:$REAL_USER" /var/log/rfid_cam.log
    chmod 640 /var/log/rfid_cam.log
    
    # Install logrotate configuration
    if [ -f "logrotate/rfid_cam" ]; then
        cp logrotate/rfid_cam /etc/logrotate.d/
        log_info "Logrotate configuration installed"
    fi
}

setup_permissions() {
    log_info "Setting up user permissions..."
    
    # Add user to required groups
    local USER_GROUPS=("dialout" "video" "gpio")
    
    for group in "${USER_GROUPS[@]}"; do
        if getent group "$group" > /dev/null; then
            usermod -a -G "$group" "$REAL_USER"
            log_info "Added $REAL_USER to $group group"
        else
            log_warn "Group $group does not exist"
        fi
    done
}

setup_hardware() {
    log_info "Configuring hardware interfaces..."
    
    # Enable camera interface
    CONFIG_FILE="/boot/firmware/config.txt"
    if [ ! -f "$CONFIG_FILE" ]; then
        CONFIG_FILE="/boot/config.txt"  # Fallback for older systems
    fi
    
    if [ -f "$CONFIG_FILE" ]; then
        if ! grep -q "^camera_auto_detect=1" "$CONFIG_FILE"; then
            echo "camera_auto_detect=1" >> "$CONFIG_FILE"
            log_info "Camera interface enabled in $CONFIG_FILE"
            REBOOT_REQUIRED=true
        fi
        
        # Enable serial interface if needed
        if ! grep -q "^enable_uart=1" "$CONFIG_FILE"; then
            echo "enable_uart=1" >> "$CONFIG_FILE"
            log_info "UART interface enabled"
            REBOOT_REQUIRED=true
        fi
    else
        log_warn "Could not find config.txt to enable camera interface"
    fi
}

install_service() {
    log_info "Installing systemd service..."
    
    if [ -f "systemd/rfid_cam.service" ]; then
        # Check if service file has changed
        SERVICE_CHANGED=true
        if [ -f "/etc/systemd/system/rfid_cam.service" ] && [ -f "systemd/rfid_cam.service" ]; then
            # Create temp file with updated paths for comparison
            TEMP_SERVICE=$(mktemp)
            cp systemd/rfid_cam.service "$TEMP_SERVICE"
            sed -i "s|/home/pi/|${REAL_HOME}/|g" "$TEMP_SERVICE"
            sed -i "s|User=pi|User=$REAL_USER|g" "$TEMP_SERVICE"
            
            if diff -q "/etc/systemd/system/rfid_cam.service" "$TEMP_SERVICE" >/dev/null; then
                SERVICE_CHANGED=false
                log_info "Service file unchanged, skipping update"
            fi
            rm -f "$TEMP_SERVICE"
        fi
        
        if [ "$SERVICE_CHANGED" = true ]; then
            cp systemd/rfid_cam.service /etc/systemd/system/
            
            # Update service file with correct paths
            sed -i "s|/home/pi/|${REAL_HOME}/|g" /etc/systemd/system/rfid_cam.service
            sed -i "s|User=pi|User=$REAL_USER|g" /etc/systemd/system/rfid_cam.service
            
            systemctl daemon-reload
            log_info "Service file updated"
        fi
        
        systemctl enable rfid_cam
        log_info "Systemd service installed and enabled"
    else
        log_error "Service file not found at systemd/rfid_cam.service"
    fi
}

restart_service_if_was_running() {
    if [ "$SERVICE_RUNNING" = true ]; then
        log_info "Restarting service (was running before installation)..."
        if systemctl start rfid_cam; then
            sleep 3
            if systemctl is-active --quiet rfid_cam; then
                log_info "Service restarted successfully"
            else
                log_warn "Service failed to start - check logs with: journalctl -u rfid_cam -n 20"
            fi
        else
            log_error "Failed to restart service"
        fi
    else
        log_info "Service was not running before installation - leaving stopped"
    fi
}

run_tests() {
    log_info "Running system tests..."
    
    # Test Python imports
    python3 -c "
import sys
try:
    import serial
    import dotenv
    import requests
    from PIL import Image
    print('✓ All required Python modules imported successfully')
except ImportError as e:
    print(f'✗ Import error: {e}')
    sys.exit(1)
" >> "$LOG_FILE" 2>&1
    
    if [ $? -eq 0 ]; then
        log_info "Python module tests passed"
    else
        log_warn "Some Python modules failed to import"
    fi
    
    # Test camera (if available)
    if command -v libcamera-hello > /dev/null; then
        log_info "Testing camera interface..."
        timeout 5s libcamera-hello --list-cameras >> "$LOG_FILE" 2>&1 || log_warn "Camera test failed or no cameras found"
    fi
}

print_completion_message() {
    echo -e "${GREEN}"
    echo "=================================================================="
    echo "   🎉 INSTALLATION COMPLETED SUCCESSFULLY!"
    echo "=================================================================="
    echo -e "${NC}"
    
    # Show backup information if created
    if [ -f "/tmp/rfid_backup_location" ]; then
        BACKUP_LOCATION=$(cat /tmp/rfid_backup_location | cut -d'=' -f2)
        echo -e "${BLUE}📦 Backup Information:${NC}"
        echo "   Previous installation backed up to: $BACKUP_LOCATION"
        echo ""
    fi
    
    # Show service status
    if [ "$SERVICE_RUNNING" = true ]; then
        echo -e "${GREEN}🔄 Service Status:${NC}"
        echo "   Service was restarted and is now: $(systemctl is-active rfid_cam)"
        echo ""
    fi
    
    echo -e "${BLUE}Next Steps:${NC}"
    echo ""
    if [ "$SERVICE_EXISTS" = true ]; then
        echo "1. 🔍 Verify service is running:"
        echo "   sudo systemctl status rfid_cam"
        echo ""
        echo "2. 📊 Monitor the logs:"
        echo "   journalctl -u rfid_cam -f"
        echo ""
        echo "3. 📝 Update configuration if needed:"
        echo "   sudo nano ./rfid_cam/.env"
        echo ""
    else
        echo "1. 📝 Configure your settings:"
        echo "   sudo nano ./rfid_cam/.env"
        echo ""
        echo "2. 🧪 Test the application:"
        echo "   cd ./rfid_cam && ./scripts/test_locally.sh"
        echo ""
        echo "3. 🚀 Start the service:"
        echo "   sudo systemctl start rfid_cam"
        echo ""
        echo "4. 📊 Monitor the service:"
        echo "   sudo systemctl status rfid_cam"
        echo "   journalctl -u rfid_cam -f"
        echo ""
    fi
    
    echo -e "${YELLOW}Configuration Required:${NC}"
    echo "• OpenAI API key for AI animal identification"
    echo "• SMTP settings for email/SMS notifications"
    echo "• rclone configuration for cloud storage"
    echo ""
    
    echo -e "${PURPLE}Hardware Checklist:${NC}"
    echo "• Connect RBC-A04 chip reader to USB port"
    echo "• Connect Camera Module 3 to CSI port"
    echo "• Optional: GPS USB dongle for location tracking"
    echo ""
    
    if [ "${REBOOT_REQUIRED:-false}" = "true" ]; then
        echo -e "${RED}⚠️  REBOOT REQUIRED${NC}"
        echo "Hardware interfaces were enabled. Please reboot before using the system."
        echo ""
    fi
    
    echo -e "${GREEN}Installation log saved to: $LOG_FILE${NC}"
}

cleanup() {
    if [ -f "/tmp/rfid_requirements.txt" ]; then
        rm -f /tmp/rfid_requirements.txt
    fi
}

# Trap to ensure cleanup on exit
trap cleanup EXIT

# Main installation flow
main() {
    print_header
    
    log_info "Starting RFID Pet Chip Reader installation..."
    
    check_prerequisites
    backup_existing_installation
    stop_existing_service
    update_system
    install_system_dependencies
    install_python_dependencies
    setup_project_structure
    setup_configuration
    setup_logging
    setup_permissions
    setup_hardware
    install_service
    run_tests
    restart_service_if_was_running
    
    print_completion_message
    
    log_info "Installation completed successfully!"
}

# Run main installation
main "$@"