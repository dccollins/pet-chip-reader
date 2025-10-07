#!/usr/bin/env python3
"""
Test dual camera capture and email with proper HTML formatting
"""
import os
import sys
import time
import smtplib
from datetime import datetime
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage

# Add the src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

try:
    from picamera2 import Picamera2
    from dotenv import load_dotenv
except ImportError as e:
    print(f"Missing required module: {e}")
    sys.exit(1)

def test_dual_camera_capture():
    """Test capturing photos from both cameras"""
    print("🔍 Testing dual camera capture...")
    
    # Load environment
    load_dotenv()
    
    try:
        # Initialize cameras
        cameras = {}
        camera_info = Picamera2.global_camera_info()
        
        print(f"📷 Found {len(camera_info)} cameras")
        
        for i, info in enumerate(camera_info[:2]):  # Only use first 2 cameras
            print(f"   Camera {i}: {info['Model']}")
            
            camera = Picamera2(camera_num=i)
            config = camera.create_still_configuration(
                main={"size": (2304, 1296)},
                lores={"size": (640, 480)}
            )
            camera.configure(config)
            camera.start()
            
            # Allow camera to initialize
            time.sleep(2)
            
            cameras[i] = camera
        
        # Capture test photos
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        test_tag = "TEST123456789"
        photo_paths = []
        
        photo_dir = Path(os.getenv('PHOTO_DIR', '/home/collins/rfid_photos'))
        photo_dir.mkdir(parents=True, exist_ok=True)
        
        for cam_id, camera in cameras.items():
            filename = f"{timestamp}_{test_tag}_cam{cam_id}_test.jpg"
            filepath = photo_dir / filename
            
            print(f"📸 Capturing from camera {cam_id}...")
            camera.capture_file(str(filepath))
            photo_paths.append(filepath)
            print(f"   Saved: {filepath}")
        
        # Clean up cameras
        for camera in cameras.values():
            camera.stop()
            camera.close()
        
        return photo_paths
        
    except Exception as e:
        print(f"❌ Camera test failed: {e}")
        return []

def create_test_html_email(photo_paths):
    """Create a proper HTML test email"""
    
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pet Chip Reader Test</title>
</head>
<body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; background-color: #f5f5f5;">
    <div style="background-color: white; padding: 30px; border-radius: 15px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
        
        <h1 style="color: #2E8B57; text-align: center; margin-bottom: 10px; font-size: 36px;">
            🐾 Pet Chip Reader Test
        </h1>
        
        <p style="text-align: center; color: #666; margin-bottom: 30px; font-size: 18px;">
            Dual Camera System Test - """ + datetime.now().strftime('%A, %B %d, %Y at %H:%M') + """
        </p>
        
        <hr style="border: 3px solid #2E8B57; margin: 30px 0; border-radius: 3px;">
        
        <div style="background: linear-gradient(135deg, #e8f5e8, #c8e6c8); padding: 25px; border-radius: 12px; margin: 25px 0; border-left: 6px solid #4CAF50;">
            <h2 style="margin-top: 0; color: #4CAF50; font-size: 28px;">📊 System Status</h2>
            
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-top: 20px;">
                <div style="background-color: white; padding: 25px; border-radius: 12px; text-align: center; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
                    <div style="font-size: 42px; font-weight: bold; color: #2E8B57;">✅</div>
                    <div style="color: #666; font-size: 16px; margin-top: 8px;">Dual Camera System</div>
                </div>
                
                <div style="background-color: white; padding: 25px; border-radius: 12px; text-align: center; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
                    <div style="font-size: 42px; font-weight: bold; color: #FF6B6B;">📧</div>
                    <div style="color: #666; font-size: 16px; margin-top: 8px;">HTML Email Test</div>
                </div>
                
                <div style="background-color: white; padding: 25px; border-radius: 12px; text-align: center; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
                    <div style="font-size: 42px; font-weight: bold; color: #9C27B0;">🔧</div>
                    <div style="color: #666; font-size: 16px; margin-top: 8px;">System Integration</div>
                </div>
            </div>
        </div>
        
        <div style="background: linear-gradient(135deg, #fff8dc, #ffeaa7); padding: 25px; border-radius: 12px; margin: 25px 0; border-left: 6px solid #FF9800;">
            <h2 style="margin-top: 0; color: #FF9800; font-size: 28px;">📸 Camera Test Results</h2>
            
            <p style="font-size: 16px; color: #555; margin-bottom: 25px;">
                Testing both cameras in your dual camera setup. Each camera captures from a different angle for comprehensive pet monitoring.
            </p>
            
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px;">
    """
    
    # Add camera results
    for i, photo_path in enumerate(photo_paths):
        camera_name = "Standard Camera" if i == 0 else "Wide-Angle Camera"
        camera_icon = "📷" if i == 0 else "📸"
        
        html_content += f"""
                <div style="background-color: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); text-align: center;">
                    <h3 style="color: #FF9800; margin-top: 0; font-size: 20px;">
                        {camera_icon} Camera {i} - {camera_name}
                    </h3>
                    
                    <img src="cid:camera_{i}" style="width: 100%; max-width: 300px; height: auto; border-radius: 8px; margin: 15px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.2);" alt="Camera {i} Test Photo">
                    
                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; margin-top: 15px;">
                        <div style="font-weight: bold; color: #FF9800; margin-bottom: 5px;">File Details:</div>
                        <div style="font-size: 12px; color: #666; font-family: monospace;">
                            {photo_path.name}<br>
                            Size: {photo_path.stat().st_size / 1024:.1f} KB
                        </div>
                    </div>
                </div>
        """
    
    html_content += """
            </div>
        </div>
        
        <div style="background: linear-gradient(135deg, #f0f8ff, #e6f3ff); padding: 25px; border-radius: 12px; margin: 25px 0; border-left: 6px solid #2196F3;">
            <h2 style="margin-top: 0; color: #2196F3; font-size: 28px;">✨ What's Working</h2>
            
            <ul style="font-size: 16px; line-height: 1.8;">
                <li style="margin: 8px 0;">✅ <strong>Dual Camera Capture:</strong> Both cameras operational</li>
                <li style="margin: 8px 0;">✅ <strong>HTML Email Formatting:</strong> Beautiful Gmail-compatible design</li>
                <li style="margin: 8px 0;">✅ <strong>Photo Attachments:</strong> Images embedded in email</li>
                <li style="margin: 8px 0;">✅ <strong>System Integration:</strong> Ready for pet detection</li>
            </ul>
        </div>
        
        <hr style="margin: 40px 0; border: 2px solid #ddd;">
        
        <footer style="text-align: center; font-size: 14px; color: #888; background: linear-gradient(135deg, #f8f9fa, #e9ecef); padding: 25px; border-radius: 12px;">
            <p style="margin: 0; line-height: 1.8;">
                <strong>Test Generated:</strong> """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """<br>
                🔧 <strong>Pet Chip Reader System v2.1.0</strong> | Dual Camera Test<br>
                📧 <strong>HTML Email System Test</strong> - Ready for deployment
            </p>
        </footer>
        
    </div>
</body>
</html>
    """
    
    # Text fallback
    text_content = f"""
Pet Chip Reader System Test
===========================

Dual Camera System Test - {datetime.now().strftime('%A, %B %d, %Y at %H:%M')}

System Status:
✅ Dual Camera System
📧 HTML Email Test  
🔧 System Integration

Camera Test Results:
"""
    
    for i, photo_path in enumerate(photo_paths):
        camera_name = "Standard Camera" if i == 0 else "Wide-Angle Camera"
        text_content += f"""
📷 Camera {i} - {camera_name}
   File: {photo_path.name}
   Size: {photo_path.stat().st_size / 1024:.1f} KB
"""
    
    text_content += f"""
What's Working:
✅ Dual Camera Capture: Both cameras operational
✅ HTML Email Formatting: Beautiful Gmail-compatible design  
✅ Photo Attachments: Images embedded in email
✅ System Integration: Ready for pet detection

Test Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🔧 Pet Chip Reader System v2.1.0 | Dual Camera Test
"""
    
    return {'html': html_content, 'text': text_content}

def send_test_email(photo_paths, email_content):
    """Send test email with proper HTML formatting and photo attachments"""
    
    # Load environment
    load_dotenv()
    
    config = {
        'smtp_host': os.getenv('SMTP_HOST', 'smtp.gmail.com'),
        'smtp_port': int(os.getenv('SMTP_PORT', '587')),
        'smtp_user': os.getenv('SMTP_USER', ''),
        'smtp_pass': os.getenv('SMTP_PASS', ''),
        'email_from': os.getenv('EMAIL_FROM', ''),
        'digest_email': os.getenv('DIGEST_EMAIL', 'dccollins@gmail.com'),
    }
    
    if not all([config['smtp_user'], config['smtp_pass'], config['digest_email']]):
        print("❌ Email configuration incomplete")
        return False
    
    try:
        # Create multipart message
        msg = MIMEMultipart('related')
        msg['From'] = config['email_from']
        msg['To'] = config['digest_email']
        msg['Subject'] = "🐾 Pet Chip Reader - Dual Camera & HTML Email Test"
        
        # Create alternative container for text and HTML
        msg_alternative = MIMEMultipart('alternative')
        msg.attach(msg_alternative)
        
        # Add text version (fallback)
        text_part = MIMEText(email_content['text'], 'plain')
        msg_alternative.attach(text_part)
        
        # Add HTML version (preferred)
        html_part = MIMEText(email_content['html'], 'html')
        msg_alternative.attach(html_part)
        
        # Add photo attachments
        for i, photo_path in enumerate(photo_paths):
            if photo_path.exists():
                try:
                    with open(photo_path, 'rb') as f:
                        img_data = f.read()
                    
                    img = MIMEImage(img_data)
                    img.add_header('Content-ID', f'<camera_{i}>')
                    img.add_header('Content-Disposition', f'attachment; filename="{photo_path.name}"')
                    msg.attach(img)
                    
                    print(f"📎 Attached: {photo_path.name} ({len(img_data) / 1024:.1f} KB)")
                    
                except Exception as e:
                    print(f"⚠️  Failed to attach {photo_path}: {e}")
        
        # Send email
        print("📤 Sending test email...")
        with smtplib.SMTP(config['smtp_host'], config['smtp_port']) as server:
            server.starttls()
            server.login(config['smtp_user'], config['smtp_pass'])
            server.send_message(msg)
        
        print(f"✅ Test email sent successfully to {config['digest_email']}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send test email: {e}")
        return False

def main():
    print("🧪 Pet Chip Reader - Dual Camera & HTML Email Test")
    print("=" * 60)
    
    # Test camera capture
    photo_paths = test_dual_camera_capture()
    
    if not photo_paths:
        print("❌ Camera test failed - cannot proceed with email test")
        return
    
    print(f"\n📷 Successfully captured {len(photo_paths)} test photos")
    
    # Create email content
    print("📝 Creating HTML email content...")
    email_content = create_test_html_email(photo_paths)
    
    # Send test email
    print("\n📧 Sending test email with HTML formatting...")
    success = send_test_email(photo_paths, email_content)
    
    if success:
        print("\n🎉 Test completed successfully!")
        print("📧 Check your Gmail inbox for the HTML-formatted test email")
        print("📸 Email should contain photos from both cameras")
        print("\n💡 Please review the email and let me know if:")
        print("   • HTML formatting displays properly in Gmail")
        print("   • Both camera photos are visible and attached")
        print("   • Overall presentation looks good")
        print("\n⏳ Waiting for your approval before making any commits...")
    else:
        print("\n❌ Test failed - please check configuration and try again")

if __name__ == '__main__':
    main()