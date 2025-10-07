#!/usr/bin/env python3
"""
Test WORKING SMS format - no broken Google Drive links
"""

import os
import sys
import smtplib
from datetime import datetime
from pathlib import Path
from email.mime.text import MIMEText

# Add the src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from dotenv import load_dotenv

def test_working_sms():
    """Test SMS format with working photo references (no broken links)"""
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
        
        # Create message with working format (no broken links)
        now = datetime.now()
        date_str = now.strftime('%A, %B %d, %Y')
        time_str = now.strftime('%H:%M')
        
        body = f"🐾 Pet detected{chr(10)}Chip: {tag_id}{chr(10)}Date: {date_str}{chr(10)}Time: {time_str}"
        
        # Find recent photos
        photo_dir = Path("/home/collins/rfid_photos")
        recent_photos = list(photo_dir.glob(f"*{tag_id}*.jpg"))[-2:]  # Last 2 photos
        
        if recent_photos:
            body += f"{chr(10)}Photos: {len(recent_photos)} captured"
            # Add photo filenames for reference
            for i, photo_path in enumerate(recent_photos):
                filename = photo_path.name
                body += f"{chr(10)}Cam{i+1}: {filename}"
            # Add Google Drive folder reference
            body += f"{chr(10)}Location: Google Drive/rfid_photos/"
        else:
            body += f"{chr(10)}Photo: Uploaded to Google Drive"
        
        print("🔧 Testing WORKING SMS format (no broken links):")
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
        
        print(f"✅ Working SMS sent successfully!")
        print(f"📱 No broken Google Drive links - just file references")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to send working SMS: {e}")
        return False

if __name__ == '__main__':
    print("🔧 Testing WORKING SMS Format")
    print("=============================")
    print("✅ Fixed: No more broken Google Drive links")
    print("📱 Shows: Photo count, filenames, and folder location")
    print("🔗 Simple: Easy to understand references")
    print()
    
    success = test_working_sms()
    
    if success:
        print("\\n✨ Test completed successfully!")
        print("📱 Check SMS - should have working photo info")
        print("🔗 No more 'Document Lookup failed' errors")
    else:
        print("\\n❌ Test failed")
        sys.exit(1)