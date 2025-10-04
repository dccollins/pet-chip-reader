#!/usr/bin/env python3
"""
Enhanced Daily Digest with Photo Highlight Reel

Generates daily activity summaries with embedded photos of the best detections.
Includes actual animal photos as attachments for a visual highlight reel.
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
from email.mime.image import MIMEImage
import random

# Add the src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from dotenv import load_dotenv
except ImportError as e:
    print(f"Missing required module: {e}")
    print("Please install requirements: pip install -r requirements.txt")
    sys.exit(1)

class EnhancedDailyDigest:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Configuration
        self.config = {
            'photo_dir': os.getenv('PHOTO_DIR', '/home/collins/rfid_photos'),
            'rclone_path': os.getenv('RCLONE_PATH', 'rfid_photos'),
            'smtp_host': os.getenv('SMTP_HOST', 'smtp.gmail.com'),
            'smtp_port': int(os.getenv('SMTP_PORT', '587')),
            'smtp_user': os.getenv('SMTP_USER', ''),
            'smtp_pass': os.getenv('SMTP_PASS', ''),
            'email_from': os.getenv('EMAIL_FROM', ''),
            'digest_email': os.getenv('DIGEST_EMAIL', 'dccollins@gmail.com'),
            'daily_digest_enabled': os.getenv('DAILY_DIGEST_ENABLED', 'true').lower() == 'true',
            'max_photos_in_digest': int(os.getenv('MAX_PHOTOS_IN_DIGEST', '6')),
            'photo_attachment_max_size': int(os.getenv('PHOTO_ATTACHMENT_MAX_SIZE', '500000')),  # 500KB max per photo
        }
    
    def get_daily_detections_with_photos(self, target_date=None):
        """Get all detections for a specific day with photo analysis"""
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
                    photo_quality_score = 0
                    
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
                    
                    # Calculate photo quality score for highlight reel selection
                    photo_quality_score = self.calculate_photo_quality_score(
                        photo_file, ai_description, timestamp
                    )
                    
                    detection = {
                        'timestamp': timestamp,
                        'chip_id': chip_id,
                        'photo_path': str(photo_file),
                        'ai_description': ai_description,
                        'gps_coordinates': gps_coordinates,
                        'quality_score': photo_quality_score,
                        'file_size': photo_file.stat().st_size
                    }
                    
                    detections.append(detection)
                    
            except (ValueError, IndexError):
                continue
        
        # Sort by timestamp
        detections.sort(key=lambda x: x['timestamp'])
        
        return detections
    
    def calculate_photo_quality_score(self, photo_file, ai_description, timestamp):
        """Calculate a quality score for photo selection in highlight reel"""
        score = 0
        
        # Base score for file size (larger usually means more detail)
        file_size = photo_file.stat().st_size
        if file_size > 400000:  # > 400KB
            score += 3
        elif file_size > 300000:  # > 300KB
            score += 2
        else:
            score += 1
        
        # Bonus for AI description (indicates interesting content)
        if ai_description and ai_description != 'AI analysis not available':
            score += 5
            # Extra points for animal-related keywords
            animal_keywords = ['cat', 'dog', 'pet', 'kitten', 'puppy', 'animal', 'fur', 'tail', 'whiskers']
            if any(keyword in ai_description.lower() for keyword in animal_keywords):
                score += 3
        
        # Time-based scoring (prefer daylight hours for better photos)
        hour = timestamp.hour
        if 6 <= hour <= 18:  # Daytime
            score += 2
        elif 18 <= hour <= 22:  # Evening  
            score += 1
        
        # Random factor to add variety
        score += random.randint(0, 2)
        
        return score
    
    def get_google_drive_files_cache(self):
        """Get cached list of Google Drive files with IDs"""
        if not hasattr(self, '_drive_files_cache'):
            try:
                print("Fetching Google Drive file list...")
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

    def group_photos_by_pet_and_timeframe(self, detections):
        """Group photos by pet ID and timeframe, filtering for animal photos"""
        pet_groups = defaultdict(lambda: {'all_photos': [], 'animal_photos': []})
        
        for detection in detections:
            pet_id = detection['chip_id']
            ai_desc = detection.get('ai_description') or ''
            
            # Add to all photos
            pet_groups[pet_id]['all_photos'].append(detection)
            
            # Check if AI description suggests an animal is visible
            if isinstance(ai_desc, str) and ai_desc.strip():
                animal_keywords = ['cat', 'dog', 'pet', 'animal', 'kitten', 'puppy', 'fur', 'tail', 'whiskers', 
                                 'paws', 'nose', 'eyes', 'ears', 'face', 'head', 'body', 'sitting', 'lying', 
                                 'looking', 'feline', 'canine', 'mammal', 'creature']
                
                if any(keyword in ai_desc.lower() for keyword in animal_keywords):
                    pet_groups[pet_id]['animal_photos'].append(detection)
                # Also include photos with high quality scores (likely to contain animals)
                elif detection.get('quality_score', 0) > 8:
                    pet_groups[pet_id]['animal_photos'].append(detection)
        
        # Sort animal photos by quality score for each pet
        for pet_data in pet_groups.values():
            pet_data['animal_photos'].sort(key=lambda x: x.get('quality_score', 0), reverse=True)
            # Keep only top 4 photos per pet to avoid overwhelming the email
            pet_data['animal_photos'] = pet_data['animal_photos'][:4]
        
        return dict(pet_groups)

    def select_highlight_photos(self, detections, max_photos=6):
        """Select the best photos for the highlight reel"""
        if not detections:
            return []
        
        # Filter photos by size limit and sort by quality score
        suitable_photos = [
            d for d in detections 
            if d['file_size'] <= self.config['photo_attachment_max_size']
        ]
        
        if not suitable_photos:
            # If no photos meet size limit, take smaller ones and resize later
            suitable_photos = sorted(detections, key=lambda x: x['file_size'])[:max_photos]
        
        # Sort by quality score descending
        suitable_photos.sort(key=lambda x: x['quality_score'], reverse=True)
        
        # Select diverse photos (different times and pets when possible)
        selected_photos = []
        used_hours = set()
        used_chips = set()
        
        # First pass: prioritize diversity
        for photo in suitable_photos:
            if len(selected_photos) >= max_photos:
                break
                
            hour = photo['timestamp'].hour
            chip = photo['chip_id']
            
            # Prefer photos from different hours and different pets
            if hour not in used_hours or chip not in used_chips:
                selected_photos.append(photo)
                used_hours.add(hour)
                used_chips.add(chip)
        
        # Second pass: fill remaining slots with best quality
        for photo in suitable_photos:
            if len(selected_photos) >= max_photos:
                break
            if photo not in selected_photos:
                selected_photos.append(photo)
        
        return selected_photos[:max_photos]
    
    def create_enhanced_daily_digest(self, analysis, target_date, highlight_photos, all_detections):
        """Create enhanced daily digest with photo highlight reel and detection table"""
        date_str = target_date.strftime('%A, %B %d, %Y')
        
        if analysis['total_detections'] == 0:
            subject = f"🐾 Daily Pet Report - {target_date.strftime('%B %d')} - No Activity"
            
            # Create HTML content for no activity
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
                    <h1 style="color: #2E8B57; text-align: center; margin-bottom: 10px; font-size: 28px;">🐾 Daily Pet Activity Report</h1>
                    <p style="text-align: center; color: #666; margin-bottom: 30px; font-size: 18px;">{date_str}</p>
                    <hr style="border: 2px solid #2E8B57; margin: 20px 0;">
                    
                    <div style="background: linear-gradient(135deg, #f0f8f0, #e8f5e8); padding: 30px; border-radius: 10px; text-align: center; border-left: 5px solid #2E8B57;">
                        <h2 style="color: #2E8B57; margin-top: 0;">😴 No pet activity detected today</h2>
                        <p style="font-size: 16px; color: #555;">All systems operating normally. Your pets had a quiet day!</p>
                    </div>
                    
                    <hr style="margin: 30px 0; border: 1px solid #ddd;">
                    <footer style="text-align: center; font-size: 12px; color: #888;">
                        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
                        🔧 Pet Chip Reader System v2.1.0 | Enhanced Daily Digest</p>
                    </footer>
                </div>
            </body>
            </html>
            """
            
            text_body = f"Daily Pet Activity Report\\n========================\\n\\n📅 Date: {date_str}\\n\\n😴 No pet activity detected today.\\nAll systems operating normally.\\n"
        else:
            subject = f"🐾 Daily Pet Report - {target_date.strftime('%B %d')} - {analysis['total_detections']} detections"
            
            # Create beautiful HTML content
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Daily Pet Activity Report</title>
                <style>
                    .detection-table {{
                        width: 100%;
                        border-collapse: collapse;
                        margin: 20px 0;
                        font-size: 14px;
                        background-color: white;
                        border-radius: 8px;
                        overflow: hidden;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    }}
                    .detection-table th {{
                        background: linear-gradient(135deg, #2E8B57, #20B2AA);
                        color: white;
                        padding: 12px 8px;
                        text-align: left;
                        font-weight: bold;
                        font-size: 13px;
                    }}
                    .detection-table td {{
                        padding: 10px 8px;
                        border-bottom: 1px solid #f0f0f0;
                        vertical-align: top;
                    }}
                    .detection-table tr:nth-child(even) {{
                        background-color: #fafafa;
                    }}
                    .detection-table tr:hover {{
                        background-color: #f5f5f5;
                    }}
                    .chip-id {{
                        font-family: monospace;
                        background-color: #e8f4f8;
                        padding: 2px 6px;
                        border-radius: 4px;
                        font-size: 11px;
                        color: #2E8B57;
                        font-weight: bold;
                    }}
                    .timestamp {{
                        font-weight: bold;
                        color: #555;
                    }}
                    .ai-description {{
                        max-width: 200px;
                        font-style: italic;
                        color: #666;
                        font-size: 12px;
                    }}
                    .photo-link {{
                        background: linear-gradient(135deg, #4CAF50, #45a049);
                        color: white;
                        padding: 4px 8px;
                        text-decoration: none;
                        border-radius: 4px;
                        font-size: 11px;
                        font-weight: bold;
                        display: inline-block;
                        transition: background 0.3s;
                    }}
                    .photo-link:hover {{
                        background: linear-gradient(135deg, #45a049, #4CAF50);
                        text-decoration: none;
                        color: white;
                    }}
                    .highlight-badge {{
                        background: linear-gradient(135deg, #ff6b6b, #ff5252);
                        color: white;
                        padding: 2px 6px;
                        border-radius: 10px;
                        font-size: 10px;
                        font-weight: bold;
                        margin-left: 5px;
                    }}
                </style>
            </head>
            <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; max-width: 900px; margin: 0 auto; padding: 20px; background-color: #f9f9f9;">
                <div style="background-color: white; padding: 30px; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    <h1 style="color: #2E8B57; text-align: center; margin-bottom: 10px; font-size: 32px;">🐾 Daily Pet Activity Report</h1>
                    <p style="text-align: center; color: #666; margin-bottom: 30px; font-size: 18px;">{date_str}</p>
                    <hr style="border: 2px solid #2E8B57; margin: 20px 0;">
                
                    <div style="background: linear-gradient(135deg, #f0f8f0, #e8f5e8); padding: 20px; border-radius: 10px; margin: 20px 0; border-left: 5px solid #2E8B57;">
                        <h2 style="margin-top: 0; color: #2E8B57; font-size: 24px;">📊 Activity Summary</h2>
                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-top: 15px;">
                            <div style="background-color: white; padding: 15px; border-radius: 8px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                                <div style="font-size: 28px; font-weight: bold; color: #2E8B57;">{analysis['total_detections']}</div>
                                <div style="color: #666; font-size: 14px;">Total Detections</div>
                            </div>
                            <div style="background-color: white; padding: 15px; border-radius: 8px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                                <div style="font-size: 28px; font-weight: bold; color: #20B2AA;">{analysis['unique_chips']}</div>
                                <div style="color: #666; font-size: 14px;">Unique Pets</div>
                            </div>
            """
            
            if analysis['first_detection'] and analysis['last_detection']:
                html_body += f"""
                            <div style="background-color: white; padding: 15px; border-radius: 8px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                                <div style="font-size: 18px; font-weight: bold; color: #FF6B6B;">{analysis['first_detection'].strftime('%H:%M')}</div>
                                <div style="color: #666; font-size: 14px;">First Activity</div>
                            </div>
                            <div style="background-color: white; padding: 15px; border-radius: 8px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                                <div style="font-size: 18px; font-weight: bold; color: #9C27B0;">{analysis['last_detection'].strftime('%H:%M')}</div>
                                <div style="color: #666; font-size: 14px;">Last Activity</div>
                            </div>
                """
            
            if analysis['peak_hour'] is not None:
                html_body += f"""
                            <div style="background-color: white; padding: 15px; border-radius: 8px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                                <div style="font-size: 18px; font-weight: bold; color: #FF9800;">{analysis['peak_hour']:02d}:00</div>
                                <div style="color: #666; font-size: 14px;">Peak Hour</div>
                            </div>
                """
            
            html_body += """
                        </div>
                    </div>
            """
            
            # Activity timeline (moved to second position)
            if analysis['hourly_activity']:
                html_body += """
                    <div style="background: linear-gradient(135deg, #fff0f5, #ffdeef); padding: 20px; border-radius: 10px; margin: 20px 0; border-left: 5px solid #E91E63;">
                        <h2 style="margin-top: 0; color: #E91E63; font-size: 24px;">⏰ Hourly Activity Timeline</h2>
                        <div style="background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                """
                max_count = max(analysis['hourly_activity'].values()) if analysis['hourly_activity'] else 1
                
                for hour in range(24):
                    count = analysis['hourly_activity'].get(hour, 0)
                    if count > 0:
                        bar_width = max(int((count / max_count) * 300), 20)  # Scale to max 300px
                        color_intensity = int((count / max_count) * 255)
                        bar_color = f"rgba(46, 139, 87, {0.3 + (count / max_count) * 0.7})"
                        
                        html_body += f"""
                            <div style="margin: 8px 0; display: flex; align-items: center;">
                                <span style="display: inline-block; width: 60px; font-weight: bold; color: #333;">{hour:02d}:00</span>
                                <div style="flex: 1; background-color: #f0f0f0; border-radius: 10px; height: 25px; margin: 0 15px; position: relative; overflow: hidden;">
                                    <div style="width: {bar_width}px; height: 100%; background: {bar_color}; border-radius: 10px; display: flex; align-items: center; justify-content: center; transition: width 0.3s ease;"></div>
                                </div>
                                <span style="font-weight: bold; color: #2E8B57; min-width: 40px; text-align: right;">({count})</span>
                            </div>
                        """
                
                html_body += """
                        </div>
                    </div>
                """
            
            # Complete detection table
            html_body += f"""
                    <div style="background: linear-gradient(135deg, #fff8dc, #ffeaa7); padding: 20px; border-radius: 10px; margin: 20px 0; border-left: 5px solid #FF9800;">
                        <h2 style="margin-top: 0; color: #FF9800; font-size: 24px;">📋 All Detections ({len(all_detections)} total)</h2>
                        <table class="detection-table">
                            <thead>
                                <tr>
                                    <th style="width: 8%;">#</th>
                                    <th style="width: 15%;">Time</th>
                                    <th style="width: 22%;">Pet ID</th>
                                    <th style="width: 40%;">AI Description</th>
                                    <th style="width: 15%;">Google Drive</th>
                                </tr>
                            </thead>
                            <tbody>
            """
            
            # Create highlight photo lookup for badges
            highlight_paths = {photo['photo_path'] for photo in highlight_photos}
            
            for i, detection in enumerate(all_detections, 1):
                chip_display = f"...{detection['chip_id'][-8:]}" if len(detection['chip_id']) > 8 else detection['chip_id']
                time_str = detection['timestamp'].strftime('%H:%M:%S')
                
                # AI Description with fallback
                ai_desc = detection.get('ai_description') or ''
                if isinstance(ai_desc, str):
                    ai_desc = ai_desc.strip()
                else:
                    ai_desc = ''
                    
                if not ai_desc or ai_desc == 'AI analysis not available':
                    ai_desc = '<span style="color: #999; font-style: italic;">No AI analysis available</span>'
                elif len(ai_desc) > 100:
                    ai_desc = ai_desc[:97] + '...'
                
                # Generate Google Drive link
                photo_filename = Path(detection['photo_path']).name
                drive_link = self.get_google_drive_link(photo_filename)
                
                # Create Google Drive button
                if drive_link:
                    drive_button = f'<a href="{drive_link}" target="_blank" class="photo-link" style="background: linear-gradient(135deg, #4285f4, #34a853); color: white; padding: 6px 12px; text-decoration: none; border-radius: 6px; font-size: 11px; font-weight: bold; display: inline-block;">📸 View Photo</a>'
                else:
                    drive_button = '<span style="color: #999; font-size: 11px; font-style: italic;">Not uploaded</span>'
                
                # Check if this is a highlight photo
                if detection['photo_path'] in highlight_paths:
                    drive_button += '<br><span class="highlight-badge" style="background: linear-gradient(135deg, #ff6b6b, #ff5252); color: white; padding: 2px 6px; border-radius: 10px; font-size: 10px; font-weight: bold; margin-top: 4px; display: inline-block;">★ HIGHLIGHT</span>'
                
                html_body += f"""
                                <tr>
                                    <td><strong>{i}</strong></td>
                                    <td class="timestamp">{time_str}</td>
                                    <td><span class="chip-id">{chip_display}</span></td>
                                    <td class="ai-description">{ai_desc}</td>
                                    <td style="text-align: center;">{drive_button}</td>
                                </tr>
                """
            
            html_body += """
                            </tbody>
                        </table>
                    </div>
            """
            
            # Pet activity breakdown summary
            if analysis['chip_summary']:
                html_body += """
                    <div style="background: linear-gradient(135deg, #e8f5e8, #c8e6c8); padding: 20px; border-radius: 10px; margin: 20px 0; border-left: 5px solid #4CAF50;">
                        <h2 style="margin-top: 0; color: #4CAF50; font-size: 24px;">🐾 Pet Activity Summary</h2>
                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px;">
                """
                for chip_id, count in analysis['chip_summary'].items():
                    chip_display = f"...{chip_id[-8:]}" if len(chip_id) > 8 else chip_id
                    html_body += f"""
                            <div style="background-color: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                                <div style="font-size: 20px; font-weight: bold; color: #4CAF50;">{count}</div>
                                <div style="color: #666; font-size: 14px; margin-top: 5px;">Pet {chip_display}</div>
                            </div>
                    """
                html_body += """
                        </div>
                    </div>
                """
            
            # Create pet-specific photo galleries with animal detection grouping
            pet_photos = self.group_photos_by_pet_and_timeframe(all_detections)
            
            if pet_photos:
                html_body += f"""
                    <div style="background: linear-gradient(135deg, #f0fff0, #e8ffe8); padding: 20px; border-radius: 10px; margin: 20px 0; border-left: 5px solid #32CD32;">
                        <h2 style="margin-top: 0; color: #32CD32; font-size: 24px;">� Pet Photo Gallery</h2>
                        <p style="font-size: 16px; color: #666; margin-bottom: 20px;">Photos organized by pet, showing only images with detected animals:</p>
                """
                
                for pet_id, pet_data in pet_photos.items():
                    chip_display = f"...{pet_id[-8:]}" if len(pet_id) > 8 else pet_id
                    animal_photos = pet_data['animal_photos']
                    
                    if animal_photos:  # Only show pets with animal photos
                        html_body += f"""
                        <div style="background-color: white; padding: 20px; margin: 15px 0; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-left: 4px solid #32CD32;">
                            <h3 style="color: #32CD32; margin-top: 0; font-size: 20px;">🏷️ Pet {chip_display}</h3>
                            <div style="margin-bottom: 15px;">
                                <span style="background-color: #e8ffe8; padding: 5px 10px; border-radius: 15px; font-size: 12px; color: #32CD32; font-weight: bold;">
                                    {len(animal_photos)} photos with animals detected
                                </span>
                            </div>
                            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px;">
                        """
                        
                        for photo in animal_photos:
                            time_str = photo['timestamp'].strftime('%H:%M:%S')
                            photo_filename = Path(photo['photo_path']).name
                            ai_desc = photo.get('ai_description') or ''
                            if isinstance(ai_desc, str):
                                ai_desc = ai_desc.strip()
                            else:
                                ai_desc = ''
                                
                            if not ai_desc or ai_desc == 'AI analysis not available':
                                ai_desc = 'Animal detected in photo'
                            
                            # Check if this is a highlight photo
                            highlight_badge = ''
                            if photo['photo_path'] in highlight_paths:
                                highlight_badge = '<div style="position: absolute; top: 10px; right: 10px; background: linear-gradient(135deg, #FFD700, #FFA500); color: white; padding: 5px 8px; border-radius: 10px; font-size: 11px; font-weight: bold;">⭐ BEST</div>'
                            
                            # Get Google Drive link for this photo
                            drive_link = self.get_google_drive_link(photo_filename)
                            drive_button = ''
                            if drive_link:
                                drive_button = f'<a href="{drive_link}" target="_blank" style="background: linear-gradient(135deg, #4285f4, #34a853); color: white; padding: 8px 16px; text-decoration: none; border-radius: 6px; font-size: 12px; font-weight: bold; display: inline-block; margin-top: 8px;">📸 View in Drive</a>'
                            
                            html_body += f"""
                                <div style="background-color: #fafafa; padding: 15px; border-radius: 8px; position: relative; border: 1px solid #e0e0e0;">
                                    {highlight_badge}
                                    <img src="cid:photo_{photo_filename}" style="width: 100%; height: auto; border-radius: 6px; margin-bottom: 10px;" id="{photo_filename}">
                                    <div style="text-align: center;">
                                        <div style="font-weight: bold; color: #32CD32; margin-bottom: 5px;">{time_str}</div>
                                        <div style="font-style: italic; color: #555; font-size: 12px; line-height: 1.4; margin-bottom: 8px;">{ai_desc}</div>
                                        {drive_button}
                                    </div>
                                </div>
                            """
                        
                        html_body += "</div></div>"
                
                html_body += "</div>"
            
            # Photo Highlight Reel (now simplified)
            if highlight_photos:
                html_body += f"""
                    <div style="background: linear-gradient(135deg, #f5f5ff, #e8e8ff); padding: 20px; border-radius: 10px; margin: 20px 0; border-left: 5px solid #9C27B0;">
                        <h2 style="margin-top: 0; color: #9C27B0; font-size: 24px;">⭐ Top Highlights</h2>
                        <p style="font-size: 16px; color: #666; margin-bottom: 20px;">The {len(highlight_photos)} highest quality photos from today:</p>
                        
                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
                """
                
                for i, photo in enumerate(highlight_photos):
                    time_str = photo['timestamp'].strftime('%H:%M:%S')
                    chip_short = f"...{photo['chip_id'][-8:]}" if len(photo['chip_id']) > 8 else photo['chip_id']
                    photo_filename = Path(photo['photo_path']).name
                    
                    ai_desc = photo.get('ai_description') or ''
                    if isinstance(ai_desc, str):
                        ai_desc = ai_desc.strip()
                    else:
                        ai_desc = ''
                        
                    if not ai_desc or ai_desc == 'AI analysis not available':
                        ai_desc = 'High quality photo'
                    elif len(ai_desc) > 60:
                        ai_desc = ai_desc[:57] + '...'
                    
                    html_body += f"""
                            <div style="background-color: white; padding: 12px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center;">
                                <img src="cid:photo{i}" style="width: 100%; height: auto; border-radius: 6px; margin-bottom: 8px;" id="highlight_{photo_filename}">
                                <div style="font-size: 11px; font-weight: bold; color: #9C27B0;">{time_str}</div>
                                <div style="font-size: 10px; color: #666; margin-top: 2px;">Pet {chip_short}</div>
                            </div>
                    """
                
                html_body += """
                        </div>
                    </div>
                """
            
            html_body += f"""
                    <hr style="margin: 30px 0; border: 2px solid #ddd;">
                    <footer style="text-align: center; background: linear-gradient(135deg, #f8f9fa, #e9ecef); padding: 20px; border-radius: 10px;">
                        <p style="margin: 0; font-size: 14px; color: #666; line-height: 1.6;">
                            <strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
                            🔧 <strong>Pet Chip Reader System v2.1.0</strong> | Enhanced Daily Digest with Photo Highlights<br>
                            📧 Delivered to: {self.config['digest_email']}
                        </p>
                    </footer>
                </div>
            </body>
            </html>
            """
            
            # Create text version (fallback)
            text_body = f"Daily Pet Activity Report\\n========================\\n\\n"
            text_body += f"📅 Date: {date_str}\\n\\n"
            text_body += f"📊 Activity Summary:\\n• Total detections: {analysis['total_detections']}\\n• Unique pets: {analysis['unique_chips']}\\n"
            
            if highlight_photos:
                text_body += f"\\n📸 This email includes {len(highlight_photos)} photo attachments from today's activity.\\n"
            
        return {'subject': subject, 'html_body': html_body, 'text_body': text_body}
    
    def send_enhanced_digest(self, digest_data, highlight_photos, all_detections, dry_run=False):
        """Send enhanced digest with photo attachments"""
        if not self.config['daily_digest_enabled']:
            print("Daily digest is disabled in configuration")
            return False
            
        if not all([self.config['smtp_user'], self.config['smtp_pass'], self.config['digest_email']]):
            print("Email configuration incomplete")
            return False
        
        if dry_run:
            print("DRY RUN - Would send enhanced email with photos:")
            print(f"To: {self.config['digest_email']}")
            print(f"Subject: {digest_data['subject']}")
            print(f"Photo attachments: {len(highlight_photos)}")
            for i, photo in enumerate(highlight_photos):
                print(f"  Photo {i+1}: {Path(photo['photo_path']).name} ({photo['file_size']} bytes)")
            return True
        
        try:
            # Create multipart message
            msg = MIMEMultipart('related')
            msg['From'] = self.config['email_from']
            msg['To'] = self.config['digest_email']
            msg['Subject'] = digest_data['subject']
            
            # Create alternative container for text and HTML
            msg_alternative = MIMEMultipart('alternative')
            msg.attach(msg_alternative)
            
            # Add text version
            text_part = MIMEText(digest_data['text_body'], 'plain')
            msg_alternative.attach(text_part)
            
            # Add HTML version
            html_part = MIMEText(digest_data['html_body'], 'html')
            msg_alternative.attach(html_part)
            
            # Add photo attachments
            attached_photos = set()
            
            # First add highlight photos
            for i, photo in enumerate(highlight_photos):
                try:
                    with open(photo['photo_path'], 'rb') as f:
                        img_data = f.read()
                    
                    # Create image attachment for highlight photos
                    img = MIMEImage(img_data)
                    img.add_header('Content-ID', f'<photo{i}>')
                    img.add_header('Content-Disposition', f'attachment; filename="{Path(photo["photo_path"]).name}"')
                    msg.attach(img)
                    
                    # Also add with filename-based CID for clickable links
                    photo_filename = Path(photo['photo_path']).name
                    if photo_filename not in attached_photos:
                        img_copy = MIMEImage(img_data)
                        img_copy.add_header('Content-ID', f'<photo_{photo_filename}>')
                        msg.attach(img_copy)
                        attached_photos.add(photo_filename)
                    
                except Exception as e:
                    print(f"Failed to attach highlight photo {photo['photo_path']}: {e}")
            
            # Add any additional animal photos that aren't already attached
            pet_photos = self.group_photos_by_pet_and_timeframe(all_detections)
            for pet_data in pet_photos.values():
                for photo in pet_data['animal_photos']:
                    photo_filename = Path(photo['photo_path']).name
                    if photo_filename not in attached_photos:
                        try:
                            with open(photo['photo_path'], 'rb') as f:
                                img_data = f.read()
                            
                            # Create image attachment
                            img = MIMEImage(img_data)
                            img.add_header('Content-ID', f'<photo_{photo_filename}>')
                            img.add_header('Content-Disposition', f'attachment; filename="{photo_filename}"')
                            msg.attach(img)
                            attached_photos.add(photo_filename)
                            
                        except Exception as e:
                            print(f"Failed to attach animal photo {photo['photo_path']}: {e}")
            
            # Send email
            with smtplib.SMTP(self.config['smtp_host'], self.config['smtp_port']) as server:
                server.starttls()
                server.login(self.config['smtp_user'], self.config['smtp_pass'])
                server.send_message(msg)
            
            print(f"✓ Enhanced daily digest sent to {self.config['digest_email']} with {len(highlight_photos)} photos")
            return True
            
        except Exception as e:
            print(f"✗ Failed to send enhanced daily digest: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description='Generate enhanced daily pet activity digest with photos')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be sent without sending')
    parser.add_argument('--date', help='Target date (YYYY-MM-DD), defaults to today')
    parser.add_argument('--max-photos', type=int, default=6, help='Maximum photos to include')
    
    args = parser.parse_args()
    
    # Determine target date
    if args.date:
        target_date = datetime.strptime(args.date, '%Y-%m-%d').date()
    else:
        target_date = datetime.now().date()
    
    generator = EnhancedDailyDigest()
    generator.config['max_photos_in_digest'] = args.max_photos
    
    print(f"Generating enhanced daily digest for {target_date.strftime('%Y-%m-%d')}...")
    
    # Get detections with photo analysis
    detections = generator.get_daily_detections_with_photos(target_date)
    print(f"Found {len(detections)} detections")
    
    # Select highlight photos
    highlight_photos = generator.select_highlight_photos(detections, args.max_photos)
    print(f"Selected {len(highlight_photos)} photos for highlight reel")
    
    # Analyze activity (reuse existing logic)
    from generate_daily_digest import DailyDigestGenerator
    basic_generator = DailyDigestGenerator()
    basic_detections = basic_generator.get_daily_detections(target_date)
    analysis = basic_generator.analyze_daily_activity(basic_detections)
    
    # Create enhanced email content
    digest_data = generator.create_enhanced_daily_digest(analysis, target_date, highlight_photos, detections)
    
    # Send email
    success = generator.send_enhanced_digest(digest_data, highlight_photos, detections, args.dry_run)
    
    if success and not args.dry_run:
        print("Enhanced daily digest sent successfully!")
    elif args.dry_run:
        print("Dry run completed - no email sent")
    else:
        print("Failed to send enhanced daily digest")
        sys.exit(1)

if __name__ == '__main__':
    main()