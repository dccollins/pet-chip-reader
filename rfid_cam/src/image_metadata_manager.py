#!/usr/bin/env python3
"""
Image Metadata Manager for Pet Chip Reader System
Handles EXIF metadata, GPS data embedding, and AI description tagging
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple
from pathlib import Path

try:
    from PIL import Image, ExifTags
    from PIL.ExifTags import TAGS, GPSTAGS
    import piexif
    EXIF_AVAILABLE = True
except ImportError:
    EXIF_AVAILABLE = False
    logging.warning("EXIF dependencies not installed. Run: pip install Pillow piexif")


class ImageMetadataManager:
    """
    Manages comprehensive metadata for captured pet images
    Includes EXIF data, GPS coordinates, AI descriptions, and chip information
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Metadata configuration
        self.embed_metadata = config.get('EMBED_METADATA', 'true').lower() == 'true'
        self.save_json_files = config.get('SAVE_METADATA_JSON', 'true').lower() == 'true'
        self.metadata_quality = config.get('METADATA_QUALITY', 'high').lower()
        
        if self.embed_metadata and not EXIF_AVAILABLE:
            self.logger.warning("EXIF libraries not available - metadata embedding disabled")
            self.embed_metadata = False
        
        self.logger.info(f"Image Metadata Manager initialized - Embedding: {self.embed_metadata}")
    
    def create_comprehensive_metadata(self, 
                                    image_path: str,
                                    chip_id: str,
                                    camera_id: int,
                                    gps_coordinates: Optional[Tuple[float, float, Optional[float]]] = None,
                                    ai_description: Optional[str] = None,
                                    detection_time: Optional[datetime] = None,
                                    additional_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create comprehensive metadata for an image
        
        Args:
            image_path: Path to the image file
            chip_id: Pet microchip ID
            camera_id: Camera identifier (0, 1, etc.)
            gps_coordinates: (latitude, longitude, altitude) tuple
            ai_description: AI-generated description of the animal
            detection_time: When the detection occurred
            additional_info: Any additional metadata
            
        Returns:
            Dictionary containing all metadata
        """
        if not detection_time:
            detection_time = datetime.now(timezone.utc)
        
        # Base metadata
        metadata = {
            'version': '2.0.0',
            'system': 'pet-chip-reader',
            'created': detection_time.isoformat(),
            'image': {
                'filename': Path(image_path).name,
                'path': str(image_path),
                'camera_id': camera_id,
                'capture_timestamp': detection_time.isoformat()
            },
            'detection': {
                'chip_id': chip_id,
                'detection_time': detection_time.isoformat(),
                'detection_date': detection_time.strftime('%Y-%m-%d'),
                'detection_day': detection_time.strftime('%A'),
                'detection_hour': detection_time.hour,
                'timezone': str(detection_time.tzinfo)
            }
        }
        
        # Add GPS information if available
        if gps_coordinates:
            lat, lon, alt = gps_coordinates
            metadata['location'] = {
                'latitude': lat,
                'longitude': lon,
                'altitude': alt,
                'coordinate_format': 'decimal_degrees',
                'datum': 'WGS84'
            }
            
            # Add human-readable location description
            metadata['location']['description'] = f"GPS: {lat:.6f}, {lon:.6f}"
            if alt is not None:
                metadata['location']['description'] += f" (Alt: {alt:.1f}m)"
        
        # Add AI description if available
        if ai_description:
            metadata['ai_analysis'] = {
                'description': ai_description,
                'analyzed_at': datetime.now(timezone.utc).isoformat(),
                'model': 'openai-gpt4-vision',
                'confidence': 'high'  # Could be enhanced with actual confidence scores
            }
        
        # Add image technical details
        if os.path.exists(image_path):
            try:
                with Image.open(image_path) as img:
                    metadata['image'].update({
                        'width': img.width,
                        'height': img.height,
                        'format': img.format,
                        'mode': img.mode,
                        'file_size': os.path.getsize(image_path)
                    })
            except Exception as e:
                self.logger.debug(f"Could not read image properties: {e}")
        
        # Add additional information
        if additional_info:
            metadata.update(additional_info)
        
        # Add system information
        metadata['system_info'] = {
            'hostname': os.uname().nodename if hasattr(os, 'uname') else 'unknown',
            'system': os.uname().sysname if hasattr(os, 'uname') else 'unknown',
            'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        }
        
        return metadata
    
    def embed_exif_metadata(self, image_path: str, metadata: Dict[str, Any]) -> bool:
        """
        Embed metadata into image EXIF data
        
        Args:
            image_path: Path to the image file
            metadata: Metadata dictionary to embed
            
        Returns:
            True if successful, False otherwise
        """
        if not self.embed_metadata or not EXIF_AVAILABLE:
            return False
        
        try:
            # Load existing EXIF data
            img = Image.open(image_path)
            exif_dict = piexif.load(img.info.get('exif', b''))
            
            # Update basic EXIF fields
            detection_time = datetime.fromisoformat(metadata['detection']['detection_time'].replace('Z', '+00:00'))
            
            # Format datetime for EXIF (YYYY:MM:DD HH:MM:SS format)
            exif_datetime = detection_time.strftime('%Y:%m:%d %H:%M:%S')
            
            # Update 0th IFD (main image data)
            exif_dict['0th'][piexif.ImageIFD.DateTime] = exif_datetime
            exif_dict['0th'][piexif.ImageIFD.Software] = f"pet-chip-reader v{metadata['version']}"
            exif_dict['0th'][piexif.ImageIFD.Artist] = "Pet Chip Reader System"
            exif_dict['0th'][piexif.ImageIFD.Copyright] = f"Chip ID: {metadata['detection']['chip_id']}"
            
            # Update EXIF IFD
            exif_dict['Exif'][piexif.ExifIFD.DateTimeOriginal] = exif_datetime
            exif_dict['Exif'][piexif.ExifIFD.DateTimeDigitized] = exif_datetime
            
            # Add custom description with AI analysis and chip info
            description_parts = [
                f"Pet Detection - Chip: {metadata['detection']['chip_id']}",
                f"Camera: {metadata['image']['camera_id']}",
                f"Date: {metadata['detection']['detection_date']} ({metadata['detection']['detection_day']})"
            ]
            
            if 'ai_analysis' in metadata:
                description_parts.append(f"AI: {metadata['ai_analysis']['description'][:100]}...")
            
            if 'location' in metadata:
                description_parts.append(f"GPS: {metadata['location']['latitude']:.4f},{metadata['location']['longitude']:.4f}")
            
            exif_dict['0th'][piexif.ImageIFD.ImageDescription] = "; ".join(description_parts)
            
            # Add GPS data if available
            if 'location' in metadata:
                self._embed_gps_data(exif_dict, metadata['location'])
            
            # Add user comment with full metadata (JSON format)
            if self.metadata_quality == 'high':
                metadata_json = json.dumps(metadata, default=str, indent=None)
                # Encode as bytes for UserComment (direct UTF-8 encoding)
                exif_dict['Exif'][piexif.ExifIFD.UserComment] = metadata_json.encode('utf-8')
            
            # Save image with updated EXIF
            exif_bytes = piexif.dump(exif_dict)
            img.save(image_path, exif=exif_bytes, quality=95)
            
            self.logger.debug(f"EXIF metadata embedded in {image_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to embed EXIF metadata: {e}")
            return False
    
    def _embed_gps_data(self, exif_dict: Dict, location: Dict[str, Any]):
        """Embed GPS data into EXIF GPS IFD"""
        try:
            lat = location['latitude']
            lon = location['longitude']
            alt = location.get('altitude')
            
            # Convert decimal degrees to degrees/minutes/seconds format
            def decimal_to_dms(decimal_degrees):
                degrees = int(abs(decimal_degrees))
                minutes_float = (abs(decimal_degrees) - degrees) * 60
                minutes = int(minutes_float)
                seconds = (minutes_float - minutes) * 60
                return [(degrees, 1), (minutes, 1), (int(seconds * 100), 100)]
            
            # GPS data
            gps_data = {
                piexif.GPSIFD.GPSVersionID: (2, 0, 0, 0),
                piexif.GPSIFD.GPSLatitudeRef: 'N' if lat >= 0 else 'S',
                piexif.GPSIFD.GPSLatitude: decimal_to_dms(lat),
                piexif.GPSIFD.GPSLongitudeRef: 'E' if lon >= 0 else 'W',
                piexif.GPSIFD.GPSLongitude: decimal_to_dms(lon),
                piexif.GPSIFD.GPSMapDatum: 'WGS-84'
            }
            
            if alt is not None:
                gps_data[piexif.GPSIFD.GPSAltitudeRef] = 0  # Above sea level
                gps_data[piexif.GPSIFD.GPSAltitude] = (int(alt * 100), 100)
            
            exif_dict['GPS'] = gps_data
            
        except Exception as e:
            self.logger.error(f"Failed to embed GPS data: {e}")
    
    def save_metadata_json(self, image_path: str, metadata: Dict[str, Any]) -> bool:
        """
        Save metadata as separate JSON file alongside image
        
        Args:
            image_path: Path to the image file
            metadata: Metadata dictionary to save
            
        Returns:
            True if successful, False otherwise
        """
        if not self.save_json_files:
            return False
        
        try:
            json_path = Path(image_path).with_suffix('.json')
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, default=str, ensure_ascii=False)
            
            self.logger.debug(f"Metadata JSON saved: {json_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save metadata JSON: {e}")
            return False
    
    def process_image_metadata(self, 
                             image_path: str,
                             chip_id: str,
                             camera_id: int,
                             gps_coordinates: Optional[Tuple[float, float, Optional[float]]] = None,
                             ai_description: Optional[str] = None,
                             detection_time: Optional[datetime] = None,
                             additional_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Complete metadata processing pipeline for an image
        
        Creates comprehensive metadata and embeds it into the image file
        """
        try:
            # Create comprehensive metadata
            metadata = self.create_comprehensive_metadata(
                image_path=image_path,
                chip_id=chip_id,
                camera_id=camera_id,
                gps_coordinates=gps_coordinates,
                ai_description=ai_description,
                detection_time=detection_time,
                additional_info=additional_info
            )
            
            # Embed EXIF metadata
            exif_success = self.embed_exif_metadata(image_path, metadata)
            
            # Save JSON metadata
            json_success = self.save_metadata_json(image_path, metadata)
            
            # Log results
            if exif_success or json_success:
                self.logger.info(f"Metadata processed for {Path(image_path).name} "
                               f"(EXIF: {exif_success}, JSON: {json_success})")
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Failed to process image metadata: {e}")
            return {}
    
    def read_image_metadata(self, image_path: str) -> Dict[str, Any]:
        """
        Read metadata from an image file
        
        Tries JSON file first, then EXIF data
        """
        metadata = {}
        
        # Try to read JSON metadata first
        json_path = Path(image_path).with_suffix('.json')
        if json_path.exists():
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                self.logger.debug(f"Loaded metadata from {json_path}")
                return metadata
            except Exception as e:
                self.logger.debug(f"Could not read JSON metadata: {e}")
        
        # Fallback to EXIF data
        if EXIF_AVAILABLE:
            try:
                with Image.open(image_path) as img:
                    exif_data = piexif.load(img.info.get('exif', b''))
                    
                    # Extract basic metadata
                    if 'Exif' in exif_data and piexif.ExifIFD.UserComment in exif_data['Exif']:
                        try:
                            user_comment_bytes = exif_data['Exif'][piexif.ExifIFD.UserComment]
                            user_comment = user_comment_bytes.decode('utf-8')
                            metadata = json.loads(user_comment)
                        except:
                            pass
                    
                    self.logger.debug(f"Loaded metadata from EXIF: {image_path}")
                    
            except Exception as e:
                self.logger.debug(f"Could not read EXIF metadata: {e}")
        
        return metadata
    
    def extract_gps_from_exif(self, image_path: str) -> Optional[Tuple[float, float, Optional[float]]]:
        """Extract GPS coordinates from image EXIF data"""
        if not EXIF_AVAILABLE:
            return None
        
        try:
            with Image.open(image_path) as img:
                exif_data = piexif.load(img.info.get('exif', b''))
                
                if 'GPS' not in exif_data:
                    return None
                
                gps_data = exif_data['GPS']
                
                # Extract latitude
                if piexif.GPSIFD.GPSLatitude in gps_data and piexif.GPSIFD.GPSLatitudeRef in gps_data:
                    lat_dms = gps_data[piexif.GPSIFD.GPSLatitude]
                    lat_ref = gps_data[piexif.GPSIFD.GPSLatitudeRef].decode('ascii')
                    lat = self._dms_to_decimal(lat_dms)
                    if lat_ref == 'S':
                        lat = -lat
                else:
                    return None
                
                # Extract longitude
                if piexif.GPSIFD.GPSLongitude in gps_data and piexif.GPSIFD.GPSLongitudeRef in gps_data:
                    lon_dms = gps_data[piexif.GPSIFD.GPSLongitude]
                    lon_ref = gps_data[piexif.GPSIFD.GPSLongitudeRef].decode('ascii')
                    lon = self._dms_to_decimal(lon_dms)
                    if lon_ref == 'W':
                        lon = -lon
                else:
                    return None
                
                # Extract altitude (optional)
                alt = None
                if piexif.GPSIFD.GPSAltitude in gps_data:
                    alt_data = gps_data[piexif.GPSIFD.GPSAltitude]
                    alt = alt_data[0] / alt_data[1]  # Convert from fraction
                    
                    if (piexif.GPSIFD.GPSAltitudeRef in gps_data and 
                        gps_data[piexif.GPSIFD.GPSAltitudeRef] == 1):
                        alt = -alt  # Below sea level
                
                return (lat, lon, alt)
                
        except Exception as e:
            self.logger.debug(f"Could not extract GPS from EXIF: {e}")
            return None
    
    def _dms_to_decimal(self, dms_tuple):
        """Convert degrees/minutes/seconds to decimal degrees"""
        degrees, minutes, seconds = dms_tuple
        decimal = degrees[0] / degrees[1]
        decimal += (minutes[0] / minutes[1]) / 60
        decimal += (seconds[0] / seconds[1]) / 3600
        return decimal


def test_metadata_manager():
    """Test function for metadata manager"""
    import tempfile
    from PIL import Image
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    logger.info("Testing Image Metadata Manager...")
    
    config = {
        'EMBED_METADATA': 'true',
        'SAVE_METADATA_JSON': 'true',
        'METADATA_QUALITY': 'high'
    }
    
    metadata_manager = ImageMetadataManager(config)
    
    # Create test image
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
        # Create a simple test image
        test_img = Image.new('RGB', (640, 480), color='red')
        test_img.save(temp_file.name, 'JPEG')
        
        # Process metadata
        test_gps = (40.7128, -74.0060, 10.0)  # New York City coordinates
        test_ai = "A small brown dog sitting on grass, looking alert and friendly"
        
        metadata = metadata_manager.process_image_metadata(
            image_path=temp_file.name,
            chip_id="123456789012345",
            camera_id=0,
            gps_coordinates=test_gps,
            ai_description=test_ai,
            detection_time=datetime.now(timezone.utc)
        )
        
        logger.info(f"Created metadata: {json.dumps(metadata, indent=2, default=str)}")
        
        # Test reading metadata back
        read_metadata = metadata_manager.read_image_metadata(temp_file.name)
        logger.info(f"Read back metadata keys: {list(read_metadata.keys())}")
        
        # Test GPS extraction
        gps_coords = metadata_manager.extract_gps_from_exif(temp_file.name)
        logger.info(f"Extracted GPS: {gps_coords}")
        
        # Cleanup
        os.unlink(temp_file.name)
        json_file = temp_file.name.replace('.jpg', '.json')
        if os.path.exists(json_file):
            os.unlink(json_file)
    
    logger.info("Metadata manager test completed")


if __name__ == "__main__":
    test_metadata_manager()