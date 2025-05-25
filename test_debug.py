import os
import sys
import logging
import traceback

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ii_agent.llm.chutes_openai import ChutesOpenAIClient
from ii_agent.llm.base import (
    TextPrompt,
    ToolParam,
)

# Configure logging to see debug output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_tools_debug():
    """Debug test for tools."""
    print("\n=== Debug Test: Tools ===")
    
    try:
        client = ChutesOpenAIClient(
            model_name="deepseek-ai/DeepSeek-V3-0324",
            max_retries=1,
            use_caching=True,
            test_mode=True
        )
        print("✅ Client created successfully")
        
        # Define a simple tool
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
        print("✅ Tools defined successfully")
        
        # Simple message
        messages = [
            [TextPrompt(text="What is 25 * 37?")],
        ]
        print("✅ Messages created successfully")
        
        response, metadata = client.generate(
            messages=messages,
            max_tokens=500,
            temperature=0.0,
            system_prompt="You are a helpful assistant. Use the calculate tool when asked to perform calculations.",
            tools=tools,
            tool_choice={"type": "auto"}
        )
        
        print(f"✅ Response: {response}")
        print("✅ Test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        print(f"Error type: {type(e)}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if not os.getenv("CHUTES_API_KEY"):
        print("❌ Error: CHUTES_API_KEY environment variable is not set!")
    else:
        test_tools_debug() 