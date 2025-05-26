#!/usr/bin/env python3
"""
Test script for the transcription endpoint.
"""

import os
import requests
import base64
import json

def test_transcription_endpoint():
    """Test the backend transcription endpoint."""
    
    # Check if CHUTES_API_KEY is set
    api_key = os.getenv("CHUTES_API_KEY")
    if not api_key:
        print("❌ Error: CHUTES_API_KEY environment variable is not set!")
        print("Please set it with: export CHUTES_API_KEY=your_api_key")
        return False
    
    print(f"✅ API Key is set: {api_key[:10]}...")
    
    # Create a simple test audio data (base64 encoded silence)
    # This is a minimal WAV file with 1 second of silence
    wav_header = b'RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00D\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00'
    test_audio_b64 = base64.b64encode(wav_header).decode('utf-8')
    
    # Test the backend endpoint
    backend_url = "http://localhost:8000/api/transcribe"
    
    try:
        print(f"🔄 Testing backend endpoint: {backend_url}")
        response = requests.post(
            backend_url,
            headers={'Content-Type': 'application/json'},
            json={'audio_b64': test_audio_b64},
            timeout=30
        )
        
        print(f"📊 Response status: {response.status_code}")
        print(f"📄 Response content: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Backend transcription successful!")
            print(f"📝 Transcription: '{data.get('transcription', '')}'")
            return True
        else:
            print(f"❌ Backend transcription failed: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to backend server. Is it running on localhost:8000?")
        return False
    except Exception as e:
        print(f"❌ Error testing backend: {str(e)}")
        return False

if __name__ == "__main__":
    print("🎤 Testing Transcription Endpoint")
    print("=" * 40)
    
    success = test_transcription_endpoint()
    
    if success:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Tests failed!")
        print("\nTroubleshooting:")
        print("1. Make sure CHUTES_API_KEY is set in your environment")
        print("2. Make sure the backend server is running: python ws_server.py")
        print("3. Check the server logs for any errors") 