#!/usr/bin/env python3
"""
Pet Chip Reader - Python Hardware Test
Tests cameras, serial communication, and Python environment
"""

import os
import sys
import time
import subprocess
from pathlib import Path

def print_status(success, message):
    """Print colored status message"""
    if success:
        print(f"✓ {message}")
    else:
        print(f"✗ {message}")

def print_info(message):
    """Print info message"""
    print(f"ℹ {message}")

def print_warning(message):
    """Print warning message"""
    print(f"⚠ {message}")

def test_python_imports():
    """Test required Python imports"""
    print("\n1. Python Import Test")
    print("---------------------")
    
    # Test serial
    try:
        import serial
        print_status(True, "pyserial import successful")
    except ImportError as e:
        print_status(False, f"pyserial import failed: {e}")
        return False
    
    # Test dotenv
    try:
        from dotenv import load_dotenv
        print_status(True, "python-dotenv import successful")
    except ImportError as e:
        print_status(False, f"python-dotenv import failed: {e}")
        return False
        
    # Test twilio
    try:
        from twilio.rest import Client
        print_status(True, "twilio import successful")
    except ImportError as e:
        print_status(False, f"twilio import failed: {e}")
        print_warning("Install with: pip install twilio")
        
    # Test picamera2
    try:
        from picamera2 import Picamera2
        print_status(True, "picamera2 import successful")
    except ImportError as e:
        print_status(False, f"picamera2 import failed: {e}")
        print_warning("Install with: sudo apt install python3-picamera2")
        return False
        
    return True

def test_cameras():
    """Test camera functionality"""
    print("\n2. Camera Hardware Test")
    print("-----------------------")
    
    try:
        from picamera2 import Picamera2
        
        # Get available cameras
        cameras = Picamera2.global_camera_info()
        print_info(f"Found {len(cameras)} camera(s)")
        
        if len(cameras) < 2:
            print_status(False, f"Need 2 cameras, found {len(cameras)}")
            return False
            
        # Test camera 0
        try:
            print_info("Testing camera 0...")
            cam0 = Picamera2(0)
            config0 = cam0.create_still_configuration(main={"size": (640, 480)})
            cam0.configure(config0)
            cam0.start()
            time.sleep(2)  # Allow camera to initialize
            
            # Take test photo
            test_file = "test_cam0_python.jpg"
            cam0.capture_file(test_file)
            cam0.stop()
            cam0.close()
            
            if Path(test_file).exists():
                print_status(True, f"Camera 0 test successful: {test_file}")
            else:
                print_status(False, "Camera 0 test failed - no file created")
                
        except Exception as e:
            print_status(False, f"Camera 0 test failed: {e}")
            
        # Test camera 1
        try:
            print_info("Testing camera 1...")
            cam1 = Picamera2(1)
            config1 = cam1.create_still_configuration(main={"size": (640, 480)})
            cam1.configure(config1)
            cam1.start()
            time.sleep(2)  # Allow camera to initialize
            
            # Take test photo
            test_file = "test_cam1_python.jpg"
            cam1.capture_file(test_file)
            cam1.stop()
            cam1.close()
            
            if Path(test_file).exists():
                print_status(True, f"Camera 1 test successful: {test_file}")
            else:
                print_status(False, "Camera 1 test failed - no file created")
                
        except Exception as e:
            print_status(False, f"Camera 1 test failed: {e}")
            
        return True
        
    except Exception as e:
        print_status(False, f"Camera test failed: {e}")
        return False

def test_serial_ports():
    """Test serial port access"""
    print("\n3. Serial Port Test")
    print("------------------")
    
    try:
        import serial
        import serial.tools.list_ports
        
        # List available ports
        ports = list(serial.tools.list_ports.comports())
        print_info(f"Found {len(ports)} serial ports")
        
        usb_ports = [port for port in ports if 'USB' in port.device or 'ttyUSB' in port.device]
        
        if not usb_ports:
            print_status(False, "No USB serial ports found")
            print_warning("Check USB-RS485 adapter connection")
            return False
            
        for port in usb_ports:
            print_info(f"  {port.device}: {port.description}")
            
            # Test opening the port
            try:
                ser = serial.Serial(port.device, 9600, timeout=1)
                ser.close()
                print_status(True, f"{port.device} can be opened")
            except serial.SerialException as e:
                print_status(False, f"{port.device} cannot be opened: {e}")
                print_warning("Add user to dialout group: sudo usermod -a -G dialout $USER")
                
        return True
        
    except ImportError:
        print_status(False, "pyserial not available for port testing")
        return False

def test_configuration():
    """Test configuration file"""
    print("\n4. Configuration Test")
    print("--------------------")
    
    if not Path(".env").exists():
        print_status(False, ".env file not found")
        print_warning("Copy from .env.example and configure")
        return False
        
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        # Check key settings
        port = os.getenv('PORT', '/dev/ttyUSB0')
        photo_dir = os.getenv('PHOTO_DIR', '/home/pi/rfid_photos')
        
        print_info(f"Serial port: {port}")
        print_info(f"Photo directory: {photo_dir}")
        
        # Check if port exists
        if Path(port).exists():
            print_status(True, f"Serial port {port} exists")
        else:
            print_status(False, f"Serial port {port} does not exist")
            
        # Check/create photo directory
        photo_path = Path(photo_dir)
        if photo_path.exists():
            print_status(True, f"Photo directory exists: {photo_dir}")
        else:
            print_info(f"Creating photo directory: {photo_dir}")
            photo_path.mkdir(parents=True, exist_ok=True)
            print_status(True, f"Photo directory created: {photo_dir}")
            
        return True
        
    except Exception as e:
        print_status(False, f"Configuration test failed: {e}")
        return False

def test_rbc_a04_communication():
    """Test basic RBC-A04 communication"""
    print("\n5. RBC-A04 Communication Test")
    print("-----------------------------")
    
    try:
        import serial
        from dotenv import load_dotenv
        load_dotenv()
        
        port = os.getenv('PORT', '/dev/ttyUSB0')
        baud = int(os.getenv('BAUD', '9600'))
        
        if not Path(port).exists():
            print_status(False, f"Serial port {port} not found")
            return False
            
        # Calculate BCC for poll command
        def calculate_bcc(data):
            bcc = 0
            for byte in data.encode('ascii'):
                bcc ^= byte
            return f"{bcc:02X}"
            
        # Create poll command
        addr = os.getenv('POLL_ADDR', '01')
        fmt = os.getenv('POLL_FMT', 'D')
        payload = f"A{addr}01{fmt}"
        bcc = calculate_bcc(payload)
        command = f"${payload}{bcc}#"
        
        print_info(f"Testing with command: {command}")
        
        try:
            ser = serial.Serial(port, baud, timeout=2)
            print_status(True, f"Serial connection opened on {port}")
            
            # Send poll command
            ser.write(command.encode('ascii'))
            print_info("Poll command sent")
            
            # Wait for response
            response = ''
            start_time = time.time()
            while time.time() - start_time < 3:
                if ser.in_waiting > 0:
                    data = ser.read(ser.in_waiting)
                    response += data.decode('ascii', errors='ignore')
                    if response.endswith('#'):
                        break
                time.sleep(0.1)
                
            ser.close()
            
            if response:
                print_status(True, f"Received response: {response}")
                print_info("RBC-A04 reader is responding")
            else:
                print_status(False, "No response from RBC-A04 reader")
                print_warning("Check reader connection and power")
                
        except serial.SerialException as e:
            print_status(False, f"Serial communication failed: {e}")
            return False
            
        return True
        
    except Exception as e:
        print_status(False, f"Communication test failed: {e}")
        return False

def main():
    """Main test function"""
    print("=========================================")
    print("Pet Chip Reader - Python Hardware Test")
    print("=========================================")
    
    # Change to the correct directory if needed
    if Path("src/a04_dualcam_notify.py").exists():
        print_info("Running from correct directory")
    else:
        print_warning("Should be run from rfid_cam directory")
    
    # Run tests
    tests_passed = 0
    total_tests = 5
    
    if test_python_imports():
        tests_passed += 1
        
    if test_cameras():
        tests_passed += 1
        
    if test_serial_ports():
        tests_passed += 1
        
    if test_configuration():
        tests_passed += 1
        
    if test_rbc_a04_communication():
        tests_passed += 1
    
    # Summary
    print(f"\n=========================================")
    print(f"Test Summary: {tests_passed}/{total_tests} tests passed")
    print(f"=========================================")
    
    if tests_passed == total_tests:
        print("✓ All tests passed! Hardware appears to be working correctly.")
        print("  Next step: Run ./scripts/test_locally.sh")
    else:
        print("✗ Some tests failed. Please address the issues above.")
        print("  Refer to the README.md troubleshooting section.")
    
    return tests_passed == total_tests

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)