#!/usr/bin/env python3
"""
Test GPS and Image Metadata Integration
Tests the new GPS and metadata features for the pet chip reader system
"""

import os
import sys
import time
import logging
import tempfile
from pathlib import Path
from datetime import datetime, timezone

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from gps_manager import GPSManager
    from image_metadata_manager import ImageMetadataManager
    from PIL import Image
    GPS_TEST_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    GPS_TEST_AVAILABLE = False


def setup_test_logging():
    """Setup logging for testing"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)


def test_gps_manager():
    """Test GPS manager functionality"""
    logger = logging.getLogger(__name__)
    logger.info("🛰️  Testing GPS Manager...")
    
    # Test configuration - GPS disabled for this test since no hardware
    config = {
        'GPS_ENABLED': 'false',  # Disabled for testing without hardware
        'GPS_PORT': '/dev/ttyUSB0',
        'GPS_BAUD': '9600',
        'GPS_TIMEOUT': '5.0'
    }
    
    gps_manager = GPSManager(config)
    
    # Test that GPS is properly disabled
    assert not gps_manager.is_gps_available(), "GPS should be unavailable when disabled"
    assert gps_manager.get_current_location() is None, "Should return None when GPS disabled"
    
    logger.info("✅ GPS Manager test passed (GPS disabled mode)")
    
    # Test with GPS enabled but no hardware (will fail gracefully)
    config_enabled = config.copy()
    config_enabled['GPS_ENABLED'] = 'true'
    config_enabled['GPS_PORT'] = '/dev/nonexistent'  # Non-existent port for testing
    
    gps_manager_enabled = GPSManager(config_enabled)
    
    # Wait a moment for connection attempt
    time.sleep(2)
    
    # Should still be unavailable due to no hardware
    assert not gps_manager_enabled.is_gps_available(), "GPS should be unavailable without hardware"
    
    # Test export function
    export_data = gps_manager_enabled.export_location_data()
    assert export_data['gps_available'] == False, "Export should show GPS unavailable"
    
    # Cleanup
    gps_manager.stop_gps_monitoring()
    gps_manager_enabled.stop_gps_monitoring()
    
    logger.info("✅ GPS Manager test completed successfully")
    return True


def test_metadata_manager():
    """Test image metadata manager functionality"""
    logger = logging.getLogger(__name__)
    logger.info("📄 Testing Image Metadata Manager...")
    
    config = {
        'EMBED_METADATA': 'false',  # Disable EXIF for testing
        'SAVE_METADATA_JSON': 'true',
        'METADATA_QUALITY': 'high'
    }
    
    metadata_manager = ImageMetadataManager(config)
    
    # Create a temporary test image
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
        try:
            # Create test image
            test_image = Image.new('RGB', (640, 480), color='blue')
            test_image.save(temp_file.name, 'JPEG')
            
            # Test metadata creation
            test_coordinates = (40.7128, -74.0060, 10.0)  # NYC coordinates
            test_ai_description = "A curious orange tabby cat sitting by a window, alert and attentive"
            test_chip_id = "123456789012345"
            test_time = datetime.now(timezone.utc)
            
            logger.info(f"Processing metadata for test image: {temp_file.name}")
            
            # Process comprehensive metadata
            metadata = metadata_manager.process_image_metadata(
                image_path=temp_file.name,
                chip_id=test_chip_id,
                camera_id=0,
                gps_coordinates=test_coordinates,
                ai_description=test_ai_description,
                detection_time=test_time,
                additional_info={'test_mode': True}
            )
            
            # Verify metadata structure
            assert 'version' in metadata, "Metadata should have version"
            assert 'detection' in metadata, "Metadata should have detection info"
            assert 'image' in metadata, "Metadata should have image info"
            assert 'location' in metadata, "Metadata should have location info"
            assert 'ai_analysis' in metadata, "Metadata should have AI analysis"
            
            # Verify detection data
            assert metadata['detection']['chip_id'] == test_chip_id, "Chip ID should match"
            
            # Verify location data
            assert abs(metadata['location']['latitude'] - test_coordinates[0]) < 0.0001, "Latitude should match"
            assert abs(metadata['location']['longitude'] - test_coordinates[1]) < 0.0001, "Longitude should match"
            
            # Verify AI data
            assert metadata['ai_analysis']['description'] == test_ai_description, "AI description should match"
            
            logger.info("✅ Metadata creation test passed")
            
            # Test reading metadata back
            read_metadata = metadata_manager.read_image_metadata(temp_file.name)
            
            if read_metadata:
                logger.info("✅ Metadata reading test passed")
                
                # Verify key fields are preserved
                if 'detection' in read_metadata:
                    assert read_metadata['detection']['chip_id'] == test_chip_id, "Read chip ID should match"
                    
                if 'location' in read_metadata:
                    assert abs(read_metadata['location']['latitude'] - test_coordinates[0]) < 0.0001, "Read latitude should match"
                    
                logger.info("✅ Metadata verification test passed")
            else:
                logger.warning("⚠️  Could not read metadata back (may be normal if EXIF libraries not available)")
            
            # Test GPS extraction
            gps_coords = metadata_manager.extract_gps_from_exif(temp_file.name)
            if gps_coords:
                logger.info(f"✅ GPS extraction test passed: {gps_coords}")
            else:
                logger.info("ℹ️  GPS extraction returned None (may be normal if EXIF libraries not available)")
            
        finally:
            # Cleanup
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
            
            # Clean up JSON file if it exists
            json_file = temp_file.name.replace('.jpg', '.json')
            if os.path.exists(json_file):
                os.unlink(json_file)
    
    logger.info("✅ Image Metadata Manager test completed successfully")
    return True


def test_integration():
    """Test GPS and metadata integration"""
    logger = logging.getLogger(__name__)
    logger.info("🔗 Testing GPS and Metadata Integration...")
    
    # Test configuration
    config = {
        'GPS_ENABLED': 'false',  # Disabled for testing
        'GPS_PORT': '/dev/ttyUSB0',
        'GPS_BAUD': '9600',
        'EMBED_METADATA': 'true',
        'SAVE_METADATA_JSON': 'true',
        'METADATA_QUALITY': 'high'
    }
    
    # Initialize both managers
    gps_manager = GPSManager(config)
    metadata_manager = ImageMetadataManager(config)
    
    # Simulate what the main application would do
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
        try:
            # Create test image
            test_image = Image.new('RGB', (800, 600), color='green')
            test_image.save(temp_file.name, 'JPEG')
            
            # Get GPS coordinates (will be None since GPS disabled)
            gps_coordinates = gps_manager.get_coordinates_for_exif()
            
            # Process image with or without GPS
            metadata = metadata_manager.process_image_metadata(
                image_path=temp_file.name,
                chip_id="987654321098765",
                camera_id=1,
                gps_coordinates=gps_coordinates,  # Will be None
                detection_time=datetime.now(timezone.utc)
            )
            
            # Verify integration worked
            assert 'detection' in metadata, "Integration should create detection metadata"
            assert metadata['detection']['chip_id'] == "987654321098765", "Chip ID should be preserved"
            
            # GPS should not be in metadata since disabled
            if 'location' not in metadata:
                logger.info("✅ GPS correctly excluded when not available")
            else:
                logger.warning("⚠️  GPS data present when it shouldn't be")
            
            logger.info("✅ Integration test completed successfully")
            
        finally:
            # Cleanup
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
            
            json_file = temp_file.name.replace('.jpg', '.json')
            if os.path.exists(json_file):
                os.unlink(json_file)
            
            gps_manager.stop_gps_monitoring()
    
    return True


def main():
    """Run all tests"""
    logger = setup_test_logging()
    logger.info("🧪 Starting GPS and Metadata Integration Tests")
    logger.info("=" * 60)
    
    if not GPS_TEST_AVAILABLE:
        logger.error("❌ Required modules not available for testing")
        logger.error("Please install: pip install pynmea2 Pillow piexif")
        return False
    
    success = True
    
    try:
        # Test individual components
        logger.info("\n📋 Running Component Tests...")
        success &= test_gps_manager()
        success &= test_metadata_manager()
        
        # Test integration
        logger.info("\n🔗 Running Integration Tests...")
        success &= test_integration()
        
        logger.info("\n" + "=" * 60)
        if success:
            logger.info("🎉 All tests passed! GPS and metadata integration is ready.")
            logger.info("\n📝 Next steps:")
            logger.info("1. Connect GPS USB dongle to enable location tracking")
            logger.info("2. Update .env with GPS_ENABLED=true and correct GPS_PORT")
            logger.info("3. Test with real GPS hardware using: python3 src/gps_manager.py")
            logger.info("4. Verify metadata in captured photos")
        else:
            logger.error("❌ Some tests failed. Please check the logs above.")
        
        return success
        
    except Exception as e:
        logger.error(f"❌ Test suite failed with error: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)