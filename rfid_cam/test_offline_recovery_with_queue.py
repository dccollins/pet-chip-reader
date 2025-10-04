#!/usr/bin/env python3
"""
Test Offline Recovery with Real Queue Files

Creates test queue files and runs complete recovery workflow
"""

import os
import sys
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

# Add the scripts directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'scripts'))

from process_offline_queue import OfflineQueueProcessor

def create_test_queues():
    """Create test queue files for offline recovery testing"""
    
    # Get queue directories from config
    processor = OfflineQueueProcessor()
    offline_queue_dir = processor.config.get('offline_queue_dir')
    
    # Create directories if they don't exist
    os.makedirs(offline_queue_dir, exist_ok=True)
    
    print(f"📁 Offline queue directory: {offline_queue_dir}")
    
    # Create test photos directory and sample files
    photos_dir = Path(processor.config.get('photo_dir', '/home/collins/rfid_photos'))
    photos_dir.mkdir(exist_ok=True)
    
    base_time = datetime.now() - timedelta(hours=2)
    pets = ['900263003496836', '987654321098765']
    
    # Create photo upload queue (upload_queue.txt format)
    upload_queue_entries = []
    notification_queue_entries = []
    
    for i in range(5):
        pet_id = pets[i % 2]
        time_offset = timedelta(minutes=i*15)
        detection_time = base_time + time_offset
        
        # Photo filename
        photo_filename = f"{detection_time.strftime('%Y%m%d_%H%M%S')}_{pet_id}_cam0.jpg"
        photo_path = photos_dir / photo_filename
        
        # Create a dummy photo file if it doesn't exist
        if not photo_path.exists():
            # Create a small dummy JPEG file
            dummy_jpeg = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00\xaa\xff\xd9'
            photo_path.write_bytes(dummy_jpeg)
        
        # Add to upload queue (timestamp|photo_path format)
        upload_queue_entries.append(f"{detection_time.isoformat()}|{photo_path}")
        
        # Create notification entries
        email_notification = {
            'type': 'email',
            'timestamp': detection_time.isoformat() + 'Z',
            'recipient': processor.config['digest_email'],
            'data': {
                'tag_id': pet_id,
                'message': f'Pet detected: {pet_id}',
                'photo_links': [str(photo_path)]
            },
            'attempts': 0,
            'sent': False
        }
        notification_queue_entries.append(email_notification)
        
        # SMS every 2nd detection
        if i % 2 == 0:
            sms_notification = {
                'type': 'sms',
                'timestamp': detection_time.isoformat() + 'Z',
                'recipient': processor.config.get('alert_to_sms', '8651234567@msg.fi.google.com'),
                'data': {
                    'tag_id': pet_id,
                    'message': f'🐾 Pet chip {pet_id[-6:]} detected'
                },
                'attempts': 0,
                'sent': False
            }
            notification_queue_entries.append(sms_notification)
    
    # Write upload queue file
    upload_queue_file = os.path.join(offline_queue_dir, 'upload_queue.txt')
    with open(upload_queue_file, 'w') as f:
        for photo_path in upload_queue_entries:
            f.write(f"{photo_path}\n")
    
    # Write notification queue file
    notification_queue_file = os.path.join(offline_queue_dir, 'notification_queue.json')
    with open(notification_queue_file, 'w') as f:
        json.dump(notification_queue_entries, f, indent=2)
    
    return upload_queue_file, notification_queue_file

def test_complete_recovery_workflow():
    """Test the complete offline recovery workflow with real queue files"""
    
    print("🧪 Testing Complete Offline Recovery with Real Queue Files")
    print("=" * 60)
    
    # Create test queues
    print("\n📝 Creating test queue files...")
    upload_queue_file, notification_queue_file = create_test_queues()
    
    print(f"   ✓ Created upload queue: {upload_queue_file}")
    print(f"   ✓ Created notification queue: {notification_queue_file}")
    
    # Initialize processor
    print("\n🔧 Initializing offline queue processor...")
    processor = OfflineQueueProcessor()
    
    # Run complete recovery
    print("\n🚀 Running complete offline recovery...")
    results = processor.complete_offline_recovery(dry_run=False)
    
    if results:
        print("\n✅ Complete offline recovery completed successfully!")
        print(f"   📸 Photos processed: {results.get('photos_processed', 0)}")
        print(f"   📱 Notifications sent: {results.get('notifications_sent', 0)}")
        print(f"   🧠 AI descriptions: {results.get('ai_descriptions', 0)}")
        print(f"   📧 Recovery digest sent: {'✓' if results.get('digest_sent') else '✗'}")
    else:
        print("❌ Offline recovery failed")
    
    return results

def cleanup_test_files():
    """Clean up test queue files"""
    
    processor = OfflineQueueProcessor()
    offline_queue_dir = processor.config.get('offline_queue_dir')
    
    # Clean up queue files
    upload_queue_file = os.path.join(offline_queue_dir, 'upload_queue.txt')
    notification_queue_file = os.path.join(offline_queue_dir, 'notification_queue.json')
    
    for file_path in [upload_queue_file, notification_queue_file]:
        if os.path.exists(file_path):
            os.remove(file_path)
    
    print("🧹 Cleaned up test queue files")

if __name__ == '__main__':
    try:
        # Test complete workflow
        results = test_complete_recovery_workflow()
        
        if results:
            print("\n" + "=" * 60)
            response = input("🧹 Would you like to clean up test queue files? (Y/n): ")
            if response.lower() != 'n':
                cleanup_test_files()
        
        print("\n🎉 Test completed!")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrupted by user")
        cleanup_test_files()
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()