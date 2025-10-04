#!/usr/bin/env python3
"""
Send Test SMS to Verify Newline Fix

Sends a real test SMS to your Google Fi gateway to confirm newlines work properly
"""

import os
import sys
from datetime import datetime
sys.path.append(os.path.join(os.path.dirname(__file__), 'scripts'))

from process_offline_queue import OfflineQueueProcessor

def send_test_sms():
    """Send test SMS messages to verify newline formatting works"""
    
    print("📱 Sending Test SMS Messages")
    print("=" * 30)
    
    processor = OfflineQueueProcessor()
    
    # Check SMS configuration
    sms_recipient = processor.config.get('alert_to_sms', '')
    if not sms_recipient:
        print("❌ SMS not configured")
        print("   Set ALERT_TO_SMS=865XXXXXX@msg.fi.google.com in .env file")
        return False
    
    if '@msg.fi.google.com' not in sms_recipient:
        print("❌ SMS gateway format incorrect")
        print(f"   Current: {sms_recipient}")
        print("   Expected: 865XXXXXX@msg.fi.google.com")
        return False
    
    print(f"📧 SMS Gateway: {sms_recipient}")
    print(f"⏰ Time: {datetime.now().strftime('%H:%M:%S')}")
    
    # Test 1: Simple newline test
    print("\n📤 Test 1: Simple newline test...")
    test1_message = "🐾 SMS Test 1\nLine 2: Newlines working?\nLine 3: Success!"
    success1 = processor.send_simple_email(test1_message, sms_recipient)
    
    if success1:
        print("   ✅ Sent successfully")
    else:
        print("   ❌ Failed to send")
        return False
    
    # Wait a moment
    import time
    time.sleep(3)
    
    # Test 2: Recovery digest format
    print("\n📤 Test 2: Recovery digest format...")
    test_digest_data = {
        'total_detections': 7,
        'unique_chips': 2,
        'time_span_hours': 2,
        'most_active_chip': '900263003496836',
        'max_detections': 4,
        'chip_detections': {
            '900263003496836': ['t1', 't2', 't3', 't4'],
            '987654321098765': ['t1', 't2', 't3']
        }
    }
    
    digest_message = processor.create_sms_digest(test_digest_data)
    print(f"   Message: {repr(digest_message)}")
    
    success2 = processor.send_digest_sms(digest_message)
    
    if success2:
        print("   ✅ Sent successfully")
    else:
        print("   ❌ Failed to send")
        return False
    
    # Wait a moment
    time.sleep(3)
    
    # Test 3: Individual notification format
    print("\n📤 Test 3: Individual notification format...")
    test_notification_data = {
        'tag_id': '900263003496836',
        'message': '🐾 Pet chip 496836 detected'
    }
    
    success3 = processor.send_queued_sms(test_notification_data)
    
    if success3:
        print("   ✅ Sent successfully")
    else:
        print("   ❌ Failed to send")
        return False
    
    print("\n🎉 ALL TEST SMS MESSAGES SENT!")
    print("📱 Check your phone - you should receive 3 text messages:")
    print("   1. Simple multi-line test message")
    print("   2. Recovery digest with proper line breaks")
    print("   3. Individual pet detection notification")
    print("\nIf newlines appear correctly (not as \\n), the fix is working! ✅")
    
    return True

if __name__ == '__main__':
    print("⚠️  This will send 3 test SMS messages to your configured phone number.")
    response = input("Continue? (y/N): ")
    
    if response.lower() == 'y':
        success = send_test_sms()
        if not success:
            print("\n❌ Test failed - check configuration")
    else:
        print("Test cancelled")