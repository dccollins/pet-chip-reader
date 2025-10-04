#!/usr/bin/env python3
"""
Test SMS Newline Issue

Create a simple test to send SMS via email gateway to check newline handling
"""

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'scripts'))

from process_offline_queue import OfflineQueueProcessor

def test_sms_send():
    """Test sending actual SMS to see newline behavior"""
    
    print("📱 Testing SMS Newline Sending")
    print("=" * 30)
    
    processor = OfflineQueueProcessor()
    
    # Check SMS configuration
    sms_recipient = processor.config.get('alert_to_sms', '')
    if not sms_recipient or '@msg.fi.google.com' not in sms_recipient:
        print("⚠️  SMS gateway not configured")
        print("   Set ALERT_TO_SMS=865XXXXXX@msg.fi.google.com in .env")
        return
    
    print(f"📧 SMS Gateway: {sms_recipient}")
    
    # Test messages with different formatting
    test_messages = [
        # Simple message with newlines
        "🐾 Test SMS\nLine 2\nLine 3",
        
        # Message similar to digest
        "🐾 Pet Digest\n3 detections from 1 pet\nMost active: ...496836 (3x)",
        
        # Single line message
        "🐾 Single line test message"
    ]
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n📤 Sending Test Message {i}:")
        print(f"   Content: {repr(message)}")
        
        success = processor.send_simple_email(message, sms_recipient)
        
        if success:
            print("   ✅ Sent successfully")
        else:
            print("   ❌ Failed to send")
        
        # Wait a moment between sends
        import time
        time.sleep(2)
    
    print("\n✅ SMS Test Complete")
    print("Check your phone to see how newlines appear in the messages")

if __name__ == '__main__':
    response = input("📱 Send test SMS messages? This will send to your configured SMS gateway. (y/N): ")
    if response.lower() == 'y':
        test_sms_send()
    else:
        print("Test cancelled")