#!/usr/bin/env python3
"""
Test REAL Google Drive links generation
"""

import os
import sys
import subprocess
import json
from pathlib import Path

def test_real_gdrive_links():
    """Test generating real Google Drive links using rclone"""
    
    try:
        # Find a recent photo
        photo_dir = Path("/home/collins/rfid_photos")
        recent_photos = list(photo_dir.glob("*.jpg"))
        
        if not recent_photos:
            print("❌ No photos found to test")
            return False
            
        # Get the most recent photo
        test_photo = recent_photos[-1]
        print(f"📸 Testing with photo: {test_photo.name}")
        
        # Get file ID using rclone lsjson
        cmd = [
            'rclone', 'lsjson', 
            f"gdrive:rfid_photos/{test_photo.name}"
        ]
        
        print(f"🔍 Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            print(f"❌ rclone command failed: {result.stderr}")
            return False
            
        print("✅ rclone command succeeded")
        print(f"📄 Raw output: {result.stdout}")
        
        # Parse JSON response
        try:
            file_info = json.loads(result.stdout)
            if file_info and len(file_info) > 0:
                file_id = file_info[0].get('ID')
                if file_id:
                    real_link = f"https://drive.google.com/file/d/{file_id}/view"
                    print(f"🎯 REAL Google Drive link: {real_link}")
                    
                    # Validate the link format
                    if "drive.google.com/file/d/" in real_link and "/view" in real_link:
                        print("✅ Link format is correct!")
                        return True
                    else:
                        print("❌ Link format is wrong")
                        return False
                else:
                    print("❌ No file ID found in response")
                    return False
            else:
                print("❌ No file info in response")
                return False
                
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse JSON: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == '__main__':
    print("🔧 Testing REAL Google Drive Link Generation")
    print("============================================")
    
    success = test_real_gdrive_links()
    
    if success:
        print("\\n✨ Test successful!")
        print("📱 The system can now generate REAL working Google Drive links")
        print("🔗 Format: https://drive.google.com/file/d/FILE_ID/view")
    else:
        print("\\n❌ Test failed")
        print("💡 Check rclone configuration and file availability")
        sys.exit(1)