import os
import sys

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ii_agent.llm.chutes_openai import ChutesOpenAIClient
from ii_agent.llm.base import TextPrompt, TextResult, ToolParam, ToolCall, ToolFormattedResult

def test_complex():
    """Test complex scenario."""
    print("=== Complex Scenario Test ===")
    
    try:
        client = ChutesOpenAIClient(
            model_name="deepseek-ai/DeepSeek-V3-0324",
            max_retries=1,
            test_mode=True
        )
        
        tools = [ToolParam(name="read_file", description="Read file", input_schema={"type": "object", "properties": {}})]
        
        messages = [
            [TextPrompt(text="Read file")],
            [TextResult(text="I'll read it"), ToolCall(tool_call_id="123", tool_name="read_file", tool_input={"file": "test.py"})],
            [ToolFormattedResult(tool_call_id="123", tool_name="read_file", tool_output="print('hello')")]
        ]
        
        response, _ = client.generate(
            messages=messages,
            max_tokens=50,
            temperature=0.0,
            tools=tools
        )
        
        print("✅ Complex scenario works")
        return True
        
    except Exception as e:
        print(f"❌ Complex scenario failed: {e}")
        return False

if __name__ == "__main__":
    if not os.getenv("CHUTES_API_KEY"):
        print("❌ No API key")
    else:
        result = test_complex()
        print(f"Result: {result}") 