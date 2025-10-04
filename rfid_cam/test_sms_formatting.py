#!/usr/bin/env python3
"""
Test SMS Message Formatting

Check if the newlines are being sent correctly in SMS messages
"""

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'scripts'))

from process_offline_queue import OfflineQueueProcessor

def test_sms_formatting():
    """Test SMS message formatting to see if newlines work"""
    
    print("📱 Testing SMS Message Formatting")
    print("=" * 35)
    
    processor = OfflineQueueProcessor()
    
    # Create test digest data
    test_data = {
        'total_detections': 15,
        'unique_chips': 2,
        'time_span_hours': 3,
        'most_active_chip': '900263003496836',
        'max_detections': 8,
        'chip_detections': {
            '900263003496836': ['time1', 'time2', 'time3', 'time4', 'time5', 'time6', 'time7', 'time8'],
            '987654321098765': ['time1', 'time2', 'time3', 'time4', 'time5', 'time6', 'time7']
        }
    }
    
    # Generate SMS digest
    sms_message = processor.create_sms_digest(test_data)
    
    print("📝 Generated SMS Message:")
    print("-" * 25)
    print(f"'{sms_message}'")
    print("-" * 25)
    
    print(f"\n📏 Message length: {len(sms_message)} characters")
    
    # Show character by character to see newlines
    print("\n🔍 Character Analysis:")
    for i, char in enumerate(sms_message):
        if char == '\n':
            print(f"  [{i}]: \\n (newline)")
        elif char == '\\':
            print(f"  [{i}]: \\\\ (backslash)")
        elif ord(char) < 32:
            print(f"  [{i}]: \\x{ord(char):02x} (control)")
        else:
            print(f"  [{i}]: {char}")
    
    # Test simple SMS message
    print("\n🧪 Testing Simple SMS Message:")
    simple_sms = "🐾 Pet detected\nChip: 496836\nTime: now"
    print(f"Message: '{simple_sms}'")
    
    print("\n✅ SMS Formatting Test Complete")

if __name__ == '__main__':
    test_sms_formatting()