#!/usr/bin/env python3
"""
Test HTML Email Format Display
Shows what the new HTML-formatted email notifications look like
"""

from datetime import datetime

def show_email_format():
    """Display the new HTML email format examples"""
    
    time_str = datetime.now().strftime('%H:%M')
    sample_link = "https://drive.google.com/file/d/1IjFZnNS8zKqL0cjwZMetuETpJtu7pKtY/view"
    
    print("📧 NEW HTML EMAIL FORMAT:")
    print("=" * 50)
    
    print("\n🐾 REGULAR PET DETECTION:")
    print("Subject: 🐾 Pet Alert")
    print("Content-Type: text/html")
    regular_html = f"""🐾 Pet detected
Chip: 987654321098765
Time: {time_str}
<a href="{sample_link}">📸 View Photo</a>"""
    print(regular_html)
    
    print("\n🚨 LOST PET DETECTION:")
    print("Subject: 🚨 LOST PET FOUND!")
    print("Content-Type: text/html")
    lost_pet_html = f"""🚨 LOST PET DETECTED!
Chip: 900263003496836
Time: {time_str}
<a href="{sample_link}">📸 View Photo</a>"""
    print(lost_pet_html)
    
    print("\n" + "=" * 50)
    print("✅ Email will be sent as HTML format")
    print("✅ Link will be clickable in email clients")
    print("✅ Full Google Drive URLs (no shortening)")
    print("✅ Clean 📸 View Photo button")
    
    print("\n📱 HOW IT APPEARS IN GMAIL/PHONE:")
    print("- Text message via Google Fi SMS gateway")
    print("- HTML renders as clickable link")
    print("- Direct access to Google Drive photos")
    print("- No more tiny URLs!")

if __name__ == "__main__":
    show_email_format()