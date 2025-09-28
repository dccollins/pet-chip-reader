#!/usr/bin/env python3
"""
Simple RBC-A04 Reader Test - Minimal Version
Continuous monitoring with ser.readline() like you described
"""

import serial
import re
import time
from datetime import datetime

def extract_chip_id(raw_frame):
    """Extract 15-digit chip ID from RBC-A04 frame"""
    # Look for 15-digit pattern in the frame
    match = re.search(r'([0-9]{15})', raw_frame)
    return match.group(1) if match else None

def main():
    port = '/dev/ttyUSB0'  # Change to COM7/COM8 on Windows
    
    print(f"Opening {port} at 9600 baud...")
    print("Press Ctrl+C to stop\n")
    
    try:
        # Open serial port
        ser = serial.Serial(
            port=port,
            baudrate=9600,
            parity='N',
            stopbits=1,
            timeout=1.0  # 1 second timeout for readline()
        )
        
        print(f"Connected to {port}")
        print("Listening for chip data...\n")
        
        while True:
            try:
                # Read a line of data
                line_bytes = ser.readline()
                
                if line_bytes:
                    # Decode and clean up the frame
                    raw_frame = line_bytes.decode('ascii', errors='ignore').strip()
                    
                    if raw_frame:  # Skip empty lines
                        timestamp = datetime.now().strftime('%H:%M:%S')
                        print(f"[{timestamp}] RAW: {raw_frame}")
                        
                        # Extract chip ID if present
                        chip_id = extract_chip_id(raw_frame)
                        if chip_id:
                            print(f"[{timestamp}] 🐾 CHIP ID: {chip_id}")
                        
                        print()  # Empty line for readability
                        
            except Exception as e:
                # Basic error handling - keep the loop running
                print(f"Error reading data: {e}")
                time.sleep(0.1)  # Brief pause before continuing
                continue
                
    except serial.SerialException as e:
        print(f"Serial port error: {e}")
        print("Check connection and port settings")
        
    except KeyboardInterrupt:
        print("\nStopped by user")
        
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("Serial port closed")

if __name__ == "__main__":
    main()