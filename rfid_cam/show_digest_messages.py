#!/usr/bin/env python3
"""
Generate and display actual digest messages that would be sent
"""

import os
import sys
import json
from datetime import datetime

# Add the scripts directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'scripts'))

from process_offline_queue import OfflineQueueProcessor

def show_actual_digest_messages():
    """Generate and display the actual digest messages that would be sent"""
    
    # Check if sample queue exists
    queue_file = "/home/collins/rfid_photos/offline_queue/notification_queue.json"
    
    if not os.path.exists(queue_file):
        print("❌ No sample queue found. Run 'python3 test_digest_system.py' first.")
        return
    
    # Load the notifications
    with open(queue_file, 'r') as f:
        notifications = json.load(f)
    
    print("🔍 ACTUAL DIGEST MESSAGES")
    print("=" * 50)
    print(f"Processing {len(notifications)} queued notifications...")
    
    # Create processor instance
    processor = OfflineQueueProcessor()
    
    # Analyze the backlog
    digest_data = processor.analyze_notification_backlog(notifications)
    
    # Generate SMS digest
    print("\\n📱 SMS DIGEST MESSAGE:")
    print("-" * 30)
    sms_message = processor.create_sms_digest(digest_data)
    print(f'"{sms_message}"')
    print(f"\\n[Length: {len(sms_message)} characters - fits in SMS]")
    
    # Generate email digest
    print("\\n📧 EMAIL DIGEST MESSAGE:")
    print("-" * 30)
    email_digest = processor.create_email_digest(digest_data)
    
    print(f"SUBJECT: {email_digest['subject']}")
    print("\\nBODY:")
    print(email_digest['body'])
    
    # Show analysis details
    print("\\n🔍 ANALYSIS DETAILS:")
    print("-" * 30)
    print(f"• Total notifications processed: {len(notifications)}")
    print(f"• Total detections: {digest_data['total_detections']}")
    print(f"• Unique pets: {digest_data['unique_chips']}")
    print(f"• Time span: {digest_data['time_span_hours']} hours")
    print(f"• Photos included: {len(digest_data['photo_links'])}")
    print(f"• Most active pet: {digest_data['most_active_chip'][-6:] if digest_data['most_active_chip'] else 'None'} ({digest_data['max_detections']} detections)")
    
    print("\\n✅ These are the actual messages that would be sent to your phone/email!")

if __name__ == '__main__':
    show_actual_digest_messages()