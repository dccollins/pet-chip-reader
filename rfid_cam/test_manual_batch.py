#!/usr/bin/env python3
"""
Manual Batch Processing Test
Manually trigger batch processing with existing photos to demonstrate AI analysis and final notification
"""

import sys
import os
import time
from datetime import datetime
from pathlib import Path

# Add the current directory to path
sys.path.append('/home/collins/repos/pet-chip-reader/rfid_cam')

def simulate_batch_processing():
    """Manually simulate batch processing with recent photos"""
    
    print("🧠 MANUAL BATCH PROCESSING TEST")
    print("=" * 50)
    
    # Import the system class
    try:
        from src.single_camera_test import RFIDCameraSystem
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return
    
    # Initialize system (minimal setup for testing)
    print("🔧 Initializing batch processor...")
    system = RFIDCameraSystem()
    
    # Find recent photos for the test chip
    chip_id = "900263003496836"
    photo_dir = Path('/home/collins/rfid_photos')
    
    # Get recent photos for this chip
    pattern = f"*_{chip_id}_cam0.jpg"
    recent_photos = list(photo_dir.glob(pattern))
    recent_photos = sorted(recent_photos, key=lambda x: x.stat().st_mtime, reverse=True)[:3]  # Last 3 photos
    
    if not recent_photos:
        print(f"❌ No recent photos found for chip {chip_id}")
        return
    
    print(f"📸 Found {len(recent_photos)} recent photos for chip {chip_id}:")
    for i, photo in enumerate(recent_photos, 1):
        print(f"   {i}. {photo.name}")
    
    # Create mock detections from these photos
    detections = []
    for i, photo_path in enumerate(recent_photos):
        # Create mock photo links (using recent successful uploads)
        photo_links = [
            "https://drive.google.com/file/d/1SjLlHQ1tMjFa9xtzf4__Ns5ajzeN-M3t/view",
            "https://drive.google.com/file/d/16a1YN52lHyja9gzqWlNZ_jo-t4CAMkdY/view", 
            "https://drive.google.com/file/d/1rVmvhn-LarS2KgxlgirZ0iL0ysbC5WSF/view"
        ]
        
        detection = {
            'chip_id': chip_id,
            'timestamp': datetime.now(),
            'photo_paths': [photo_path],
            'photo_links': [photo_links[i % len(photo_links)]]
        }
        detections.append(detection)
    
    print(f"\n🤖 PROCESSING BATCH OF {len(detections)} DETECTIONS...")
    print("⏱️  This may take 30-60 seconds for AI analysis...")
    
    try:
        # Process the batch manually
        best_detection = system._select_best_detection(detections)
        
        if best_detection:
            print(f"✅ AI selected best photo: {best_detection['photo_paths'][0].name}")
            if 'animal_description' in best_detection:
                print(f"🐾 Animal identified: {best_detection['animal_description'] or 'unknown'}")
            
            # Calculate stats
            stats = system._calculate_encounter_stats(chip_id)
            print(f"📊 Encounter stats calculated")
            
            # Send the notification
            print(f"\n📧 SENDING FINAL NOTIFICATION...")
            system._send_batch_notification(best_detection, stats)
            print(f"✅ BATCH NOTIFICATION SENT!")
            
        else:
            print("❌ No valid detection found")
            
    except Exception as e:
        print(f"❌ Batch processing failed: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n🎯 CHECK YOUR PHONE FOR THE MESSAGE!")
    print(f"📱 You should receive a text with:")
    print(f"   • AI animal identification")
    print(f"   • Full date and time")
    print(f"   • Encounter statistics")
    print(f"   • Best photo link")

if __name__ == "__main__":
    simulate_batch_processing()