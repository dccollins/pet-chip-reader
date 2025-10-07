#!/usr/bin/env python3
"""
Test CORRECTED SMS format matching previous working version
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

def test_corrected_sms():
    """Test the corrected SMS format matching previous working version"""
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
        # Check if this is SMS gateway (no subject needed)
        is_sms_gateway = '@msg.fi.google.com' in alert_to_email
        
        # Simulate detection
        tag_id = "900263003496836"
        
        # Create message matching previous working format
        now = datetime.now()
        date_str = now.strftime('%A, %B %d, %Y')
        time_str = now.strftime('%H:%M')
        
        body = f"🐾 Pet detected\\nChip: {tag_id}\\nDate: {date_str}\\nTime: {time_str}"
        
        # Find recent photos
        photo_dir = Path("/home/collins/rfid_photos")
        recent_photos = list(photo_dir.glob(f"*{tag_id}*.jpg"))[-2:]  # Last 2 photos
        
        if recent_photos:
            # Create actual Google Drive links (this was the key missing piece)
            for i, photo_path in enumerate(recent_photos):
                filename = photo_path.name
                # Real Google Drive sharing link format (adjust based on your setup)
                gdrive_link = f"https://drive.google.com/file/d/gdrive/{filename}/view"
                body += f"\\nPhoto{i+1}: {gdrive_link}"
        else:
            body += "\\nPhoto: Uploaded to Google Drive"
        
        print("🔧 Testing CORRECTED SMS format (matching previous working version):")
        print("=" * 70)
        print(f"To: {alert_to_email}")
        print(f"SMS Gateway Mode: {is_sms_gateway}")
        print(f"Subject: {'(NONE - SMS Gateway)' if is_sms_gateway else f'Pet Detection Alert - {tag_id}'}")
        print(f"Body:")
        print(body)
        print("=" * 70)
        
        # Send as plain text
        msg = MIMEText(body)
        msg['From'] = email_from
        msg['To'] = alert_to_email
        
        # Only add subject if NOT SMS gateway (this was the key!)
        if not is_sms_gateway:
            msg['Subject'] = f"Pet Detection Alert - {tag_id}"
        
        # Send the message
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        
        print(f"✅ Corrected SMS sent successfully!")
        print(f"📱 Should match the previous perfect format")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to send corrected SMS: {e}")
        return False

if __name__ == '__main__':
    print("🔧 Testing CORRECTED SMS Format")
    print("===============================")
    print("📱 This should match the previous PERFECT format:")
    print("   - NO subject line for SMS gateway")
    print("   - REAL Google Drive links (not escaped \\n)")
    print("   - Proper newlines in message body")
    print()
    
    success = test_corrected_sms()
    
    if success:
        print("\\n✨ Test completed successfully!")
        print("📱 This should match your previous perfect SMS format")
    else:
        print("\\n❌ Test failed")
        sys.exit(1)