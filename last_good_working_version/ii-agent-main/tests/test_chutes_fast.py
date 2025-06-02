import os
import sys
import logging
import json
from typing import List

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ii_agent.llm.chutes_openai import ChutesOpenAIClient
from ii_agent.llm.base import (
    TextPrompt,
    TextResult,
    ToolCall,
    ToolFormattedResult,
    ToolParam,
)

# Configure logging to see debug output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_simple_conversation():
    """Test a simple conversation without tools."""
    print("\n=== Test 1: Simple Conversation ===")
    
    client = ChutesOpenAIClient(
        model_name="deepseek-ai/DeepSeek-V3-0324",
        max_retries=1,  # Reduce retries for faster testing
        use_caching=True,
        test_mode=True,  # Use short backoff times for testing
        no_fallback=True  # Disable fallbacks for faster testing
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
        print("✅ Test 1 passed!")
        return True
    except Exception as e:
        print(f"❌ Test 1 failed with error: {e}")
        return False

def test_conversation_with_tools():
    """Test a conversation with tool usage."""
    print("\n=== Test 2: Conversation with Tools ===")
    
    client = ChutesOpenAIClient(
        model_name="deepseek-ai/DeepSeek-V3-0324",
        max_retries=1,  # Reduce retries for faster testing
        use_caching=True,
        test_mode=True,  # Use short backoff times for testing
        no_fallback=True  # Disable fallbacks for faster testing
    )
    
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
    
    # Conversation that should trigger tool use
    messages = [
        [TextPrompt(text="What is 25 * 37?")],
    ]
    
    try:
        response, metadata = client.generate(
            messages=messages,
            max_tokens=500,
            temperature=0.0,
            system_prompt="You are a helpful assistant. Use the calculate tool when asked to perform calculations.",
            tools=tools,
            tool_choice={"type": "auto"}
        )
        
        print(f"Response: {response}")
        print(f"Metadata: {metadata}")
        print("✅ Test 2 passed!")
        return True
    except Exception as e:
        print(f"❌ Test 2 failed with error: {e}")
        return False

def test_multi_turn_conversation():
    """Test a multi-turn conversation similar to agent usage."""
    print("\n=== Test 3: Multi-turn Conversation ===")
    
    client = ChutesOpenAIClient(
        model_name="deepseek-ai/DeepSeek-V3-0324",
        max_retries=1,  # Reduce retries for faster testing
        use_caching=True,
        test_mode=True,  # Use short backoff times for testing
        no_fallback=True  # Disable fallbacks for faster testing
    )
    
    # Multi-turn conversation
    messages = [
        [TextPrompt(text="I need help creating a Python script to process CSV files.")],
        [TextResult(text="I'd be happy to help you create a Python script to process CSV files. To provide you with the most relevant solution, could you tell me more about what specific processing you need to do? For example:\n\n- Do you need to read, write, or modify CSV files?\n- What kind of data transformations or analysis do you need?\n- Are there specific columns or data types you're working with?")],
        [TextPrompt(text="I need to read a CSV file, filter rows where the 'status' column equals 'active', and save the filtered data to a new CSV file.")],
    ]
    
    try:
        response, metadata = client.generate(
            messages=messages,
            max_tokens=1000,
            temperature=0.0,
            system_prompt="You are a helpful Python programming assistant."
        )
        
        print(f"Response: {response}")
        print(f"Metadata: {metadata}")
        print("✅ Test 3 passed!")
        return True
    except Exception as e:
        print(f"❌ Test 3 failed with error: {e}")
        return False

def test_complex_agent_scenario():
    """Test a complex scenario with tools and multi-turn conversation."""
    print("\n=== Test 4: Complex Agent Scenario ===")
    
    client = ChutesOpenAIClient(
        model_name="deepseek-ai/DeepSeek-V3-0324",
        max_retries=1,  # Reduce retries for faster testing
        use_caching=True,
        test_mode=True,  # Use short backoff times for testing
        no_fallback=True  # Disable fallbacks for faster testing
    )
    
    # Define multiple tools like in the agent
    tools = [
        ToolParam(
            name="read_file",
            description="Read the contents of a file",
            input_schema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to the file"},
                    "start_line": {"type": "integer", "description": "Starting line number"},
                    "end_line": {"type": "integer", "description": "Ending line number"}
                },
                "required": ["file_path"]
            }
        ),
        ToolParam(
            name="write_file",
            description="Write content to a file",
            input_schema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to the file"},
                    "content": {"type": "string", "description": "Content to write"}
                },
                "required": ["file_path", "content"]
            }
        )
    ]
    
    # Complex conversation with tool calls
    messages = [
        [TextPrompt(text="Please read the file 'example.py' and tell me what it contains.")],
        [
            TextResult(text="I'll read the file 'example.py' for you."),
            ToolCall(
                tool_call_id="call_123",
                tool_name="read_file",
                tool_input={"file_path": "example.py"}
            )
        ],
        [ToolFormattedResult(
            tool_call_id="call_123",
            tool_name="read_file",
            tool_output="def hello_world():\n    print('Hello, World!')\n\nif __name__ == '__main__':\n    hello_world()"
        )],
    ]
    
    try:
        response, metadata = client.generate(
            messages=messages,
            max_tokens=500,
            temperature=0.0,
            system_prompt="You are a helpful coding assistant with access to file system tools.",
            tools=tools
        )
        
        print(f"Response: {response}")
        print(f"Metadata: {metadata}")
        print("✅ Test 4 passed!")
        return True
    except Exception as e:
        print(f"❌ Test 4 failed with error: {e}")
        return False

def main():
    """Run all tests."""
    # Check if API key is set
    if not os.getenv("CHUTES_API_KEY"):
        print("❌ Error: CHUTES_API_KEY environment variable is not set!")
        print("Please set it with: export CHUTES_API_KEY=your_api_key")
        return
    
    print("Starting Chutes OpenAI Client Tests (Fast Mode)...")
    print(f"API Key is set: {os.getenv('CHUTES_API_KEY')[:10]}...")
    
    # Run tests
    results = []
    results.append(test_simple_conversation())
    results.append(test_conversation_with_tools())
    results.append(test_multi_turn_conversation())
    results.append(test_complex_agent_scenario())
    
    # Summary
    print("\n=== Test Summary ===")
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed!")

if __name__ == "__main__":
    main() 