#!/usr/bin/env python3
"""Test script to diagnose malformed response issues with Chutes API."""

import os
import sys
import logging
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ii_agent.llm.chutes_openai import ChutesOpenAIClient
from ii_agent.llm.base import TextPrompt, TextResult, ToolParam

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_basic_completion():
    """Test basic text completion without tools."""
    print("\n=== Testing basic completion ===")
    
    client = ChutesOpenAIClient(
        model_name="Qwen/Qwen3-235B-A22B",
        use_native_tool_calling=False,
        no_fallback=True  # Disable fallback to isolate the issue
    )
    
    messages = [
        [TextPrompt(text="What is 2+2?")]
    ]
    
    try:
        response, metadata = client.generate(
            messages=messages,
            max_tokens=100,
            temperature=0.0
        )
        print(f"Success! Response: {response}")
        print(f"Metadata: {metadata}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

def test_with_native_tools():
    """Test with native tool calling enabled."""
    print("\n=== Testing with native tool calling ===")
    
    client = ChutesOpenAIClient(
        model_name="Qwen/Qwen3-235B-A22B",
        use_native_tool_calling=True,
        no_fallback=True
    )
    
    # Define a simple tool
    tools = [
        ToolParam(
            name="web_search",
            description="Search the web for information",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["query"]
            }
        )
    ]
    
    messages = [
        [TextPrompt(text="Search for information about fusion reactors")]
    ]
    
    try:
        response, metadata = client.generate(
            messages=messages,
            max_tokens=1000,
            temperature=0.0,
            tools=tools
        )
        print(f"Success! Response: {response}")
        print(f"Metadata: {metadata}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

def test_with_json_tools():
    """Test with JSON workaround for tools."""
    print("\n=== Testing with JSON workaround tools ===")
    
    client = ChutesOpenAIClient(
        model_name="Qwen/Qwen3-235B-A22B",
        use_native_tool_calling=False,  # Use JSON workaround
        no_fallback=True
    )
    
    # Define a simple tool
    tools = [
        ToolParam(
            name="web_search",
            description="Search the web for information",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["query"]
            }
        )
    ]
    
    messages = [
        [TextPrompt(text="Search for information about fusion reactors")]
    ]
    
    try:
        response, metadata = client.generate(
            messages=messages,
            max_tokens=1000,
            temperature=0.0,
            tools=tools
        )
        print(f"Success! Response: {response}")
        print(f"Metadata: {metadata}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

def test_different_model():
    """Test with a different model to see if the issue is model-specific."""
    print("\n=== Testing with different model (DeepSeek) ===")
    
    client = ChutesOpenAIClient(
        model_name="deepseek-ai/DeepSeek-V3-0324",
        use_native_tool_calling=False,
        no_fallback=True
    )
    
    messages = [
        [TextPrompt(text="What is 2+2?")]
    ]
    
    try:
        response, metadata = client.generate(
            messages=messages,
            max_tokens=100,
            temperature=0.0
        )
        print(f"Success! Response: {response}")
        print(f"Metadata: {metadata}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Check if API key is set
    if not os.getenv("CHUTES_API_KEY"):
        print("Error: CHUTES_API_KEY environment variable not set")
        sys.exit(1)
    
    # Run tests
    test_basic_completion()
    test_with_json_tools()
    test_with_native_tools()
    test_different_model() 