#!/usr/bin/env python3
"""
RFID Pet Chip Reader with Immediate Notifications
Simplified version that sends SMS notification for every detection
"""

import os
import sys
import time
import serial
import signal
import logging
import smtplib
import subprocess
import base64
import requests
from datetime import datetime, timedelta
from email.mime.text import MIMEText as MimeText
from email.mime.multipart import MIMEMultipart as MimeMultipart
from collections import defaultdict, deque
from dotenv import load_dotenv

try:
    from picamera2 import Picamera2
    from libcamera import controls
    CAMERA_AVAILABLE = True
except ImportError:
    CAMERA_AVAILABLE = False
    print("Warning: picamera2 not available")

class RFIDCameraSystem:
    def __init__(self):
        """Initialize the RFID Camera System"""
        load_dotenv()
        self.running = False
        
        # Configuration from environment
        self.config = {
            'serial_port': os.getenv('SERIAL_PORT', '/dev/ttyUSB1'),
            'baud_rate': int(os.getenv('BAUD_RATE', '9600')),
            'poll_interval': float(os.getenv('POLL_INTERVAL', '0.5')),
            'dedupe_seconds': int(os.getenv('DEDUPE_SECONDS', '5')),
            'photo_dir': os.getenv('PHOTO_DIR', '/home/collins/rfid_photos'),
            'rclone_remote': os.getenv('RCLONE_REMOTE', 'gdrive'),
            'rclone_path': os.getenv('RCLONE_PATH', 'pet-photos'),
            'poll_address': os.getenv('POLL_ADDRESS', '01'),
            'poll_format': os.getenv('POLL_FORMAT', 'D'),
            'lost_tag': os.getenv('LOST_TAG', ''),
            'capture_on_any': os.getenv('CAPTURE_ON_ANY', 'true').lower() == 'true',
            'smtp_server': os.getenv('SMTP_HOST'),
            'smtp_port': int(os.getenv('SMTP_PORT', '587')),
            'smtp_username': os.getenv('SMTP_USER'),
            'smtp_password': os.getenv('SMTP_PASS'),
            'notification_email': os.getenv('ALERT_TO_EMAIL'),
            'openai_api_key': os.getenv('OPENAI_API_KEY'),
        }
        
        # State tracking
        self.last_tag_time = {}
        self.last_notification_time = {}
        self.encounter_history = defaultdict(deque)
        
        # Hardware components
        self.serial_conn = None
        self.camera = None
        
        # Setup logging
        self.setup_logging()
        
    def setup_logging(self):
        """Setup logging configuration"""
        log_format = '%(asctime)s - %(levelname)s - %(message)s'
        
        # Setup file logging
        file_handler = logging.FileHandler('/var/log/rfid_cam.log')
        file_handler.setFormatter(logging.Formatter(log_format))
        
        # Setup console logging
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(log_format))
        
        # Configure logger
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
    def initialize_hardware(self):
        """Initialize camera and serial connection"""
        self.logger.info("Initializing system components...")
        
        # Initialize camera
        if CAMERA_AVAILABLE:
            try:
                self.camera = Picamera2()
                config = self.camera.create_still_configuration(
                    main={"size": (2304, 1296)},
                    lores={"size": (640, 480)},
                )
                self.camera.configure(config)
                self.camera.set_controls({"AfMode": controls.AfModeEnum.Continuous})
                self.camera.start()
                time.sleep(2)  # Allow camera to stabilize
                self.logger.info("Camera initialized successfully (single camera mode)")
            except Exception as e:
                self.logger.error(f"Camera initialization failed: {e}")
                self.camera = None
        
        # Initialize serial connection
        try:
            self.serial_conn = serial.Serial(
                port=self.config['serial_port'],
                baudrate=self.config['baud_rate'],
                timeout=1
            )
            self.logger.info(f"Serial connection established on {self.config['serial_port']} at {self.config['baud_rate']} baud")
        except Exception as e:
            self.logger.error(f"Serial connection failed: {e}")
            raise
            
        # Initialize email notifications
        if self.config['smtp_server']:
            self.logger.info("Email notifications configured")
        
    def calculate_bcc(self, data_without_bcc):
        """Calculate BCC (XOR checksum) for RBC-A04 protocol"""
        bcc = 0
        for byte in data_without_bcc:
            bcc ^= byte
        return bcc
        
    def create_poll_command(self):
        """Create polling command for RBC-A04"""
        addr = self.config['poll_address']
        fmt = self.config['poll_format']
        
        command_str = f"$A{addr}01{fmt}"
        command_bytes = command_str.encode('ascii')
        
        bcc = self.calculate_bcc(command_bytes[1:])  # Skip the $ character
        full_command = f"{command_str}{bcc:02X}#"
        
        return full_command.encode('ascii')
        
    def poll_reader(self):
        """Poll the RBC-A04 reader for tag data"""
        if not self.serial_conn:
            return None
            
        try:
            # Send polling command
            command = self.create_poll_command()
            self.serial_conn.write(command)
            
            # Read response
            response = self.serial_conn.read(50)
            if response:
                response_str = response.decode('ascii', errors='ignore')
                
                # Extract tag ID using regex for 15-digit FDX-B format
                import re
                match = re.search(r'(\d{15})', response_str)
                if match:
                    return match.group(1)
                    
        except Exception as e:
            self.logger.error(f"Serial communication error: {e}")
            time.sleep(5)  # Wait before retrying
            
        return None
        
    def capture_photo(self, tag_id):
        """Capture photo when tag is detected"""
        if not self.camera:
            self.logger.warning("No camera available for photo capture")
            return []
            
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        photo_paths = []
        
        try:
            # Ensure photo directory exists
            os.makedirs(self.config['photo_dir'], exist_ok=True)
            
            # Capture photo
            filename = f"{timestamp}_{tag_id}_cam0.jpg"
            filepath = os.path.join(self.config['photo_dir'], filename)
            
            self.camera.capture_file(filepath)
            photo_paths.append(filepath)
            self.logger.info(f"Photo saved: {filepath}")
            
        except Exception as e:
            self.logger.error(f"Photo capture failed: {e}")
            
        return photo_paths
        
    def upload_photos(self, photo_paths):
        """Upload photos to cloud storage using rclone"""
        photo_links = []
        
        for photo_path in photo_paths:
            try:
                filename = os.path.basename(photo_path)
                remote_path = f"{self.config['rclone_remote']}:{self.config['rclone_path']}/{filename}"
                
                # Upload using rclone
                result = subprocess.run([
                    'rclone', 'copy', photo_path, f"{self.config['rclone_remote']}:{self.config['rclone_path']}"
                ], capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    self.logger.info(f"Upload successful: {filename}")
                    
                    # Generate share link
                    link_result = subprocess.run([
                        'rclone', 'link', remote_path
                    ], capture_output=True, text=True, timeout=10)
                    
                    if link_result.returncode == 0:
                        link = link_result.stdout.strip()
                        photo_links.append(link)
                        self.logger.info(f"Photo link: {link}")
                    else:
                        self.logger.warning(f"Link generation failed for {filename}")
                        
                else:
                    self.logger.error(f"Upload failed for {filename}: {result.stderr}")
                    
            except Exception as e:
                self.logger.error(f"Upload error for {photo_path}: {e}")
                
        return photo_links
        
    def analyze_animal_with_ai(self, image_path):
        """Analyze animal in photo using OpenAI Vision API"""
        if not self.config['openai_api_key']:
            return "animal (AI analysis not configured)"
            
        try:
            # Read and encode the image
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config['openai_api_key']}"
            }
            
            payload = {
                "model": "gpt-4o",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Analyze this photo and describe the animal you see. Be very specific about colors, patterns, and species. Include your confidence level as a percentage. Examples: 'orange and white tabby cat (95% confident)', 'black animal that is possibly a cat (70% confident)', 'raccoon with distinctive mask markings (90% confident)', 'small brown dog, possibly a terrier mix (80% confident)'. If you're unsure about the species, say so. Focus on detailed visual description."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 150
            }
            
            response = requests.post("https://api.openai.com/v1/chat/completions", 
                                   headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            
            if 'choices' in result and len(result['choices']) > 0:
                analysis = result['choices'][0]['message']['content'].strip()
                self.logger.info(f"AI Analysis: {analysis}")
                return analysis
            else:
                self.logger.warning("No AI analysis result returned")
                return "animal (AI analysis failed)"
                
        except Exception as e:
            self.logger.error(f"AI analysis failed: {e}")
            return "animal (AI analysis error)"
        
    def send_notification(self, tag_id, photo_links, animal_description=None):
        """Send immediate SMS/email notification with AI analysis"""
        if not self.config['smtp_server']:
            return
            
        try:
            # Create message with AI description
            now = datetime.now()
            if animal_description:
                message_text = f"🐾 {animal_description} detected at {now.strftime('%I:%M %p')}!\n\nChip: {tag_id}"
            else:
                message_text = f"Pet detected at {now.strftime('%I:%M %p')}! Chip: {tag_id}"
            
            if photo_links:
                message_text += f"\n\nPhoto: {photo_links[0]}"
                
            # Special handling for lost pet
            if tag_id == self.config['lost_tag']:
                message_text = f"🚨 LOST PET FOUND! {message_text}"
                
            # Send via SMTP (SMS gateway)
            msg = MimeMultipart()
            msg['From'] = self.config['smtp_username']
            msg['To'] = self.config['notification_email']
            msg['Subject'] = ""  # Empty subject for SMS
            
            msg.attach(MimeText(message_text, 'plain'))
            
            with smtplib.SMTP(self.config['smtp_server'], self.config['smtp_port']) as server:
                server.starttls()
                server.login(self.config['smtp_username'], self.config['smtp_password'])
                server.send_message(msg)
                
            self.logger.info("SMS notification sent successfully")
            
        except Exception as e:
            self.logger.error(f"Notification failed: {e}")
            
    def should_process_tag(self, tag_id):
        """Check if we should process this tag detection"""
        now = time.time()
        
        # Check deduplication
        if tag_id in self.last_tag_time:
            time_diff = now - self.last_tag_time[tag_id]
            if time_diff < self.config['dedupe_seconds']:
                return False
                
        self.last_tag_time[tag_id] = now
        return True
        
    def process_tag_detection(self, tag_id):
        """Process a detected tag - capture photo, analyze with AI, and send notification"""
        try:
            self.logger.info(f"Tag detected: {tag_id}")
            
            # Capture photos
            photo_paths = self.capture_photo(tag_id)
            
            # Analyze animal with AI if photo was captured
            animal_description = None
            if photo_paths:
                self.logger.info("Analyzing photo with AI...")
                animal_description = self.analyze_animal_with_ai(photo_paths[0])
            
            # Upload photos
            photo_links = self.upload_photos(photo_paths)
            
            # Send immediate notification with AI description
            self.send_notification(tag_id, photo_links, animal_description)
            
            # Update encounter history
            now = datetime.now()
            self.encounter_history[tag_id].append(now)
            
            # Clean old history (keep only recent encounters)
            cutoff = now - timedelta(days=7)
            while (self.encounter_history[tag_id] and 
                   self.encounter_history[tag_id][0] < cutoff):
                self.encounter_history[tag_id].popleft()
                
        except Exception as e:
            self.logger.error(f"Error processing tag {tag_id}: {e}")
            
    def cleanup(self):
        """Cleanup resources"""
        self.logger.info("Cleaning up resources...")
        
        if self.serial_conn:
            self.serial_conn.close()
            self.logger.info("Serial connection closed")
            
        if self.camera:
            self.camera.stop()
            self.logger.info("Camera stopped")
            
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
        
    def run(self):
        """Main application loop"""
        self.logger.info("Starting RFID Camera System (Immediate Notification Mode)...")
        
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
        
        try:
            # Initialize hardware
            self.initialize_hardware()
            
            self.logger.info("System initialized successfully, starting main loop...")
            self.running = True
            
            # Main detection loop
            while self.running:
                try:
                    tag_id = self.poll_reader()
                    
                    if tag_id and self.should_process_tag(tag_id):
                        self.process_tag_detection(tag_id)
                        
                    time.sleep(self.config['poll_interval'])
                    
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    self.logger.error(f"Main loop error: {e}")
                    time.sleep(1)
                    
        except Exception as e:
            self.logger.error(f"System initialization failed: {e}")
            return 1
            
        finally:
            self.cleanup()
            self.logger.info("System shutdown complete")
            
        return 0

if __name__ == "__main__":
    app = RFIDCameraSystem()
    sys.exit(app.run())