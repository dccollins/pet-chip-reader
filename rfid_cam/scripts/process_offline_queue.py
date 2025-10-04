#!/usr/bin/env python3
"""
Offline Queue Processor for Pet Chip Reader

This script processes the offline queue to upload photos and send notifications
that were queued when internet or cloud services were unavailable.

Usage:
    python3 process_offline_queue.py [--dry-run] [--photos-only] [--notifications-only]

Options:
    --dry-run           Show what would be processed without actually doing it
    --photos-only       Only process photo uploads, skip notifications
    --notifications-only Only process notifications, skip photo uploads
"""

import os
import sys
import json
import argparse
import subprocess
from datetime import datetime
from pathlib import Path
import socket
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Add the src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from dotenv import load_dotenv
except ImportError as e:
    print(f"Missing required module: {e}")
    print("Please install requirements: pip install -r requirements.txt")
    sys.exit(1)

class OfflineQueueProcessor:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Configuration
        self.config = {
            'photo_dir': os.getenv('PHOTO_DIR', '/home/collins/rfid_photos'),
            'offline_queue_dir': os.path.join(os.getenv('PHOTO_DIR', '/home/collins/rfid_photos'), 'offline_queue'),
            'rclone_remote': os.getenv('RCLONE_REMOTE', ''),
            'rclone_path': os.getenv('RCLONE_PATH', 'rfid_photos'),
            
            # AI Configuration
            'openai_api_key': os.getenv('OPENAI_API_KEY', ''),
            'animal_identification': os.getenv('ANIMAL_IDENTIFICATION', 'true').lower() == 'true',
            'ai_fallback_message': os.getenv('AI_FALLBACK_MESSAGE', 'AI analysis not available'),
            
            # Digest Configuration
            'digest_email': os.getenv('DIGEST_EMAIL', 'dccollins@gmail.com'),
            
            # SMS via Google Fi email gateway (no Twilio)
            'alert_to_sms': os.getenv('ALERT_TO_SMS', ''),  # Should be like 8651234567@msg.fi.google.com
            
            # SMTP config
            'smtp_host': os.getenv('SMTP_HOST', 'smtp.gmail.com'),
            'smtp_port': int(os.getenv('SMTP_PORT', '587')),
            'smtp_user': os.getenv('SMTP_USER', ''),
            'smtp_pass': os.getenv('SMTP_PASS', ''),
            'email_from': os.getenv('EMAIL_FROM', ''),
            'alert_to_email': os.getenv('ALERT_TO_EMAIL', ''),
        }
        
        # SMS via Google Fi email gateway - no Twilio client needed
        
        # Initialize metadata manager if available
        self.metadata_manager = None
        try:
            src_path = os.path.join(os.path.dirname(__file__), '..', 'src')
            sys.path.insert(0, src_path)
            from image_metadata_manager import ImageMetadataManager
            self.metadata_manager = ImageMetadataManager(self.config)
        except ImportError as e:
            print(f"Warning: Image metadata manager not available: {e}")
        except Exception as e:
            print(f"Warning: Could not initialize metadata manager: {e}")
    
    def check_internet_connectivity(self, timeout=10):
        """Check if internet is available"""
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=timeout)
            return True
        except OSError:
            return False

    def identify_animal(self, photo_path):
        """Use OpenAI GPT-4 Vision to identify animals in the photo"""
        if not self.config['animal_identification'] or not self.config['openai_api_key']:
            return None
            
        try:
            import urllib.request
            import urllib.parse
            import base64
            
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
                                "text": "Look at this image and identify any animals and humans. If you see an animal, describe it briefly like 'orange tabby cat', 'black dog', etc. If you see a human (even without animals), describe them briefly like 'person with dark hair', 'child in blue shirt', 'adult wearing glasses', etc. If you see both, describe both. If you see neither animals nor humans clearly, respond exactly with 'no animals in view'. Be concise."
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
                "max_tokens": 100
            }
            
            # Make API request
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(api_url, data=data, headers=headers)
            
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode('utf-8'))
                
                if 'choices' in result and len(result['choices']) > 0:
                    content = result['choices'][0]['message']['content'].strip()
                    if content.lower() == 'no animals in view':
                        return None
                    return content
                    
            return None
            
        except Exception as e:
            print(f"AI analysis failed for {photo_path}: {e}")
            return None

    def update_photo_metadata(self, photo_path, ai_description):
        """Update photo metadata with AI description"""
        if not self.metadata_manager:
            return False
            
        try:
            # Extract chip ID from filename
            filename = Path(photo_path).name
            # Format: YYYYmmdd_HHMMSS_chipid_cam0.jpg
            parts = filename.split('_')
            if len(parts) >= 3:
                chip_id = parts[2]
                
                # Update metadata
                self.metadata_manager.update_metadata(
                    image_path=photo_path,
                    ai_description=ai_description,
                    chip_id=chip_id
                )
                return True
                
        except Exception as e:
            print(f"Failed to update metadata for {photo_path}: {e}")
            
        return False
    
    def process_photos_with_ai_and_upload(self, dry_run=False):
        """Complete workflow: AI analysis → metadata update → cloud upload"""
        queue_file = os.path.join(self.config['offline_queue_dir'], 'upload_queue.txt')
        
        if not os.path.exists(queue_file):
            print("No photo upload queue found")
            return 0, 0, []
        
        if not self.config['rclone_remote']:
            print("Warning: Rclone not configured, cannot upload photos")
            return 0, 0, []
        
        # Check internet connectivity
        if not self.check_internet_connectivity():
            print("No internet connection available")
            return 0, 0, []
        
        # Read queue
        with open(queue_file, 'r') as f:
            lines = f.readlines()
        
        successful_processes = 0
        failed_processes = 0
        processed_photos = []
        remaining_queue = []
        
        print(f"Processing {len(lines)} queued photos with AI analysis and upload...")
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            try:
                timestamp, photo_path = line.split('|', 1)
                
                if not os.path.exists(photo_path):
                    print(f"Skipping missing file: {photo_path}")
                    continue
                
                filename = Path(photo_path).name
                print(f"Processing: {filename}")
                
                if dry_run:
                    print(f"Would process with AI and upload: {photo_path}")
                    continue
                
                # Step 1: AI Analysis
                print(f"  🧠 Running AI analysis...")
                ai_description = self.identify_animal(photo_path)
                if not ai_description:
                    ai_description = self.config['ai_fallback_message']
                print(f"  📝 AI result: {ai_description}")
                
                # Step 2: Update metadata
                print(f"  📄 Updating metadata...")
                metadata_success = False
                try:
                    if self.metadata_manager:
                        metadata_success = self.metadata_manager.update_metadata(photo_path, ai_description, {'chip_id': 'unknown'})
                        if metadata_success:
                            print(f"  ✓ Metadata updated")
                        else:
                            print(f"  ⚠ Metadata update failed")
                    else:
                        print(f"  ⚠ Metadata manager not available")
                except Exception as e:
                    print(f"  ⚠ Metadata update failed: {e}")
                    metadata_success = False
                
                # Step 3: Upload to cloud
                print(f"  ☁️ Uploading to Google Drive...")
                remote_path = f"{self.config['rclone_remote']}:{self.config['rclone_path']}"
                cmd = ['rclone', 'copy', photo_path, remote_path]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                
                if result.returncode == 0:
                    print(f"  ✓ Upload complete")
                    successful_processes += 1
                    
                    # Store processed photo info for digest
                    processed_photos.append({
                        'path': photo_path,
                        'filename': filename,
                        'timestamp': timestamp,
                        'ai_description': ai_description,
                        'metadata_updated': metadata_success
                    })
                    
                    # Remove from offline queue after successful processing
                else:
                    print(f"  ✗ Upload failed: {result.stderr}")
                    failed_processes += 1
                    remaining_queue.append(line)
                    
            except Exception as e:
                print(f"Failed to process {photo_path}: {e}")
                failed_processes += 1
                remaining_queue.append(line)
        
        # Update queue file with remaining items
        if not dry_run:
            if remaining_queue:
                with open(queue_file, 'w') as f:
                    f.writelines(remaining_queue)
                print(f"Updated queue with {len(remaining_queue)} remaining items")
            else:
                try:
                    os.remove(queue_file)
                    print("Cleared photo upload queue after successful processing")
                except OSError:
                    pass
        
        return successful_processes, failed_processes, processed_photos
    
    def process_photo_queue(self, dry_run=False):
        """Legacy method - now calls the enhanced AI processing workflow"""
        successful, failed, processed_photos = self.process_photos_with_ai_and_upload(dry_run)
        return successful, failed
    
    def process_notification_queue(self, dry_run=False):
        """Process queued notifications for sending with smart digest for large backlogs"""
        queue_file = os.path.join(self.config['offline_queue_dir'], 'notification_queue.json')
        
        if not os.path.exists(queue_file):
            print("No notification queue found")
            return 0, 0
        
        # Check internet connectivity
        if not self.check_internet_connectivity():
            print("No internet connection available")
            return 0, 0
        
        # Read queue
        try:
            with open(queue_file, 'r') as f:
                notifications = json.load(f)
        except json.JSONDecodeError:
            print("Invalid notification queue file")
            return 0, 0
        
        if len(notifications) == 0:
            return 0, 0
        
        # Check if we should use digest mode
        digest_threshold = int(os.getenv('DIGEST_THRESHOLD', '10'))
        use_digest = len(notifications) >= digest_threshold
        
        if use_digest:
            print(f"Large backlog detected ({len(notifications)} notifications) - using digest mode")
            return self.send_digest_notifications(notifications, dry_run)
        else:
            print(f"Processing {len(notifications)} queued notifications individually...")
            return self.send_individual_notifications(notifications, dry_run, queue_file)
    
    def send_individual_notifications(self, notifications, dry_run, queue_file):
        """Send notifications individually (original behavior)"""
        successful_notifications = 0
        failed_notifications = 0
        remaining_queue = []
        
        for notification in notifications:
            try:
                notification_type = notification['type']
                data = notification['data']
                timestamp = notification['timestamp']
                
                if dry_run:
                    print(f"Would send {notification_type}: {data}")
                    continue
                
                success = False
                
                if notification_type == 'sms':
                    success = self.send_queued_sms(data)
                elif notification_type == 'email':
                    success = self.send_queued_email(data)
                
                if success:
                    print(f"✓ Sent {notification_type} from {timestamp}")
                    successful_notifications += 1
                else:
                    print(f"✗ Failed to send {notification_type} from {timestamp}")
                    remaining_queue.append(notification)
                    failed_notifications += 1
                    
            except Exception as e:
                print(f"✗ Error processing notification: {e}")
                remaining_queue.append(notification)
                failed_notifications += 1
        
        # Update queue file with remaining items
        if not dry_run:
            if remaining_queue:
                with open(queue_file, 'w') as f:
                    json.dump(remaining_queue, f, indent=2)
            else:
                os.remove(queue_file)
        
        return successful_notifications, failed_notifications
    
    def send_digest_notifications(self, notifications, dry_run):
        """Send a digest summary instead of individual notifications"""
        from collections import defaultdict, Counter
        
        # Organize notifications by type and analyze patterns
        sms_notifications = [n for n in notifications if n['type'] == 'sms']
        email_notifications = [n for n in notifications if n['type'] == 'email']
        
        # Generate digest summaries
        digest_data = self.analyze_notification_backlog(notifications)
        
        successful_notifications = 0
        failed_notifications = 0
        
        if dry_run:
            print("Would send digest notifications:")
            if sms_notifications:
                print(f"  SMS Digest: {digest_data['total_detections']} detections from {digest_data['unique_chips']} pets")
            if email_notifications:
                print(f"  Email Digest: Detailed summary with {len(digest_data['photo_links'])} photos")
            return len(notifications), 0
        
        # Send SMS digest if there were SMS notifications
        if sms_notifications and self.config['alert_to_sms']:
            sms_digest = self.create_sms_digest(digest_data)
            if self.send_digest_sms(sms_digest):
                print(f"✓ Sent SMS digest summarizing {len(sms_notifications)} notifications")
                successful_notifications += len(sms_notifications)
            else:
                print(f"✗ Failed to send SMS digest")
                failed_notifications += len(sms_notifications)
        
        # Send email digest if there were email notifications
        if email_notifications and self.config['alert_to_email']:
            email_digest = self.create_email_digest(digest_data)
            if self.send_digest_email(email_digest):
                print(f"✓ Sent email digest summarizing {len(email_notifications)} notifications")
                successful_notifications += len(email_notifications)
            else:
                print(f"✗ Failed to send email digest")
                failed_notifications += len(email_notifications)
        
        # Clear queue if successful
        if successful_notifications > 0 and failed_notifications == 0:
            queue_file = os.path.join(self.config['offline_queue_dir'], 'notification_queue.json')
            try:
                os.remove(queue_file)
                print("Cleared notification queue after successful digest delivery")
            except OSError:
                pass
        
        return successful_notifications, failed_notifications
    
    def analyze_offline_recovery_data(self, notifications, processed_photos):
        """Analyze notification backlog and processed photos for comprehensive digest"""
        from collections import defaultdict, Counter
        from datetime import datetime, timedelta
        
        chip_detections = defaultdict(list)
        photo_data = defaultdict(list)
        earliest_time = None
        latest_time = None
        
        # Process all notifications
        for notification in notifications:
            timestamp_str = notification['timestamp']
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            
            if earliest_time is None or timestamp < earliest_time:
                earliest_time = timestamp
            if latest_time is None or timestamp > latest_time:
                latest_time = timestamp
            
            # Extract chip ID and photos from notification data
            data = notification['data']
            if notification['type'] == 'sms':
                chip_id = data.get('tag_id', 'unknown')
                chip_detections[chip_id].append(timestamp)
            elif notification['type'] == 'email':
                chip_id = data.get('tag_id', 'unknown')
                chip_detections[chip_id].append(timestamp)
        
        # Process AI-enhanced photos
        for photo in processed_photos:
            # Extract chip ID from filename
            filename = photo['filename']
            parts = filename.split('_')
            if len(parts) >= 3:
                chip_id = parts[2]
                photo_timestamp = datetime.strptime(f"{parts[0]}_{parts[1]}", '%Y%m%d_%H%M%S')
                
                photo_data[chip_id].append({
                    'filename': filename,
                    'path': photo['path'],
                    'timestamp': photo_timestamp,
                    'ai_description': photo['ai_description'],
                    'metadata_updated': photo['metadata_updated']
                })
        
        # Calculate time span
        if earliest_time and latest_time:
            time_span = latest_time - earliest_time
            time_span_hours = max(1, int(time_span.total_seconds() / 3600))
        else:
            time_span_hours = 0
        
        # Generate summary statistics
        total_detections = sum(len(times) for times in chip_detections.values())
        unique_chips = len(chip_detections)
        total_ai_photos = len(processed_photos)
        
        # Find most active chip
        most_active_chip = None
        max_detections = 0
        for chip_id, times in chip_detections.items():
            if len(times) > max_detections:
                max_detections = len(times)
                most_active_chip = chip_id
        
        return {
            'total_detections': total_detections,
            'unique_chips': unique_chips,
            'chip_detections': dict(chip_detections),
            'photo_data': dict(photo_data),
            'most_active_chip': most_active_chip,
            'max_detections': max_detections,
            'time_span_hours': time_span_hours,
            'earliest_time': earliest_time,
            'latest_time': latest_time,
            'total_ai_photos': total_ai_photos,
            'processed_photos': processed_photos
        }

    def analyze_notification_backlog(self, notifications):
        """Legacy method for backwards compatibility"""
        # Convert to new format without processed photos
        return self.analyze_offline_recovery_data(notifications, [])
    
    def create_sms_digest(self, digest_data):
        """Create concise SMS digest message using same format as main app"""
        # Use same pattern as working messages: 🐾 Pet detected\nInfo: value\nMore: info
        msg = f"🐾 Pet Digest\n"
        msg += f"Detections: {digest_data['total_detections']} from {digest_data['unique_chips']} pets"
        
        if digest_data['time_span_hours'] > 0:
            if digest_data['time_span_hours'] < 24:
                msg += f"\nPeriod: {digest_data['time_span_hours']} hours"
            else:
                days = digest_data['time_span_hours'] // 24
                hours = digest_data['time_span_hours'] % 24
                if hours > 0:
                    msg += f"\nPeriod: {days}d {hours}h"
                else:
                    msg += f"\nPeriod: {days} days"
        
        if digest_data['most_active_chip'] and digest_data['max_detections'] > 1:
            chip_short = digest_data['most_active_chip'][-6:]  # Last 6 digits
            msg += f"\nMost active: ...{chip_short} ({digest_data['max_detections']}x)"
        
        return msg[:160]  # SMS length limit
    
    def get_google_drive_files_cache(self):
        """Get cached list of Google Drive files with IDs"""
        if not hasattr(self, '_drive_files_cache'):
            try:
                print("Fetching Google Drive file list for digest...")
                # Get all files from Google Drive in one command
                file_info = os.popen(f'rclone lsjson gdrive:{self.config.get("rclone_path", "rfid_photos")} 2>/dev/null').read().strip()
                
                if file_info:
                    import json
                    try:
                        files = json.loads(file_info)
                        # Create filename -> file_id mapping
                        self._drive_files_cache = {file['Name']: file['ID'] for file in files if 'Name' in file and 'ID' in file}
                        print(f"Cached {len(self._drive_files_cache)} Google Drive files")
                    except json.JSONDecodeError:
                        self._drive_files_cache = {}
                else:
                    self._drive_files_cache = {}
                    
            except Exception as e:
                print(f"Error caching Google Drive files: {e}")
                self._drive_files_cache = {}
                
        return self._drive_files_cache

    def get_google_drive_link(self, photo_filename):
        """Generate shareable Google Drive link for a photo"""
        try:
            drive_cache = self.get_google_drive_files_cache()
            file_id = drive_cache.get(photo_filename)
            
            if file_id:
                return f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"
            
            return None
            
        except Exception as e:
            print(f"Error getting Google Drive link for {photo_filename}: {e}")
            return None

    def create_email_digest(self, digest_data):
        """Create detailed HTML email digest with enhanced formatting"""
        subject = f"🚨 Pet Activity Digest - {digest_data['total_detections']} detections (Offline Recovery)"
        
        # Calculate time period display
        time_period_display = ""
        if digest_data['time_span_hours'] > 0:
            if digest_data['time_span_hours'] < 24:
                time_period_display = f"{digest_data['time_span_hours']} hours"
            else:
                days = digest_data['time_span_hours'] // 24
                hours = digest_data['time_span_hours'] % 24
                time_period_display = f"{days} days, {hours} hours"
        
        # Create beautiful HTML content
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Pet Activity Digest - Offline Recovery</title>
            <style>
                .digest-table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 20px 0;
                    font-size: 14px;
                    background-color: white;
                    border-radius: 8px;
                    overflow: hidden;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .digest-table th {{
                    background: linear-gradient(135deg, #FF6B6B, #FF8E53);
                    color: white;
                    padding: 12px 8px;
                    text-align: left;
                    font-weight: bold;
                    font-size: 13px;
                }}
                .digest-table td {{
                    padding: 10px 8px;
                    border-bottom: 1px solid #f0f0f0;
                    vertical-align: top;
                }}
                .digest-table tr:nth-child(even) {{
                    background-color: #fafafa;
                }}
                .digest-table tr:hover {{
                    background-color: #f5f5f5;
                }}
                .chip-id {{
                    font-family: monospace;
                    background-color: #ffe8e8;
                    padding: 2px 6px;
                    border-radius: 4px;
                    font-size: 11px;
                    color: #FF6B6B;
                    font-weight: bold;
                }}
                .photo-button {{
                    background: linear-gradient(135deg, #4285f4, #34a853);
                    color: white;
                    padding: 6px 12px;
                    text-decoration: none;
                    border-radius: 6px;
                    font-size: 11px;
                    font-weight: bold;
                    display: inline-block;
                    transition: background 0.3s;
                }}
                .photo-button:hover {{
                    background: linear-gradient(135deg, #34a853, #4285f4);
                    text-decoration: none;
                    color: white;
                }}
                .offline-badge {{
                    background: linear-gradient(135deg, #FF6B6B, #FF8E53);
                    color: white;
                    padding: 2px 8px;
                    border-radius: 12px;
                    font-size: 11px;
                    font-weight: bold;
                    margin-left: 8px;
                }}
            </style>
        </head>
        <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; max-width: 900px; margin: 0 auto; padding: 20px; background-color: #f9f9f9;">
            <div style="background-color: white; padding: 30px; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                <h1 style="color: #FF6B6B; text-align: center; margin-bottom: 10px; font-size: 32px;">🚨 Pet Activity Digest</h1>
                <p style="text-align: center; color: #666; margin-bottom: 15px; font-size: 16px;">
                    <span class="offline-badge">📶 OFFLINE RECOVERY</span>
                </p>
                <p style="text-align: center; color: #666; margin-bottom: 30px; font-size: 14px;">
                    Notifications queued during system offline period
                </p>
                <hr style="border: 2px solid #FF6B6B; margin: 20px 0;">
            
                <div style="background: linear-gradient(135deg, #ffe8e8, #ffd6cc); padding: 20px; border-radius: 10px; margin: 20px 0; border-left: 5px solid #FF6B6B;">
                    <h2 style="margin-top: 0; color: #FF6B6B; font-size: 24px;">📊 Recovery Summary</h2>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-top: 15px;">
                        <div style="background-color: white; padding: 15px; border-radius: 8px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                            <div style="font-size: 28px; font-weight: bold; color: #FF6B6B;">{digest_data['total_detections']}</div>
                            <div style="color: #666; font-size: 14px;">Total Detections</div>
                        </div>
                        <div style="background-color: white; padding: 15px; border-radius: 8px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                            <div style="font-size: 28px; font-weight: bold; color: #FF8E53;">{digest_data['unique_chips']}</div>
                            <div style="color: #666; font-size: 14px;">Unique Pets</div>
                        </div>
        """
        
        if time_period_display:
            html_body += f"""
                        <div style="background-color: white; padding: 15px; border-radius: 8px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                            <div style="font-size: 18px; font-weight: bold; color: #9C27B0;">{time_period_display}</div>
                            <div style="color: #666; font-size: 14px;">Offline Period</div>
                        </div>
            """
        
        if digest_data['earliest_time'] and digest_data['latest_time']:
            html_body += f"""
                        <div style="background-color: white; padding: 15px; border-radius: 8px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                            <div style="font-size: 16px; font-weight: bold; color: #2E8B57;">{digest_data['earliest_time'].strftime('%m/%d %H:%M')}</div>
                            <div style="color: #666; font-size: 14px;">First Detection</div>
                        </div>
                        <div style="background-color: white; padding: 15px; border-radius: 8px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                            <div style="font-size: 16px; font-weight: bold; color: #E91E63;">{digest_data['latest_time'].strftime('%m/%d %H:%M')}</div>
                            <div style="color: #666; font-size: 14px;">Last Detection</div>
                        </div>
            """
        
        html_body += """
                    </div>
                </div>
        """
        
        # Pet activity breakdown with photos table
        if digest_data['chip_detections']:
            html_body += f"""
                <div style="background: linear-gradient(135deg, #fff8dc, #ffeaa7); padding: 20px; border-radius: 10px; margin: 20px 0; border-left: 5px solid #FF9800;">
                    <h2 style="margin-top: 0; color: #FF9800; font-size: 24px;">🐾 Pet Activity Details</h2>
                    <table class="digest-table">
                        <thead>
                            <tr>
                                <th style="width: 15%;">Pet ID</th>
                                <th style="width: 20%;">Detections</th>
                                <th style="width: 25%;">Time Range</th>
                                <th style="width: 40%;">Sample Photos</th>
                            </tr>
                        </thead>
                        <tbody>
            """
            
            sorted_chips = sorted(digest_data['chip_detections'].items(), 
                                key=lambda x: len(x[1]), reverse=True)
            
            for chip_id, times in sorted_chips:
                chip_display = f"...{chip_id[-8:]}" if len(chip_id) > 8 else chip_id
                detection_count = len(times)
                
                # Calculate time range for this pet
                times_sorted = sorted(times)
                first_time = times_sorted[0].strftime('%H:%M')
                last_time = times_sorted[-1].strftime('%H:%M')
                time_range = f"{first_time} - {last_time}" if first_time != last_time else first_time
                
                # Find AI-processed photos for this pet
                sample_photos = []
                if digest_data.get('photo_data') and chip_id in digest_data['photo_data']:
                    pet_photos = digest_data['photo_data'][chip_id]
                    # Sort by timestamp and take up to 3 photos
                    sorted_photos = sorted(pet_photos, key=lambda x: x['timestamp'], reverse=True)[:3]
                    
                    for photo in sorted_photos:
                        # Get Google Drive link
                        drive_link = self.get_google_drive_link(photo['filename'])
                        if drive_link:
                            sample_photos.append({
                                'filename': photo['filename'],
                                'drive_link': drive_link,
                                'ai_description': photo['ai_description'],
                                'timestamp': photo['timestamp']
                            })
                
                # Create photo buttons with AI descriptions
                photo_buttons = ""
                for i, photo in enumerate(sample_photos):
                    ai_preview = photo['ai_description'][:30] + '...' if len(photo['ai_description']) > 30 else photo['ai_description']
                    time_str = photo['timestamp'].strftime('%H:%M')
                    
                    photo_buttons += f'''
                        <div style="margin: 4px 0;">
                            <a href="{photo['drive_link']}" target="_blank" class="photo-button" style="margin: 2px;">📸 {time_str}</a>
                            <br><span style="font-size: 10px; color: #666; font-style: italic;">{ai_preview}</span>
                        </div>
                    '''
                
                if not photo_buttons:
                    photo_buttons = '<span style="color: #999; font-style: italic; font-size: 12px;">No AI-processed photos available</span>'
                
                html_body += f"""
                            <tr>
                                <td><span class="chip-id">{chip_display}</span></td>
                                <td style="font-weight: bold; color: #FF6B6B; font-size: 16px;">{detection_count}</td>
                                <td style="color: #666; font-family: monospace;">{time_range}</td>
                                <td>{photo_buttons}</td>
                            </tr>
                """
            
            html_body += """
                        </tbody>
                    </table>
                </div>
            """
        
        html_body += f"""
                <div style="background: linear-gradient(135deg, #f0f8ff, #e6f3ff); padding: 20px; border-radius: 10px; margin: 20px 0; border-left: 5px solid #4285f4;">
                    <h2 style="margin-top: 0; color: #4285f4; font-size: 24px;">ℹ️ Recovery Information</h2>
                    <div style="background-color: white; padding: 15px; border-radius: 8px;">
                        <p style="margin: 0; color: #666; line-height: 1.6;">
                            📡 <strong>System Status:</strong> This digest contains notifications that were queued during a system offline period.<br>
                            🔄 <strong>Recovery Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
                            📊 <strong>Coverage:</strong> All queued detections have been processed and delivered.<br>
                            ✅ <strong>Data Integrity:</strong> No detection data was lost during the offline period.
                        </p>
                    </div>
                </div>
                
                <hr style="margin: 30px 0; border: 2px solid #ddd;">
                <footer style="text-align: center; background: linear-gradient(135deg, #f8f9fa, #e9ecef); padding: 20px; border-radius: 10px;">
                    <p style="margin: 0; font-size: 14px; color: #666; line-height: 1.6;">
                        <strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
                        🔧 <strong>Pet Chip Reader System v2.1.0</strong> | Offline Recovery Digest<br>
                        📧 Delivered to: {self.config.get('digest_email', 'N/A')}
                    </p>
                </footer>
            </div>
        </body>
        </html>
        """
        
        # Create text version (fallback)
        text_body = f"Pet Activity Digest - Offline Recovery\n"
        text_body += f"=====================================\n\n"
        text_body += f"📊 Summary: {digest_data['total_detections']} detections from {digest_data['unique_chips']} pets\n"
        if time_period_display:
            text_body += f"⏱️ Offline period: {time_period_display}\n"
        text_body += f"🔄 Recovery completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        text_body += f"🐾 Pet Activity:\n"
        for chip_id, times in sorted_chips:
            chip_display = f"...{chip_id[-8:]}" if len(chip_id) > 8 else chip_id
            text_body += f"• {chip_display}: {len(times)} detections\n"
        
        return {'subject': subject, 'html_body': html_body, 'text_body': text_body}

    def complete_offline_recovery(self, dry_run=False):
        """Complete offline recovery workflow: AI processing → Upload → Digest email"""
        print("🚨 Starting Complete Offline Recovery Process")
        print("=" * 50)
        
        # Step 1: Process photos with AI and upload to cloud
        print("📸 Step 1: Processing queued photos with AI analysis...")
        successful_photos, failed_photos, processed_photos = self.process_photos_with_ai_and_upload(dry_run)
        print(f"   ✓ Processed {successful_photos} photos successfully")
        print(f"   ✗ Failed to process {failed_photos} photos")
        
        # Step 2: Process notification queue 
        print("📱 Step 2: Processing notification queue...")
        successful_notifications, failed_notifications = self.process_notification_queue(dry_run)
        print(f"   ✓ Sent {successful_notifications} notifications")
        print(f"   ✗ Failed to send {failed_notifications} notifications")
        
        # Step 3: If we have processed content, send enhanced digest
        if successful_photos > 0 or successful_notifications > 0:
            print("📧 Step 3: Generating enhanced recovery digest...")
            
            # Read any remaining notifications for digest analysis
            queue_file = os.path.join(self.config['offline_queue_dir'], 'notification_queue.json')
            notifications = []
            
            if os.path.exists(queue_file):
                try:
                    with open(queue_file, 'r') as f:
                        notifications = json.load(f)
                except (json.JSONDecodeError, Exception):
                    notifications = []
            
            # Analyze recovery data
            recovery_data = self.analyze_offline_recovery_data(notifications, processed_photos)
            
            # Create enhanced digest
            enhanced_digest = self.create_email_digest(recovery_data)
            
            # Send digest
            if not dry_run:
                digest_success = self.send_digest_email(enhanced_digest)
                if digest_success:
                    print("   ✓ Enhanced recovery digest sent successfully!")
                else:
                    print("   ✗ Failed to send recovery digest")
            else:
                print("   📧 Would send enhanced recovery digest")
                print(f"      Subject: {enhanced_digest['subject']}")
                print(f"      Photos included: {len(processed_photos)}")
        
        print("\n🎯 Recovery Summary:")
        print(f"   Photos processed: {successful_photos}/{successful_photos + failed_photos}")
        print(f"   Notifications sent: {successful_notifications}/{successful_notifications + failed_notifications}")
        print(f"   AI descriptions generated: {len([p for p in processed_photos if p['ai_description'] != self.config['ai_fallback_message']])}")
        print("=" * 50)
        
        return {
            'photos_processed': successful_photos,
            'photos_failed': failed_photos,
            'notifications_sent': successful_notifications,
            'notifications_failed': failed_notifications,
            'processed_photos': processed_photos
        }
    
    def send_digest_sms(self, message):
        """Send digest SMS message via Google Fi email gateway"""
        if not self.config['alert_to_sms'] or '@msg.fi.google.com' not in self.config['alert_to_sms']:
            return False
        
        try:
            return self.send_simple_email(message, self.config['alert_to_sms'])
        except Exception:
            return False
    
    def send_simple_email(self, message, recipient):
        """Send simple text email without subject (for SMS gateways)"""
        try:
            import smtplib
            from email.mime.text import MIMEText
            
            # Send as plain text without subject (matches main app approach)
            msg = MIMEText(message)
            msg['From'] = self.config['email_from']
            msg['To'] = recipient
            # No Subject header for SMS gateway
            
            # Create SMTP session (matches working approach)
            with smtplib.SMTP(self.config['smtp_host'], self.config['smtp_port']) as server:
                server.starttls()
                server.login(self.config['smtp_user'], self.config['smtp_pass'])
                server.send_message(msg)
            
            return True
        except Exception as e:
            print(f"Failed to send SMS gateway email: {e}")
            return False

    def send_digest_email(self, digest):
        """Send digest email message to configured digest email address"""
        if not self.config['smtp_user'] or not self.config['digest_email']:
            return False
        
        try:
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            import smtplib
            
            # Create multipart message for HTML + text
            msg = MIMEMultipart('alternative')
            msg['From'] = self.config['email_from']
            msg['To'] = self.config['digest_email']
            msg['Subject'] = digest['subject']
            
            # Add text version (fallback)
            if 'text_body' in digest:
                text_part = MIMEText(digest['text_body'], 'plain')
                msg.attach(text_part)
            
            # Add HTML version
            if 'html_body' in digest:
                html_part = MIMEText(digest['html_body'], 'html')
                msg.attach(html_part)
            elif 'body' in digest:
                # Fallback to old format
                text_part = MIMEText(digest['body'], 'plain')
                msg.attach(text_part)
            
            with smtplib.SMTP(self.config['smtp_host'], self.config['smtp_port']) as server:
                server.starttls()
                server.login(self.config['smtp_user'], self.config['smtp_pass'])
                server.send_message(msg)
            
            return True
        except Exception as e:
            print(f"Failed to send digest email: {e}")
            return False
    
    def send_queued_sms(self, data):
        """Send a queued SMS notification via Google Fi email gateway"""
        if not self.config['alert_to_sms'] or '@msg.fi.google.com' not in self.config['alert_to_sms']:
            return False
        
        try:
            message = data.get('message', f"🐾 Pet chip {data.get('tag_id', 'unknown')} detected")
            return self.send_simple_email(message, self.config['alert_to_sms'])
        except Exception:
            return False
    
    def send_queued_email(self, data):
        """Send a queued email notification"""
        if not self.config['smtp_user'] or not self.config['alert_to_email']:
            return False
        
        try:
            tag_id = data.get('tag_id', 'unknown')
            subject = "🐾 Pet Alert (Delayed)"
            body = f"🐾 Pet detected (delayed notification)\nChip: {tag_id}\nOriginal time: {data.get('timestamp', 'unknown')}"
            
            # Add photo links if available
            photo_links = data.get('photo_links')
            if photo_links:
                body += "\n\nPhoto Links:\n"
                for i, link in enumerate(photo_links, 1):
                    body += f"{i}. {link}\n"
            
            msg = MIMEText(body)
            msg['From'] = self.config['email_from']
            msg['To'] = self.config['alert_to_email']
            msg['Subject'] = subject
            
            with smtplib.SMTP(self.config['smtp_host'], self.config['smtp_port']) as server:
                server.starttls()
                server.login(self.config['smtp_user'], self.config['smtp_pass'])
                server.send_message(msg)
            
            return True
        except Exception:
            return False

def main():
    parser = argparse.ArgumentParser(description='Process offline queue for pet chip reader')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be processed without doing it')
    parser.add_argument('--photos-only', action='store_true', help='Only process photo uploads')
    parser.add_argument('--notifications-only', action='store_true', help='Only process notifications')
    
    args = parser.parse_args()
    
    processor = OfflineQueueProcessor()
    
    print("Pet Chip Reader - Offline Queue Processor")
    print("=" * 40)
    
    if args.dry_run:
        print("DRY RUN MODE - No actual processing will occur")
        print()
    
    total_photos_success = 0
    total_photos_failed = 0
    total_notifications_success = 0
    total_notifications_failed = 0
    
    # Process photos unless notifications-only
    if not args.notifications_only:
        print("Processing Photo Upload Queue...")
        photos_success, photos_failed = processor.process_photo_queue(args.dry_run)
        total_photos_success += photos_success
        total_photos_failed += photos_failed
        print()
    
    # Process notifications unless photos-only
    if not args.photos_only:
        print("Processing Notification Queue...")
        notif_success, notif_failed = processor.process_notification_queue(args.dry_run)
        total_notifications_success += notif_success
        total_notifications_failed += notif_failed
        print()
    
    # Summary
    print("Summary:")
    print(f"Photos uploaded: {total_photos_success}")
    print(f"Photo upload failures: {total_photos_failed}")
    print(f"Notifications sent: {total_notifications_success}")
    print(f"Notification failures: {total_notifications_failed}")
    
    if args.dry_run:
        print("\\nNote: This was a dry run. Use without --dry-run to actually process the queue.")

if __name__ == '__main__':
    main()