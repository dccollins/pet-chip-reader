#!/usr/bin/env python3
"""
GPS Manager Module for Pet Chip Reader System
Handles GPS data acquisition from USB dongle and provides location services
"""

import os
import time
import threading
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple
import json

try:
    import serial
    import pynmea2
    NMEA_AVAILABLE = True
except ImportError:
    NMEA_AVAILABLE = False
    logging.warning("GPS dependencies not installed. Run: pip install pynmea2 pyserial")


class GPSManager:
    """
    Manages GPS functionality for the pet chip reader system
    Supports USB GPS dongles that output NMEA sentences
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # GPS configuration
        self.gps_enabled = config.get('GPS_ENABLED', 'false').lower() == 'true'
        self.gps_port = config.get('GPS_PORT', '/dev/ttyUSB0')  # Separate from RFID reader
        self.gps_baud = int(config.get('GPS_BAUD', '9600'))
        self.gps_timeout = float(config.get('GPS_TIMEOUT', '5.0'))
        
        # GPS state
        self.gps_connection = None
        self.current_location = None
        self.location_lock = threading.Lock()
        self.gps_thread = None
        self.running = False
        self.last_fix_time = None
        self.fix_quality = 0
        
        # Location history for accuracy improvement
        self.location_history = []
        self.max_history = 10
        
        if self.gps_enabled and NMEA_AVAILABLE:
            self.logger.info("GPS Manager initialized - GPS enabled")
            self.start_gps_monitoring()
        else:
            self.logger.info("GPS Manager initialized - GPS disabled or dependencies missing")
    
    def start_gps_monitoring(self):
        """Start GPS monitoring in background thread"""
        if not self.gps_enabled or not NMEA_AVAILABLE:
            return
            
        self.running = True
        self.gps_thread = threading.Thread(target=self._gps_monitor_loop, daemon=True)
        self.gps_thread.start()
        self.logger.info(f"GPS monitoring started on {self.gps_port}")
    
    def stop_gps_monitoring(self):
        """Stop GPS monitoring"""
        self.running = False
        if self.gps_connection:
            try:
                self.gps_connection.close()
                self.logger.info("GPS connection closed")
            except Exception as e:
                self.logger.error(f"Error closing GPS connection: {e}")
        
        if self.gps_thread:
            self.gps_thread.join(timeout=5.0)
    
    def _gps_monitor_loop(self):
        """Main GPS monitoring loop"""
        while self.running:
            try:
                self._connect_gps()
                if self.gps_connection:
                    self._read_gps_data()
            except Exception as e:
                self.logger.error(f"GPS monitoring error: {e}")
                time.sleep(5)  # Wait before retry
    
    def _connect_gps(self):
        """Establish connection to GPS device"""
        if self.gps_connection:
            return  # Already connected
            
        try:
            # Check if GPS device exists
            if not os.path.exists(self.gps_port):
                self.logger.debug(f"GPS device not found at {self.gps_port}")
                time.sleep(10)  # Wait longer for USB devices
                return
            
            self.gps_connection = serial.Serial(
                port=self.gps_port,
                baudrate=self.gps_baud,
                timeout=self.gps_timeout,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE
            )
            
            self.logger.info(f"GPS connected to {self.gps_port} at {self.gps_baud} baud")
            
        except serial.SerialException as e:
            self.logger.warning(f"Failed to connect to GPS: {e}")
            self.gps_connection = None
            time.sleep(5)
        except Exception as e:
            self.logger.error(f"Unexpected GPS connection error: {e}")
            self.gps_connection = None
            time.sleep(5)
    
    def _read_gps_data(self):
        """Read and parse GPS data"""
        try:
            while self.running and self.gps_connection:
                try:
                    # Read line from GPS
                    line = self.gps_connection.readline().decode('ascii', errors='replace').strip()
                    
                    if not line:
                        continue
                    
                    # Parse NMEA sentence
                    if line.startswith('$'):
                        try:
                            msg = pynmea2.parse(line)
                            self._process_nmea_message(msg)
                        except pynmea2.ParseError:
                            # Ignore parsing errors - GPS data can be noisy
                            continue
                
                except serial.SerialException:
                    self.logger.warning("GPS connection lost")
                    self.gps_connection = None
                    break
                except UnicodeDecodeError:
                    # Ignore decode errors - GPS data can be corrupted
                    continue
                    
        except Exception as e:
            self.logger.error(f"GPS data reading error: {e}")
            self.gps_connection = None
    
    def _process_nmea_message(self, msg):
        """Process parsed NMEA message"""
        try:
            # Handle different NMEA message types
            if hasattr(msg, 'sentence_type'):
                if msg.sentence_type == 'GGA':  # Global Positioning System Fix Data
                    self._process_gga_message(msg)
                elif msg.sentence_type == 'RMC':  # Recommended Minimum Course
                    self._process_rmc_message(msg)
                elif msg.sentence_type == 'GSA':  # GPS DOP and active satellites
                    self._process_gsa_message(msg)
                    
        except Exception as e:
            self.logger.debug(f"Error processing NMEA message: {e}")
    
    def _process_gga_message(self, msg):
        """Process GGA (Fix Data) message"""
        try:
            if hasattr(msg, 'latitude') and hasattr(msg, 'longitude') and \
               msg.latitude and msg.longitude and \
               hasattr(msg, 'gps_qual') and msg.gps_qual and msg.gps_qual > 0:
                
                location_data = {
                    'latitude': float(msg.latitude),
                    'longitude': float(msg.longitude),
                    'altitude': float(msg.altitude) if msg.altitude else None,
                    'fix_quality': int(msg.gps_qual),
                    'satellites': int(msg.num_sats) if msg.num_sats else 0,
                    'hdop': float(msg.horizontal_dil) if msg.horizontal_dil else None,
                    'timestamp': datetime.now(timezone.utc),
                    'fix_time': msg.timestamp if hasattr(msg, 'timestamp') else None
                }
                
                self._update_location(location_data)
                
        except (ValueError, AttributeError) as e:
            self.logger.debug(f"Error processing GGA message: {e}")
    
    def _process_rmc_message(self, msg):
        """Process RMC (Recommended Minimum Course) message"""
        try:
            if hasattr(msg, 'latitude') and hasattr(msg, 'longitude') and \
               msg.latitude and msg.longitude and \
               hasattr(msg, 'status') and msg.status == 'A':  # A = Active, V = Void
                
                location_data = {
                    'latitude': float(msg.latitude),
                    'longitude': float(msg.longitude),
                    'speed': float(msg.spd_over_grnd) if msg.spd_over_grnd else None,
                    'course': float(msg.true_course) if msg.true_course else None,
                    'timestamp': datetime.now(timezone.utc),
                    'date': msg.datestamp if hasattr(msg, 'datestamp') else None,
                    'time': msg.timestamp if hasattr(msg, 'timestamp') else None
                }
                
                self._update_location(location_data)
                
        except (ValueError, AttributeError) as e:
            self.logger.debug(f"Error processing RMC message: {e}")
    
    def _process_gsa_message(self, msg):
        """Process GSA (GPS DOP and active satellites) message"""
        try:
            if hasattr(msg, 'mode_fix_type'):
                self.fix_quality = int(msg.mode_fix_type) if msg.mode_fix_type else 0
        except (ValueError, AttributeError):
            pass
    
    def _update_location(self, location_data: Dict[str, Any]):
        """Update current location with new GPS data"""
        with self.location_lock:
            # Add to history for averaging
            self.location_history.append(location_data)
            if len(self.location_history) > self.max_history:
                self.location_history.pop(0)
            
            # Update current location
            self.current_location = location_data
            self.last_fix_time = datetime.now()
            
            # Log significant location changes
            if len(self.location_history) == 1:  # First fix
                self.logger.info(f"GPS fix acquired: {location_data['latitude']:.6f}, {location_data['longitude']:.6f}")
    
    def get_current_location(self) -> Optional[Dict[str, Any]]:
        """Get current GPS location"""
        with self.location_lock:
            if not self.current_location:
                return None
            
            # Check if fix is recent (within last 2 minutes)
            if self.last_fix_time and \
               (datetime.now() - self.last_fix_time).total_seconds() > 120:
                self.logger.debug("GPS fix is stale")
                return None
            
            return self.current_location.copy()
    
    def get_averaged_location(self) -> Optional[Dict[str, Any]]:
        """Get averaged location from recent fixes for better accuracy"""
        with self.location_lock:
            if not self.location_history:
                return None
            
            # Filter recent locations (last 30 seconds)
            recent_threshold = datetime.now() - timedelta(seconds=30)
            recent_locations = [
                loc for loc in self.location_history
                if loc.get('timestamp', datetime.min) > recent_threshold
            ]
            
            if not recent_locations:
                return self.get_current_location()
            
            # Calculate averages
            avg_lat = sum(loc['latitude'] for loc in recent_locations) / len(recent_locations)
            avg_lon = sum(loc['longitude'] for loc in recent_locations) / len(recent_locations)
            
            # Use most recent metadata
            latest = recent_locations[-1]
            
            return {
                'latitude': avg_lat,
                'longitude': avg_lon,
                'altitude': latest.get('altitude'),
                'accuracy_samples': len(recent_locations),
                'fix_quality': latest.get('fix_quality', 0),
                'satellites': latest.get('satellites', 0),
                'timestamp': latest.get('timestamp'),
                'hdop': latest.get('hdop')
            }
    
    def is_gps_available(self) -> bool:
        """Check if GPS is available and has recent fix"""
        return self.gps_enabled and self.get_current_location() is not None
    
    def get_location_string(self) -> str:
        """Get formatted location string for logging/display"""
        location = self.get_averaged_location()
        if not location:
            return "GPS: No fix"
        
        lat = location['latitude']
        lon = location['longitude']
        alt = location.get('altitude', 'Unknown')
        quality = location.get('fix_quality', 0)
        sats = location.get('satellites', 0)
        
        return f"GPS: {lat:.6f}, {lon:.6f} (Alt: {alt}m, Q:{quality}, Sats:{sats})"
    
    def get_coordinates_for_exif(self) -> Optional[Tuple[float, float, Optional[float]]]:
        """Get coordinates in format suitable for EXIF metadata"""
        location = self.get_averaged_location()
        if not location:
            return None
        
        return (
            location['latitude'],
            location['longitude'],
            location.get('altitude')
        )
    
    def export_location_data(self) -> Dict[str, Any]:
        """Export location data for JSON/API purposes"""
        location = self.get_averaged_location()
        if not location:
            return {'gps_available': False}
        
        return {
            'gps_available': True,
            'latitude': location['latitude'],
            'longitude': location['longitude'],
            'altitude': location.get('altitude'),
            'accuracy_samples': location.get('accuracy_samples', 1),
            'fix_quality': location.get('fix_quality', 0),
            'satellites': location.get('satellites', 0),
            'timestamp': location.get('timestamp').isoformat() if location.get('timestamp') else None,
            'location_string': self.get_location_string()
        }


def test_gps_manager():
    """Test function for GPS manager"""
    # Test configuration
    config = {
        'GPS_ENABLED': 'true',
        'GPS_PORT': '/dev/ttyUSB0',
        'GPS_BAUD': '9600'
    }
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    logger.info("Testing GPS Manager...")
    
    gps_manager = GPSManager(config)
    
    try:
        # Monitor for 60 seconds
        for i in range(60):
            location = gps_manager.get_current_location()
            if location:
                logger.info(f"GPS Fix: {gps_manager.get_location_string()}")
            else:
                logger.info("Waiting for GPS fix...")
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Test interrupted")
    finally:
        gps_manager.stop_gps_monitoring()
        logger.info("GPS test completed")


if __name__ == "__main__":
    test_gps_manager()