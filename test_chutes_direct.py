import os
from openai import OpenAI
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_direct_openai():
    """Test direct OpenAI client with Chutes API."""
    api_key = os.getenv("CHUTES_API_KEY")
    if not api_key:
        print("CHUTES_API_KEY not set!")
        return
    
    client = OpenAI(
        api_key=api_key,
        base_url="https://llm.chutes.ai/v1",
        max_retries=1,
        timeout=60,
    )
    
    # Test 1: Simple text message
    print("\n=== Test 1: Simple text message ===")
    try:
        response = client.chat.completions.create(
            model="deepseek-ai/DeepSeek-V3-0324",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello, how are you?"}
            ],
            max_tokens=100,
            temperature=0.0
        )
        print(f"Success! Response: {response.choices[0].message.content}")
    except Exception as e:
        print(f"Error: {e}")
        print(f"Error type: {type(e)}")
        if hasattr(e, 'response'):
            print(f"Response status: {e.response.status_code if hasattr(e.response, 'status_code') else 'N/A'}")
            print(f"Response text: {e.response.text if hasattr(e.response, 'text') else 'N/A'}")
    
    # Test 2: Message with content array (like in the failing test)
    print("\n=== Test 2: Message with content array ===")
    try:
        response = client.chat.completions.create(
            model="deepseek-ai/DeepSeek-V3-0324",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": [{"type": "text", "text": "Hello, how are you?"}]}
            ],
            max_tokens=100,
            temperature=0.0
        )
        print(f"Success! Response: {response.choices[0].message.content}")
    except Exception as e:
        print(f"Error: {e}")
        print(f"Error type: {type(e)}")
        if hasattr(e, 'response'):
            print(f"Response status: {e.response.status_code if hasattr(e.response, 'status_code') else 'N/A'}")
            print(f"Response text: {e.response.text if hasattr(e.response, 'text') else 'N/A'}")
    
    # Test 3: Try a different model
    print("\n=== Test 3: Different model (Llama) ===")
    try:
        response = client.chat.completions.create(
            model="chutesai/Llama-4-Maverick-17B-128E-Instruct-FP8",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello, how are you?"}
            ],
            max_tokens=100,
            temperature=0.0
        )
        print(f"Success! Response: {response.choices[0].message.content}")
    except Exception as e:
        print(f"Error: {e}")
        print(f"Error type: {type(e)}")

if __name__ == "__main__":
    test_direct_openai() 