import os
import sys

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ii_agent.llm.chutes_openai import ChutesOpenAIClient
from ii_agent.llm.base import TextPrompt

def test_no_tools():
    """Test the same message but without tools."""
    print("=== No Tools Test ===")
    
    try:
        client = ChutesOpenAIClient(
            model_name="deepseek-ai/DeepSeek-V3-0324",
            max_retries=1,
            test_mode=True
        )
        
        messages = [[TextPrompt(text="What is 25 * 37?")]]
        
        response, metadata = client.generate(
            messages=messages,
            max_tokens=200,
            temperature=0.0,
            system_prompt="You are a helpful assistant. Calculate mathematical expressions when asked."
        )
        
        print(f"✅ Success: {response[0].text[:100]}...")
        return True
        
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

if __name__ == "__main__":
    if not os.getenv("CHUTES_API_KEY"):
        print("❌ No API key")
    else:
        result = test_no_tools()
        print(f"Result: {result}") 