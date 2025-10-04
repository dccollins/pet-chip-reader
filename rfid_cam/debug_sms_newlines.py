#!/usr/bin/env python3
"""
Debug SMS Newline Issue

Compare message formats between working and non-working SMS
"""

def debug_sms_formats():
    """Debug different SMS message formats"""
    
    print("🔍 SMS Message Format Debug")
    print("=" * 30)
    
    # Working format from main app
    working_message = f"🐾 Pet detected\nAnimal: Orange tabby cat\nChip: 496836"
    
    # Recovery digest format (the problematic one)
    digest_message = f"🐾 Pet Alert Digest\n15 detections from 2 pets over 3h\nMost active: ...496836 (8x)"
    
    # Simple test message
    simple_message = "🐾 Test\nLine 2\nLine 3"
    
    messages = [
        ("Working Format (Main App)", working_message),
        ("Digest Format (Recovery)", digest_message), 
        ("Simple Test", simple_message)
    ]
    
    for name, message in messages:
        print(f"\n📝 {name}:")
        print(f"   Raw: {repr(message)}")
        print(f"   Display:")
        for line in message.split('\n'):
            print(f"      {line}")
        print(f"   Length: {len(message)}")
        print(f"   Newlines at positions: {[i for i, c in enumerate(message) if c == chr(10)]}")
    
    # Check for any hidden characters
    print(f"\n🔍 Character Analysis of Digest Message:")
    for i, char in enumerate(digest_message):
        if ord(char) < 32 or ord(char) > 126:
            print(f"   Position {i}: {repr(char)} (ord={ord(char)})")
    
    print("\n💡 Suggestion:")
    print("   Try sending a simple working format first to confirm SMS gateway works")
    print("   Then gradually add complexity to isolate the issue")

if __name__ == '__main__':
    debug_sms_formats()