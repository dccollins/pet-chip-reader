# 🐾 Pet Chip Reader - Ultra-Fast Intelligent Monitoring System

A high-performance IoT system for Raspberry Pi 5 with **50ms response time** that monitors pet microchip readers (RBC-A04 family) and automatically captures photos from **dual cameras** when pets are detected. Features **individual AI analysis per camera**, robust upload system with retry logic, sequential processing workflow, and professional SMS notifications.

## ✨ Features

### ⚡ **Ultra-Fast Performance**
- **🔍 50ms Response Time**: 10x faster chip detection (vs 500ms previously)
- **📸 Dual Camera System**: Simultaneous capture from 2x Camera Module 3
- **⚡ Sequential Processing**: Capture → Upload → AI Analysis → Complete Notification

### 🤖 **Advanced AI Analysis**
- **👁️ Individual Photo Analysis**: Each camera gets separate AI description
- **📊 Smart AI Summaries**: Overall findings across both cameras
- **🎯 Concise Responses**: "no animals seen" when appropriate
- **� Professional Format**: AI Summary + individual photo descriptions

### 📤 **Robust Upload System**
- **� 3-Attempt Retry Logic**: 60-second timeout with automatic retries
- **📊 Upload Status Tracking**: "2/2 photos uploaded" status in SMS
- **🔗 Real Google Drive Links**: Working clickable links with proper file IDs
- **💾 Local Backup**: Photos preserved during upload failures

### 📱 **Professional Notifications**
- **� SMS via Email Gateway**: Clean format without subject line clutter
- **🔗 Working Photo Links**: Each camera result with individual AI description
- **⬆️ Upload Status**: Clear indication when some photos fail to upload
- **⏱️ Complete Workflow**: Notifications sent only after all processing finished

### 🛰️ **Enhanced Infrastructure** 
- **�️ GPS Location Tracking**: Ready for USB GPS dongles with NMEA support
- **📄 Enhanced Metadata**: Comprehensive EXIF and JSON metadata with GPS coordinates
- **🔄 Offline Recovery**: AI-enhanced recovery with smart digest system
- **🎨 Enhanced Digests**: Beautiful HTML emails with Google Drive integration
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

# Performance Settings (Ultra-Fast Mode)
POLL_INTERVAL=0.05                 # 50ms polling (10x faster than default)
DEDUPE_SECONDS=0                   # Disabled for testing (process every scan)

# Performance Settings (Ultra-Fast Mode)
POLL_INTERVAL=0.05                 # 50ms polling (10x faster than default)
DEDUPE_SECONDS=0                   # Disabled for testing (process every scan)
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
- **Offline Recovery**: AI processes queued photos, creates enhanced digest emails
- **Smart Digests**: HTML emails with pet galleries, Google Drive buttons, activity stats
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
│   │   ├── a04_dualcam_notify.py     # Main dual camera system (v2.2.0) - ACTIVE
│   │   ├── single_camera_test.py     # Legacy single camera system (v2.1.0)
│   │   ├── gps_manager.py           # GPS tracking with NMEA support
│   │   └── image_metadata_manager.py # Enhanced EXIF/JSON metadata
│   ├── scripts/
│   │   ├── install.sh                # Installation script
│   │   ├── test_locally.sh          # Local testing
│   │   ├── process_offline_queue.py  # Enhanced offline recovery system
│   │   ├── generate_enhanced_digest.py # Beautiful HTML digest emails
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