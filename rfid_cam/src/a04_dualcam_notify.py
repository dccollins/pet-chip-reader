#!/usr/bin/env python3
"""
Pet Chip Reader with Dual Camera System
Monitors RS-485 pet microchip reader and captures photos from dual cameras
"""

import os
import sys
import time
import logging
import signal
import re
import subprocess
import smtplib
import ssl
from datetime import datetime, timedelta
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import serial
from dotenv import load_dotenv
from twilio.rest import Client
from twilio.base.exceptions import TwilioException

try:
    from picamera2 import Picamera2
except ImportError:
    print("ERROR: picamera2 not installed. Run: sudo apt install python3-picamera2")
    sys.exit(1)

# Import GPS and metadata managers (optional)
try:
    from gps_manager import GPSManager
    GPS_AVAILABLE = True
except ImportError:
    GPS_AVAILABLE = False
    print("WARNING: GPS manager not available. GPS features disabled.")

try:
    from image_metadata_manager import ImageMetadataManager
    METADATA_AVAILABLE = True
except ImportError:
    METADATA_AVAILABLE = False
    print("WARNING: Image metadata manager not available. Metadata features disabled.")


class RFIDCameraSystem:
    """Main application class for RFID camera system"""
    
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Setup logging
        self.setup_logging()
        self.logger.info("Starting RFID Camera System...")
        
        # Load configuration
        self.config = self.load_config()
        
        # Initialize state
        self.running = False
        self.last_tag_time = {}  # For deduplication
        self.last_notification_time = {}  # For notification deduplication (60s)
        
        # Initialize components
        self.serial_conn = None
        self.cameras = {}
        self.twilio_client = None
        
        # Initialize GPS and metadata managers
        self.gps_manager = None
        self.metadata_manager = None
        
        if GPS_AVAILABLE:
            self.gps_manager = GPSManager(self.config)
            self.logger.info("GPS Manager initialized")
        
        if METADATA_AVAILABLE:
            self.metadata_manager = ImageMetadataManager(self.config)
            self.logger.info("Image Metadata Manager initialized")
        
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
        
    def setup_logging(self):
        """Configure logging to file and console"""
        self.logger = logging.getLogger('rfid_cam')
        self.logger.setLevel(logging.INFO)
        
        # Clear any existing handlers
        self.logger.handlers.clear()
        
        # File handler
        log_file = Path('/var/log/rfid_cam.log')
        file_handler = logging.FileHandler(log_file)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
    def load_config(self):
        """Load configuration from environment variables"""
        config = {
            'port': os.getenv('PORT', '/dev/ttyUSB0'),
            'baud': int(os.getenv('BAUD', '9600')),
            'poll_addr': os.getenv('POLL_ADDR', '01'),
            'poll_fmt': os.getenv('POLL_FMT', 'D'),
            'poll_interval': float(os.getenv('POLL_INTERVAL', '0.5')),
            'dedupe_seconds': int(os.getenv('DEDUPE_SECONDS', '2')),
            'capture_on_any': os.getenv('CAPTURE_ON_ANY', 'true').lower() == 'true',
            'lost_tag': os.getenv('LOST_TAG', ''),
            'photo_dir': Path(os.getenv('PHOTO_DIR', '/home/pi/rfid_photos')),
            'rclone_remote': os.getenv('RCLONE_REMOTE', ''),
            'rclone_path': os.getenv('RCLONE_PATH', 'rfid_photos'),
            'twilio_sid': os.getenv('TWILIO_ACCOUNT_SID', ''),
            'twilio_token': os.getenv('TWILIO_AUTH_TOKEN', ''),
            'twilio_from': os.getenv('TWILIO_FROM', ''),
            'alert_to_sms': os.getenv('ALERT_TO_SMS', ''),
            'smtp_host': os.getenv('SMTP_HOST', 'smtp.gmail.com'),
            'smtp_port': int(os.getenv('SMTP_PORT', '587')),
            'smtp_user': os.getenv('SMTP_USER', ''),
            'smtp_pass': os.getenv('SMTP_PASS', ''),
            'email_from': os.getenv('EMAIL_FROM', ''),
            'alert_to_email': os.getenv('ALERT_TO_EMAIL', ''),
            
            # GPS Configuration (optional) - keep as strings for GPS manager compatibility
            'GPS_ENABLED': os.getenv('GPS_ENABLED', 'false'),
            'GPS_PORT': os.getenv('GPS_PORT', '/dev/ttyACM0'),
            'GPS_BAUD': int(os.getenv('GPS_BAUD', '9600')),
            'GPS_TIMEOUT': float(os.getenv('GPS_TIMEOUT', '5.0')),
            
            # Metadata Configuration - keep as strings for metadata manager compatibility
            'EMBED_METADATA': os.getenv('EMBED_METADATA', 'true'),
            'SAVE_METADATA_JSON': os.getenv('SAVE_METADATA_JSON', 'true'),
            'METADATA_QUALITY': os.getenv('METADATA_QUALITY', 'high'),
        }
        
        # Create photo directory if it doesn't exist
        config['photo_dir'].mkdir(parents=True, exist_ok=True)
        
        return config
        
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
        
    def initialize_serial(self):
        """Initialize serial connection to RFID reader"""
        try:
            self.serial_conn = serial.Serial(
                port=self.config['port'],
                baudrate=self.config['baud'],
                timeout=1.0
            )
            self.logger.info(f"Serial connection established on {self.config['port']} at {self.config['baud']} baud")
            return True
        except serial.SerialException as e:
            self.logger.error(f"Failed to initialize serial connection: {e}")
            return False
            
    def initialize_cameras(self):
        """Initialize both camera modules"""
        try:
            # Check available cameras
            available_cameras = Picamera2.global_camera_info()
            if len(available_cameras) < 2:
                self.logger.error(f"Only {len(available_cameras)} cameras detected, need 2")
                return False
                
            # Initialize camera 0
            self.cameras[0] = Picamera2(0)
            config0 = self.cameras[0].create_still_configuration(
                main={"size": (2304, 1296)},  # 3MP still
                lores={"size": (640, 480)},   # Preview for AF
                display="lores"
            )
            self.cameras[0].configure(config0)
            self.cameras[0].set_controls({"AfMode": 2})  # Continuous AF
            self.cameras[0].start()
            
            # Initialize camera 1
            self.cameras[1] = Picamera2(1) 
            config1 = self.cameras[1].create_still_configuration(
                main={"size": (2304, 1296)},
                lores={"size": (640, 480)},
                display="lores"
            )
            self.cameras[1].configure(config1)
            self.cameras[1].set_controls({"AfMode": 2})  # Continuous AF
            self.cameras[1].start()
            
            # Allow time for cameras to initialize
            time.sleep(2)
            
            self.logger.info("Both cameras initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize cameras: {e}")
            return False
            
    def initialize_notifications(self):
        """Initialize notification services"""
        # Initialize Twilio if configured
        if self.config['twilio_sid'] and self.config['twilio_token']:
            try:
                self.twilio_client = Client(self.config['twilio_sid'], self.config['twilio_token'])
                self.logger.info("Twilio SMS client initialized")
            except TwilioException as e:
                self.logger.warning(f"Failed to initialize Twilio: {e}")
                
        # Test SMTP if configured
        if self.config['smtp_user'] and self.config['smtp_pass']:
            self.logger.info("Email notifications configured")
            
    def calculate_bcc(self, data):
        """Calculate BCC (XOR checksum) for A04 protocol"""
        bcc = 0
        for byte in data.encode('ascii'):
            bcc ^= byte
        return f"{bcc:02X}"
        
    def create_poll_command(self):
        """Create polling command for A04 reader"""
        addr = self.config['poll_addr']
        fmt = self.config['poll_fmt']
        payload = f"A{addr}01{fmt}"
        bcc = self.calculate_bcc(payload)
        return f"${payload}{bcc}#"
        
    def parse_response(self, response):
        """Parse response from A04 reader and extract 15-digit FDX-B ID"""
        if not response or not response.startswith('$') or not response.endswith('#'):
            return None
            
        # Remove frame markers
        payload = response[1:-1]
        
        if len(payload) < 4:
            return None
            
        # Extract data portion (skip BCC)
        data = payload[:-2]
        bcc_received = payload[-2:]
        
        # Verify BCC
        bcc_calculated = self.calculate_bcc(data)
        if bcc_calculated != bcc_received:
            self.logger.warning(f"BCC mismatch: calculated {bcc_calculated}, received {bcc_received}")
            return None
            
        # Look for 15-digit FDX-B ID pattern in the data
        fdx_match = re.search(r'(\d{15})', data)
        if fdx_match:
            return fdx_match.group(1)
            
        return None
        
    def is_duplicate_tag(self, tag_id):
        """Check if this tag was recently detected (deduplication)"""
        now = datetime.now()
        if tag_id in self.last_tag_time:
            time_diff = (now - self.last_tag_time[tag_id]).total_seconds()
            if time_diff < self.config['dedupe_seconds']:
                return True
                
        self.last_tag_time[tag_id] = now
        return False
        
    def capture_photos(self, tag_id):
        """Capture photos from both cameras with GPS and metadata"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        photo_paths = []
        
        # Get GPS coordinates if available
        gps_coordinates = None
        if self.gps_manager:
            gps_coordinates = self.gps_manager.get_current_location()
        
        for cam_id in [0, 1]:
            if cam_id not in self.cameras:
                self.logger.error(f"Camera {cam_id} not initialized")
                continue
                
            try:
                filename = f"{timestamp}_{tag_id}_cam{cam_id}.jpg"
                filepath = self.config['photo_dir'] / filename
                
                # Capture still image
                self.cameras[cam_id].capture_file(str(filepath))
                
                # Add metadata if available
                if self.metadata_manager and filepath.exists():
                    try:
                        # Create metadata for this photo
                        metadata = {
                            'chip_id': tag_id,
                            'camera_id': cam_id,
                            'timestamp': timestamp,
                            'gps_coordinates': gps_coordinates,
                            'system_version': 'v2.1.0',
                        }
                        
                        # Embed metadata in photo and save JSON
                        self.metadata_manager.add_metadata_to_photo(
                            str(filepath), metadata, gps_coordinates
                        )
                        
                    except Exception as e:
                        self.logger.warning(f"Failed to add metadata to {filepath}: {e}")
                
                photo_paths.append(filepath)
                self.logger.info(f"Photo saved with metadata: {filepath}")
                
            except Exception as e:
                self.logger.error(f"Failed to capture photo from camera {cam_id}: {e}")
                
        return photo_paths
        
    def upload_photos(self, photo_paths):
        """Upload photos using rclone"""
        if not self.config['rclone_remote']:
            self.logger.info("Rclone not configured, skipping upload")
            return
            
        for photo_path in photo_paths:
            try:
                remote_path = f"{self.config['rclone_remote']}:{self.config['rclone_path']}"
                cmd = ['rclone', 'copy', str(photo_path), remote_path]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    self.logger.info(f"Upload successful: {photo_path.name}")
                else:
                    self.logger.warning(f"Upload failed for {photo_path.name}: {result.stderr}")
                    
            except subprocess.TimeoutExpired:
                self.logger.warning(f"Upload timeout for {photo_path.name}")
            except Exception as e:
                self.logger.error(f"Upload error for {photo_path.name}: {e}")
                
    def should_notify(self, tag_id):
        """Check if we should send notifications for this tag"""
        # Only notify for the specific lost tag
        if not self.config['lost_tag'] or tag_id != self.config['lost_tag']:
            return False
            
        # Check notification deduplication (60 seconds)
        now = datetime.now()
        if tag_id in self.last_notification_time:
            time_diff = (now - self.last_notification_time[tag_id]).total_seconds()
            if time_diff < 60:
                return False
                
        self.last_notification_time[tag_id] = now
        return True
        
    def send_sms(self, tag_id):
        """Send SMS notification via Twilio"""
        if not self.twilio_client or not self.config['alert_to_sms']:
            return
            
        try:
            message_body = f"ALERT: Pet chip {tag_id} detected at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            message = self.twilio_client.messages.create(
                body=message_body,
                from_=self.config['twilio_from'],
                to=self.config['alert_to_sms']
            )
            
            self.logger.info(f"SMS sent successfully: {message.sid}")
            
        except TwilioException as e:
            self.logger.error(f"Failed to send SMS: {e}")
            
    def send_email(self, tag_id):
        """Send email notification via SMTP"""
        if not self.config['smtp_user'] or not self.config['alert_to_email']:
            return
            
        try:
            msg = MIMEMultipart()
            msg['From'] = self.config['email_from']
            msg['To'] = self.config['alert_to_email']
            msg['Subject'] = f"Pet Chip Alert: {tag_id}"
            
            body = f"""
            Pet chip detection alert:
            
            Chip ID: {tag_id}
            Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            Location: Pet Chip Reader System
            
            Photos have been captured and uploaded automatically.
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Create SMTP session
            with smtplib.SMTP(self.config['smtp_host'], self.config['smtp_port']) as server:
                server.starttls()
                server.login(self.config['smtp_user'], self.config['smtp_pass'])
                server.send_message(msg)
                
            self.logger.info("Email sent successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to send email: {e}")
            
    def process_tag(self, tag_id):
        """Process a detected tag - capture photos and notify if needed"""
        self.logger.info(f"Tag detected: {tag_id}")
        
        # Check if we should capture photos
        if self.config['capture_on_any']:
            photo_paths = self.capture_photos(tag_id)
            
            # Upload photos if any were captured
            if photo_paths:
                self.upload_photos(photo_paths)
                
        # Send notifications if this is the lost tag
        if self.should_notify(tag_id):
            self.logger.info(f"Sending notifications for lost tag: {tag_id}")
            self.send_sms(tag_id)
            self.send_email(tag_id)
            
    def run(self):
        """Main application loop"""
        self.logger.info("Initializing system components...")
        
        # Initialize all components
        if not self.initialize_serial():
            self.logger.error("Failed to initialize serial connection")
            sys.exit(1)
            
        if not self.initialize_cameras():
            self.logger.error("Failed to initialize cameras")
            sys.exit(1)
            
        self.initialize_notifications()
        
        self.logger.info("System initialized successfully, starting main loop...")
        
        self.running = True
        poll_command = self.create_poll_command()
        
        try:
            while self.running:
                try:
                    # Send poll command
                    self.serial_conn.write(poll_command.encode('ascii'))
                    
                    # Read response with timeout
                    response = ''
                    start_time = time.time()
                    while time.time() - start_time < 1.0:
                        if self.serial_conn.in_waiting > 0:
                            data = self.serial_conn.read(self.serial_conn.in_waiting)
                            response += data.decode('ascii', errors='ignore')
                            
                            # Check if we have a complete frame
                            if response.endswith('#'):
                                break
                                
                    # Process response if we got one
                    if response:
                        tag_id = self.parse_response(response)
                        if tag_id and not self.is_duplicate_tag(tag_id):
                            self.process_tag(tag_id)
                            
                    # Wait before next poll
                    time.sleep(self.config['poll_interval'])
                    
                except serial.SerialException as e:
                    self.logger.error(f"Serial communication error: {e}")
                    time.sleep(5)  # Wait before retrying
                    
        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt")
        finally:
            self.cleanup()
            
    def cleanup(self):
        """Clean up resources"""
        self.logger.info("Cleaning up resources...")
        
        # Close GPS manager
        if self.gps_manager:
            try:
                self.gps_manager.close()
                self.logger.info("GPS manager closed")
            except Exception as e:
                self.logger.warning(f"Error closing GPS manager: {e}")
        
        # Close metadata manager
        if self.metadata_manager:
            try:
                self.metadata_manager.close()
                self.logger.info("Metadata manager closed")
            except Exception as e:
                self.logger.warning(f"Error closing metadata manager: {e}")
        
        # Close serial connection
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            self.logger.info("Serial connection closed")
            
        # Stop cameras
        for cam_id, camera in self.cameras.items():
            try:
                camera.stop()
                camera.close()
                self.logger.info(f"Camera {cam_id} stopped")
            except Exception as e:
                self.logger.warning(f"Error stopping camera {cam_id}: {e}")
                
        self.logger.info("System shutdown complete")


if __name__ == "__main__":
    app = RFIDCameraSystem()
    try:
        app.run()
    except Exception as e:
        app.logger.error(f"Unhandled exception: {e}", exc_info=True)
        sys.exit(1)