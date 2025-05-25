import os
import sys
import logging
from openai import OpenAI

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ii_agent.llm.chutes_openai import ChutesOpenAIClient
from ii_agent.llm.base import TextPrompt

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_direct():
    """Test with direct OpenAI client."""
    print("\n=== Direct OpenAI Client Test ===")
    
    api_key = os.getenv("CHUTES_API_KEY")
    client = OpenAI(
        api_key=api_key,
        base_url="https://llm.chutes.ai/v1",
        max_retries=1,
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
        print(f"✅ Success! Response: {response.choices[0].message.content[:100]}...")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_chutes_client():
    """Test with ChutesOpenAIClient."""
    print("\n=== ChutesOpenAIClient Test ===")
    
    # Temporarily disable retry logic for faster testing
    client = ChutesOpenAIClient(
        model_name="deepseek-ai/DeepSeek-V3-0324",
        max_retries=1,
        use_caching=True,
        fallback_models=[]  # No fallback models for this test
    )
    
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
        print(f"✅ Success! Response: {response}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    if not os.getenv("CHUTES_API_KEY"):
        print("❌ Error: CHUTES_API_KEY environment variable is not set!")
    else:
        print(f"API Key is set: {os.getenv('CHUTES_API_KEY')[:10]}...")
        
        # Reduce logging for cleaner output
        logging.getLogger("openai").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        
        # Run both tests
        direct_success = test_direct()
        chutes_success = test_chutes_client()
        
        print("\n=== Summary ===")
        print(f"Direct OpenAI Client: {'✅ Passed' if direct_success else '❌ Failed'}")
        print(f"ChutesOpenAIClient: {'✅ Passed' if chutes_success else '❌ Failed'}") 