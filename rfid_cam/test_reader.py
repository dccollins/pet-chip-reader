#!/usr/bin/env python3
"""
RBC-A04 Pet Microchip Reader Test Script
Standalone test for reading and parsing pet chip data from RBC-A04 reader

Usage:
    python test_reader.py --port /dev/ttyUSB0 --baud 9600
    python test_reader.py --port /dev/ttyUSB0 --baud 9600 --timeout 30
"""

import serial
import time
import re
import argparse
import sys
from datetime import datetime


def parse_rbc_frame(raw_data):
    """
    Parse RBC-A04 frame and extract 15-digit pet chip ID
    
    Expected format examples:
    $A0112OKD900263003496836#
    $A{addr}{cmd}{status}{data}#
    
    Args:
        raw_data (str): Raw serial data received
        
    Returns:
        dict: Parsed data with chip_id, raw_frame, valid, etc.
    """
    result = {
        'raw_frame': raw_data,
        'valid_frame': False,
        'chip_id': None,
        'status': None,
        'parse_error': None
    }
    
    # Check basic frame structure
    if not raw_data.startswith('$') or not raw_data.endswith('#'):
        result['parse_error'] = 'Frame does not start with $ or end with #'
        return result
    
    # Remove frame markers
    payload = raw_data[1:-1]  # Remove $ and #
    
    if len(payload) < 6:
        result['parse_error'] = f'Payload too short: {len(payload)} chars'
        return result
    
    result['valid_frame'] = True
    
    try:
        # Parse the frame structure
        # Expected: A{addr}{cmd}{status}{data}
        if payload.startswith('A'):
            addr = payload[1:3]      # Address (e.g., "01")
            cmd = payload[3:5]       # Command (e.g., "12")
            status = payload[5:7]    # Status (e.g., "OK")
            data = payload[7:]       # Data portion
            
            result['address'] = addr
            result['command'] = cmd
            result['status'] = status
            result['data'] = data
            
            # Look for 15-digit chip ID in the data portion
            # Try different patterns based on your example
            chip_patterns = [
                r'([0-9]{15})',           # Exactly 15 digits
                r'D([0-9]{15})',          # D prefix + 15 digits
                r'([0-9]{12,18})',        # 12-18 digits (flexible)
            ]
            
            for pattern in chip_patterns:
                match = re.search(pattern, data)
                if match:
                    potential_chip = match.group(1)
                    # Validate it's exactly 15 digits for FDX-B standard
                    if len(potential_chip) == 15 and potential_chip.isdigit():
                        result['chip_id'] = potential_chip
                        break
                    elif len(potential_chip) >= 12:  # Store longer IDs too
                        result['chip_id'] = potential_chip
                        result['chip_note'] = f'Non-standard length: {len(potential_chip)} digits'
                        break
            
            # If no chip found, at least note what we found
            if not result['chip_id'] and data:
                result['parse_error'] = f'No chip ID pattern found in data: {data}'
                
        else:
            result['parse_error'] = f'Frame does not start with A: {payload[:5]}'
            
    except Exception as e:
        result['parse_error'] = f'Parse exception: {str(e)}'
    
    return result


def test_rbc_reader(port='/dev/ttyUSB0', baud=9600, timeout=None):
    """
    Test RBC-A04 reader by listening for incoming data frames
    
    Args:
        port (str): Serial port path
        baud (int): Baud rate (typically 9600)
        timeout (float): Test timeout in seconds, None for infinite
    """
    
    print(f"RBC-A04 Pet Microchip Reader Test")
    print(f"{'='*50}")
    print(f"Port: {port}")
    print(f"Baud: {baud} (8N1)")
    print(f"Timeout: {timeout}s" if timeout else "Timeout: None (run until Ctrl+C)")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # Open serial connection
        ser = serial.Serial(
            port=port,
            baudrate=baud,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1.0  # 1 second read timeout
        )
        
        print(f"✓ Serial connection opened successfully")
        print(f"  Device: {ser.name}")
        print(f"  Settings: {ser.baudrate} {ser.bytesize}{ser.parity}{ser.stopbits}")
        print()
        print("Listening for data... (Press Ctrl+C to stop)")
        print("-" * 50)
        
        # Statistics
        total_frames = 0
        valid_frames = 0
        invalid_frames = 0
        chip_detections = 0
        
        start_time = time.time()
        
        while True:
            try:
                # Check timeout
                if timeout and (time.time() - start_time) > timeout:
                    print(f"\n⏰ Test timeout reached ({timeout}s)")
                    break
                
                # Read a line (blocks until \n or timeout)
                line_bytes = ser.readline()
                
                if line_bytes:
                    total_frames += 1
                    
                    # Decode to string, handling encoding errors gracefully
                    try:
                        raw_frame = line_bytes.decode('ascii', errors='replace').strip()
                    except UnicodeDecodeError:
                        raw_frame = line_bytes.decode('ascii', errors='ignore').strip()
                    
                    # Skip empty lines
                    if not raw_frame:
                        continue
                    
                    # Print raw frame with timestamp
                    timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
                    print(f"[{timestamp}] RAW: {raw_frame}")
                    
                    # Parse the frame
                    try:
                        result = parse_rbc_frame(raw_frame)
                        
                        if result['valid_frame']:
                            valid_frames += 1
                            print(f"              ✓ Valid frame")
                            print(f"                Address: {result.get('address', 'N/A')}")
                            print(f"                Command: {result.get('command', 'N/A')}")
                            print(f"                Status:  {result.get('status', 'N/A')}")
                            print(f"                Data:    {result.get('data', 'N/A')}")
                            
                            if result['chip_id']:
                                chip_detections += 1
                                print(f"                🐾 CHIP ID: {result['chip_id']}")
                                if 'chip_note' in result:
                                    print(f"                   Note: {result['chip_note']}")
                            else:
                                print(f"                ⚠ No chip ID found")
                                if result.get('parse_error'):
                                    print(f"                   Error: {result['parse_error']}")
                        else:
                            invalid_frames += 1
                            print(f"              ✗ Invalid frame")
                            if result.get('parse_error'):
                                print(f"                Error: {result['parse_error']}")
                    
                    except Exception as parse_error:
                        invalid_frames += 1
                        print(f"              ✗ Parse error: {parse_error}")
                    
                    print()  # Empty line for readability
                    
            except serial.SerialTimeoutException:
                # Timeout is normal, just continue
                continue
                
            except serial.SerialException as e:
                print(f"✗ Serial read error: {e}")
                print("  Connection may have been lost, trying to continue...")
                time.sleep(1)
                continue
                
            except Exception as e:
                print(f"✗ Unexpected error: {e}")
                print("  Continuing to read...")
                continue
            
    except serial.SerialException as e:
        print(f"✗ Serial connection failed: {e}")
        print(f"  Check:")
        print(f"  - Port exists: ls -la {port}")
        print(f"  - Permissions: sudo chmod 666 {port}")
        print(f"  - User in dialout group: groups $USER")
        return False
        
    except KeyboardInterrupt:
        print(f"\n🛑 Test stopped by user")
        
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print(f"✓ Serial connection closed")
    
    # Print summary statistics
    elapsed = time.time() - start_time
    print(f"\n{'='*50}")
    print(f"Test Summary:")
    print(f"  Duration: {elapsed:.1f}s")
    print(f"  Total frames received: {total_frames}")
    print(f"  Valid frames: {valid_frames}")
    print(f"  Invalid frames: {invalid_frames}")
    print(f"  Chip detections: {chip_detections}")
    
    if total_frames > 0:
        print(f"  Frame rate: {total_frames/elapsed:.1f} frames/sec")
        print(f"  Success rate: {valid_frames/total_frames*100:.1f}%")
    
    return True


def main():
    """Main function with command line argument parsing"""
    parser = argparse.ArgumentParser(
        description='Test RBC-A04 Pet Microchip Reader',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python test_reader.py
    python test_reader.py --port /dev/ttyUSB0 --baud 9600
    python test_reader.py --port /dev/ttyUSB1 --timeout 30
    python test_reader.py --help

Expected data format: $A0112OKD900263003496836#
    $ = Start marker
    A = Protocol identifier  
    01 = Address
    12 = Command
    OK = Status
    D900263003496836 = Data (contains 15-digit chip ID)
    # = End marker
        """
    )
    
    parser.add_argument(
        '--port', '-p',
        default='/dev/ttyUSB0',
        help='Serial port path (default: /dev/ttyUSB0)'
    )
    
    parser.add_argument(
        '--baud', '-b',
        type=int,
        default=9600,
        help='Baud rate (default: 9600)'
    )
    
    parser.add_argument(
        '--timeout', '-t',
        type=float,
        default=None,
        help='Test timeout in seconds (default: run until Ctrl+C)'
    )
    
    parser.add_argument(
        '--test-parse',
        action='store_true',
        help='Test frame parsing with sample data and exit'
    )
    
    args = parser.parse_args()
    
    # Test parsing function with sample data
    if args.test_parse:
        print("Testing frame parsing with sample data:")
        print("=" * 40)
        
        test_frames = [
            "$A0112OKD900263003496836#",
            "$A0112OK123456789012345#",  
            "$A0112ERROR#",
            "$INVALID",
            "A0112OKD900263003496836",  # Missing $ #
            "$A01#",  # Too short
        ]
        
        for frame in test_frames:
            print(f"\nFrame: {frame}")
            result = parse_rbc_frame(frame)
            for key, value in result.items():
                if value is not None:
                    print(f"  {key}: {value}")
        return
    
    # Validate arguments
    if args.baud not in [9600, 19200, 38400, 57600, 115200]:
        print(f"Warning: Unusual baud rate {args.baud}, RBC-A04 typically uses 9600")
    
    # Run the test
    success = test_rbc_reader(args.port, args.baud, args.timeout)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()