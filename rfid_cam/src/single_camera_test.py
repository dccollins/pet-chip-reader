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
import base64
import json
import threading
import queue
from collections import defaultdict, deque
from datetime import datetime, timedelta
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage

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
        
        # Batching system
        self.detection_queue = queue.Queue()
        self.batch_processor_thread = None
        self.pending_batches = defaultdict(list)  # chip_id -> list of detections
        self.batch_timers = {}  # chip_id -> timer
        self.encounter_history = defaultdict(deque)  # chip_id -> deque of timestamps
        
        # Local backup and retry system
        self.local_backup_dir = Path(self.config['photo_dir']) / 'backup'
        self.local_backup_dir.mkdir(exist_ok=True)
        self.upload_retry_queue = queue.Queue()
        self.retry_thread = None
        self.immediate_notifications_sent = set()  # Track immediate notifications to avoid duplicates
        
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
            'notify_on_any': os.getenv('NOTIFY_ON_ANY', 'false').lower() == 'true',
            'photo_dir': Path(os.getenv('PHOTO_DIR', '/home/collins/rfid_photos')),
            'rclone_remote': os.getenv('RCLONE_REMOTE', ''),
            'rclone_path': os.getenv('RCLONE_PATH', 'rfid_photos'),
            'twilio_sid': os.getenv('TWILIO_ACCOUNT_SID', ''),
            'twilio_auth_token': os.getenv('TWILIO_AUTH_TOKEN', ''),
            'twilio_from_number': os.getenv('TWILIO_FROM_NUMBER', ''),
            'twilio_to_number': os.getenv('TWILIO_TO_NUMBER', ''),
            
            # OpenAI Configuration
            'openai_api_key': os.getenv('OPENAI_API_KEY', ''),
            'animal_identification': os.getenv('ANIMAL_IDENTIFICATION', 'false').lower() == 'true',
            
            # Batching Configuration
            'batch_delay_minutes': float(os.getenv('BATCH_DELAY_MINUTES', '1')),
            'encounter_window_minutes': int(os.getenv('ENCOUNTER_WINDOW_MINUTES', '30')),
            'max_photos_per_batch': int(os.getenv('MAX_PHOTOS_PER_BATCH', '5')),
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
        """Upload photos using rclone and return specific photo links, with local backup on failure"""
        photo_links = []
        failed_uploads = []
        
        if not self.config['rclone_remote']:
            self.logger.info("Rclone not configured, storing locally")
            self.store_photos_locally(photo_paths)
            return photo_links
            
        for photo_path in photo_paths:
            try:
                remote_path = f"{self.config['rclone_remote']}:{self.config['rclone_path']}"
                cmd = ['rclone', 'copy', str(photo_path), remote_path]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    self.logger.info(f"Upload successful: {photo_path.name}")
                    
                    # Get specific photo link
                    photo_link = self.get_photo_link(photo_path.name)
                    if photo_link:
                        photo_links.append(photo_link)
                        self.logger.info(f"Photo link: {photo_link}")
                else:
                    self.logger.warning(f"Upload failed for {photo_path.name}: {result.stderr}")
                    failed_uploads.append(photo_path)
                    
            except subprocess.TimeoutExpired:
                self.logger.warning(f"Upload timeout for {photo_path.name}")
            except Exception as e:
                self.logger.error(f"Upload error for {photo_path.name}: {e}")
                failed_uploads.append(photo_path)
                
        # Handle failed uploads
        if failed_uploads:
            self.logger.info(f"Storing {len(failed_uploads)} photos locally for retry")
            backup_paths = self.store_photos_locally(failed_uploads)
            
            # Queue for retry
            for backup_path in backup_paths:
                self.upload_retry_queue.put(backup_path)
                
        return photo_links
    
    def get_photo_link(self, filename):
        """Get specific Google Drive link for a photo"""
        try:
            # Try to get direct link to the specific file
            remote_file_path = f"{self.config['rclone_remote']}:{self.config['rclone_path']}/{filename}"
            
            result = subprocess.run(
                ['rclone', 'link', remote_file_path],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode == 0:
                link = result.stdout.strip()
                # Convert to direct view link if it's a Google Drive link
                if 'drive.google.com' in link and 'open?id=' in link:
                    # Convert from open?id= to file/d/ format for direct viewing
                    file_id = link.split('open?id=')[1].split('&')[0]
                    full_link = f"https://drive.google.com/file/d/{file_id}/view"
                    return full_link
                return link
            else:
                self.logger.warning(f"Failed to get link for {filename}: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            self.logger.warning(f"Link generation timeout for {filename}")
        except Exception as e:
            self.logger.warning(f"Link generation error for {filename}: {e}")
        
        # Return None if link generation failed
        return None
    
    def identify_animal(self, photo_path):
        """Use OpenAI GPT-4 Vision to identify the animal in the photo"""
        if not self.config['animal_identification'] or not self.config['openai_api_key']:
            return None
            
        try:
            import urllib.request
            import urllib.parse
            
            # Encode image to base64
            with open(photo_path, 'rb') as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            
            # Prepare OpenAI API request
            api_url = "https://api.openai.com/v1/chat/completions"
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config['openai_api_key']}"
            }
            
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Look at this photo and identify the animal. Respond with just a brief description like 'black cat', 'golden retriever', 'tabby cat', 'white dog', etc. Focus on the main animal in the photo. If no clear animal is visible, respond with 'animal'."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                    "detail": "low"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 50,
                "temperature": 0.3
            }
            
            # Make API request
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(api_url, data=data, headers=headers)
            
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode('utf-8'))
                
            if 'choices' in result and len(result['choices']) > 0:
                animal_description = result['choices'][0]['message']['content'].strip().lower()
                self.logger.info(f"Animal identified: {animal_description}")
                return animal_description
            else:
                self.logger.warning("No animal identification in API response")
                
        except Exception as e:
            self.logger.warning(f"Animal identification failed: {e}")
            
        return None
    
    def start_batch_processor(self):
        """Start the background batch processing thread"""
        if self.batch_processor_thread and self.batch_processor_thread.is_alive():
            return
            
        self.batch_processor_thread = threading.Thread(target=self._batch_processor_worker, daemon=True)
        self.batch_processor_thread.start()
        self.logger.info("Batch processor thread started")
    
    def _batch_processor_worker(self):
        """Background worker that processes detection batches"""
        while self.running:
            try:
                # Wait for detection or timeout
                detection = self.detection_queue.get(timeout=1.0)
                if detection is None:  # Shutdown signal
                    break
                    
                chip_id = detection['chip_id']
                
                # Add to pending batch
                self.pending_batches[chip_id].append(detection)
                
                # Cancel existing timer for this chip if any
                if chip_id in self.batch_timers:
                    self.batch_timers[chip_id].cancel()
                
                # Start new timer for batch processing
                delay = self.config['batch_delay_minutes'] * 60
                timer = threading.Timer(delay, self._process_batch, args=[chip_id])
                timer.start()
                self.batch_timers[chip_id] = timer
                
                self.logger.info(f"Detection queued for {chip_id}, batch will process in {self.config['batch_delay_minutes']} minute(s)")
                
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Batch processor error: {e}")
    
    def _process_batch(self, chip_id):
        """Process accumulated detections for a chip ID"""
        try:
            batch = self.pending_batches[chip_id].copy()
            self.pending_batches[chip_id].clear()
            
            if not batch:
                return
                
            self.logger.info(f"Processing batch of {len(batch)} detections for chip {chip_id}")
            
            # Find the best photo using AI
            best_detection = self._select_best_detection(batch)
            
            if best_detection:
                # Calculate encounter statistics
                stats = self._calculate_encounter_stats(chip_id)
                
                # Send the final notification
                self._send_batch_notification(best_detection, stats)
                
                # Update encounter history
                now = datetime.now()
                self.encounter_history[chip_id].append(now)
                
                # Clean old history (keep only recent encounters)
                cutoff = now - timedelta(days=7)  # Keep 7 days of history
                while (self.encounter_history[chip_id] and 
                       self.encounter_history[chip_id][0] < cutoff):
                    self.encounter_history[chip_id].popleft()
                    
        except Exception as e:
            self.logger.error(f"Batch processing failed for {chip_id}: {e}")
    
    def _select_best_detection(self, batch):
        """Select the best detection from a batch using AI analysis"""
        if not batch:
            return None
            
        if len(batch) == 1:
            # Only one detection, try to identify the animal
            detection = batch[0]
            if detection['photo_paths']:
                animal_description = self.identify_animal(detection['photo_paths'][0])
                detection['animal_description'] = animal_description
            return detection
        
        # Multiple detections - try AI analysis on each until we get a good result
        best_detection = None
        best_score = -1
        
        for detection in batch:
            if not detection['photo_paths']:
                continue
                
            try:
                animal_description = self.identify_animal(detection['photo_paths'][0])
                
                # Score based on AI response quality
                score = 0
                if animal_description:
                    if animal_description != 'animal':  # Generic response
                        score = 10
                        if any(word in animal_description.lower() for word in ['cat', 'dog', 'kitten', 'puppy']):
                            score += 5
                        if any(word in animal_description.lower() for word in ['black', 'white', 'brown', 'golden', 'tabby']):
                            score += 3
                
                detection['animal_description'] = animal_description
                detection['ai_score'] = score
                
                if score > best_score:
                    best_score = score
                    best_detection = detection
                    
                # If we got a really good identification, use it
                if score >= 15:
                    break
                    
            except Exception as e:
                self.logger.warning(f"AI analysis failed for detection: {e}")
        
        # Fallback to first detection if no AI analysis worked
        if not best_detection:
            best_detection = batch[0]
            best_detection['animal_description'] = None
            
        return best_detection
    
    def _calculate_encounter_stats(self, chip_id):
        """Calculate encounter statistics for a chip ID"""
        now = datetime.now()
        window_start = now - timedelta(minutes=self.config['encounter_window_minutes'])
        
        # Count recent encounters (including current batch)
        recent_count = 1  # Current encounter
        for timestamp in self.encounter_history[chip_id]:
            if timestamp >= window_start:
                recent_count += 1
        
        # Total historical encounters
        total_count = len(self.encounter_history[chip_id]) + 1  # +1 for current
        
        return {
            'recent_encounters': recent_count,
            'total_encounters': total_count,
            'window_minutes': self.config['encounter_window_minutes']
        }
    
    def _send_batch_notification(self, detection, stats):
        """Send the final batched notification"""
        try:
            chip_id = detection['chip_id']
            photo_paths = detection['photo_paths']
            photo_links = detection['photo_links']
            animal_description = detection.get('animal_description')
            
            # Check if this is the lost pet
            is_lost_pet = self.config['lost_tag'] and chip_id == self.config['lost_tag']
            
            # Get current date and time with day name
            now = datetime.now()
            date_str = now.strftime('%A, %B %d, %Y')
            time_str = now.strftime('%H:%M')
            
            # Create enhanced message with encounter statistics
            if is_lost_pet:
                subject = "🚨 LOST PET FOUND!"
                if animal_description:
                    body = f"🚨 LOST PET DETECTED!\nAnimal: {animal_description}\nChip: {chip_id}"
                else:
                    body = f"🚨 LOST PET DETECTED!\nChip: {chip_id}"
            else:
                subject = "🐾 Pet Alert"
                if animal_description:
                    body = f"🐾 Pet detected\nAnimal: {animal_description}\nChip: {chip_id}"
                else:
                    body = f"🐾 Pet detected\nChip: {chip_id}"
            
            # Add encounter statistics
            body += f"\nDate: {date_str}\nTime: {time_str}"
            body += f"\nRecent visits: {stats['recent_encounters']} in {stats['window_minutes']} min"
            body += f"\nTotal visits: {stats['total_encounters']}"
            
            # Add photo link
            if photo_links and len(photo_links) > 0:
                body += f"\nPhoto: {photo_links[0]}"
            elif self.config['rclone_remote']:
                body += "\nPhoto: Uploaded to Google Drive"
            
            # Send notification
            is_sms_gateway = '@msg.fi.google.com' in self.config['alert_to_email']
            
            msg = MIMEText(body)
            msg['From'] = self.config['email_from']
            msg['To'] = self.config['alert_to_email']
            
            # Only add subject if not SMS gateway
            if not is_sms_gateway:
                msg['Subject'] = subject
            
            with smtplib.SMTP(self.config['smtp_host'], self.config['smtp_port']) as server:
                server.starttls()
                server.login(self.config['smtp_user'], self.config['smtp_pass'])
                server.send_message(msg)
                
            self.logger.info(f"Batched notification sent for {chip_id} (animal: {animal_description or 'unknown'}) - SMS mode: {is_sms_gateway}")
            
            # Log for daily summary
            self.log_detection(chip_id, photo_paths)
            
        except Exception as e:
            self.logger.error(f"Failed to send batched notification: {e}")
    

    def should_notify(self, tag_id):
        """Check if we should send notifications for this tag"""
        # Check if notifications are enabled for any tag OR this is the lost tag
        should_send = False
        
        if self.config['notify_on_any']:
            should_send = True
        elif self.config['lost_tag'] and tag_id == self.config['lost_tag']:
            should_send = True
            
        if not should_send:
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
            
    def send_email(self, tag_id, photo_links=None, photo_paths=None):
        """Send email notification via SMTP"""
        if not self.config['smtp_user'] or not self.config['alert_to_email']:
            return
            
        try:
            # Check if this is the lost pet
            is_lost_pet = self.config['lost_tag'] and tag_id == self.config['lost_tag']
            
            # Get current date and time with day name
            now = datetime.now()
            date_str = now.strftime('%A, %B %d, %Y')  # Monday, September 29, 2025
            time_str = now.strftime('%H:%M')
            
            # Try to identify the animal if photo is available
            animal_description = None
            if photo_paths and len(photo_paths) > 0 and self.config['animal_identification']:
                animal_description = self.identify_animal(photo_paths[0])
            
            # Create message with animal identification and full date
            if is_lost_pet:
                subject = "🚨 LOST PET FOUND!"
                if animal_description:
                    body = f"🚨 LOST PET DETECTED!\nAnimal: {animal_description}\nChip: {tag_id}\nDate: {date_str}\nTime: {time_str}"
                else:
                    body = f"🚨 LOST PET DETECTED!\nChip: {tag_id}\nDate: {date_str}\nTime: {time_str}"
            else:
                subject = "🐾 Pet Alert"
                if animal_description:
                    body = f"🐾 Pet detected\nAnimal: {animal_description}\nChip: {tag_id}\nDate: {date_str}\nTime: {time_str}"
                else:
                    body = f"🐾 Pet detected\nChip: {tag_id}\nDate: {date_str}\nTime: {time_str}"
            
            # Add specific photo link if available
            if photo_links and len(photo_links) > 0:
                # Add explicit Google Drive link as plain text
                body += f"\nPhoto: {photo_links[0]}"
            elif self.config['rclone_remote']:
                # Fallback to indicating photo was captured
                body += "\nPhoto: Uploaded to Google Drive"
                
            # Send as plain text
            msg = MIMEText(body)
            msg['From'] = self.config['email_from']
            msg['To'] = self.config['alert_to_email'] 
            msg['Subject'] = subject
            
            # Create SMTP session
            with smtplib.SMTP(self.config['smtp_host'], self.config['smtp_port']) as server:
                server.starttls()
                server.login(self.config['smtp_user'], self.config['smtp_pass'])
                server.send_message(msg)
                
            self.logger.info("Email sent successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to send email: {e}")
            
    def send_immediate_notification(self, chip_id, photo_paths, photo_links):
        """Send immediate notification when pet is first detected"""
        try:
            timestamp = datetime.now()
            time_str = timestamp.strftime('%H:%M')
            date_str = timestamp.strftime('%A, %B %d, %Y')
            
            # Create immediate notification message with full date/time info
            message = f"🐾 Pet detected!\n"
            message += f"📅 {date_str}\n"
            message += f"🕐 {time_str}\n"
            message += f"🏷️ Chip: {chip_id}\n"
            
            # Add photo link or fallback message
            if photo_links:
                message += f"📸 Photo: {photo_links[0]}\n"
            elif photo_paths:
                message += f"📸 Photo captured locally (uploading...)\n"
            else:
                message += "📸 No photo available\n"
                
            message += "\n📊 Detailed encounter report coming shortly..."
            
            # Send via configured methods
            notification_sent = False
            
            if self.config.get('alert_to_sms'):
                try:
                    self.send_sms_notification(message)
                    notification_sent = True
                except Exception as e:
                    self.logger.warning(f"SMS notification failed: {e}")
                
            if self.config.get('alert_to_email'):
                try:
                    # Check if this is SMS gateway email (no subject needed)
                    is_sms_gateway = '@msg.fi.google.com' in self.config['alert_to_email']
                    
                    if is_sms_gateway:
                        # Send without subject for SMS gateway
                        if not photo_links and photo_paths:
                            # For SMS gateway, don't attach photos - just mention it
                            sms_message = message.replace("Photo captured locally (uploading...)", "Photo captured (uploading to cloud)")
                            self.send_simple_email_no_subject(sms_message)
                        else:
                            self.send_simple_email_no_subject(message)
                    else:
                        # Regular email with subject
                        subject = f"Pet Detection Alert - {chip_id}"
                        if not photo_links and photo_paths:
                            self.send_email_with_attachment(message, subject, photo_paths[0])
                        else:
                            self.send_simple_email(message, subject)
                            
                    notification_sent = True
                except Exception as e:
                    self.logger.warning(f"Email notification failed: {e}")
                    
            if notification_sent:
                self.logger.info(f"Immediate notification sent for {chip_id}")
            else:
                self.logger.warning("No notification methods configured or all failed")
            
        except Exception as e:
            self.logger.error(f"Failed to send immediate notification: {e}")
            
    def send_email_with_attachment(self, body, subject, photo_path):
        """Send email with photo attachment when upload fails"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.config['email_from']
            msg['To'] = self.config['alert_to_email']
            msg['Subject'] = subject
            
            # Add text body
            msg.attach(MIMEText(body))
            
            # Add photo attachment
            with open(photo_path, 'rb') as f:
                img_data = f.read()
                img = MIMEImage(img_data)
                img.add_header('Content-Disposition', f'attachment; filename="{photo_path.name}"')
                msg.attach(img)
            
            # Send email
            with smtplib.SMTP(self.config['smtp_host'], self.config['smtp_port']) as server:
                server.starttls()
                server.login(self.config['smtp_user'], self.config['smtp_pass'])
                server.send_message(msg)
                
            self.logger.info(f"Email with attachment sent successfully: {photo_path.name}")
            
        except Exception as e:
            self.logger.error(f"Failed to send email with attachment: {e}")
            
    def send_simple_email(self, body, subject):
        """Send simple text email"""
        try:
            # Send as plain text
            msg = MIMEText(body)
            msg['From'] = self.config['email_from']
            msg['To'] = self.config['alert_to_email'] 
            msg['Subject'] = subject
            
            # Create SMTP session
            with smtplib.SMTP(self.config['smtp_host'], self.config['smtp_port']) as server:
                server.starttls()
                server.login(self.config['smtp_user'], self.config['smtp_pass'])
                server.send_message(msg)
                
            self.logger.info("Simple email sent successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to send simple email: {e}")
            raise
            
    def send_simple_email_no_subject(self, body):
        """Send simple text email without subject (for SMS gateways)"""
        try:
            # Send as plain text without subject
            msg = MIMEText(body)
            msg['From'] = self.config['email_from']
            msg['To'] = self.config['alert_to_email'] 
            # No Subject header for SMS gateway
            
            # Create SMTP session
            with smtplib.SMTP(self.config['smtp_host'], self.config['smtp_port']) as server:
                server.starttls()
                server.login(self.config['smtp_user'], self.config['smtp_pass'])
                server.send_message(msg)
                
            self.logger.info("SMS gateway email sent successfully (no subject)")
            
        except Exception as e:
            self.logger.error(f"Failed to send SMS gateway email: {e}")
            raise
            
    def log_detection(self, tag_id, photo_paths):
        """Log detection for daily summary"""
        try:
            from pathlib import Path
            log_file = Path(self.config['photo_dir']).parent / 'daily_detections.log'
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            with open(log_file, 'a') as f:
                photo_names = [p.name for p in photo_paths] if photo_paths else []
                f.write(f"{timestamp},{tag_id},{';'.join(photo_names)}\n")
                
        except Exception as e:
            self.logger.error(f"Failed to log detection: {e}")
            
    def send_daily_summary(self):
        """Send daily summary of all detections with thumbnails"""
        try:
            from email.mime.multipart import MIMEMultipart
            from email.mime.image import MIMEImage
            import os
            from pathlib import Path
            
            # Read daily detection log
            log_file = Path(self.config['photo_dir']).parent / 'daily_detections.log'
            if not log_file.exists():
                return
                
            today = datetime.now().strftime('%Y-%m-%d')
            detections = []
            
            with open(log_file, 'r') as f:
                for line in f:
                    if line.startswith(today):
                        parts = line.strip().split(',')
                        if len(parts) >= 3:
                            detections.append({
                                'time': parts[0],
                                'chip_id': parts[1],
                                'photos': parts[2].split(';') if parts[2] else []
                            })
            
            if not detections:
                return
                
            # Create multipart email with thumbnails
            msg = MIMEMultipart()
            msg['From'] = self.config['email_from']
            msg['To'] = 'dccollins@gmail.com'
            msg['Subject'] = f"🐾 Daily Pet Detection Summary - {today}"
            
            # Create summary text
            summary_text = f"Daily Pet Detection Report - {today}\n"
            summary_text += "=" * 50 + "\n\n"
            summary_text += f"Total Detections: {len(detections)}\n\n"
            
            for i, detection in enumerate(detections, 1):
                summary_text += f"{i}. Time: {detection['time']}\n"
                summary_text += f"   Chip ID: {detection['chip_id']}\n"
                if detection['photos']:
                    summary_text += f"   Photos: {len(detection['photos'])} captured\n"
                summary_text += "\n"
                
            msg.attach(MIMEText(summary_text))
            
            # Attach thumbnail images
            photo_dir = Path(self.config['photo_dir'])
            for detection in detections:
                for photo_name in detection['photos']:
                    photo_path = photo_dir / photo_name
                    if photo_path.exists():
                        try:
                            # Create thumbnail and attach
                            with open(photo_path, 'rb') as f:
                                img_data = f.read()
                                img = MIMEImage(img_data)
                                img.add_header('Content-Disposition', f'attachment; filename={photo_name}')
                                msg.attach(img)
                        except Exception as e:
                            self.logger.warning(f"Failed to attach {photo_name}: {e}")
            
            # Send email
            with smtplib.SMTP(self.config['smtp_host'], self.config['smtp_port']) as server:
                server.starttls()
                server.login(self.config['smtp_user'], self.config['smtp_pass'])
                server.send_message(msg)
                
            self.logger.info(f"Daily summary sent with {len(detections)} detections")
            
            # Clear the log file for next day
            log_file.unlink()
            
        except Exception as e:
            self.logger.error(f"Failed to send daily summary: {e}")
            
    def process_tag(self, tag_id):
        """Process a detected tag - send immediate notification then queue for detailed batching"""
        self.logger.info(f"Tag detected: {tag_id}")
        
        photo_paths = []
        photo_links = []
        
        # Always capture photos for analysis
        photo_paths = self.capture_photo(tag_id)
        
        # Upload photos to get links (with local backup on failure)
        if photo_paths:
            photo_links = self.upload_photos(photo_paths)
            
        # Send immediate notification if this is first contact for this chip
        notification_key = f"{tag_id}_{datetime.now().strftime('%Y%m%d')}"
        if notification_key not in self.immediate_notifications_sent:
            self.send_immediate_notification(tag_id, photo_paths, photo_links)
            self.immediate_notifications_sent.add(notification_key)
            
        # Queue detection for detailed batching
        detection = {
            'chip_id': tag_id,
            'timestamp': datetime.now(),
            'photo_paths': photo_paths,
            'photo_links': photo_links
        }
        
        self.detection_queue.put(detection)
        self.logger.info(f"Detection queued for batching: {tag_id}")
            
    def simulate_tag_detection(self):
        """Simulate tag detection for testing"""
        import random
        
        # Simulate different chip IDs
        test_tags = [
            "900263003496836",  # Your actual RBC-A04 chip (will trigger notifications)
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
        
        # Start batch processing and retry system
        self.start_batch_processor()
        self.start_retry_processor()
        
        self.logger.info("System initialized successfully, starting main loop...")
        
        self.running = True
        last_daily_check = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        try:
            if simulate_mode:
                # Run simulation
                self.simulate_tag_detection()
            else:
                # Run real polling
                poll_command = self.create_poll_command()
                
                while self.running:
                    try:
                        # Check for daily summary (send at 11:59 PM)
                        now = datetime.now()
                        if (now.hour == 23 and now.minute == 59 and 
                            now.date() > last_daily_check.date()):
                            self.send_daily_summary()
                            last_daily_check = now
                            
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
        
        # Stop batch processor and retry processor
        if self.batch_processor_thread and self.batch_processor_thread.is_alive():
            self.detection_queue.put(None)  # Shutdown signal
            self.batch_processor_thread.join(timeout=2)
            
        if self.retry_thread and self.retry_thread.is_alive():
            self.retry_thread.join(timeout=2)
            
        # Cancel any pending timers
        for timer in self.batch_timers.values():
            timer.cancel()
        self.batch_timers.clear()
        
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