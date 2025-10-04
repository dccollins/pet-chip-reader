#!/usr/bin/env python3
"""
Direct GPS data test - reads raw NMEA data from GPS device
"""
import time
import serial

def test_gps_direct():
    print("=== Direct GPS Test ===")
    print("Reading raw NMEA data from /dev/ttyACM0...")
    
    try:
        # Open GPS port
        gps_port = serial.Serial('/dev/ttyACM0', 9600, timeout=2)
        print("✅ GPS port opened successfully")
        
        print("\n--- Raw NMEA Data (next 15 sentences) ---")
        sentence_count = 0
        start_time = time.time()
        
        while sentence_count < 15 and (time.time() - start_time) < 30:
            try:
                line = gps_port.readline().decode('ascii', errors='ignore').strip()
                if line and line.startswith('$'):
                    print(f"   {line}")
                    sentence_count += 1
                    
                    # Parse key sentence types
                    if line.startswith('$GPGGA') or line.startswith('$GNGGA'):
                        parts = line.split(',')
                        if len(parts) > 6 and parts[6]:  # Quality indicator
                            quality = parts[6]
                            satellites = parts[7] if len(parts) > 7 else 'Unknown'
                            print(f"      → GPS Quality: {quality}, Satellites: {satellites}")
                    
                    elif line.startswith('$GPRMC') or line.startswith('$GNRMC'):
                        parts = line.split(',')
                        if len(parts) > 2 and parts[2] == 'A':  # Active/Valid
                            lat = parts[3] if len(parts) > 3 else ''
                            lat_dir = parts[4] if len(parts) > 4 else ''
                            lon = parts[5] if len(parts) > 5 else ''
                            lon_dir = parts[6] if len(parts) > 6 else ''
                            if lat and lon:
                                print(f"      → Position: {lat} {lat_dir}, {lon} {lon_dir}")
                            
            except Exception as e:
                print(f"   Error reading line: {e}")
                
        gps_port.close()
        print(f"\n✅ Read {sentence_count} NMEA sentences")
        
        if sentence_count == 0:
            print("\n⚠️  No NMEA data received - GPS may need more time to initialize")
            print("   Try waiting a few minutes near a window for satellite acquisition")
        
    except serial.SerialException as e:
        print(f"❌ Error opening GPS port: {e}")
        print("   Check that GPS device is connected to /dev/ttyACM0")
        print("   Run 'ls -la /dev/ttyACM*' to verify device presence")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    test_gps_direct()