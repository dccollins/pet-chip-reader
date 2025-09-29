#!/usr/bin/env python3
"""
Test Local Backup and Retry System
Simulates Google Drive failure and tests local backup with retry
"""

import os
import sys
import time
import subprocess
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from single_camera_test import RFIDCameraSystem

def simulate_gdrive_failure():
    """Temporarily break rclone to test backup system"""
    print("🚫 Simulating Google Drive failure...")
    
    # Rename rclone temporarily to cause failure
    original_path = "/usr/bin/rclone"
    backup_path = "/usr/bin/rclone.backup"
    
    if Path(original_path).exists():
        try:
            subprocess.run(['sudo', 'mv', original_path, backup_path], check=True)
            print("   ✅ Temporarily disabled rclone")
            return True
        except subprocess.CalledProcessError:
            print("   ❌ Could not disable rclone (permission denied)")
            return False
    else:
        print("   ⚠️ rclone not found at expected location")
        return False

def restore_gdrive():
    """Restore rclone functionality"""
    print("🔄 Restoring Google Drive functionality...")
    
    original_path = "/usr/bin/rclone"
    backup_path = "/usr/bin/rclone.backup"
    
    if Path(backup_path).exists():
        try:
            subprocess.run(['sudo', 'mv', backup_path, original_path], check=True)
            print("   ✅ rclone restored")
            return True
        except subprocess.CalledProcessError:
            print("   ❌ Could not restore rclone (permission denied)")
            return False
    else:
        print("   ⚠️ rclone backup not found")
        return False

def test_backup_and_retry():
    """Test the backup and retry system"""
    
    print("🔧 TESTING BACKUP AND RETRY SYSTEM")
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
        
        # Phase 1: Test with Google Drive working
        print("🧪 Phase 1: Normal operation (Google Drive working)")
        test_chip = "900263003496836"
        system.process_tag(test_chip)
        print("   ⏳ Waiting 3 seconds...")
        time.sleep(3)
        
        # Phase 2: Simulate Google Drive failure
        if simulate_gdrive_failure():
            print()
            print("🧪 Phase 2: Testing with Google Drive failure")
            system.process_tag(test_chip)  # This should trigger local backup
            print("   ⏳ Waiting 3 seconds...")
            time.sleep(3)
            
            # Check if backup directory has photos
            backup_dir = Path(system.local_backup_dir)
            backup_files = list(backup_dir.glob("*.jpg"))
            print(f"   📁 Backup directory has {len(backup_files)} photos")
            
            # Phase 3: Restore Google Drive and test retry
            print()
            print("🧪 Phase 3: Restoring Google Drive and testing retry")
            restore_gdrive()
            
            # Wait for retry processor to attempt uploads
            print("   ⏳ Waiting for retry processor (30 seconds)...")
            time.sleep(30)
            
            # Check if backup directory is cleaned up
            backup_files_after = list(backup_dir.glob("*.jpg"))
            print(f"   📁 Backup directory now has {len(backup_files_after)} photos")
            
            if len(backup_files_after) < len(backup_files):
                print("   ✅ Retry system working - photos uploaded and cleaned up")
            else:
                print("   ⚠️ Photos still in backup (retry may still be in progress)")
        
        print()
        print("✅ Backup and retry test completed!")
        print("📧 Check your notifications - should have received immediate alerts")
        
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Always restore rclone if it was disabled
        restore_gdrive()
        
        # Cleanup
        system.running = False
        system.cleanup()
        print("🔄 System shutdown complete")

if __name__ == "__main__":
    print("⚠️  This test requires sudo access to temporarily disable rclone")
    print("⚠️  Press Ctrl+C to cancel, or Enter to continue...")
    try:
        input()
        test_backup_and_retry()
    except KeyboardInterrupt:
        print("\n❌ Test cancelled by user")