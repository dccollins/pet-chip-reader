#!/usr/bin/env python3
"""
Show Updated Email Format Examples
Displays exactly what you'll receive with explicit Google Drive links
"""

from datetime import datetime

def show_updated_format():
    """Show the updated plain text email format with explicit links"""
    
    time_str = datetime.now().strftime('%H:%M')
    sample_link = "https://drive.google.com/file/d/1IjFZnNS8zKqL0cjwZMetuETpJtu7pKtY/view"
    
    print("📧 UPDATED EMAIL FORMAT (PLAIN TEXT):")
    print("=" * 50)
    
    print("\n🐾 REGULAR PET DETECTION:")
    print("Subject: 🐾 Pet Alert")
    print("Content-Type: text/plain")
    regular_msg = f"""🐾 Pet detected
Chip: 987654321098765
Time: {time_str}
Photo: {sample_link}"""
    print(regular_msg)
    
    print("\n🚨 LOST PET DETECTION:")
    print("Subject: 🚨 LOST PET FOUND!")
    print("Content-Type: text/plain") 
    lost_pet_msg = f"""🚨 LOST PET DETECTED!
Chip: 900263003496836
Time: {time_str}
Photo: {sample_link}"""
    print(lost_pet_msg)
    
    print("\n📧 DAILY SUMMARY EMAIL:")
    print("Subject: 🐾 Daily Pet Detection Summary - 2025-09-29")
    print("To: dccollins@gmail.com")
    print("Content-Type: multipart/mixed (with image attachments)")
    daily_summary = f"""Daily Pet Detection Report - 2025-09-29
==================================================

Total Detections: 3

1. Time: 2025-09-29 09:15:23
   Chip ID: 987654321098765
   Photos: 1 captured

2. Time: 2025-09-29 14:30:45
   Chip ID: 555666777888999
   Photos: 1 captured

3. Time: 2025-09-29 18:22:10
   Chip ID: 900263003496836 (LOST PET!)
   Photos: 1 captured

[Attached: thumbnail images for each detection]"""
    print(daily_summary)
    
    print("\n" + "=" * 50)
    print("✅ FIXED: Plain text with explicit Google Drive links")
    print("✅ FIXED: No HTML formatting")
    print("✅ FIXED: No TinyURL shortening") 
    print("✅ NEW: Daily summary at 11:59 PM")
    print("✅ NEW: Email to dccollins@gmail.com with thumbnails")
    
    print("\n📱 WHAT YOU'LL RECEIVE:")
    print("- Instant SMS via Google Fi with full photo links")
    print("- Daily email summary with photo thumbnails")
    print("- Direct Google Drive access, no redirects")

if __name__ == "__main__":
    show_updated_format()