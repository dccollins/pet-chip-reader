#!/usr/bin/env python3
"""
Daily Digest Generator for Pet Chip Reader

Generates and sends daily activity summaries with all detections from the past 24 hours.
Designed to be run via cron job every evening.

Usage:
    python3 generate_daily_digest.py [--dry-run] [--date YYYY-MM-DD]
"""

import os
import sys
import json
import argparse
import smtplib
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
from email.mime.text import MIMEText

# Add the src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from dotenv import load_dotenv
except ImportError as e:
    print(f"Missing required module: {e}")
    print("Please install requirements: pip install -r requirements.txt")
    sys.exit(1)

class DailyDigestGenerator:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Configuration
        self.config = {
            'photo_dir': os.getenv('PHOTO_DIR', '/home/collins/rfid_photos'),
            'smtp_host': os.getenv('SMTP_HOST', 'smtp.gmail.com'),
            'smtp_port': int(os.getenv('SMTP_PORT', '587')),
            'smtp_user': os.getenv('SMTP_USER', ''),
            'smtp_pass': os.getenv('SMTP_PASS', ''),
            'email_from': os.getenv('EMAIL_FROM', ''),
            'digest_email': os.getenv('DIGEST_EMAIL', 'dccollins@gmail.com'),
            'daily_digest_enabled': os.getenv('DAILY_DIGEST_ENABLED', 'true').lower() == 'true',
        }
        
    def get_daily_detections(self, target_date=None):
        """Get all detections for a specific day from photos and log files"""
        if target_date is None:
            target_date = datetime.now().date()
        elif isinstance(target_date, str):
            target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
        
        detections = []
        photo_dir = Path(self.config['photo_dir'])
        
        # Scan photo files for the target date
        date_pattern = target_date.strftime('%Y%m%d')
        
        for photo_file in photo_dir.glob(f"{date_pattern}_*.jpg"):
            try:
                # Parse filename: YYYYmmdd_HHMMSS_chipid_cam0.jpg
                parts = photo_file.stem.split('_')
                if len(parts) >= 3:
                    date_str = parts[0]
                    time_str = parts[1] 
                    chip_id = parts[2]
                    
                    # Create timestamp
                    timestamp = datetime.strptime(f"{date_str}_{time_str}", '%Y%m%d_%H%M%S')
                    
                    # Check for corresponding JSON metadata
                    json_file = photo_file.with_suffix('.json')
                    ai_description = None
                    gps_coordinates = None
                    
                    if json_file.exists():
                        try:
                            with open(json_file, 'r') as f:
                                metadata = json.load(f)
                                ai_description = metadata.get('ai_description')
                                gps_data = metadata.get('gps_coordinates')
                                if gps_data and isinstance(gps_data, dict):
                                    gps_coordinates = (gps_data.get('latitude'), gps_data.get('longitude'))
                        except (json.JSONDecodeError, Exception):
                            pass
                    
                    detections.append({
                        'timestamp': timestamp,
                        'chip_id': chip_id,
                        'photo_path': str(photo_file),
                        'ai_description': ai_description,
                        'gps_coordinates': gps_coordinates
                    })
                    
            except (ValueError, IndexError):
                continue
        
        # Sort by timestamp
        detections.sort(key=lambda x: x['timestamp'])
        
        return detections
    
    def analyze_daily_activity(self, detections):
        """Analyze daily detection patterns"""
        if not detections:
            return {
                'total_detections': 0,
                'unique_chips': 0,
                'chip_summary': {},
                'hourly_activity': defaultdict(int),
                'first_detection': None,
                'last_detection': None,
                'peak_hour': None,
                'ai_descriptions': []
            }
        
        chip_detections = defaultdict(list)
        hourly_activity = defaultdict(int)
        ai_descriptions = []
        
        for detection in detections:
            chip_id = detection['chip_id']
            timestamp = detection['timestamp']
            hour = timestamp.hour
            
            chip_detections[chip_id].append(detection)
            hourly_activity[hour] += 1
            
            if detection['ai_description'] and detection['ai_description'] != 'AI analysis not available':
                ai_descriptions.append({
                    'chip_id': chip_id,
                    'time': timestamp.strftime('%H:%M'),
                    'description': detection['ai_description']
                })
        
        # Find peak activity hour
        peak_hour = max(hourly_activity.items(), key=lambda x: x[1])[0] if hourly_activity else None
        
        # Create chip summary sorted by activity
        chip_summary = {chip_id: len(times) for chip_id, times in chip_detections.items()}
        chip_summary = dict(sorted(chip_summary.items(), key=lambda x: x[1], reverse=True))
        
        return {
            'total_detections': len(detections),
            'unique_chips': len(chip_detections),
            'chip_summary': chip_summary,
            'hourly_activity': dict(hourly_activity),
            'first_detection': detections[0]['timestamp'],
            'last_detection': detections[-1]['timestamp'],
            'peak_hour': peak_hour,
            'ai_descriptions': ai_descriptions[:10]  # Limit to 10 most interesting
        }
    
    def create_daily_digest_email(self, analysis, target_date):
        """Create the daily digest email content"""
        date_str = target_date.strftime('%A, %B %d, %Y')
        
        if analysis['total_detections'] == 0:
            subject = f"🐾 Daily Pet Report - {target_date.strftime('%B %d')} - No Activity"
            body = f"Daily Pet Activity Report\\n"
            body += f"========================\\n\\n"
            body += f"📅 Date: {date_str}\\n\\n"
            body += f"😴 No pet activity detected today.\\n"
            body += f"All systems operating normally.\\n"
        else:
            subject = f"🐾 Daily Pet Report - {target_date.strftime('%B %d')} - {analysis['total_detections']} detections"
            
            body = f"Daily Pet Activity Report\\n"
            body += f"========================\\n\\n"
            body += f"📅 Date: {date_str}\\n\\n"
            
            # Overview
            body += f"📊 Activity Summary:\\n"
            body += f"• Total detections: {analysis['total_detections']}\\n"
            body += f"• Unique pets: {analysis['unique_chips']}\\n"
            
            if analysis['first_detection'] and analysis['last_detection']:
                body += f"• First activity: {analysis['first_detection'].strftime('%H:%M')}\\n"
                body += f"• Last activity: {analysis['last_detection'].strftime('%H:%M')}\\n"
            
            if analysis['peak_hour'] is not None:
                body += f"• Peak activity: {analysis['peak_hour']:02d}:00 hour\\n"
            
            # Per-pet breakdown
            if analysis['chip_summary']:
                body += f"\\n🐾 Pet Activity:\\n"
                for chip_id, count in analysis['chip_summary'].items():
                    chip_display = f"...{chip_id[-8:]}" if len(chip_id) > 8 else chip_id
                    body += f"• {chip_display}: {count} detections\\n"
            
            # Hourly activity pattern
            if analysis['hourly_activity']:
                body += f"\\n⏰ Activity Timeline:\\n"
                for hour in range(24):
                    if hour in analysis['hourly_activity']:
                        count = analysis['hourly_activity'][hour]
                        if count > 0:
                            bar = '█' * min(count, 20)  # Visual bar, max 20 chars
                            body += f"{hour:02d}:00 │{bar} ({count})\\n"
            
            # AI Insights
            if analysis['ai_descriptions']:
                body += f"\\n🤖 AI Insights:\\n"
                for insight in analysis['ai_descriptions']:
                    chip_short = f"...{insight['chip_id'][-6:]}" if len(insight['chip_id']) > 6 else insight['chip_id']
                    body += f"• {insight['time']} - {chip_short}: {insight['description']}\\n"
        
        body += f"\\n📈 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\\n"
        body += f"🔧 Pet Chip Reader System v2.1.0\\n"
        
        return {'subject': subject, 'body': body}
    
    def send_daily_digest(self, digest_data, dry_run=False):
        """Send the daily digest email"""
        if not self.config['daily_digest_enabled']:
            print("Daily digest is disabled in configuration")
            return False
            
        if not all([self.config['smtp_user'], self.config['smtp_pass'], self.config['digest_email']]):
            print("Email configuration incomplete")
            return False
        
        if dry_run:
            print("DRY RUN - Would send email:")
            print(f"To: {self.config['digest_email']}")
            print(f"Subject: {digest_data['subject']}")
            print(f"Body:\\n{digest_data['body']}")
            return True
        
        try:
            msg = MIMEText(digest_data['body'])
            msg['From'] = self.config['email_from']
            msg['To'] = self.config['digest_email']
            msg['Subject'] = digest_data['subject']
            
            with smtplib.SMTP(self.config['smtp_host'], self.config['smtp_port']) as server:
                server.starttls()
                server.login(self.config['smtp_user'], self.config['smtp_pass'])
                server.send_message(msg)
            
            print(f"✓ Daily digest sent to {self.config['digest_email']}")
            return True
            
        except Exception as e:
            print(f"✗ Failed to send daily digest: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description='Generate daily pet activity digest')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be sent without sending')
    parser.add_argument('--date', help='Target date (YYYY-MM-DD), defaults to yesterday')
    
    args = parser.parse_args()
    
    # Determine target date (default to yesterday for evening cron job)
    if args.date:
        target_date = datetime.strptime(args.date, '%Y-%m-%d').date()
    else:
        target_date = (datetime.now() - timedelta(days=0)).date()  # Today for testing, change to yesterday for production
    
    generator = DailyDigestGenerator()
    
    print(f"Generating daily digest for {target_date.strftime('%Y-%m-%d')}...")
    
    # Get detections for the day
    detections = generator.get_daily_detections(target_date)
    print(f"Found {len(detections)} detections")
    
    # Analyze activity
    analysis = generator.analyze_daily_activity(detections)
    
    # Create email content
    digest_data = generator.create_daily_digest_email(analysis, target_date)
    
    # Send email
    success = generator.send_daily_digest(digest_data, args.dry_run)
    
    if success and not args.dry_run:
        print("Daily digest sent successfully!")
    elif args.dry_run:
        print("Dry run completed - no email sent")
    else:
        print("Failed to send daily digest")
        sys.exit(1)

if __name__ == '__main__':
    main()