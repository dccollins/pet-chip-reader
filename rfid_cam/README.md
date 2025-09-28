# Pet Chip Reader with Dual Camera System

A Python application for Raspberry Pi 5 that monitors an RS-485 pet microchip reader and automatically captures photos from dual Camera Module 3 units when tags are detected.

## Features

- **Dual Camera Support**: Captures simultaneous photos from two Raspberry Pi Camera Module 3 units
- **Pet Microchip Detection**: Polls RBC-A04 family readers via USB-RS485 adapter
- **Cloud Integration**: Automatic photo upload via rclone
- **Smart Notifications**: SMS (Twilio) and email alerts for specific tags
- **Robust Logging**: Comprehensive logging to `/var/log/rfid_cam.log` with logrotate
- **Systemd Service**: Runs as a reliable background service with auto-restart
- **Deduplication**: Prevents spam from repeated tag reads

## Hardware Requirements

- Raspberry Pi 5 running Raspberry Pi OS (Bookworm)
- 2x Raspberry Pi Camera Module 3 (connected to CSI ports)
- RBC-A04 family pet microchip reader
- USB-RS485 adapter
- Internet connection (for uploads and notifications)

## Software Dependencies

- Python 3.11+ (included with Bookworm)
- picamera2 (via apt)
- libcamera-apps (via apt)
- rclone (via apt)
- Additional Python packages (via pip)

## Getting Started

### 1. Hardware Setup

1. **Connect Cameras**:
   - Camera 0: Connect to CSI-1 port (closest to HDMI)
   - Camera 1: Connect to CSI-2 port (closer to USB ports)

2. **Connect Microchip Reader**:
   - Connect RBC-A04 reader to USB-RS485 adapter
   - Plug USB-RS485 adapter into Raspberry Pi USB port
   - Note the device path (usually `/dev/ttyUSB0`)

### 2. Software Installation

1. **Clone and setup the project**:
   ```bash
   cd /home/pi
   git clone <your-repo> rfid_cam
   cd rfid_cam
   ```

2. **Run the installer** (requires sudo):
   ```bash
   sudo ./scripts/install.sh
   ```

3. **Configure the application**:
   ```bash
   cp .env.example .env
   nano .env
   ```

### 3. Configuration

Edit `.env` with your specific settings:

#### Required Settings
```bash
# Serial port settings
PORT=/dev/ttyUSB0              # Your USB-RS485 device
BAUD=9600                      # Reader baud rate
POLL_ADDR=01                   # Reader address (usually 01)

# Photo storage
PHOTO_DIR=/home/pi/rfid_photos # Local photo storage directory
```

#### Cloud Upload (Optional)
```bash
# Configure rclone first: rclone config
RCLONE_REMOTE=gdrive           # Your rclone remote name  
RCLONE_PATH=rfid_photos        # Remote directory path
```

#### Notifications (Optional)
```bash
# SMS via Twilio
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
TWILIO_FROM=+1234567890
ALERT_TO_SMS=+1987654321

# Email via SMTP
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASS=your_app_password
EMAIL_FROM=your_email@gmail.com
ALERT_TO_EMAIL=alerts@example.com

# Trigger notifications for specific tags
LOST_TAG=123456789012345       # 15-digit chip ID to alert for
```

### 4. Testing

Test the application before enabling the service:
```bash
./scripts/test_locally.sh
```

This will run the application in the foreground so you can see logs and verify everything works.

### 5. Enable Service

Once testing is successful, start the systemd service:
```bash
sudo systemctl start rfid_cam
sudo systemctl status rfid_cam
```

Monitor logs in real-time:
```bash
journalctl -u rfid_cam -f
```

## File Structure

```
rfid_cam/
├── README.md                    # This file
├── requirements.txt             # Python dependencies
├── .env.example                # Sample configuration
├── src/
│   └── a04_dualcam_notify.py   # Main application
├── systemd/
│   └── rfid_cam.service        # Systemd service unit
├── logrotate/
│   └── rfid_cam                # Log rotation config
└── scripts/
    ├── install.sh              # Installation script
    ├── test_locally.sh         # Local testing script
    └── stop_disable.sh         # Service stop/disable script
```

## Usage

### Service Management
```bash
# Start service
sudo systemctl start rfid_cam

# Stop service
sudo systemctl stop rfid_cam

# Check status
sudo systemctl status rfid_cam

# View logs
journalctl -u rfid_cam -f

# Restart service
sudo systemctl restart rfid_cam
```

### Log Files
- **Application logs**: `/var/log/rfid_cam.log`
- **System logs**: `journalctl -u rfid_cam`

### Photo Storage
- **Local directory**: Set by `PHOTO_DIR` (default: `/home/pi/rfid_photos`)
- **Filename format**: `YYYYmmdd_HHMMSS_{chip_id}_cam{0|1}.jpg`
- **Cloud storage**: Uploaded via rclone if configured

## Troubleshooting

### Service Won't Start

1. **Check service status**:
   ```bash
   sudo systemctl status rfid_cam
   journalctl -u rfid_cam -n 20
   ```

2. **Common issues**:
   - **Permission denied**: Ensure pi user can access `/dev/ttyUSB0`
   - **Camera not found**: Check camera connections and enable camera interface
   - **Missing dependencies**: Re-run `sudo ./scripts/install.sh`

### Camera Issues

1. **Check camera detection**:
   ```bash
   libcamera-hello --list-cameras
   ```

2. **Enable camera interface**:
   ```bash
   sudo raspi-config
   # Navigate to Interface Options > Camera > Enable
   ```

3. **Check CSI connections**: Ensure ribbon cables are properly seated

### Serial Port Issues

1. **List available serial ports**:
   ```bash
   ls -la /dev/ttyUSB*
   dmesg | grep tty
   ```

2. **Add pi user to dialout group**:
   ```bash
   sudo usermod -a -G dialout pi
   # Logout and login again
   ```

3. **Test serial communication**:
   ```bash
   sudo minicom -D /dev/ttyUSB0 -b 9600
   ```

### Rclone Issues

1. **Test rclone configuration**:
   ```bash
   rclone listremotes
   rclone ls your_remote:
   ```

2. **Configure rclone**:
   ```bash
   rclone config
   ```

### Memory/Performance Issues

1. **Check system resources**:
   ```bash
   htop
   free -h
   df -h
   ```

2. **Reduce camera resolution** in the code if needed
3. **Increase swap file size** for image processing

### Log Analysis

**View recent errors**:
```bash
tail -n 50 /var/log/rfid_cam.log | grep ERROR
```

**Monitor live activity**:
```bash
tail -f /var/log/rfid_cam.log
```

**Check for specific events**:
```bash
grep "Tag detected" /var/log/rfid_cam.log
grep "Photo saved" /var/log/rfid_cam.log
grep "Upload" /var/log/rfid_cam.log
```

### Network Issues

1. **Test internet connectivity**:
   ```bash
   ping -c 3 google.com
   ```

2. **Check DNS resolution**:
   ```bash
   nslookup smtp.gmail.com
   ```

3. **Test SMTP connection**:
   ```bash
   telnet smtp.gmail.com 587
   ```

### Complete Reset

If you need to start fresh:
```bash
sudo ./scripts/stop_disable.sh
sudo ./scripts/install.sh
```

## Configuration Reference

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `/dev/ttyUSB0` | Serial port for RS-485 adapter |
| `BAUD` | `9600` | Serial communication baud rate |
| `POLL_ADDR` | `01` | Reader device address |
| `POLL_FMT` | `D` | Polling format (D for data) |
| `POLL_INTERVAL` | `0.5` | Seconds between polls |
| `DEDUPE_SECONDS` | `2` | Ignore same tag within N seconds |
| `CAPTURE_ON_ANY` | `true` | Capture photos for any detected tag |
| `LOST_TAG` | `` | Specific chip ID to trigger alerts |
| `PHOTO_DIR` | `/home/pi/rfid_photos` | Local photo storage directory |
| `RCLONE_REMOTE` | `` | Rclone remote name for uploads |
| `RCLONE_PATH` | `rfid_photos` | Remote directory path |

### Logging Levels

The application logs all significant events:
- **INFO**: Normal operations (startup, tag detection, photo capture)
- **WARNING**: Recoverable issues (upload failures, notification failures)  
- **ERROR**: Critical errors that may require intervention

## License

This project is licensed under the MIT License.