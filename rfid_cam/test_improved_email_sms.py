#!/usr/bin/env python3
"""
Test improved email-to-SMS notification format
Tests the new concise email that gets converted to SMS via Google Fi
"""

import os
import sys
import smtplib
from datetime import datetime
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Add the src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from dotenv import load_dotenv

def test_improved_email_sms():
    """Test the improved email-to-SMS notification format"""
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
        # Simulate a detection with recent photos
        tag_id = "900263003496836"  # Real detected chip ID
        chip_short = f"...{tag_id[-8:]}" if len(tag_id) > 8 else tag_id
        time_str = datetime.now().strftime('%H:%M')
        
        # Find recent photos
        photo_dir = Path("/home/collins/rfid_photos")
        recent_photos = list(photo_dir.glob(f"*{tag_id}*.jpg"))[-2:]  # Last 2 photos
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = email_from
        msg['To'] = alert_to_email
        msg['Subject'] = f"Pet {chip_short} detected"
        
        # Create concise body that works well as SMS
        body = f"🐾 Pet {chip_short} detected {time_str}"
        
        if recent_photos:
            body += f"\\n📸 {len(recent_photos)} photos captured"
            body += f"\\n🔗 Google Drive: rfid_photos/"
            
            # Add filenames for reference
            for photo_path in recent_photos:
                cam_num = "1" if "cam0" in photo_path.name else "2"
                body += f"\\nCam{cam_num}: {photo_path.name}"
        
        msg.attach(MIMEText(body, 'plain'))
        
        print("🧪 Testing improved Email-to-SMS format:")
        print("=" * 60)
        print(f"To: {alert_to_email}")
        print(f"Subject: {msg['Subject']}")
        print(f"Body:\\n{body}")
        print("=" * 60)
        print(f"📊 Message length: {len(body)} characters")
        
        # Send the message
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        
        print(f"✅ Improved email-to-SMS sent successfully!")
        print(f"📱 Should arrive as SMS via Google Fi gateway")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to send improved email: {e}")
        return False

if __name__ == '__main__':
    print("🔧 Testing Improved Email-to-SMS Notification Format")
    print("====================================================")
    
    success = test_improved_email_sms()
    
    if success:
        print("\\n✨ Test completed successfully!")
        print("📱 Check your phone for the improved SMS format")
        print("💡 The message should be much more concise with photo info")
    else:
        print("\\n❌ Test failed")
        sys.exit(1)