#!/usr/bin/env python3
"""
GPS Status Monitor - shows real-time GPS acquisition status
"""
import time
import serial
import re

def parse_gga(sentence):
    """Parse GPGGA sentence for fix info"""
    parts = sentence.split(',')
    if len(parts) < 15:
        return None
    
    return {
        'time': parts[1],
        'latitude': parts[2],
        'lat_dir': parts[3], 
        'longitude': parts[4],
        'lon_dir': parts[5],
        'quality': parts[6],
        'satellites': parts[7],
        'hdop': parts[8],
        'altitude': parts[9],
        'alt_unit': parts[10]
    }

def parse_gsv(sentence):
    """Parse GPGSV sentence for satellite info"""
    parts = sentence.split(',')
    if len(parts) < 4:
        return None
    
    return {
        'total_msgs': parts[1],
        'msg_num': parts[2], 
        'total_sats': parts[3]
    }

def monitor_gps_status():
    print("=== GPS Status Monitor ===")
    print("Monitoring GPS acquisition status...")
    print("Press Ctrl+C to stop\n")
    
    try:
        gps_port = serial.Serial('/dev/ttyACM0', 9600, timeout=2)
        print("✅ GPS connected to /dev/ttyACM0")
        
        last_status_time = 0
        satellites_in_view = 0
        gps_quality = 0
        
        while True:
            try:
                line = gps_port.readline().decode('ascii', errors='ignore').strip()
                
                if line.startswith('$GPGGA') or line.startswith('$GNGGA'):
                    gga_data = parse_gga(line)
                    if gga_data:
                        gps_quality = int(gga_data['quality']) if gga_data['quality'] else 0
                        satellites_used = int(gga_data['satellites']) if gga_data['satellites'] else 0
                        
                        # Print status every 5 seconds
                        current_time = time.time()
                        if current_time - last_status_time > 5:
                            status = "🔴 NO FIX"
                            if gps_quality > 0:
                                if gps_quality == 1:
                                    status = "🟢 GPS FIX"
                                elif gps_quality == 2:
                                    status = "🟢 DGPS FIX"
                                else:
                                    status = f"🟢 FIX (Q:{gps_quality})"
                            
                            print(f"{time.strftime('%H:%M:%S')} - {status} | Sats Used: {satellites_used:2d} | Sats Visible: {satellites_in_view:2d}")
                            
                            if gps_quality > 0 and gga_data['latitude']:
                                # Convert to decimal degrees
                                lat_deg = float(gga_data['latitude'][:2])
                                lat_min = float(gga_data['latitude'][2:])
                                latitude = lat_deg + lat_min/60
                                if gga_data['lat_dir'] == 'S':
                                    latitude = -latitude
                                
                                lon_deg = float(gga_data['longitude'][:3])  
                                lon_min = float(gga_data['longitude'][3:])
                                longitude = lon_deg + lon_min/60
                                if gga_data['lon_dir'] == 'W':
                                    longitude = -longitude
                                
                                altitude = float(gga_data['altitude']) if gga_data['altitude'] else 0
                                
                                print(f"           📍 Lat: {latitude:.6f}° Lon: {longitude:.6f}° Alt: {altitude:.1f}m")
                            
                            last_status_time = current_time
                
                elif line.startswith('$GPGSV') or line.startswith('$GNGSV'):
                    gsv_data = parse_gsv(line)
                    if gsv_data and gsv_data['msg_num'] == '1':  # First message has total count
                        satellites_in_view = int(gsv_data['total_sats']) if gsv_data['total_sats'] else 0
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                # Skip individual line errors
                continue
                
        gps_port.close()
        print("\n🔚 GPS monitoring stopped")
        
    except serial.SerialException as e:
        print(f"❌ Error opening GPS: {e}")
    except KeyboardInterrupt:
        print("\n🔚 Monitoring stopped by user")

if __name__ == "__main__":
    monitor_gps_status()