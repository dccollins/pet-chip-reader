#!/usr/bin/env python3
"""
Test improved SMS notification format
Tests the new concise SMS with photo information
"""

import os
import sys
from datetime import datetime
from pathlib import Path

# Add the src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from dotenv import load_dotenv
from twilio.rest import Client

def test_improved_sms():
    """Test the improved SMS notification format"""
    load_dotenv()
    
    # Get Twilio credentials
    twilio_sid = os.getenv('TWILIO_ACCOUNT_SID', '')
    twilio_token = os.getenv('TWILIO_AUTH_TOKEN', '')
    twilio_from = os.getenv('TWILIO_FROM', '')
    alert_to_sms = os.getenv('ALERT_TO_SMS', '')
    
    if not all([twilio_sid, twilio_token, twilio_from, alert_to_sms]):
        print("❌ Twilio configuration incomplete")
        return False
    
    try:
        client = Client(twilio_sid, twilio_token)
        
        # Simulate a detection with recent photos
        tag_id = "900263003496836"  # Real detected chip ID
        chip_short = f"...{tag_id[-8:]}" if len(tag_id) > 8 else tag_id
        time_str = datetime.now().strftime('%H:%M')
        
        # Find recent photos
        photo_dir = Path("/home/collins/rfid_photos")
        recent_photos = list(photo_dir.glob(f"*{tag_id}*.jpg"))[-2:]  # Last 2 photos
        
        # Create improved message
        message_body = f"🐾 Pet {chip_short} detected {time_str}"
        
        if recent_photos:
            message_body += f"\n📸 {len(recent_photos)} photos captured & uploaded"
            message_body += f"\n🔗 Check Google Drive: rfid_photos/"
            
            # Add specific filenames for reference
            for photo_path in recent_photos:
                cam_num = "1" if "cam0" in photo_path.name else "2" 
                message_body += f"\nCam{cam_num}: {photo_path.name}"
        
        print("🧪 Testing improved SMS format:")
        print("=" * 50)
        print(f"To: {alert_to_sms}")
        print(f"Message:\n{message_body}")
        print("=" * 50)
        
        # Send the message
        message = client.messages.create(
            body=message_body,
            from_=twilio_from,
            to=alert_to_sms
        )
        
        print(f"✅ Improved SMS sent successfully!")
        print(f"📱 Message SID: {message.sid}")
        print(f"📊 Message length: {len(message_body)} characters")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to send improved SMS: {e}")
        return False

if __name__ == '__main__':
    print("🔧 Testing Improved SMS Notification Format")
    print("==========================================")
    
    success = test_improved_sms()
    
    if success:
        print("\n✨ Test completed successfully!")
        print("📱 Check your phone for the improved SMS format")
    else:
        print("\n❌ Test failed")
        sys.exit(1)