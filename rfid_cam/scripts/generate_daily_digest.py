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
from email.mime.multipart import MIMEMultipart

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
        """Create the daily digest email content with beautiful HTML formatting"""
        date_str = target_date.strftime('%A, %B %d, %Y')
        
        if analysis['total_detections'] == 0:
            subject = f"🐾 Daily Pet Report - {target_date.strftime('%B %d')} - No Activity"
            
            # HTML version for no activity
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Daily Pet Activity Report</title>
            </head>
            <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; background-color: #f9f9f9;">
                <div style="background-color: white; padding: 30px; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    <h1 style="color: #2E8B57; text-align: center; margin-bottom: 10px; font-size: 32px;">🐾 Daily Pet Activity Report</h1>
                    <p style="text-align: center; color: #666; margin-bottom: 30px; font-size: 18px;">{date_str}</p>
                    <hr style="border: 2px solid #2E8B57; margin: 20px 0;">
                    
                    <div style="background: linear-gradient(135deg, #f0f8f0, #e8f5e8); padding: 30px; border-radius: 10px; text-align: center; border-left: 5px solid #2E8B57;">
                        <h2 style="color: #2E8B57; margin-top: 0; font-size: 28px;">😴 No pet activity detected today</h2>
                        <p style="font-size: 18px; color: #555;">All systems operating normally. Your pets had a quiet day!</p>
                    </div>
                    
                    <hr style="margin: 30px 0; border: 1px solid #ddd;">
                    <footer style="text-align: center; font-size: 14px; color: #888; background: linear-gradient(135deg, #f8f9fa, #e9ecef); padding: 15px; border-radius: 10px;">
                        <p style="margin: 0;">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
                        🔧 <strong>Pet Chip Reader System v2.1.0</strong> | Daily Digest</p>
                    </footer>
                </div>
            </body>
            </html>
            """
            
            # Text fallback
            text_body = f"Daily Pet Activity Report\\n========================\\n\\n📅 Date: {date_str}\\n\\n😴 No pet activity detected today.\\nAll systems operating normally."
            
        else:
            subject = f"🐾 Daily Pet Report - {target_date.strftime('%B %d')} - {analysis['total_detections']} detections"
            
            # Beautiful HTML version for activity
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Daily Pet Activity Report</title>
            </head>
            <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; max-width: 900px; margin: 0 auto; padding: 20px; background-color: #f9f9f9;">
                <div style="background-color: white; padding: 30px; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    <h1 style="color: #2E8B57; text-align: center; margin-bottom: 10px; font-size: 32px;">🐾 Daily Pet Activity Report</h1>
                    <p style="text-align: center; color: #666; margin-bottom: 30px; font-size: 18px;">{date_str}</p>
                    <hr style="border: 2px solid #2E8B57; margin: 20px 0;">
                
                    <div style="background: linear-gradient(135deg, #f0f8f0, #e8f5e8); padding: 25px; border-radius: 12px; margin: 20px 0; border-left: 5px solid #2E8B57;">
                        <h2 style="margin-top: 0; color: #2E8B57; font-size: 24px;">📊 Activity Summary</h2>
                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px; margin-top: 20px;">
                            <div style="background-color: white; padding: 20px; border-radius: 10px; text-align: center; box-shadow: 0 3px 6px rgba(0,0,0,0.1);">
                                <div style="font-size: 36px; font-weight: bold; color: #2E8B57;">{analysis['total_detections']}</div>
                                <div style="color: #666; font-size: 16px; margin-top: 5px;">Total Detections</div>
                            </div>
                            <div style="background-color: white; padding: 20px; border-radius: 10px; text-align: center; box-shadow: 0 3px 6px rgba(0,0,0,0.1);">
                                <div style="font-size: 36px; font-weight: bold; color: #20B2AA;">{analysis['unique_chips']}</div>
                                <div style="color: #666; font-size: 16px; margin-top: 5px;">Unique Pets</div>
                            </div>
            """
            
            if analysis['first_detection'] and analysis['last_detection']:
                html_body += f"""
                            <div style="background-color: white; padding: 20px; border-radius: 10px; text-align: center; box-shadow: 0 3px 6px rgba(0,0,0,0.1);">
                                <div style="font-size: 24px; font-weight: bold; color: #FF6B6B;">{analysis['first_detection'].strftime('%H:%M')}</div>
                                <div style="color: #666; font-size: 16px; margin-top: 5px;">First Activity</div>
                            </div>
                            <div style="background-color: white; padding: 20px; border-radius: 10px; text-align: center; box-shadow: 0 3px 6px rgba(0,0,0,0.1);">
                                <div style="font-size: 24px; font-weight: bold; color: #9C27B0;">{analysis['last_detection'].strftime('%H:%M')}</div>
                                <div style="color: #666; font-size: 16px; margin-top: 5px;">Last Activity</div>
                            </div>
                """
            
            if analysis['peak_hour'] is not None:
                html_body += f"""
                            <div style="background-color: white; padding: 20px; border-radius: 10px; text-align: center; box-shadow: 0 3px 6px rgba(0,0,0,0.1);">
                                <div style="font-size: 24px; font-weight: bold; color: #FF9800;">{analysis['peak_hour']:02d}:00</div>
                                <div style="color: #666; font-size: 16px; margin-top: 5px;">Peak Hour</div>
                            </div>
                """
            
            html_body += """
                        </div>
                    </div>
            """
            
            # Pet activity breakdown
            if analysis['chip_summary']:
                html_body += """
                    <div style="background: linear-gradient(135deg, #e8f5e8, #c8e6c8); padding: 25px; border-radius: 12px; margin: 20px 0; border-left: 5px solid #4CAF50;">
                        <h2 style="margin-top: 0; color: #4CAF50; font-size: 24px;">🐾 Pet Activity Breakdown</h2>
                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 15px;">
                """
                for chip_id, count in analysis['chip_summary'].items():
                    chip_display = f"...{chip_id[-8:]}" if len(chip_id) > 8 else chip_id
                    html_body += f"""
                            <div style="background-color: white; padding: 20px; border-radius: 10px; box-shadow: 0 3px 6px rgba(0,0,0,0.1); border-left: 4px solid #4CAF50;">
                                <div style="font-size: 28px; font-weight: bold; color: #4CAF50; text-align: center;">{count}</div>
                                <div style="color: #666; font-size: 16px; text-align: center; margin-top: 5px;">Pet {chip_display}</div>
                            </div>
                    """
                html_body += """
                        </div>
                    </div>
                """
            
            # Hourly activity timeline
            if analysis['hourly_activity']:
                html_body += """
                    <div style="background: linear-gradient(135deg, #fff0f5, #ffe8f0); padding: 25px; border-radius: 12px; margin: 20px 0; border-left: 5px solid #E91E63;">
                        <h2 style="margin-top: 0; color: #E91E63; font-size: 24px;">⏰ Hourly Activity Timeline</h2>
                        <div style="background-color: white; padding: 25px; border-radius: 10px; box-shadow: 0 3px 6px rgba(0,0,0,0.1);">
                """
                max_count = max(analysis['hourly_activity'].values()) if analysis['hourly_activity'] else 1
                
                for hour in range(24):
                    count = analysis['hourly_activity'].get(hour, 0)
                    if count > 0:
                        bar_width = max(int((count / max_count) * 400), 30)  # Scale to max 400px
                        bar_color = f"rgba(233, 30, 99, {0.4 + (count / max_count) * 0.6})"
                        
                        html_body += f"""
                            <div style="margin: 10px 0; display: flex; align-items: center;">
                                <span style="display: inline-block; width: 70px; font-weight: bold; color: #333; font-size: 16px;">{hour:02d}:00</span>
                                <div style="flex: 1; background-color: #f5f5f5; border-radius: 12px; height: 30px; margin: 0 20px; position: relative; overflow: hidden;">
                                    <div style="width: {bar_width}px; height: 100%; background: {bar_color}; border-radius: 12px; display: flex; align-items: center; justify-content: center; transition: width 0.5s ease;"></div>
                                </div>
                                <span style="font-weight: bold; color: #E91E63; min-width: 50px; text-align: right; font-size: 16px;">({count})</span>
                            </div>
                        """
                
                html_body += """
                        </div>
                    </div>
                """
            
            # AI Insights section
            if analysis['ai_descriptions']:
                html_body += """
                    <div style="background: linear-gradient(135deg, #f0f8ff, #e6f3ff); padding: 25px; border-radius: 12px; margin: 20px 0; border-left: 5px solid #2196F3;">
                        <h2 style="margin-top: 0; color: #2196F3; font-size: 24px;">🤖 AI Insights</h2>
                        <div style="background-color: white; padding: 20px; border-radius: 10px; box-shadow: 0 3px 6px rgba(0,0,0,0.1);">
                """
                for insight in analysis['ai_descriptions']:
                    chip_short = f"...{insight['chip_id'][-8:]}" if len(insight['chip_id']) > 8 else insight['chip_id']
                    html_body += f"""
                            <div style="margin: 15px 0; padding: 15px; background-color: #f8f9fa; border-radius: 8px; border-left: 4px solid #2196F3;">
                                <div style="font-weight: bold; color: #2196F3; margin-bottom: 5px;">
                                    🕒 {insight['time']} - Pet {chip_short}
                                </div>
                                <div style="color: #555; font-style: italic; line-height: 1.5;">
                                    "{insight['description']}"
                                </div>
                            </div>
                    """
                html_body += """
                        </div>
                    </div>
                """
            
            html_body += f"""
                    <hr style="margin: 30px 0; border: 2px solid #ddd;">
                    <footer style="text-align: center; font-size: 14px; color: #888; background: linear-gradient(135deg, #f8f9fa, #e9ecef); padding: 20px; border-radius: 10px;">
                        <p style="margin: 0; line-height: 1.6;">
                            <strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
                            🔧 <strong>Pet Chip Reader System v2.1.0</strong> | Daily Digest<br>
                            📧 Delivered to: {self.config.get('digest_email', 'Unknown')}
                        </p>
                    </footer>
                </div>
            </body>
            </html>
            """
            
            # Text fallback
            text_body = f"Daily Pet Activity Report\\n========================\\n\\n📅 Date: {date_str}\\n\\n"
            text_body += f"📊 Activity Summary:\\n• Total detections: {analysis['total_detections']}\\n• Unique pets: {analysis['unique_chips']}\\n"
            
            if analysis['first_detection'] and analysis['last_detection']:
                text_body += f"• First activity: {analysis['first_detection'].strftime('%H:%M')}\\n"
                text_body += f"• Last activity: {analysis['last_detection'].strftime('%H:%M')}\\n"
            
            if analysis['peak_hour'] is not None:
                text_body += f"• Peak activity: {analysis['peak_hour']:02d}:00 hour\\n"
            
            if analysis['chip_summary']:
                text_body += f"\\n🐾 Pet Activity:\\n"
                for chip_id, count in analysis['chip_summary'].items():
                    chip_display = f"...{chip_id[-8:]}" if len(chip_id) > 8 else chip_id
                    text_body += f"• {chip_display}: {count} detections\\n"
            
            if analysis['ai_descriptions']:
                text_body += f"\\n🤖 AI Insights:\\n"
                for insight in analysis['ai_descriptions'][:5]:  # Limit to 5 for text version
                    chip_short = f"...{insight['chip_id'][-6:]}" if len(insight['chip_id']) > 6 else insight['chip_id']
                    text_body += f"• {insight['time']} - {chip_short}: {insight['description']}\\n"
        
        return {'subject': subject, 'html_body': html_body, 'text_body': text_body}
    
    def send_daily_digest(self, digest_data, dry_run=False):
        """Send the daily digest email with beautiful HTML formatting"""
        if not self.config['daily_digest_enabled']:
            print("Daily digest is disabled in configuration")
            return False
            
        if not all([self.config['smtp_user'], self.config['smtp_pass'], self.config['digest_email']]):
            print("Email configuration incomplete")
            return False
        
        if dry_run:
            print("DRY RUN - Would send HTML email:")
            print(f"To: {self.config['digest_email']}")
            print(f"Subject: {digest_data['subject']}")
            print(f"HTML Body length: {len(digest_data.get('html_body', ''))} characters")
            print(f"Text fallback length: {len(digest_data.get('text_body', ''))} characters")
            return True
        
        try:
            # Create multipart message for HTML + text
            msg = MIMEMultipart('alternative')
            msg['From'] = self.config['email_from']
            msg['To'] = self.config['digest_email']
            msg['Subject'] = digest_data['subject']
            
            # Add text version as fallback
            text_part = MIMEText(digest_data['text_body'], 'plain')
            msg.attach(text_part)
            
            # Add HTML version (preferred)
            html_part = MIMEText(digest_data['html_body'], 'html')
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.config['smtp_host'], self.config['smtp_port']) as server:
                server.starttls()
                server.login(self.config['smtp_user'], self.config['smtp_pass'])
                server.send_message(msg)
            
            print(f"✓ Beautiful HTML daily digest sent to {self.config['digest_email']}")
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