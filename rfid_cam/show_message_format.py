#!/usr/bin/env python3
"""
Show example of brief notification messages
"""

from datetime import datetime

def show_message_examples():
    """Show what the brief messages look like"""
    
    time_str = datetime.now().strftime('%H:%M')
    
    print("📱 BRIEF MESSAGE EXAMPLES:")
    print("=" * 40)
    
    print("\n🐾 REGULAR PET DETECTION:")
    print("Subject: 🐾 Pet Alert")
    regular_msg = f"""🐾 Pet detected
Chip: 987654321098765
Time: {time_str}
VIEW: https://tinyurl.com/2xz9rqu9"""
    print(regular_msg)
    
    print("\n🚨 LOST PET DETECTION:")
    print("Subject: 🚨 LOST PET FOUND!")
    lost_pet_msg = f"""🚨 LOST PET DETECTED!
Chip: 900263003496836
Time: {time_str}
VIEW: https://tinyurl.com/4a5b6c7d"""
    print(lost_pet_msg)
    
    print("\n" + "=" * 40)
    print("✅ These messages will arrive as text messages on your phone via Google Fi!")
    print("✅ Much more concise than the original long emails")
    print("✅ Includes direct link to Google Drive photos folder")
    print("✅ Special alert format for your lost pet")

if __name__ == "__main__":
    show_message_examples()