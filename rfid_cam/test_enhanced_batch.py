#!/usr/bin/env python3
"""
Enhanced Batch Processing Test
Properly counts actual scan history and simulates AI response to show correct statistics
"""

import sys
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
import re

# Add the current directory to path
sys.path.append('/home/collins/repos/pet-chip-reader/rfid_cam')

def enhanced_batch_test():
    """Enhanced batch test with proper history counting and mock AI"""
    
    print("🧠 ENHANCED BATCH PROCESSING TEST")
    print("=" * 50)
    
    # Import the system class
    try:
        from src.single_camera_test import RFIDCameraSystem
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return
    
    print("🔧 Initializing enhanced batch processor...")
    system = RFIDCameraSystem()
    
    # Analyze your actual scan history
    chip_id = "900263003496836"
    photo_dir = Path('/home/collins/rfid_photos')
    
    # Get ALL photos for this chip from today
    today = datetime.now().strftime('%Y%m%d')
    pattern = f"{today}_*_{chip_id}_cam0.jpg"
    all_photos = list(photo_dir.glob(pattern))
    all_photos = sorted(all_photos, key=lambda x: x.stat().st_mtime)
    
    print(f"📸 Found {len(all_photos)} total scans for chip {chip_id} today:")
    
    # Parse timestamps and calculate encounter windows
    recent_window = datetime.now() - timedelta(minutes=30)
    recent_count = 0
    total_count = len(all_photos)
    
    print(f"📊 ANALYZING SCAN HISTORY:")
    for i, photo in enumerate(all_photos, 1):
        # Extract timestamp from filename
        match = re.search(r'(\d{8})_(\d{6})_', photo.name)
        if match:
            date_str, time_str = match.groups()
            timestamp = datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
            
            if timestamp >= recent_window:
                recent_count += 1
                status = "✅ RECENT"
            else:
                status = "⏰ older"
                
            print(f"   {i:2d}. {timestamp.strftime('%H:%M:%S')} - {photo.name} {status}")
    
    print(f"\n📈 ENCOUNTER STATISTICS:")
    print(f"   Recent visits (last 30 min): {recent_count}")
    print(f"   Total visits today: {total_count}")
    
    # Use the 3 most recent photos for AI analysis simulation
    recent_photos = all_photos[-3:] if len(all_photos) >= 3 else all_photos
    
    print(f"\n🤖 SIMULATING AI ANALYSIS ON {len(recent_photos)} RECENT PHOTOS...")
    
    # Create enhanced detections with proper timestamps
    detections = []
    photo_links = [
        "https://drive.google.com/file/d/1SjLlHQ1tMjFa9xtzf4__Ns5ajzeN-M3t/view",
        "https://drive.google.com/file/d/16a1YN52lHyja9gzqWlNZ_jo-t4CAMkdY/view", 
        "https://drive.google.com/file/d/1rVmvhn-LarS2KgxlgirZ0iL0ysbC5WSF/view"
    ]
    
    for i, photo_path in enumerate(recent_photos):
        detection = {
            'chip_id': chip_id,
            'timestamp': datetime.fromtimestamp(photo_path.stat().st_mtime),
            'photo_paths': [photo_path],
            'photo_links': [photo_links[i % len(photo_links)]]
        }
        detections.append(detection)
    
    # Mock the AI analysis to bypass rate limiting
    print("🎭 MOCKING AI ANALYSIS (bypassing rate limit)...")
    
    # Simulate AI scoring - pick the largest file (usually clearest photo)
    best_detection = max(detections, key=lambda d: d['photo_paths'][0].stat().st_size)
    best_detection['animal_description'] = "tabby cat"  # Mock AI response
    best_detection['ai_score'] = 15
    
    print(f"✅ AI selected best photo: {best_detection['photo_paths'][0].name}")
    print(f"🐾 Animal identified: {best_detection['animal_description']}")
    print(f"📊 AI confidence score: {best_detection['ai_score']}")
    
    # Manually create correct encounter stats
    stats = {
        'recent_encounters': recent_count,
        'total_encounters': total_count,
        'window_minutes': 30
    }
    
    print(f"\n📧 SENDING ENHANCED NOTIFICATION...")
    print(f"📱 Message will show:")
    print(f"   • Animal: {best_detection['animal_description']}")
    print(f"   • Recent visits: {stats['recent_encounters']} in 30 min")
    print(f"   • Total visits: {stats['total_encounters']}")
    print(f"   • Best photo from your {len(detections)} recent scans")
    
    try:
        # Send the corrected notification
        system._send_batch_notification(best_detection, stats)
        print(f"✅ ENHANCED NOTIFICATION SENT!")
        
    except Exception as e:
        print(f"❌ Notification failed: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n🎯 CHECK YOUR PHONE NOW!")
    print(f"📱 You should receive a CORRECTED message with:")
    print(f"   🐾 Animal: tabby cat")
    print(f"   📊 Recent visits: {recent_count} in 30 min") 
    print(f"   📊 Total visits: {total_count}")
    print(f"   📸 Best photo link")

if __name__ == "__main__":
    enhanced_batch_test()