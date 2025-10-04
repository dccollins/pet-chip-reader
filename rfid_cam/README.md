# Pet Chip Reader - Intelligent Monitoring System

A sophisticated Python application for Raspberry Pi 5 that monitors RS-485 pet microchip readers and automatically captures photos when tags are detected. Features intelligent batching, AI animal identification, and advanced notification systems.

## Features

- **🧠 Intelligent Batching**: Reduces notification spam by collecting multiple detections and sending smart summaries
- **🤖 AI Animal Identification**: OpenAI GPT-4 Vision identifies animals in photos automatically  
- **📱 Immediate + Detailed Notifications**: Instant alerts on first contact + comprehensive encounter reports
- **📸 Camera Module 3 Support**: High-quality photo capture with continuous autofocus
- **☁️ Cloud Integration**: Google Drive upload with local backup and retry mechanisms
- **📊 Encounter Statistics**: Tracks visit patterns ("Recent visits: 3 in 30 min, Total: 15")
- **🔄 Fault Tolerance**: Local backup when cloud fails, automatic retry system
- **📧 SMS Gateway Support**: Clean SMS via email (no subject line clutter)
- **🛡️ Security**: Environment-based configuration, no hardcoded secrets
- **🎯 Lost Pet Alerts**: Special notifications for registered missing pets
- **💪 Resilience**: Graceful handling of AI and internet outages with offline queuing
- **🔄 Automatic Recovery**: Offline queue processor runs periodically to catch up when services return

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
├── README.md                        # This file
├── requirements.txt                 # Python dependencies  
├── .env.example                    # Configuration template
├── src/
│   ├── single_camera_test.py       # Main intelligent batching system
│   └── a04_dualcam_notify.py      # Original dual camera version
├── systemd/
│   └── rfid_cam.service           # Systemd service unit
├── logrotate/
│   └── rfid_cam                   # Log rotation config
├── scripts/
│   ├── install.sh                 # Installation script
│   ├── test_locally.sh           # Local testing script
│   └── stop_disable.sh           # Service stop/disable script
├── test_*.py                      # Comprehensive test suite
└── backup/                        # Local photo backup directory
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

## Resilience & Offline Operation

The system is designed to continue operating even when AI services or internet connectivity are temporarily unavailable.

### Offline Queue System

When internet or cloud services are unavailable, the system automatically:

- **Photos**: Queues photos for later upload to cloud storage
- **Notifications**: Queues SMS and email notifications for later delivery  
- **AI Analysis**: Uses fallback message instead of failing completely
- **Local Storage**: Continues saving photos locally as backup

### Offline Queue Management

**Automatic Processing**: 
Set up automatic queue processing every 15 minutes:
```bash
./scripts/setup_offline_cron.sh
```

**Manual Processing**:
```bash
# Process all queued items
./scripts/process_offline_queue.py

# Dry run to see what would be processed
./scripts/process_offline_queue.py --dry-run

# Process only photos or notifications
./scripts/process_offline_queue.py --photos-only
./scripts/process_offline_queue.py --notifications-only
```

**Monitor Queue Status**:
```bash
# Check if there are items in the offline queue
ls -la /path/to/photos/offline_queue/

# View processing logs
tail -f /path/to/rfid_cam/offline_queue_processing.log
```

### AI Resilience

When OpenAI services are unavailable:
- Photos are still captured and stored
- Metadata includes fallback message: "AI analysis not available"
- System continues normal operation
- AI analysis will resume when service returns

### Smart Digest System

When there's a large backlog of notifications (10+ by default), the system automatically switches to digest mode instead of sending individual notifications:

**SMS Digest**: Concise summary with key statistics
```
🐾 Pet Alert Digest
25 detections from 4 pets over 2d 6h
Most active: ...496836 (12x)
Pets: ...496836(12), ...345678(8), ...123456(3), ...987654(2)
```

**Email Digest**: Detailed breakdown with selected photos
- Complete activity summary with timestamps
- Per-pet detection counts
- Up to 20 selected photos (3 max per pet)
- Clear indication this covers an offline period

**Configuration**:
```bash
DIGEST_THRESHOLD=10              # Switch to digest mode when 10+ notifications queued
DIGEST_MAX_AGE_HOURS=48         # Consider notifications older than 48h for digest
DIGEST_MAX_PHOTOS_PER_CHIP=3    # Max photos per pet in email digest
```

### Daily Digest Reports

Automatic daily summary emails sent to your main email address every evening:

**Features**:
- Complete day's activity summary with hourly timeline
- Per-pet detection counts and patterns
- AI insights from the most interesting detections  
- Visual activity timeline showing peak hours
- Sent to your main email (not SMS gateway)

**Sample Daily Report**:
```
Daily Pet Activity Report
========================

📅 Date: Friday, October 04, 2025

📊 Activity Summary:
• Total detections: 125
• Unique pets: 4
• First activity: 02:14
• Last activity: 14:24
• Peak activity: 04:00 hour

🐾 Pet Activity:
• ...03496836: 38 detections
• ...89012345: 36 detections  
• ...21098765: 28 detections
• ...77888999: 23 detections

⏰ Activity Timeline:
04:00 │████████████████████ (92)
14:00 │████████████████████ (26)
13:00 │█████ (5)
02:00 │█ (1)

🤖 AI Insights:
• 04:15 - ...496836: Orange tabby cat sitting by food bowl
• 14:22 - ...012345: Gray cat walking through frame
```

**Setup**:
```bash
# Enable daily digest emails (automatic at 6 PM)
./scripts/setup_daily_digest.sh

# Test today's digest
./scripts/generate_daily_digest.py --dry-run

# Send digest manually
./scripts/generate_daily_digest.py
```

**Configuration**:
```bash
DAILY_DIGEST_ENABLED=true       # Enable/disable daily digest emails
DAILY_DIGEST_TIME=18:00         # Time to send digest (24h format)
DIGEST_EMAIL=your@email.com     # Email address for digest reports
```

### Recovery Behavior

The system automatically recovers when services return:
- Queued photos are uploaded to cloud storage
- Small backlogs: Individual notifications sent (marked as delayed)
- Large backlogs: Smart digest summaries sent instead
- AI analysis resumes for new photos
- No manual intervention required

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
| `AI_FALLBACK_MESSAGE` | `AI analysis not available` | Message shown when AI analysis fails |
| `DIGEST_THRESHOLD` | `10` | Notification count that triggers digest mode |
| `DIGEST_MAX_AGE_HOURS` | `48` | Max age of notifications to include in digest |
| `DIGEST_MAX_PHOTOS_PER_CHIP` | `3` | Max photos per pet in email digest |
| `DAILY_DIGEST_ENABLED` | `true` | Enable automatic daily digest emails |
| `DAILY_DIGEST_TIME` | `18:00` | Time to send daily digest (24h format) |
| `DIGEST_EMAIL` | `dccollins@gmail.com` | Email address for digest reports |

### Logging Levels

The application logs all significant events:
- **INFO**: Normal operations (startup, tag detection, photo capture)
- **WARNING**: Recoverable issues (upload failures, notification failures)  
- **ERROR**: Critical errors that may require intervention

## License

This project is licensed under the MIT License.