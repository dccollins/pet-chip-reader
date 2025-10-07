#!/usr/bin/env python3
"""
Test SMS with REAL Google Drive links - final test
"""

import os
import sys
import smtplib
import subprocess
import json
from datetime import datetime
from pathlib import Path
from email.mime.text import MIMEText

# Add the src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from dotenv import load_dotenv

def get_real_gdrive_link(filename):
    """Get real Google Drive link for a file"""
    try:
        cmd = ['rclone', 'lsjson', f"gdrive:rfid_photos/{filename}"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            file_info = json.loads(result.stdout)
            if file_info and len(file_info) > 0:
                file_id = file_info[0].get('ID')
                if file_id:
                    return f"https://drive.google.com/file/d/{file_id}/view"
    except Exception as e:
        print(f"Warning: Could not get link for {filename}: {e}")
    
    return None

def test_sms_with_real_links():
    """Test SMS with actual working Google Drive links"""
    load_dotenv()
    
    # Get email credentials
    smtp_host = os.getenv('SMTP_HOST', '')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    smtp_user = os.getenv('SMTP_USER', '')
    smtp_pass = os.getenv('SMTP_PASS', '')
    email_from = os.getenv('EMAIL_FROM', '')
    alert_to_email = os.getenv('ALERT_TO_EMAIL', '')
    
    if not all([smtp_host, smtp_user, smtp_pass, email_from, alert_to_email]):
        print("❌ Email configuration incomplete")
        return False
    
    try:
        # Check if this is SMS gateway
        is_sms_gateway = '@msg.fi.google.com' in alert_to_email
        
        # Simulate detection
        tag_id = "900263003496836"
        
        # Create message
        now = datetime.now()
        date_str = now.strftime('%A, %B %d, %Y')
        time_str = now.strftime('%H:%M')
        
        body = f"🐾 Pet detected{chr(10)}Chip: {tag_id}{chr(10)}Date: {date_str}{chr(10)}Time: {time_str}"
        
        # Find recent photos and get REAL links
        photo_dir = Path("/home/collins/rfid_photos")
        recent_photos = list(photo_dir.glob(f"*{tag_id}*.jpg"))[-2:]  # Last 2 photos
        
        if recent_photos:
            print("🔍 Getting real Google Drive links...")
            for i, photo_path in enumerate(recent_photos):
                filename = photo_path.name
                real_link = get_real_gdrive_link(filename)
                if real_link:
                    body += f"{chr(10)}Photo{i+1}: {real_link}"
                    print(f"✅ Got real link for {filename}")
                else:
                    body += f"{chr(10)}Photo{i+1}: Upload pending for {filename}"
                    print(f"⚠️  Could not get link for {filename}")
        else:
            body += f"{chr(10)}Photo: Uploaded to Google Drive"
        
        print("\\n🔧 Testing SMS with REAL Google Drive links:")
        print("=" * 70)
        print(f"To: {alert_to_email}")
        print(f"SMS Gateway Mode: {is_sms_gateway}")
        print(f"Subject: {'(NONE - SMS Gateway)' if is_sms_gateway else f'Pet Detection Alert - {tag_id}'}")
        print("Body:")
        print("---")
        print(body)
        print("---")
        print("=" * 70)
        
        # Send as plain text
        msg = MIMEText(body)
        msg['From'] = email_from
        msg['To'] = alert_to_email
        
        # Only add subject if NOT SMS gateway
        if not is_sms_gateway:
            msg['Subject'] = f"Pet Detection Alert - {tag_id}"
        
        # Send the message
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        
        print(f"✅ SMS with REAL Google Drive links sent successfully!")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to send SMS with real links: {e}")
        return False

if __name__ == '__main__':
    print("🔧 Testing SMS with REAL Google Drive Links")
    print("===========================================")
    print("🎯 This should send WORKING clickable links!")
    print("📱 Links format: https://drive.google.com/file/d/FILE_ID/view")
    print()
    
    success = test_sms_with_real_links()
    
    if success:
        print("\\n✨ Test completed successfully!")
        print("📱 Check your phone - links should be CLICKABLE and WORKING")
        print("🔗 No more 'Document Lookup failed' errors!")
    else:
        print("\\n❌ Test failed")
        sys.exit(1)