#!/usr/bin/env python3
"""
Test OpenAI Animal Identification
Tests the GPT-4 Vision API integration with existing photos
"""

import os
import sys
import base64
import json
from datetime import datetime
from pathlib import Path

# Add the current directory to path to import from src
sys.path.append('/home/collins/repos/pet-chip-reader/rfid_cam')

def test_animal_identification():
    """Test animal identification with existing photos"""
    
    # Load OpenAI API key from environment
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY not found in environment")
        print("   Please add it to your .env file")
        return
    
    # Find the most recent photo
    photo_dir = Path("/home/collins/rfid_photos")
    if not photo_dir.exists():
        print("❌ No photos directory found")
        return
        
    photos = list(photo_dir.glob("*.jpg"))
    if not photos:
        print("❌ No photos found")
        return
        
    # Use the most recent photo
    latest_photo = max(photos, key=lambda p: p.stat().st_mtime)
    print(f"🖼️  Testing with: {latest_photo.name}")
    
    try:
        import urllib.request
        import urllib.parse
        
        # Encode image to base64
        with open(latest_photo, 'rb') as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')
        
        # Prepare OpenAI API request
        api_url = "https://api.openai.com/v1/chat/completions"
        
        headers = {
            "Content-Type": "application/json", 
            "Authorization": f"Bearer {api_key}"
        }
        
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Look at this photo and identify the animal. Respond with just a brief description like 'black cat', 'golden retriever', 'tabby cat', 'white dog', etc. Focus on the main animal in the photo. If no clear animal is visible, respond with 'animal'."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}",
                                "detail": "low"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 50,
            "temperature": 0.3
        }
        
        # Make API request
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(api_url, data=data, headers=headers)
        
        print("🤖 Analyzing photo with OpenAI GPT-4 Vision...")
        
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
            
        if 'choices' in result and len(result['choices']) > 0:
            animal_description = result['choices'][0]['message']['content'].strip().lower()
            print(f"✅ Animal identified: {animal_description}")
            
            # Show what the enhanced message would look like
            now = datetime.now()
            date_str = now.strftime('%A, %B %d, %Y')
            time_str = now.strftime('%H:%M')
            
            print(f"\n📧 ENHANCED MESSAGE PREVIEW:")
            print("=" * 40)
            enhanced_message = f"""🐾 Pet detected
Animal: {animal_description}
Chip: 987654321098765
Date: {date_str}
Time: {time_str}
Photo: https://drive.google.com/file/d/1abc123.../view"""
            print(enhanced_message)
            
        else:
            print("❌ No animal identification in API response")
            print("Response:", result)
            
    except Exception as e:
        print(f"❌ Animal identification test failed: {e}")

if __name__ == "__main__":
    print("🧪 TESTING OPENAI ANIMAL IDENTIFICATION")
    print("=" * 50)
    test_animal_identification()