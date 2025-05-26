#!/usr/bin/env python3
"""Test script to verify native tool calling functionality with Chutes LLMs."""

import os
import sys
import logging
import asyncio
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

def test_json_workaround_mode():
    """Test the JSON workaround mode (default)."""
    print("\n=== Testing JSON Workaround Mode (Default) ===\n")
    
    if not os.getenv("CHUTES_API_KEY"):
        print("❌ CHUTES_API_KEY not set, skipping test")
        return False
    
    client = ChutesOpenAIClient(
        model_name="deepseek-ai/DeepSeek-V3-0324",
        max_retries=1,
        use_caching=False,
        test_mode=True,
        no_fallback=True,
        use_native_tool_calling=False  # JSON workaround mode
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
        [TextPrompt(text="What is 42 * 17?")],
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
        
        # Check if we got a tool call
        has_tool_call = any(isinstance(msg, ToolCall) for msg in response)
        if has_tool_call:
            print("✅ JSON workaround mode test passed - tool call detected!")
            return True
        else:
            print("❌ JSON workaround mode test failed - no tool call detected")
            return False
            
    except Exception as e:
        print(f"❌ JSON workaround mode test failed with error: {e}")
        return False

def test_native_tool_calling_mode():
    """Test the native tool calling mode."""
    print("\n=== Testing Native Tool Calling Mode ===\n")
    
    if not os.getenv("CHUTES_API_KEY"):
        print("❌ CHUTES_API_KEY not set, skipping test")
        return False
    
    client = ChutesOpenAIClient(
        model_name="deepseek-ai/DeepSeek-V3-0324",
        max_retries=1,
        use_caching=False,
        test_mode=True,
        no_fallback=True,
        use_native_tool_calling=True  # Native tool calling mode
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
        [TextPrompt(text="What is 42 * 17?")],
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
        
        # Check if we got a tool call
        has_tool_call = any(isinstance(msg, ToolCall) for msg in response)
        if has_tool_call:
            print("✅ Native tool calling mode test passed - tool call detected!")
            return True
        else:
            print("❌ Native tool calling mode test failed - no tool call detected")
            return False
            
    except Exception as e:
        print(f"❌ Native tool calling mode test failed with error: {e}")
        return False

def test_conversation_with_tool_results():
    """Test a multi-turn conversation with tool results in native mode."""
    print("\n=== Testing Multi-turn Conversation with Tool Results ===\n")
    
    if not os.getenv("CHUTES_API_KEY"):
        print("❌ CHUTES_API_KEY not set, skipping test")
        return False
    
    client = ChutesOpenAIClient(
        model_name="deepseek-ai/DeepSeek-V3-0324",
        max_retries=1,
        use_caching=False,
        test_mode=True,
        no_fallback=True,
        use_native_tool_calling=True  # Native tool calling mode
    )
    
    # Define a simple tool
    tools = [
        ToolParam(
            name="get_weather",
            description="Get weather information for a location",
            input_schema={
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The location to get weather for"
                    }
                },
                "required": ["location"]
            }
        )
    ]
    
    # Multi-turn conversation with tool call and result
    messages = [
        [TextPrompt(text="What's the weather like in Berlin?")],
        [
            ToolCall(
                tool_call_id="call_123",
                tool_name="get_weather",
                tool_input={"location": "Berlin"}
            )
        ],
        [
            ToolFormattedResult(
                tool_call_id="call_123",
                tool_output="The weather in Berlin is sunny with 22°C temperature."
            )
        ]
    ]
    
    try:
        response, metadata = client.generate(
            messages=messages,
            max_tokens=500,
            temperature=0.0,
            system_prompt="You are a helpful weather assistant.",
            tools=tools
        )
        
        print(f"Response: {response}")
        print(f"Metadata: {metadata}")
        
        # Check if we got a text response
        has_text_response = any(isinstance(msg, TextResult) for msg in response)
        if has_text_response:
            print("✅ Multi-turn conversation test passed - text response received!")
            return True
        else:
            print("❌ Multi-turn conversation test failed - no text response")
            return False
            
    except Exception as e:
        print(f"❌ Multi-turn conversation test failed with error: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Testing Native Tool Calling Implementation for Chutes LLMs")
    print("=" * 60)
    
    results = []
    
    # Test JSON workaround mode
    results.append(test_json_workaround_mode())
    
    # Test native tool calling mode
    results.append(test_native_tool_calling_mode())
    
    # Test multi-turn conversation
    results.append(test_conversation_with_tool_results())
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Results Summary:")
    print(f"✅ Passed: {sum(results)}/{len(results)}")
    print(f"❌ Failed: {len(results) - sum(results)}/{len(results)}")
    
    if all(results):
        print("\n🎉 All tests passed! Native tool calling implementation is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Please check the implementation.")
    
    return all(results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 