import os
import sys

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ii_agent.llm.chutes_openai import ChutesOpenAIClient
from ii_agent.llm.base import TextPrompt

def test_simple():
    """Test a simple conversation."""
    print("=== Simple Test ===")
    
    try:
        client = ChutesOpenAIClient(
            model_name="deepseek-ai/DeepSeek-V3-0324",
            max_retries=1,
            test_mode=True
        )
        
        messages = [[TextPrompt(text="Hello, how are you?")]]
        
        response, metadata = client.generate(
            messages=messages,
            max_tokens=100,
            temperature=0.0,
            system_prompt="You are a helpful assistant."
        )
        
        print(f"✅ Success: {response[0].text[:50]}...")
        return True
        
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

if __name__ == "__main__":
    if not os.getenv("CHUTES_API_KEY"):
        print("❌ No API key")
    else:
        result = test_simple()
        print(f"Result: {result}") 