# 🐾 Pet Chip Reader Installation Guide v2.2.0

## Quick Installation

For a complete automated installation, run:

```bash
sudo ./install.sh
```

This comprehensive script will:
- ✅ Install all system dependencies (Python, cameras, communication tools)
- ✅ Set up Python packages including AI integration
- ✅ Configure hardware interfaces (camera, serial ports)
- ✅ Create proper directory structure and permissions
- ✅ Install and enable systemd service
- ✅ Set up logging and log rotation
- ✅ Run system tests to verify installation

## What Gets Installed

### System Dependencies
- **Python 3** with development tools and pip
- **python3-picamera2** for Camera Module 3 support
- **libcamera-apps** for camera utilities
- **rclone** for Google Drive integration
- **Build tools** for compiling Python packages
- **Serial communication** utilities

### Python Packages
- **pyserial** - RBC-A04 chip reader communication (ultra-fast 50ms polling)
- **python-dotenv** - Configuration management
- **openai** - GPT-4 Vision API for individual camera analysis
- **Pillow + piexif** - Image processing and EXIF metadata
- **twilio** - SMS notifications via carrier gateway
- **pynmea2** - GPS support (infrastructure ready)

### Hardware Configuration
- Camera interface enabled in `/boot/firmware/config.txt`
- UART interface enabled for serial communication
- User added to `dialout`, `video`, and `gpio` groups

## Post-Installation Configuration

### 1. Configure Environment Variables

Edit the `.env` file in the `rfid_cam` directory:

```bash
sudo nano ./rfid_cam/.env
```

**Required Settings:**
```env
# Ultra-fast response configuration (v2.2.0)
POLL_INTERVAL=0.05          # 50ms polling for instant detection
DEDUPE_SECONDS=0            # Disabled for immediate testing
ANIMAL_IDENTIFICATION=true   # Enable AI analysis per camera

# OpenAI GPT-4 Vision API for individual camera analysis
OPENAI_API_KEY=your_openai_api_key_here

# SMS via Gmail carrier gateway
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASS=your_app_password
ALERT_TO_EMAIL=your_phone@msg.fi.google.com
```

### 2. Set Up Cloud Storage

Configure rclone for Google Drive upload:

```bash
rclone config
```

Follow the prompts to set up Google Drive integration, then update `.env`:

```env
RCLONE_REMOTE=gdrive:PetPhotos
```

### 3. Test Hardware

Verify your hardware connections:

```bash
# Test camera
libcamera-hello --list-cameras

# Check for chip reader
ls /dev/ttyUSB*

# Test the application locally
cd rfid_cam && ./scripts/test_locally.sh
```

### 4. Start the Service

```bash
# Start the service
sudo systemctl start rfid_cam

# Check status
sudo systemctl status rfid_cam

# View live logs
journalctl -u rfid_cam -f
```

## Hardware Setup

### RBC-A04 Chip Reader
- Connect to Raspberry Pi via USB-to-RS485 adapter
- Default port: `/dev/ttyUSB1`
- Baud rate: 9600, 200ms timeout (5x faster than v2.1.0)
- Protocol: Standard FDX-B microchip reading with 50ms polling

### Dual Camera Module 3 Setup
- Camera 0: CSI-1 port, Camera 1: CSI-2 port
- Continuous autofocus enabled (AfMode: 2) for sharp captures
- Still resolution: 2304x1296 for detailed AI analysis
- Individual AI analysis per camera with smart summaries

### Optional: GPS Module
- USB GPS dongle support ready for location tracking
- Metadata includes GPS coordinates when available

## Service Management

```bash
# Start service
sudo systemctl start rfid_cam

# Stop service  
sudo systemctl stop rfid_cam

# Restart service
sudo systemctl restart rfid_cam

# Enable auto-start on boot
sudo systemctl enable rfid_cam

# Disable auto-start
sudo systemctl disable rfid_cam

# View service status
sudo systemctl status rfid_cam

# View recent logs
journalctl -u rfid_cam -n 50

# Follow live logs
journalctl -u rfid_cam -f
```

## Troubleshooting

### Permission Issues
```bash
# Check user groups
groups $USER

# Add user to required groups manually
sudo usermod -a -G dialout,video,gpio $USER

# Logout and login again
```

### Camera Not Detected
```bash
# Check camera connection
libcamera-hello --list-cameras

# Verify config.txt
grep camera /boot/firmware/config.txt

# Check for hardware
dmesg | grep -i camera
```

### Chip Reader Not Found
```bash
# List USB devices
lsusb

# Check serial ports
ls /dev/ttyUSB*

# Test with minicom
sudo minicom -D /dev/ttyUSB1 -b 9600
```

### Service Won't Start
```bash
# Check service logs
journalctl -u rfid_cam -n 50

# Check application logs
tail -f /var/log/rfid_cam.log

# Test manually
cd rfid_cam && python3 src/single_camera_test.py
```

### OpenAI API Issues
```bash
# Test API key
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
  https://api.openai.com/v1/models
```

## File Locations

- **Application**: `/home/$USER/repos/pet-chip-reader/rfid_cam/`
- **Photos**: `/home/$USER/rfid_photos/`
- **Logs**: `/var/log/rfid_cam.log`
- **Service**: `/etc/systemd/system/rfid_cam.service`
- **Config**: `/home/$USER/repos/pet-chip-reader/rfid_cam/.env`

## Security Features

The service runs with proper security hardening:
- Runs as regular user (not root)
- Read-only filesystem access
- Limited system call access
- Resource limits (512MB memory, 80% CPU)
- Secure credential storage in `.env` file

## Monitoring

View system status:
```bash
# Service status
sudo systemctl status rfid_cam

# Resource usage
htop

# Log analysis
tail -f /var/log/rfid_cam.log | grep -E "(DETECTION|ERROR|WARNING)"

# Photo count
ls -la ~/rfid_photos/ | wc -l
```

## Updates and Maintenance

```bash
# Update system packages
sudo apt update && sudo apt upgrade

# Update Python packages  
python3 -m pip install --upgrade --break-system-packages pyserial python-dotenv requests Pillow twilio

# Restart after updates
sudo systemctl restart rfid_cam
```

---

For additional help, check the [project documentation](README.md) or [security guide](SECURITY.md).