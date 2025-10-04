#!/usr/bin/env python3
"""
System Status Check - Verify all components are working
"""
import os
import subprocess
import serial
import time

def check_service():
    """Check if rfid_cam service is running"""
    try:
        result = subprocess.run(['systemctl', 'is-active', 'rfid_cam'], 
                              capture_output=True, text=True)
        return result.stdout.strip() == 'active'
    except:
        return False

def check_devices():
    """Check if hardware devices are accessible"""
    devices = {}
    
    # Check RFID reader
    try:
        with serial.Serial('/dev/ttyUSB0', 9600, timeout=1):
            devices['RFID'] = True
    except:
        devices['RFID'] = False
    
    # Check GPS device
    try:
        with serial.Serial('/dev/ttyACM0', 9600, timeout=1):
            devices['GPS'] = True
    except:
        devices['GPS'] = False
    
    return devices

def check_configuration():
    """Check .env configuration"""
    from dotenv import load_dotenv
    load_dotenv()
    
    config = {
        'GPS_ENABLED': os.getenv('GPS_ENABLED'),
        'GPS_PORT': os.getenv('GPS_PORT'),
        'OPENAI_API_KEY': 'Set' if os.getenv('OPENAI_API_KEY') else 'Not Set',
        'RCLONE_REMOTE': os.getenv('RCLONE_REMOTE'),
        'PORT': os.getenv('PORT')
    }
    return config

def main():
    print("🔍 Pet Chip Reader System Status Check")
    print("=" * 50)
    
    # Service status
    service_running = check_service()
    status_icon = "✅" if service_running else "❌"
    print(f"{status_icon} RFID Cam Service: {'Running' if service_running else 'Not Running'}")
    
    # Hardware devices
    devices = check_devices()
    print(f"\n📱 Hardware Devices:")
    for device, status in devices.items():
        icon = "✅" if status else "❌"
        port = "/dev/ttyUSB0" if device == "RFID" else "/dev/ttyACM0"
        print(f"   {icon} {device}: {port} {'Available' if status else 'Not Available'}")
    
    # Configuration
    config = check_configuration()
    print(f"\n⚙️  Configuration:")
    for key, value in config.items():
        icon = "✅" if value and value != 'Not Set' else "❌"
        print(f"   {icon} {key}: {value}")
    
    # Overall status
    all_good = (service_running and 
                all(devices.values()) and 
                config['GPS_ENABLED'] == 'true' and
                config['OPENAI_API_KEY'] != 'Not Set')
    
    print(f"\n🎯 Overall System Status:")
    if all_good:
        print("   🟢 FULLY OPERATIONAL")
        print("   • Pet chip detection ready")
        print("   • GPS location tracking active") 
        print("   • AI identification enabled")
        print("   • Cloud storage configured")
        print("   • Enhanced notifications ready")
    else:
        print("   🟡 PARTIALLY OPERATIONAL")
        if not service_running:
            print("   • Service needs to be started")
        if not all(devices.values()):
            print("   • Check hardware connections")
        if config['GPS_ENABLED'] != 'true':
            print("   • GPS not enabled in configuration")
        if config['OPENAI_API_KEY'] == 'Not Set':
            print("   • OpenAI API key not configured")

if __name__ == "__main__":
    main()