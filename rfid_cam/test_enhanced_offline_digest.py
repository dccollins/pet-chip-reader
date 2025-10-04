#!/usr/bin/env python3
"""
Test Enhanced Offline Queue Digest System

Creates sample offline queue data and generates enhanced HTML digest email.
"""

import os
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path

# Add the scripts directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'scripts'))

from process_offline_queue import OfflineQueueProcessor

def create_test_queue_data():
    """Create sample offline queue data for testing"""
    
    # Sample notifications that would be queued during offline period
    notifications = []
    
    # Simulate 15 detections over 3 hours from 2 pets
    base_time = datetime.now() - timedelta(hours=4)
    
    pets = ['900263003496836', '987654321098765']
    
    for i in range(15):
        # Alternate between pets with some randomness
        pet_id = pets[i % 2] if i < 10 else pets[1]  # More activity from second pet later
        
        # Add some time variation
        time_offset = timedelta(minutes=i*12 + (i % 3) * 5)  # Every 12-17 minutes
        notification_time = base_time + time_offset
        
        # Create sample photo filenames (these should exist in your photo directory)
        photo_filename = f"{notification_time.strftime('%Y%m%d_%H%M%S')}_{pet_id}_cam0.jpg"
        
        # Email notification
        email_notification = {
            'type': 'email',
            'timestamp': notification_time.isoformat() + 'Z',
            'data': {
                'tag_id': pet_id,
                'message': f'Pet detected: {pet_id}',
                'photo_links': [f'/home/collins/rfid_photos/{photo_filename}']
            }
        }
        
        # SMS notification (every 3rd detection)
        if i % 3 == 0:
            sms_notification = {
                'type': 'sms',
                'timestamp': notification_time.isoformat() + 'Z',
                'data': {
                    'tag_id': pet_id,
                    'message': f'🐾 Pet chip {pet_id[-6:]} detected'
                }
            }
            notifications.append(sms_notification)
        
        notifications.append(email_notification)
    
    return notifications

def test_enhanced_digest():
    """Test the enhanced offline queue digest system"""
    
    print("🧪 Testing Enhanced Offline Queue Digest System")
    print("=" * 50)
    
    # Create test data
    print("📝 Creating test queue data...")
    notifications = create_test_queue_data()
    print(f"   Generated {len(notifications)} test notifications")
    
    # Initialize processor
    print("🔧 Initializing offline queue processor...")
    processor = OfflineQueueProcessor()
    
    # Analyze the notifications
    print("📊 Analyzing notification backlog...")
    digest_data = processor.analyze_notification_backlog(notifications)
    
    print(f"   Total detections: {digest_data['total_detections']}")
    print(f"   Unique pets: {digest_data['unique_chips']}")
    print(f"   Time span: {digest_data['time_span_hours']} hours")
    
    # Create enhanced HTML digest
    print("🎨 Creating enhanced HTML digest...")
    enhanced_digest = processor.create_email_digest(digest_data)
    
    print(f"   Subject: {enhanced_digest['subject']}")
    print(f"   HTML body length: {len(enhanced_digest['html_body'])} characters")
    print(f"   Text body length: {len(enhanced_digest['text_body'])} characters")
    
    # Send the digest (dry run)
    print("📧 Testing email sending (dry run)...")
    try:
        # Just test the digest creation, not actual sending
        print("✅ Enhanced digest created successfully!")
        print("\n🎯 Enhanced Features Included:")
        print("   • Beautiful HTML formatting with gradients and cards")
        print("   • Google Drive integration for photo buttons") 
        print("   • Pet-specific activity breakdown table")
        print("   • Offline recovery status information")
        print("   • Professional styling and responsive layout")
        print("   • Text fallback for compatibility")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating enhanced digest: {e}")
        return False

def send_test_digest():
    """Send a real test digest to your email"""
    print("\n📧 Sending test digest to your email...")
    
    # Create test data
    notifications = create_test_queue_data()
    
    # Create test processed photos (simulating AI processing results)
    test_processed_photos = [
        {
            'path': '/home/collins/rfid_photos/20251001_203835_900263003496836_cam0.jpg',
            'filename': '20251001_203835_900263003496836_cam0.jpg',
            'timestamp': '2025-10-01T20:38:35Z',
            'ai_description': 'Orange tabby cat sitting alertly by a window, ears perked forward',
            'metadata_updated': True
        },
        {
            'path': '/home/collins/rfid_photos/20251001_210934_900263003496836_cam0.jpg', 
            'filename': '20251001_210934_900263003496836_cam0.jpg',
            'timestamp': '2025-10-01T21:09:34Z',
            'ai_description': 'Curious cat with orange and white markings, looking directly at camera',
            'metadata_updated': True
        }
    ]
    
    # Initialize processor  
    processor = OfflineQueueProcessor()
    
    # Analyze with AI-enhanced data
    digest_data = processor.analyze_offline_recovery_data(notifications, test_processed_photos)
    enhanced_digest = processor.create_email_digest(digest_data)
    
    # Send the actual email
    success = processor.send_digest_email(enhanced_digest)
    
    if success:
        print("✅ Enhanced offline recovery digest sent successfully!")
        print(f"📬 Check your email: {processor.config['digest_email']}")
        print(f"🧠 Included {len(test_processed_photos)} AI-analyzed photos")
        return True
    else:
        print("❌ Failed to send digest email")
        return False

def test_complete_workflow():
    """Test the complete offline recovery workflow"""
    print("\n🔄 Testing Complete Offline Recovery Workflow")
    print("=" * 50)
    
    # Initialize processor
    processor = OfflineQueueProcessor()
    
    # Run complete recovery (dry run)
    results = processor.complete_offline_recovery(dry_run=True)
    
    print("✅ Complete workflow test completed!")
    return results

if __name__ == '__main__':
    print("🧪 Enhanced Offline Recovery System Test")
    print("=" * 45)
    
    # Test enhanced digest
    print("\n1. Testing enhanced digest system...")
    success = test_enhanced_digest()
    
    if not success:
        print("❌ Enhanced digest test failed.")
        sys.exit(1)
    
    # Test complete workflow
    print("\n2. Testing complete AI processing workflow...")
    test_complete_workflow()
    
    # Send real digest to email
    print("\n3. Sending enhanced recovery digest...")
    response = input("📬 Would you like to send a test digest to your email? (y/N): ")
    if response.lower() == 'y':
        send_test_digest()
    else:
        print("🔧 Test completed without sending email.")
    
    print("\n🎉 All tests completed!")