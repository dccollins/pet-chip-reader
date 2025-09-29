#!/usr/bin/env python3
"""
Test Daily Summary Email with Thumbnails
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.single_camera_test import RFIDCameraSystem
from datetime import datetime
from pathlib import Path

def create_test_log():
    """Create a test detection log for today"""
    log_file = Path("/home/collins/repos/pet-chip-reader/rfid_cam/daily_detections.log")
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Create test entries for today
    test_entries = [
        f"{today} 09:15:23,987654321098765,20250929_091523_987654321098765_cam0.jpg",
        f"{today} 14:30:45,555666777888999,20250929_143045_555666777888999_cam0.jpg",
        f"{today} 18:22:10,900263003496836,20250929_182210_900263003496836_cam0.jpg",
    ]
    
    with open(log_file, 'w') as f:
        for entry in test_entries:
            f.write(entry + '\n')
    
    print(f"✅ Created test log with {len(test_entries)} entries")
    return log_file

def test_daily_summary():
    """Test the daily summary functionality"""
    print("🧪 TESTING DAILY SUMMARY EMAIL")
    print("=" * 50)
    
    try:
        # Create test log
        log_file = create_test_log()
        
        # Create system instance (minimal setup)
        system = RFIDCameraSystem()
        system.config = {
            'photo_dir': Path('/home/collins/rfid_photos'),
            'email_from': 'dccollins@gmail.com',
            'smtp_host': 'smtp.gmail.com',
            'smtp_port': 587,
            'smtp_user': 'dccollins@gmail.com',
            'smtp_pass': 'tyxw licg kzhn wijc'
        }
        
        # Initialize logger
        import logging
        system.logger = logging.getLogger('test')
        system.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
        system.logger.addHandler(handler)
        
        print(f"📧 Sending daily summary to dccollins@gmail.com...")
        system.send_daily_summary()
        
        print("✅ Daily summary test completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_daily_summary()