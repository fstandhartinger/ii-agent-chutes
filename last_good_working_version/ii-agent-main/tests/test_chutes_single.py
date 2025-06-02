import os
import sys
import logging

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ii_agent.llm.chutes_openai import ChutesOpenAIClient
from ii_agent.llm.base import TextPrompt

# Configure logging to see debug output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_simple_conversation():
    """Test a simple conversation without tools."""
    print("\n=== Test: Simple Conversation ===")
    
    client = ChutesOpenAIClient(
        model_name="deepseek-ai/DeepSeek-V3-0324",
        max_retries=1,  # Reduce retries for faster testing
        use_caching=True,
        test_mode=True  # Use short backoff times for testing
    )
    
    # Simple conversation
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
        
        print(f"Response: {response}")
        print(f"Metadata: {metadata}")
        print("✅ Test passed!")
        return True
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Check if API key is set
    if not os.getenv("CHUTES_API_KEY"):
        print("❌ Error: CHUTES_API_KEY environment variable is not set!")
        print("Please set it with: export CHUTES_API_KEY=your_api_key")
    else:
        print(f"API Key is set: {os.getenv('CHUTES_API_KEY')[:10]}...")
        test_simple_conversation() 