# 🔄 Enhanced Offline Recovery System

## Overview

The Enhanced Offline Recovery System provides intelligent handling of network outages and service disruptions. When connectivity is restored, the system processes queued photos with AI analysis, updates metadata, uploads to cloud storage, and sends beautiful HTML digest emails.

## Features

### 🧠 AI Processing Pipeline
- **OpenAI GPT-4 Vision Integration**: Analyzes queued photos for animal identification
- **Graceful Fallback**: Uses "AI analysis not available" when service unavailable
- **Metadata Enhancement**: Embeds AI descriptions into photo EXIF data

### 🎨 Enhanced Digest Emails
- **Beautiful HTML Formatting**: Professional gradient styling and responsive design
- **Google Drive Integration**: Clickable buttons for direct photo access
- **Pet-Specific Galleries**: Organized by chip ID with activity breakdowns
- **Cached Performance**: Optimized Google Drive file listings

### 📱 SMS Recovery Notifications
- **Google Fi Email Gateway**: Simple SMS via email (no Twilio complexity)
- **Clean Formatting**: Proper line breaks, no literal `\n` characters
- **Concise Digests**: Optimized for SMS length limits

## System Architecture

### Queue Management
```
Offline Period:
├── Photos → upload_queue.txt
└── Notifications → notification_queue.json

Recovery Process:
├── AI Analysis → Photo processing with GPT-4 Vision
├── Metadata Updates → EXIF embedding with descriptions
├── Cloud Upload → Google Drive with enhanced metadata
└── Enhanced Digest → HTML email with photo galleries
```

### File Structure
```
/home/collins/rfid_photos/offline_queue/
├── upload_queue.txt          # Photo paths awaiting upload
└── notification_queue.json   # Queued email/SMS notifications
```

## Configuration

### Environment Variables
```bash
# AI Processing
OPENAI_API_KEY=sk-proj-your_key_here
ANIMAL_IDENTIFICATION=true
AI_FALLBACK_MESSAGE="AI analysis not available"

# Enhanced Digests
DIGEST_EMAIL=your_email@gmail.com
RCLONE_REMOTE=gdrive
RCLONE_PATH=rfid_photos

# SMS Recovery (Google Fi)
ALERT_TO_SMS=8651234567@msg.fi.google.com
```

## Usage

### Manual Recovery
```bash
# Process offline queue immediately
cd /home/collins/repos/pet-chip-reader/rfid_cam
python scripts/process_offline_queue.py

# Dry run (preview only)
python scripts/process_offline_queue.py --dry-run
```

### Enhanced Daily Digests
```bash
# Generate beautiful HTML daily digest
python scripts/generate_enhanced_digest.py

# Set up automated daily digests
./scripts/setup_daily_digest.sh
```

### Testing
```bash
# Test complete offline recovery workflow
python test_offline_recovery_with_queue.py

# Preview SMS message formatting
python preview_sms_messages.py

# Send test SMS messages
python send_test_sms.py
```

## Recovery Workflow

### 1. Photo Processing with AI
```python
# For each queued photo:
1. Load photo from queue
2. Run AI analysis (OpenAI GPT-4 Vision)
3. Update photo metadata with AI description
4. Upload to Google Drive
5. Track success/failure
```

### 2. Notification Processing
```python
# For each queued notification:
1. Determine type (email/SMS)
2. Send individual notification
3. Track delivery status
```

### 3. Enhanced Digest Creation
```python
# Recovery summary:
1. Analyze processed photos and notifications
2. Create HTML digest with pet galleries
3. Include Google Drive buttons for photos
4. Send comprehensive recovery report
```

## HTML Digest Features

### Beautiful Styling
- **Modern Design**: Clean gradients and professional typography
- **Responsive Layout**: Mobile-friendly formatting
- **Pet Cards**: Individual sections per detected pet
- **Activity Stats**: Detection counts, time ranges, patterns

### Google Drive Integration
- **Direct Links**: Clickable buttons to view photos
- **Cached Listings**: Fast access to drive file information  
- **Quality Scoring**: Best photos highlighted first

### Email Compatibility
- **HTML Primary**: Rich formatting for modern email clients
- **Text Fallback**: Plain text version for compatibility
- **Optimized Images**: Properly sized for email viewing

## SMS Digest Format

### Recovery Digest
```
🐾 Pet Digest
Detections: 15 from 2 pets
Period: 3 hours
Most active: ...496836 (8x)
```

### Individual Notifications
```
🐾 Pet chip 496836 detected
```

## Error Handling

### AI Service Failures
- **Graceful Degradation**: Continues processing without AI descriptions
- **Fallback Messages**: Clear indication when AI unavailable
- **Retry Logic**: Attempts AI analysis on next recovery cycle

### Network Issues
- **Queue Persistence**: Photos and notifications remain queued
- **Batch Processing**: Efficient handling of large backlogs
- **Progress Tracking**: Detailed logging of recovery progress

### Metadata Failures
- **Optional Processing**: Metadata updates don't block uploads
- **Error Logging**: Clear indication of metadata issues
- **Continued Operation**: System continues with remaining photos

## Performance Optimization

### Caching
- **Google Drive Files**: Cached listings for faster digest generation
- **Batch Operations**: Efficient processing of multiple items
- **Memory Management**: Proper cleanup of large photo data

### Queue Management
- **Atomic Operations**: Safe queue file updates
- **Progress Tracking**: Real-time status of recovery process
- **Cleanup**: Automatic removal of processed items

## Security Considerations

### Credential Management
- **Environment Variables**: All secrets in `.env` files
- **No Hardcoding**: Credentials never embedded in code
- **Access Control**: Restricted file permissions on queue directories

### Data Privacy
- **Local Processing**: AI analysis optional, can be disabled
- **Encrypted Transit**: HTTPS for all API communications
- **Minimal Retention**: Queues cleaned after successful processing

## Monitoring and Logs

### Recovery Logging
```bash
# View recovery process logs
journalctl -u rfid_cam -f

# Check recovery-specific logs
tail -f /var/log/rfid_cam.log | grep -i recovery
```

### Queue Status
```bash
# Check queue sizes
ls -la /home/collins/rfid_photos/offline_queue/

# View queue contents
cat /home/collins/rfid_photos/offline_queue/upload_queue.txt
```

### Digest Monitoring
```bash
# Test digest generation
python scripts/generate_enhanced_digest.py --test

# Preview digest content
python test_enhanced_offline_digest.py
```

## Troubleshooting

### Common Issues

**AI Analysis Failing:**
```bash
# Check OpenAI API key
grep OPENAI_API_KEY rfid_cam/.env

# Test AI connectivity
python test_openai_animal.py
```

**Digest Emails Not Sending:**
```bash
# Verify SMTP configuration
grep -E "SMTP_|DIGEST_" rfid_cam/.env

# Test email functionality
python test_html_email.py
```

**SMS Messages Showing `\n`:**
- Issue: SMS messages display literal `\n` instead of line breaks
- Solution: System now uses Google Fi email gateway with proper formatting
- Test: Run `python send_test_sms.py` to verify

**Queue Files Not Processing:**
```bash
# Check queue directory permissions
ls -la /home/collins/rfid_photos/offline_queue/

# Verify queue file format
head /home/collins/rfid_photos/offline_queue/upload_queue.txt
```

### Recovery Process Stuck
1. Check available disk space: `df -h`
2. Verify network connectivity: `ping google.com`
3. Review recent logs: `journalctl -u rfid_cam -n 50`
4. Restart recovery: `sudo systemctl restart rfid_cam`

## Integration with Main System

### Automatic Recovery
- **Service Integration**: Recovery runs automatically on system startup
- **Periodic Checks**: Regular queue processing during normal operation
- **Smart Triggers**: Recovery initiated when connectivity restored

### Queue Population
- **Offline Detection**: System detects network/service outages
- **Smart Queuing**: Photos and notifications automatically queued
- **Resume Operation**: Seamless transition back to normal operation

---

**The Enhanced Offline Recovery System ensures no pet detections are lost during outages, providing users with comprehensive AI-enhanced recovery reports when connectivity is restored.** 🐾✨