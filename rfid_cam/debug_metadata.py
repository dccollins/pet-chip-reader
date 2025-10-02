#!/usr/bin/env python3
"""
Simple test to debug metadata manager issue
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import tempfile
from datetime import datetime, timezone
from PIL import Image

def test_metadata_simple():
    """Simple metadata test"""
    print("Testing metadata creation...")
    
    from image_metadata_manager import ImageMetadataManager
    
    config = {
        'EMBED_METADATA': 'false',  # Disable EXIF for now
        'SAVE_METADATA_JSON': 'true',
        'METADATA_QUALITY': 'high'
    }
    
    manager = ImageMetadataManager(config)
    
    # Create test image
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
        img = Image.new('RGB', (100, 100), 'red')
        img.save(f.name, 'JPEG')
        
        print(f"Created test image: {f.name}")
        
        try:
            # Test create_comprehensive_metadata directly
            metadata = manager.create_comprehensive_metadata(
                image_path=f.name,
                chip_id="123456789012345",
                camera_id=0,
                detection_time=datetime.now(timezone.utc)
            )
            
            print("Metadata keys:", list(metadata.keys()))
            if metadata:
                print("✅ Metadata creation successful")
                print("Version:", metadata.get('version', 'missing'))
                print("System:", metadata.get('system', 'missing'))
            else:
                print("❌ Metadata is empty")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        
        # Cleanup
        os.unlink(f.name)

if __name__ == "__main__":
    test_metadata_simple()