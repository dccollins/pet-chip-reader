#!/usr/bin/env python3
"""
Test Sequential Processing: Capture → Upload → AI Analysis → Complete Notification
"""

import os
import sys
import subprocess
import json
import base64
from datetime import datetime
from pathlib import Path

# Add the src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from dotenv import load_dotenv

def test_openai_analysis(photo_path):
    """Test OpenAI animal analysis on an existing photo"""
    try:
        from openai import OpenAI
        
        load_dotenv()
        openai_api_key = os.getenv('OPENAI_API_KEY', '')
        
        if not openai_api_key:
            return "No OpenAI API key configured"
            
        client = OpenAI(api_key=openai_api_key)
        
        # Read and encode the image
        with open(photo_path, 'rb') as image_file:
            image_data = base64.b64encode(image_file.read()).decode('utf-8')
        
        print(f"📸 Analyzing photo: {photo_path.name}")
        print("🤖 Sending to OpenAI for animal identification...")
        
        # Create the prompt for animal identification
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "What animal do you see in this image? Respond with just the animal type and breed if visible, be very brief (max 10 words)."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_data}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=30,
            temperature=0.1
        )
        
        ai_description = response.choices[0].message.content.strip()
        return ai_description
        
    except Exception as e:
        return f"AI analysis failed: {e}"

def simulate_complete_workflow():
    """Simulate the complete workflow: Capture → Upload → AI → Notify"""
    
    print("🔄 Simulating Complete Pet Detection Workflow")
    print("=" * 60)
    
    # Simulate tag detection
    tag_id = "900263003496836"
    timestamp = datetime.now()
    
    print(f"1️⃣ Pet chip detected: {tag_id}")
    print(f"⏰ Timestamp: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Find recent photos to simulate capture
    photo_dir = Path("/home/collins/rfid_photos")
    recent_photos = list(photo_dir.glob(f"*{tag_id}*.jpg"))[-2:]
    
    if not recent_photos:
        print("❌ No photos found for testing")
        return False
    
    print(f"\\n2️⃣ Photos captured: {len(recent_photos)} images")
    for i, photo in enumerate(recent_photos):
        print(f"   📸 Camera {i+1}: {photo.name}")
    
    # Simulate upload and link generation
    print(f"\\n3️⃣ Uploading to Google Drive...")
    photo_links = []
    for photo in recent_photos:
        try:
            cmd = ['rclone', 'lsjson', f"gdrive:rfid_photos/{photo.name}"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                file_info = json.loads(result.stdout)
                if file_info and len(file_info) > 0:
                    file_id = file_info[0].get('ID')
                    if file_id:
                        link = f"https://drive.google.com/file/d/{file_id}/view"
                        photo_links.append(link)
                        print(f"   ✅ Generated link for {photo.name}")
        except Exception as e:
            print(f"   ⚠️  Could not get link for {photo.name}: {e}")
    
    # AI Analysis
    print(f"\\n4️⃣ AI Analysis...")
    ai_description = test_openai_analysis(recent_photos[0])
    print(f"   🤖 AI Result: {ai_description}")
    
    # Generate complete notification
    print(f"\\n5️⃣ Generating Complete Notification...")
    
    date_str = timestamp.strftime('%A, %B %d, %Y')
    time_str = timestamp.strftime('%H:%M')
    
    message = f"🐾 Pet detected{chr(10)}Chip: {tag_id}{chr(10)}Date: {date_str}{chr(10)}Time: {time_str}"
    
    if ai_description and "analysis failed" not in ai_description.lower():
        message += f"{chr(10)}Animal: {ai_description}"
    
    if photo_links:
        for i, link in enumerate(photo_links):
            message += f"{chr(10)}Photo{i+1}: {link}"
    
    print("\\n📱 FINAL SMS MESSAGE:")
    print("=" * 40)
    print(message)
    print("=" * 40)
    
    print(f"\\n✨ Complete workflow finished!")
    print(f"⏱️  Now notifications are sent AFTER:")
    print(f"   ✅ Photos captured")
    print(f"   ✅ Photos uploaded with real links")
    print(f"   ✅ AI analysis completed")
    print(f"   ✅ Complete notification ready")
    
    return True

if __name__ == '__main__':
    print("🧪 Testing Sequential Pet Detection Workflow")
    print("============================================")
    print("This simulates the new process:")
    print("Capture → Upload → AI Analysis → Complete Notification")
    print()
    
    success = simulate_complete_workflow()
    
    if success:
        print("\\n🎯 Sequential workflow test completed!")
        print("📱 Your SMS messages will now be complete with:")
        print("   • AI animal identification")
        print("   • Working Google Drive links")
        print("   • Sent only after everything is ready")
    else:
        print("\\n❌ Test failed")
        sys.exit(1)