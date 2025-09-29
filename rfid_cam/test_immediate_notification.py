#!/usr/bin/env python3
"""
Test Immediate Notification System
Simulates pet detection with immediate notification + detailed batching
"""

import os
import sys
import time
import logging
from pathlib import Path
from datetime import datetime, timedelta

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from single_camera_test import RFIDCameraSystem

def test_immediate_notifications():
    """Test the immediate notification system"""
    
    print("🚀 TESTING IMMEDIATE NOTIFICATION SYSTEM")
    print("=" * 50)
    print()
    
    # Initialize system
    system = RFIDCameraSystem()
    
    try:
        # Initialize without starting serial (simulation mode)
        system.initialize_camera()  
        system.initialize_notifications()
        
        print("✅ System initialized successfully")
        print()
        
        # Simulate multiple detections of the same chip
        test_chip = "900263003496836"  # Your actual chip
        
        print(f"🧪 Test 1: First contact (should send immediate notification)")
        system.process_tag(test_chip)
        print("   ⏳ Waiting 5 seconds...")
        time.sleep(5)
        
        print(f"🧪 Test 2: Second contact (should NOT send immediate notification - already sent today)")
        system.process_tag(test_chip)
        print("   ⏳ Waiting 5 seconds...")
        time.sleep(5)
        
        print(f"🧪 Test 3: Third contact (still no immediate notification)")
        system.process_tag(test_chip)
        print("   ⏳ Waiting 5 seconds...")
        time.sleep(5)
        
        # Test with different chip
        test_chip2 = "123456789012345"
        print(f"🧪 Test 4: Different chip first contact (should send immediate notification)")
        system.process_tag(test_chip2)
        print("   ⏳ Waiting 5 seconds...")
        time.sleep(5)
        
        print("🧪 Test 5: Wait for batch processing to complete...")
        print("   ⏳ Waiting for detailed reports (up to 35 seconds)...")
        time.sleep(35)  # Wait for batches to process
        
        print()
        print("✅ Test completed!")
        print("📧 Check your notifications:")
        print("   - Should have received 2 immediate notifications (one per unique chip)")
        print("   - Should receive detailed batch reports shortly")
        print()
        
        # Check backup directory
        backup_dir = Path(system.local_backup_dir)
        if backup_dir.exists():
            backup_files = list(backup_dir.glob("*.jpg"))
            if backup_files:
                print(f"💾 Local backup directory has {len(backup_files)} photos")
            else:
                print("💾 Local backup directory is empty (good - uploads successful)")
        
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        system.running = False
        system.cleanup()
        print("🔄 System shutdown complete")

if __name__ == "__main__":
    test_immediate_notifications()