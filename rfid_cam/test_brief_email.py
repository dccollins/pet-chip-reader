#!/usr/bin/env python3
"""
Test brief email with Google Drive link
"""

import subprocess
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
import os
from datetime import datetime

def test_brief_notification():
    """Test brief notification with Google Drive link"""
    load_dotenv()
    
    # Test data
    chip_id = "900263003496836"  # Your lost pet chip
    time_str = datetime.now().strftime('%H:%M')
    
    # Get a link to an existing photo
    try:
        result = subprocess.run(
            ['rclone', 'link', 'gdrive:rfid_photos/test_upload.txt'], 
            capture_output=True, text=True, timeout=5
        )
        
        if result.returncode == 0:
            drive_link = result.stdout.strip()
            print(f"✓ Got Google Drive link: {drive_link}")
        else:
            drive_link = "https://drive.google.com/drive/folders/your_folder_id"
            print("⚠ Using fallback link")
    except Exception as e:
        drive_link = "Link unavailable"
        print(f"✗ Link generation failed: {e}")
    
    # Create brief message
    msg = MIMEText(f"""🚨 LOST PET DETECTED!
Chip: {chip_id}
Time: {time_str}
Photo: {drive_link}""")
    
    msg['From'] = os.getenv('EMAIL_FROM')
    msg['To'] = os.getenv('ALERT_TO_EMAIL')
    msg['Subject'] = "🚨 LOST PET FOUND!"
    
    print(f"\nBrief message preview:")
    print(f"Subject: {msg['Subject']}")
    print(f"To: {msg['To']}")
    print(f"Body:\n{msg.get_payload()}")
    
    # Send it
    try:
        with smtplib.SMTP(os.getenv('SMTP_HOST'), int(os.getenv('SMTP_PORT'))) as server:
            server.starttls()
            server.login(os.getenv('SMTP_USER'), os.getenv('SMTP_PASS'))
            server.send_message(msg)
        print(f"\n✅ Brief notification sent!")
        return True
    except Exception as e:
        print(f"✗ Send failed: {e}")
        return False

if __name__ == "__main__":
    test_brief_notification()