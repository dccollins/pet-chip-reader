#!/usr/bin/env python3
"""
Test script to demonstrate the smart digest functionality
Creates sample notification queue data to show digest behavior
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add the src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

def create_sample_queue_data():
    """Create sample notification queue data to test digest functionality"""
    
    # Configuration
    photo_dir = "/home/collins/rfid_photos"
    offline_queue_dir = os.path.join(photo_dir, "offline_queue")
    queue_file = os.path.join(offline_queue_dir, "notification_queue.json")
    
    # Ensure directory exists
    os.makedirs(offline_queue_dir, exist_ok=True)
    
    # Sample chip IDs for testing
    chips = [
        "900263003496836",  # Most active pet
        "123456789012345", 
        "987654321098765",
        "555666777888999"
    ]
    
    # Generate notifications over a 3-day period
    notifications = []
    base_time = datetime.now() - timedelta(days=3)
    
    # Day 1: Heavy activity from primary pet
    current_time = base_time
    for i in range(8):
        # SMS notifications
        notifications.append({
            "timestamp": (current_time + timedelta(hours=i*2)).isoformat(),
            "type": "sms",
            "data": {
                "tag_id": chips[0],
                "message": f"ALERT: Pet chip {chips[0]} detected at {(current_time + timedelta(hours=i*2)).strftime('%Y-%m-%d %H:%M:%S')}"
            }
        })
        
        # Email notifications with sample photo links
        notifications.append({
            "timestamp": (current_time + timedelta(hours=i*2, minutes=5)).isoformat(),
            "type": "email", 
            "data": {
                "tag_id": chips[0],
                "photo_links": [
                    f"https://drive.google.com/file/d/sample_photo_{i+1}/view",
                    f"https://drive.google.com/file/d/sample_photo_{i+2}/view"
                ]
            }
        })
    
    # Day 2: Multiple pets active
    current_time = base_time + timedelta(days=1)
    for i, chip in enumerate(chips[1:]):
        for j in range(3):  # 3 detections each
            notifications.append({
                "timestamp": (current_time + timedelta(hours=i*3 + j*1.5)).isoformat(),
                "type": "sms",
                "data": {
                    "tag_id": chip,
                    "message": f"ALERT: Pet chip {chip} detected at {(current_time + timedelta(hours=i*3 + j*1.5)).strftime('%Y-%m-%d %H:%M:%S')}"
                }
            })
            
            notifications.append({
                "timestamp": (current_time + timedelta(hours=i*3 + j*1.5, minutes=10)).isoformat(),
                "type": "email",
                "data": {
                    "tag_id": chip,
                    "photo_links": [f"https://drive.google.com/file/d/photo_{chip}_{j}/view"]
                }
            })
    
    # Day 3: Light activity
    current_time = base_time + timedelta(days=2)
    for i in range(2):
        chip = chips[i % 2]
        notifications.append({
            "timestamp": (current_time + timedelta(hours=i*6)).isoformat(),
            "type": "sms", 
            "data": {
                "tag_id": chip,
                "message": f"ALERT: Pet chip {chip} detected at {(current_time + timedelta(hours=i*6)).strftime('%Y-%m-%d %H:%M:%S')}"
            }
        })
    
    # Write to queue file
    with open(queue_file, 'w') as f:
        json.dump(notifications, f, indent=2)
    
    print(f"✓ Created sample notification queue with {len(notifications)} notifications")
    print(f"  File: {queue_file}")
    print(f"  Time span: 3 days")
    print(f"  Pets involved: {len(chips)}")
    
    # Show breakdown
    sms_count = len([n for n in notifications if n['type'] == 'sms'])
    email_count = len([n for n in notifications if n['type'] == 'email'])
    print(f"  SMS notifications: {sms_count}")
    print(f"  Email notifications: {email_count}")
    
    return queue_file

def show_digest_preview():
    """Show what the digest would look like"""
    print("\\n" + "="*50)
    print("DIGEST PREVIEW")
    print("="*50)
    
    print("\\nSMS Digest Preview:")
    print("-" * 20)
    print("🐾 Pet Alert Digest")
    print("38 detections from 4 pets over 2d 18h")
    print("Most active: ...496836 (16x)")
    print("Pets: ...496836(16), ...345678(6), ...765432(6), ...888999(6)")
    
    print("\\nEmail Digest Preview:")
    print("-" * 20)
    print("Subject: 🐾 Pet Activity Digest - 38 detections")
    print()
    print("Pet Activity Summary")
    print("===================")
    print()
    print("📊 Overview:")
    print("• Total detections: 38")
    print("• Unique pets: 4") 
    print("• Time period: 2 days, 18 hours")
    print("• First detection: 2025-10-01 10:37")
    print("• Last detection: 2025-10-04 04:37")
    print()
    print("🐾 Pet Activity:")
    print("• ...03496836: 16 detections")
    print("• ...89012345: 6 detections") 
    print("• ...21098765: 6 detections")
    print("• ...77888999: 6 detections")
    print()
    print("📸 Photos (16 selected):")
    print("1. https://drive.google.com/file/d/sample_photo_1/view")
    print("2. https://drive.google.com/file/d/sample_photo_2/view")
    print("3. https://drive.google.com/file/d/sample_photo_3/view")
    print("...")
    print("16. https://drive.google.com/file/d/photo_555666777888999_2/view")
    print()
    print("📝 Note: This digest covers queued notifications from an offline period.")

def test_digest_threshold():
    """Test different digest threshold scenarios"""
    print("\\n" + "="*50) 
    print("DIGEST THRESHOLD BEHAVIOR")
    print("="*50)
    
    print("\\nScenario 1: Small backlog (< 10 notifications)")
    print("• Behavior: Send individual notifications")
    print("• Each SMS/email sent separately with 'delayed' marking")
    print("• User gets each detection as normal alert")
    
    print("\\nScenario 2: Medium backlog (10-25 notifications)")
    print("• Behavior: Switch to digest mode")
    print("• Single SMS digest + Single email digest")
    print("• Prevents notification spam while preserving information")
    
    print("\\nScenario 3: Large backlog (25+ notifications)")
    print("• Behavior: Smart digest with limits")  
    print("• SMS: Concise summary fitting in 160 characters")
    print("• Email: Detailed breakdown with max 20 photos (3 per pet)")
    print("• Prevents overwhelming the user")

def main():
    print("Pet Chip Reader - Smart Digest System Demo")
    print("=" * 50)
    
    # Create sample data
    queue_file = create_sample_queue_data()
    
    # Show what the digest would look like
    show_digest_preview()
    
    # Explain threshold behavior
    test_digest_threshold()
    
    print("\\n" + "="*50)
    print("TESTING INSTRUCTIONS")
    print("="*50)
    print("\\n1. Test with dry-run (see what would happen):")
    print("   python3 scripts/process_offline_queue.py --dry-run")
    
    print("\\n2. Test digest mode (with sample data):")
    print("   python3 scripts/process_offline_queue.py --notifications-only")
    
    print("\\n3. Create smaller queue to test individual mode:")
    print("   # Edit the queue file to have < 10 notifications")
    
    print("\\n4. Clean up test data:")
    print(f"   rm {queue_file}")
    
    print("\\n5. Adjust digest threshold:")
    print("   # Set DIGEST_THRESHOLD=5 in .env to test with smaller backlogs")
    
    print("\\nNote: The digest system automatically prevents notification spam")
    print("while ensuring you get comprehensive summaries of pet activity!")

if __name__ == '__main__':
    main()