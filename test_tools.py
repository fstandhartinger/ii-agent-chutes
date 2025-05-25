import os
import sys

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ii_agent.llm.chutes_openai import ChutesOpenAIClient
from ii_agent.llm.base import TextPrompt, ToolParam

def test_tools():
    """Test tools functionality."""
    print("=== Tools Test ===")
    
    try:
        client = ChutesOpenAIClient(
            model_name="deepseek-ai/DeepSeek-V3-0324",
            max_retries=1,
            test_mode=True
        )
        
        tools = [
            ToolParam(
                name="calculate",
                description="Perform mathematical calculations",
                input_schema={
                    "type": "object",
                    "properties": {
                        "expression": {
                            "type": "string",
                            "description": "The mathematical expression to evaluate"
                        }
                    },
                    "required": ["expression"]
                }
            )
        ]
        
        messages = [[TextPrompt(text="What is 25 * 37?")]]
        
        response, metadata = client.generate(
            messages=messages,
            max_tokens=200,
            temperature=0.0,
            system_prompt="You are a helpful assistant. Use the calculate tool when asked to perform calculations.",
            tools=tools,
            tool_choice={"type": "auto"}
        )
        
        print(f"✅ Success: {len(response)} response(s)")
        for i, r in enumerate(response):
            print(f"  Response {i}: {type(r).__name__}")
        return True
        
    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if not os.getenv("CHUTES_API_KEY"):
        print("❌ No API key")
    else:
        result = test_tools()
        print(f"Result: {result}") 