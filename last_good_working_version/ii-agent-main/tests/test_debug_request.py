import os
import sys
import json
import logging
from openai import OpenAI

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ii_agent.llm.chutes_openai import ChutesOpenAIClient
from ii_agent.llm.base import TextPrompt

# Configure logging to capture HTTP details
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Enable debug logging for OpenAI
logging.getLogger("openai").setLevel(logging.DEBUG)

def test_direct_with_debug():
    """Test with direct OpenAI client and capture request."""
    print("\n=== Direct OpenAI Client Request ===")
    
    api_key = os.getenv("CHUTES_API_KEY")
    client = OpenAI(
        api_key=api_key,
        base_url="https://llm.chutes.ai/v1",
        max_retries=0,  # No retries
        timeout=60,
    )
    
    try:
        response = client.chat.completions.create(
            model="deepseek-ai/DeepSeek-V3-0324",
            messages=[
                {"role": "system", "content": "You are a helpful coding assistant."},
                {"role": "user", "content": "Hello, can you help me write a Python function to calculate fibonacci numbers?"}
            ],
            max_tokens=500,
            temperature=0.0
        )
        print(f"✅ Success!")
    except Exception as e:
        print(f"❌ Error: {e}")

def test_chutes_with_debug():
    """Test with ChutesOpenAIClient and capture request."""
    print("\n=== ChutesOpenAIClient Request ===")
    
    client = ChutesOpenAIClient(
        model_name="deepseek-ai/DeepSeek-V3-0324",
        max_retries=0,  # No retries
        use_caching=True,
        fallback_models=[]
    )
    
    # Override the client's max_retries
    client.client.max_retries = 0
    
    messages = [
        [TextPrompt(text="Hello, can you help me write a Python function to calculate fibonacci numbers?")],
    ]
    
    try:
        response, metadata = client.generate(
            messages=messages,
            max_tokens=500,
            temperature=0.0,
            system_prompt="You are a helpful coding assistant."
        )
        print(f"✅ Success!")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    if not os.getenv("CHUTES_API_KEY"):
        print("❌ Error: CHUTES_API_KEY environment variable is not set!")
    else:
        print(f"API Key is set: {os.getenv('CHUTES_API_KEY')[:10]}...")
        
        # First test direct client
        test_direct_with_debug()
        
        print("\n" + "="*50 + "\n")
        
        # Then test ChutesOpenAIClient
        test_chutes_with_debug() 