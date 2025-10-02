# 🐾 Pet Chip Reader - Intelligent Monitoring System

An advanced IoT system for Raspberry Pi 5 that monitors pet microchip readers (RBC-A04 family) and automatically captures photos when pets are detected. Features intelligent batching, AI animal identification, cloud storage, and smart notifications.

## ✨ Features

- **🔍 Pet Chip Detection**: RBC-A04 RS-485 microchip reader support
- **📸 Single/Dual Camera Capture**: Automatic photo capture with Camera Module 3
- **🧠 Intelligent Batching**: Reduces notification spam by batching multiple detections
- **🤖 AI Animal Identification**: OpenAI GPT-4 Vision with improved concise responses
- **🛰️ GPS Location Tracking**: Ready for USB GPS dongles with NMEA support
- **📄 Enhanced Metadata**: Comprehensive EXIF and JSON metadata with GPS coordinates
- **☁️ Cloud Storage**: Automatic Google Drive upload with local backup/retry
- **📱 Smart Notifications**: Immediate alerts + detailed encounter reports
- **📧 SMS Gateway Support**: Clean SMS via email (no subject line clutter)
- **🔄 Fault Tolerance**: Local backup, retry mechanisms, graceful error handling
- **📊 Encounter Statistics**: Tracks visit frequency and patterns
- **🛡️ Security**: Environment-based configuration, no hardcoded secrets

## 🚀 Quick Start

### Prerequisites

- **Hardware**: Raspberry Pi 5 with Camera Module 3
- **OS**: Raspberry Pi OS Bookworm (64-bit recommended)
- **Pet Chip Reader**: RBC-A04 or compatible RS-485 reader
- **USB-to-RS485 Adapter**: For connecting the chip reader

### 1. Hardware Setup

```bash
# Connect RBC-A04 reader via USB-to-RS485 adapter
# Camera Module 3 → CSI port
# Power on and boot Raspberry Pi
```

### 2. Install System Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3-picamera2 libcamera-apps rclone git

# Install Python packages
pip3 install --break-system-packages pyserial twilio python-dotenv pynmea2 piexif
```

### 3. Clone and Configure

```bash
# Clone repository
git clone https://github.com/dccollins/pet-chip-reader.git
cd pet-chip-reader/rfid_cam

# Copy configuration template
cp .env.example .env

# Edit configuration with your credentials
nano .env
```

### 4. Configure Services

**Google Drive Setup:**
```bash
rclone config
# Choose: Google Drive, follow prompts
```

**Gmail App Password:**
1. Enable 2FA: https://myaccount.google.com/security
2. Create App Password: https://support.google.com/accounts/answer/185833
3. Add to `.env` file

### 5. Install and Activate

```bash
# Run installation script
sudo ./scripts/install.sh

# Start the service
sudo systemctl start rfid_cam

# Enable auto-start on boot
sudo systemctl enable rfid_cam
```

### 6. Monitor System

```bash
# Check service status
sudo systemctl status rfid_cam

# View live logs
sudo journalctl -u rfid_cam -f

# Test with pet chip scan!
```

## 📋 Configuration Guide

### Essential Settings (`.env` file)

```bash
# Hardware
PORT=/dev/ttyUSB1                    # USB-to-RS485 adapter
BAUD=9600                           # Communication speed

# Notifications  
ALERT_TO_EMAIL=1234567890@msg.fi.google.com  # SMS via email gateway
SMTP_USER=your_email@gmail.com      # Gmail address
SMTP_PASS=your_app_password         # Gmail App Password (16 chars)

# AI Features (Optional)
OPENAI_API_KEY=sk-proj-your_key_here # For animal identification
ANIMAL_IDENTIFICATION=true          # Enable AI analysis

# GPS & Location (Optional)
GPS_ENABLED=false                   # Enable when GPS dongle connected
GPS_PORT=/dev/ttyUSB0               # GPS device port
EMBED_METADATA=true                 # Include GPS in photo metadata

# Cloud Storage (Optional)  
RCLONE_REMOTE=gdrive                # Configured rclone remote
RCLONE_PATH=rfid_photos            # Drive folder path

# Pet Management
LOST_TAG=123456789012345           # Chip ID for lost pet alerts
```

### SMS Gateway Setup

**Popular carriers:**
- **Google Fi**: `1234567890@msg.fi.google.com`
- **Verizon**: `1234567890@vtext.com`
- **AT&T**: `1234567890@txt.att.net`
- **T-Mobile**: `1234567890@tmomail.net`

## 🎯 How It Works

### Detection Flow

1. **Pet Scans Chip** → RBC-A04 reader detects microchip
2. **Photo Capture** → Camera Module 3 takes high-res photo  
3. **Immediate Alert** → SMS sent with photo link and timestamp
4. **Intelligent Batching** → Collects multiple detections (30 seconds)
5. **AI Analysis** → OpenAI identifies animal type in best photo
6. **Detailed Report** → Enhanced notification with encounter stats

### Smart Features

- **Spam Reduction**: Multiple scans = 1 notification per day per chip
- **Encounter Tracking**: "Recent visits: 3 in 30 min, Total: 15"
- **Fault Tolerance**: Local backup if Google Drive fails, auto-retry
- **Lost Pet Alerts**: Special notifications for registered lost pets

## 🔧 Management Commands

### Service Control
```bash
sudo systemctl start rfid_cam      # Start monitoring
sudo systemctl stop rfid_cam       # Stop monitoring  
sudo systemctl restart rfid_cam    # Restart service
sudo systemctl status rfid_cam     # Check status
```

### Monitoring & Logs
```bash
# Live logs
sudo journalctl -u rfid_cam -f

# Recent logs  
sudo journalctl -u rfid_cam -n 50

# System logs
tail -f /var/log/rfid_cam.log
```

### Testing & Debugging
```bash
# Manual test (stops service)
sudo systemctl stop rfid_cam
cd rfid_cam
python3 src/single_camera_test.py

# Hardware test
python3 scripts/test_hardware.sh

# Photo test
python3 test_immediate_notification.py
```

## 📁 Project Structure

```
pet-chip-reader/
├── rfid_cam/
│   ├── src/
│   │   ├── single_camera_test.py     # Main intelligent system (v2.1.0)
│   │   ├── gps_manager.py           # GPS tracking with NMEA support
│   │   ├── image_metadata_manager.py # Enhanced EXIF/JSON metadata
│   │   └── a04_dualcam_notify.py     # Original dual camera version
│   ├── scripts/
│   │   ├── install.sh                # Installation script
│   │   ├── test_locally.sh          # Local testing
│   │   └── stop_disable.sh          # Clean shutdown
│   ├── systemd/
│   │   └── rfid_cam.service         # Service configuration
│   ├── test_*.py                    # Comprehensive test suite
│   ├── .env.example                 # Configuration template
│   ├── GPS_METADATA_INTEGRATION.md  # GPS & metadata documentation
│   └── backup/                      # Local photo backup
├── README.md                        # This file
└── SECURITY.md                      # Security guidelines
```

## 🛡️ Security & Privacy

- **No Hardcoded Secrets**: All credentials in `.env` files (git-ignored)
- **Local Processing**: Photos stored locally, cloud upload optional
- **Encrypted Communication**: HTTPS/TLS for all API calls
- **Minimal Permissions**: Service runs with restricted privileges
- **See**: [SECURITY.md](SECURITY.md) for detailed security guide

## 🔍 Troubleshooting

### Common Issues

**Service won't start:**
```bash
sudo journalctl -u rfid_cam -n 20    # Check error logs
ls -la /dev/ttyUSB*                  # Verify chip reader connection
```

**Camera not working:**
```bash
libcamera-hello --list-cameras       # Test camera detection
groups $USER                         # Check video group membership
```

**No notifications:**
```bash
# Check .env configuration
grep -E "SMTP_|ALERT_" rfid_cam/.env

# Test email settings  
python3 test_email.py
```

**Photos not uploading:**
```bash
rclone lsd gdrive:                   # Test Google Drive connection
ls -la rfid_cam/backup/              # Check local backup
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📜 License

This project is licensed under the MIT License.

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/dccollins/pet-chip-reader/issues)
- **Security**: See [SECURITY.md](SECURITY.md)
- **Hardware**: RBC-A04 documentation included in `/docs/`

---

**Keep your pets safe with intelligent monitoring!** 🐕🐱