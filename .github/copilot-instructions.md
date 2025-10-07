# Pet Chip Reader - AI Coding Assistant Instructions

## Project Overview

This is a **high-performance** Raspberry Pi 5 IoT system with **50ms response time** that monitors pet microchip readers (RBC-A04 family) and automatically captures photos from dual cameras when pets are detected. Features **individual AI analysis per camera**, robust upload system with retry logic, sequential processing workflow, and professional SMS notifications with working Google Drive links.

## Architecture

**Main Components:**
- `rfid_cam/src/a04_dualcam_notify.py` - **ACTIVE v2.2.0** Ultra-fast dual camera system with individual AI analysis
- `rfid_cam/systemd/rfid_cam.service` - Systemd service for reliable background operation
- `rfid_cam/scripts/` - Installation, testing, and management utilities
- `PROJECT_INDEX.md` - **CRITICAL**: Complete implementation index to avoid reinventing features

**Key Design Patterns:**
- **Ultra-fast polling**: 50ms intervals (10x faster than original 500ms)
- **Sequential processing**: Capture → Upload → AI Analysis → Complete Notification
- **Individual AI analysis**: Each camera gets separate AI description + smart summary
- **Robust upload system**: 3-attempt retry logic with 60-second timeouts
- **Deduplication disabled**: Currently processes every scan for immediate testing
- **Graceful shutdown**: Signal handlers for SIGTERM/SIGINT with proper resource cleanup
- **Comprehensive error handling**: Upload failures, AI errors, and connectivity issues

## Hardware Integration

**Serial Protocol (RBC-A04):**
- Frame format: `$A{addr}01{fmt}{BCC}#` where BCC is XOR checksum
- Default: `$A0101D{calculated_bcc}#` for address 01, format D
- Response parsing extracts 15-digit FDX-B IDs using regex `(\d{15})`

**Dual Camera Setup:**
- Camera 0: CSI-1 port, Camera 1: CSI-2 port
- Picamera2 with continuous autofocus (`AfMode: 2`)
- Still capture at 2304x1296 resolution
- Both cameras initialized and kept running for fast capture

## Development Workflows

**Local Testing:**
```bash
cd rfid_cam && ./scripts/test_locally.sh
```
Runs in foreground with console output for debugging.

**Production Deployment:**
```bash
sudo ./scripts/install.sh    # Full system setup
sudo systemctl start rfid_cam
journalctl -u rfid_cam -f    # Monitor logs
```

**Service Management:**
```bash
sudo ./scripts/stop_disable.sh  # Clean shutdown
```

## Configuration Patterns

**Environment-based config**: All settings in `.env` file, loaded via `python-dotenv`
- **Performance settings**: `POLL_INTERVAL=0.05` (50ms), `DEDUPE_SECONDS=0` (disabled)
- Serial settings: `PORT`, `BAUD`, `POLL_ADDR`, `POLL_FMT` 
- AI settings: `OPENAI_API_KEY`, `ANIMAL_IDENTIFICATION=true`
- Notifications: `LOST_TAG`, SMS via email gateway (`@msg.fi.google.com`)
- Storage: `PHOTO_DIR`, `RCLONE_REMOTE`, `RCLONE_PATH`

**Photo naming convention**: `YYYYmmdd_HHMMSS_{chip_id}_cam{0|1}.jpg`

## ⚠️ **CRITICAL: Avoiding Feature Duplication**

**ALWAYS CHECK BEFORE IMPLEMENTING:**
1. **`PROJECT_INDEX.md`** - Complete feature inventory with locations and status
2. **Existing implementations** - Many features already exist and work well
3. **Test files** - `test_*.py` files show working examples of most features
4. **Documentation** - Multiple `.md` files contain implementation details

**Major features already implemented:**
- Ultra-fast response system (50ms polling)
- Individual AI analysis per camera with summaries  
- Robust upload system with retry logic and status tracking
- Professional SMS notifications with working Google Drive links
- Sequential processing workflow
- HTML daily digest emails
- GPS & metadata infrastructure (ready for hardware)
- Offline recovery and resilience systems

## Critical Dependencies

**System packages** (via apt):
- `python3-picamera2` - Camera control (NOT available via pip)
- `libcamera-apps` - Camera utilities and drivers
- `rclone` - Cloud upload utility

**Python packages** (via pip with `--break-system-packages`):
- `pyserial` - RS-485 communication
- `twilio` - SMS notifications  
- `python-dotenv` - Configuration management

## Logging Strategy

**Dual logging setup:**
- File: `/var/log/rfid_cam.log` with timestamps
- Console: For development/debugging
- Logrotate: Weekly rotation, 8 weeks retention, compress

**Key log events:**
- System: startup, shutdown, component initialization
- Detection: tag reads, deduplication decisions
- Capture: photo success/failure per camera
- Upload: rclone success/failure per file
- Notifications: SMS/email delivery status

## Troubleshooting Patterns

**Missing hardware failures:**
- Serial port access → Check `/dev/ttyUSB*`, user in `dialout` group
- Camera detection → `libcamera-hello --list-cameras`, CSI connections
- Permission errors → Service runs as `pi` user, needs `/var/log` write access

**Service debugging:**
```bash
systemctl status rfid_cam     # Service state
journalctl -u rfid_cam -n 20  # Recent system logs  
tail -f /var/log/rfid_cam.log # Application logs
```

## Security Considerations

**Systemd hardening** in service file:
- `NoNewPrivileges=true`, `ProtectSystem=strict`
- Read-only home, write access only to photos and logs
- Resource limits: 512M memory, 80% CPU quota

**Credential management**: All secrets in `.env` file (git-ignored), never hardcoded.