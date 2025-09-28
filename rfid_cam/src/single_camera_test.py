#!/usr/bin/env python3
"""
Single Camera Test Version - Pet Chip Reader
Modified for testing with 1 camera instead of 2
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


class RFIDCameraSystem:
    """Single camera test version of RFID camera system"""
    
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Setup logging
        self.setup_logging()
        self.logger.info("Starting RFID Camera System (Single Camera Test Mode)...")
        
        # Load configuration
        self.config = self.load_config()
        
        # Initialize state
        self.running = False
        self.last_tag_time = {}  # For deduplication
        self.last_notification_time = {}  # For notification deduplication (60s)
        
        # Initialize components
        self.serial_conn = None
        self.camera = None  # Single camera for testing
        self.twilio_client = None
        
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
            'photo_dir': Path(os.getenv('PHOTO_DIR', '/home/collins/rfid_photos')),
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
            
    def initialize_camera(self):
        """Initialize single camera for testing"""
        try:
            # Check available cameras
            available_cameras = Picamera2.global_camera_info()
            if len(available_cameras) < 1:
                self.logger.error("No cameras detected")
                return False
                
            # Initialize camera 0
            self.camera = Picamera2(0)
            config = self.camera.create_still_configuration(
                main={"size": (2304, 1296)},  # 3MP still
                lores={"size": (640, 480)},   # Preview for AF
                display="lores"
            )
            self.camera.configure(config)
            self.camera.set_controls({"AfMode": 2})  # Continuous AF
            self.camera.start()
            
            # Allow time for camera to initialize
            time.sleep(2)
            
            self.logger.info("Camera initialized successfully (single camera test mode)")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize camera: {e}")
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
        
    def capture_photo(self, tag_id):
        """Capture photo from single camera"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        photo_paths = []
        
        if not self.camera:
            self.logger.error("Camera not initialized")
            return photo_paths
                
        try:
            filename = f"{timestamp}_{tag_id}_cam0.jpg"
            filepath = self.config['photo_dir'] / filename
            
            # Capture still image
            self.camera.capture_file(str(filepath))
            
            photo_paths.append(filepath)
            self.logger.info(f"Photo saved: {filepath}")
            
        except Exception as e:
            self.logger.error(f"Failed to capture photo: {e}")
                
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
            Location: Pet Chip Reader System (Test Mode)
            
            Photo has been captured and uploaded automatically.
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
            photo_paths = self.capture_photo(tag_id)
            
            # Upload photos if any were captured
            if photo_paths:
                self.upload_photos(photo_paths)
                
        # Send notifications if this is the lost tag
        if self.should_notify(tag_id):
            self.logger.info(f"Sending notifications for lost tag: {tag_id}")
            self.send_sms(tag_id)
            self.send_email(tag_id)
            
    def simulate_tag_detection(self):
        """Simulate tag detection for testing"""
        import random
        
        # Simulate different chip IDs
        test_tags = [
            "123456789012345",
            "987654321098765",
            "555666777888999"
        ]
        
        while self.running:
            # Wait 5-10 seconds between simulated detections
            time.sleep(random.uniform(5, 10))
            
            if not self.running:
                break
                
            # Pick a random tag
            tag_id = random.choice(test_tags)
            
            if not self.is_duplicate_tag(tag_id):
                self.process_tag(tag_id)
            
    def run(self, simulate_mode=False):
        """Main application loop"""
        self.logger.info("Initializing system components...")
        
        # Initialize camera (required)
        if not self.initialize_camera():
            self.logger.error("Failed to initialize camera")
            sys.exit(1)
            
        # Initialize serial (optional in test mode)
        if not simulate_mode:
            if not self.initialize_serial():
                self.logger.warning("Failed to initialize serial connection, enabling simulation mode")
                simulate_mode = True
        else:
            self.logger.info("Running in simulation mode (no serial connection)")
            
        self.initialize_notifications()
        
        self.logger.info("System initialized successfully, starting main loop...")
        
        self.running = True
        
        try:
            if simulate_mode:
                # Run simulation
                self.simulate_tag_detection()
            else:
                # Run real polling
                poll_command = self.create_poll_command()
                
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
        
        # Close serial connection
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            self.logger.info("Serial connection closed")
            
        # Stop camera
        if self.camera:
            try:
                self.camera.stop()
                self.camera.close()
                self.logger.info("Camera stopped")
            except Exception as e:
                self.logger.warning(f"Error stopping camera: {e}")
                
        self.logger.info("System shutdown complete")


if __name__ == "__main__":
    # Check if we should run in simulation mode
    simulate = len(sys.argv) > 1 and sys.argv[1] == '--simulate'
    
    app = RFIDCameraSystem()
    try:
        app.run(simulate_mode=simulate)
    except Exception as e:
        app.logger.error(f"Unhandled exception: {e}", exc_info=True)
        sys.exit(1)