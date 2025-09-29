#!/usr/bin/env python3
"""
Test email notifications for pet chip reader
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from dotenv import load_dotenv
import os

def test_email_notification():
    """Test email notification system"""
    load_dotenv()
    
    # Get email settings
    smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    smtp_user = os.getenv('SMTP_USER', '')
    smtp_pass = os.getenv('SMTP_PASS', '')
    email_from = os.getenv('EMAIL_FROM', '')
    alert_to_email = os.getenv('ALERT_TO_EMAIL', '')
    
    if not all([smtp_user, smtp_pass, email_from, alert_to_email]):
        print("❌ Missing email configuration in .env file")
        print(f"SMTP_USER: {'✓' if smtp_user else '✗'}")
        print(f"SMTP_PASS: {'✓' if smtp_pass else '✗'}")
        print(f"EMAIL_FROM: {'✓' if email_from else '✗'}")
        print(f"ALERT_TO_EMAIL: {'✓' if alert_to_email else '✗'}")
        return False
    
    print(f"Testing email notification...")
    print(f"From: {email_from}")
    print(f"To: {alert_to_email}")
    print(f"SMTP: {smtp_host}:{smtp_port}")
    
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = email_from
        msg['To'] = alert_to_email
        msg['Subject'] = "Pet Chip Reader - Test Alert"
        
        body = f"""
🐾 PET CHIP READER TEST

This is a test of your pet chip reader notification system.

Test Details:
- Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- System: Raspberry Pi 5 Pet Chip Reader
- Status: Notifications Working ✓

If you received this message, your email notifications are configured correctly!
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        print("Connecting to SMTP server...")
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            print("Logging in...")
            server.login(smtp_user, smtp_pass)
            print("Sending test message...")
            server.send_message(msg)
            
        print("✅ Test email sent successfully!")
        print(f"Check your phone for a text message at {alert_to_email}")
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ Gmail authentication failed: {e}")
        print("Check your Gmail app password in the .env file")
        return False
        
    except Exception as e:
        print(f"❌ Email test failed: {e}")
        return False

if __name__ == "__main__":
    test_email_notification()