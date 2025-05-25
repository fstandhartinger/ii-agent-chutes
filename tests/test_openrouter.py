#!/usr/bin/env python3
"""
Simple test script to verify OpenRouter authentication and connection.
Run this to debug authentication issues.
"""

import os
import json
from openai import OpenAI

def test_openrouter_connection():
    """Test OpenRouter connection and authentication."""
    
    # Check if API key is set
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ OPENROUTER_API_KEY environment variable is not set!")
        print("Please set it with: export OPENROUTER_API_KEY='your-api-key-here'")
        return False
    
    print(f"✅ API key found: {len(api_key)} characters")
    print(f"Key starts with: {api_key[:8]}...")
    
    # Initialize OpenAI client with OpenRouter
    try:
        client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
        )
        print("✅ OpenAI client initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize OpenAI client: {e}")
        return False
    
    # Test with a simple model
    test_models = [
        "deepseek/deepseek-chat-v3-0324:free",
        "meta-llama/llama-4-maverick:free",
        "qwen/qwen2.5-vl-32b-instruct:free",
    ]
    
    for model in test_models:
        print(f"\n🧪 Testing model: {model}")
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "user", "content": "Say 'Hello, world!' and nothing else."}
                ],
                max_tokens=10,
                extra_headers={
                    "HTTP-Referer": "https://fubea.ai",
                    "X-Title": "fubea.ai Test"
                }
            )
            
            if response.choices and response.choices[0].message.content:
                print(f"✅ {model} - SUCCESS!")
                print(f"Response: {response.choices[0].message.content}")
                return True
            else:
                print(f"⚠️  {model} - Empty response")
                
        except Exception as e:
            print(f"❌ {model} - ERROR: {e}")
            
            # Check for specific error types
            error_str = str(e).lower()
            if "no auth credentials found" in error_str or "401" in error_str:
                print("   🔍 This is an authentication error.")
                print("   💡 Check: https://openrouter.ai/settings/privacy")
                print("   💡 You may need to enable 'providers that may train on inputs'")
            elif "404" in error_str or "no endpoints found" in error_str:
                print("   🔍 Model not available or no endpoints found.")
                print("   💡 This model might not be available in your region or settings.")
            elif "rate limit" in error_str:
                print("   🔍 Rate limit exceeded.")
                print("   💡 Wait a moment and try again.")
    
    print("\n❌ All models failed!")
    print("\n🔧 Troubleshooting steps:")
    print("1. Verify your API key at https://openrouter.ai/keys")
    print("2. Check privacy settings at https://openrouter.ai/settings/privacy")
    print("3. Ensure you have credits in your OpenRouter account")
    print("4. Try enabling 'providers that may train on inputs' if using free models")
    
    return False

if __name__ == "__main__":
    print("🚀 Testing OpenRouter connection...\n")
    success = test_openrouter_connection()
    
    if success:
        print("\n🎉 OpenRouter connection is working!")
    else:
        print("\n💥 OpenRouter connection failed!")
        print("\nFor more help, visit:")
        print("- OpenRouter docs: https://openrouter.ai/docs")
        print("- Privacy settings: https://openrouter.ai/settings/privacy") 