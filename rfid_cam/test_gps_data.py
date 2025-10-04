#!/usr/bin/env python3
"""
Test GPS data retrieval
"""
import time
import sys
import os
from dotenv import load_dotenv

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Load environment variables
load_dotenv()

try:
    from gps_manager import GPSManager
    
    # Load configuration like the main app does
    gps_enabled = os.getenv('GPS_ENABLED', 'false')
    if isinstance(gps_enabled, str):
        gps_enabled = gps_enabled.lower() == 'true'
    
    config = {
        'GPS_ENABLED': gps_enabled,
        'GPS_PORT': os.getenv('GPS_PORT', '/dev/ttyACM0'),
        'GPS_BAUD': int(os.getenv('GPS_BAUD', '9600')),
        'GPS_TIMEOUT': float(os.getenv('GPS_TIMEOUT', '5.0'))
    }
    
    print("=== GPS Data Test ===")
    print(f"GPS Enabled: {config['GPS_ENABLED']}")
    print(f"GPS Port: {config['GPS_PORT']}")
    print(f"GPS Baud: {config['GPS_BAUD']}")
    print()
    
    if not config['GPS_ENABLED']:
        print("GPS is disabled in configuration")
        sys.exit(1)
    
    # Initialize GPS manager
    print("Initializing GPS manager...")
    gps_manager = GPSManager(config)
    
    print("Waiting for GPS data (10 seconds)...")
    for i in range(10):
        gps_data = gps_manager.get_current_location()
        
        if gps_data and gps_data.get('latitude') is not None:
            print(f"\n✅ GPS Fix obtained!")
            print(f"   Latitude: {gps_data['latitude']:.6f}°")
            print(f"   Longitude: {gps_data['longitude']:.6f}°")
            print(f"   Altitude: {gps_data.get('altitude', 'Unknown')} m")
            print(f"   Satellites: {gps_data.get('satellites', 'Unknown')}")
            print(f"   Timestamp: {gps_data.get('timestamp', 'Unknown')}")
            print(f"   Quality: {gps_data.get('quality', 'Unknown')}")
            break
        else:
            print(f"   Waiting for GPS fix... ({i+1}/10) - {gps_data}")
            time.sleep(1)
    else:
        print("\n❌ No GPS fix obtained within 10 seconds")
        print("   GPS may need more time to acquire satellite signals")
        print("   Try moving near a window or outdoors for better reception")
    
    # Show raw NMEA data
    print(f"\n--- Raw GPS Data (last 5 NMEA sentences) ---")
    if hasattr(gps_manager, 'get_raw_data'):
        raw_data = gps_manager.get_raw_data()
        if raw_data:
            for line in raw_data[-5:]:
                print(f"   {line.strip()}")
        else:
            print("   No raw data available")
    
    gps_manager.close()
    
except ImportError as e:
    print(f"❌ GPS manager not available: {e}")
    print("   GPS features are not installed")
except Exception as e:
    print(f"❌ Error testing GPS: {e}")
    print("   Check GPS device connection and permissions")