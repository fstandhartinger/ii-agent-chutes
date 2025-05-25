#!/usr/bin/env python3
"""Test script to verify improvements to Chutes integration."""

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
from ii_agent.agents.anthropic_fc import AnthropicFC
from ii_agent.tools.base import LLMTool, ToolImplOutput
from ii_agent.llm.context_manager.base import ContextManager
from ii_agent.llm.context_manager.truncation import TruncationContextManager
from ii_agent.utils.workspace_manager import WorkspaceManager
from ii_agent.core.event import EventType, RealtimeEvent

# Configure logging to see debug output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create a mock tool for testing
class MockWebSearchTool(LLMTool):
    name = "web_search"
    description = "Search the web for information"
    input_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query"
            }
        },
        "required": ["query"]
    }
    
    def run_impl(self, tool_input: dict, message_history=None) -> ToolImplOutput:
        query = tool_input.get("query", "")
        return ToolImplOutput(
            tool_output=f"Search results for '{query}': [Mock results would appear here]",
            tool_result_message=f"Searched for: {query}"
        )

class MockSequentialThinkingTool(LLMTool):
    name = "sequential_thinking"
    description = "Think through a problem step by step"
    input_schema = {
        "type": "object",
        "properties": {
            "thought": {"type": "string"},
            "nextThoughtNeeded": {"type": "boolean"},
            "thoughtNumber": {"type": "integer"},
            "totalThoughts": {"type": "integer"}
        },
        "required": ["thought", "nextThoughtNeeded", "thoughtNumber", "totalThoughts"]
    }
    
    def run_impl(self, tool_input: dict, message_history=None) -> ToolImplOutput:
        thought = tool_input.get("thought", "")
        thought_num = tool_input.get("thoughtNumber", 1)
        return ToolImplOutput(
            tool_output=f"Thought {thought_num}: {thought}",
            tool_result_message=f"Processed thought {thought_num}"
        )

async def test_chutes_improvements():
    """Test the improvements to Chutes integration."""
    
    print("\n=== Testing Chutes Improvements ===\n")
    
    # Initialize the Chutes client
    client = ChutesOpenAIClient(
        model_name="deepseek-ai/DeepSeek-V3-0324",
        max_retries=3,
        use_caching=False,
        no_fallback=True  # Disable fallback for testing
    )
    
    # Test 1: Test tool call extraction with proper JSON
    print("Test 1: Proper JSON tool call")
    messages = [
        [TextPrompt(text="Search for information about Python programming")]
    ]
    
    tools = [
        ToolParam(
            name="web_search",
            description="Search the web for information",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query"}
                },
                "required": ["query"]
            }
        )
    ]
    
    # Simulate a response with proper JSON
    test_response = """I'll search for information about Python programming.

```json
{
  "tool_call": {
    "id": "call_123",
    "name": "web_search",
    "arguments": {"query": "Python programming language features"}
  }
}
```"""
    
    print(f"Simulated response:\n{test_response}\n")
    
    # Test 2: Test incomplete JSON handling
    print("\nTest 2: Incomplete JSON tool call")
    incomplete_response = """Let me search for that information.

```json
{
  "tool_call": {
    "id": "call_456",
    "name": "web_search",
    "arguments": {"query": "Python programming"}"""
    
    print(f"Simulated incomplete response:\n{incomplete_response}\n")
    
    # Test 3: Test agent behavior with no tools called
    print("\nTest 3: Agent behavior when no tools are called")
    
    # Create a mock workspace manager
    workspace_manager = WorkspaceManager(workspace_path="./test_workspace")
    
    # Create a message queue
    message_queue = asyncio.Queue()
    
    # Create a logger
    logger = logging.getLogger("test_agent")
    
    # Create context manager
    context_manager = TruncationContextManager(
        client=client,
        max_tokens=100000,
        truncate_from_middle=True
    )
    
    # Create the agent
    agent = AnthropicFC(
        system_prompt="You are a helpful assistant that can search the web.",
        client=client,
        tools=[MockWebSearchTool(), MockSequentialThinkingTool()],
        workspace_manager=workspace_manager,
        message_queue=message_queue,
        logger_for_agent_logs=logger,
        context_manager=context_manager,
        max_output_tokens_per_turn=1000,
        max_turns=5
    )
    
    # Start message processing
    message_task = agent.start_message_processing()
    
    try:
        # Test with a response that doesn't include tool calls
        print("Testing agent with instruction that should trigger tool use...")
        result = agent.run_agent(
            instruction="Research Python programming language and its main features",
            files=None,
            resume=False
        )
        
        print(f"\nAgent result: {result}")
        
        # Process any remaining messages
        while not message_queue.empty():
            try:
                event = await asyncio.wait_for(message_queue.get(), timeout=0.1)
                print(f"Event: {event.type} - {event.content}")
            except asyncio.TimeoutError:
                break
                
    finally:
        # Cancel the message processing task
        message_task.cancel()
        try:
            await message_task
        except asyncio.CancelledError:
            pass
    
    print("\n=== Tests completed ===")

if __name__ == "__main__":
    asyncio.run(test_chutes_improvements()) 