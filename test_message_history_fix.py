#!/usr/bin/env python3
"""Test script to verify the message_history.py fix for 'unhashable type: list' error"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ii_agent.llm.message_history import MessageHistory
from ii_agent.llm.base import ToolCall

def test_message_history_with_list_input():
    """Test that tool calls with list inputs don't cause 'unhashable type: list' error"""
    print("Testing message_history fix for 'unhashable type: list' error...")
    
    # Create a new message history
    history = MessageHistory()
    
    # Add a user prompt
    history.add_user_prompt('Test prompt')
    
    # Create a tool call with a list input (this was causing the error)
    tool_call_with_list = ToolCall(
        tool_call_id='test-123',
        tool_name='presentation',
        tool_input=['item1', {'key': 'value'}, 'item2']
    )
    
    # Add assistant turn with tool call
    history.add_assistant_turn([tool_call_with_list])
    
    try:
        # This should not throw 'unhashable type: list' error anymore
        pending_calls = history.get_pending_tool_calls()
        print(f'✅ SUCCESS: Got {len(pending_calls)} pending tool calls without error')
        print(f'Tool call: {pending_calls[0].tool_name} with input type: {type(pending_calls[0].tool_input)}')
        print(f'Input content: {pending_calls[0].tool_input}')
        return True
    except Exception as e:
        print(f'❌ ERROR: {e}')
        return False

def test_message_history_with_dict_input():
    """Test that tool calls with dict inputs still work"""
    print("\nTesting message_history with dict input...")
    
    history = MessageHistory()
    history.add_user_prompt('Test prompt')
    
    tool_call_with_dict = ToolCall(
        tool_call_id='test-456',
        tool_name='web_search',
        tool_input={'query': 'test search', 'max_results': 5}
    )
    
    history.add_assistant_turn([tool_call_with_dict])
    
    try:
        pending_calls = history.get_pending_tool_calls()
        print(f'✅ SUCCESS: Got {len(pending_calls)} pending tool calls with dict input')
        print(f'Tool call: {pending_calls[0].tool_name} with input: {pending_calls[0].tool_input}')
        return True
    except Exception as e:
        print(f'❌ ERROR: {e}')
        return False

def test_message_history_with_nested_structures():
    """Test complex nested data structures"""
    print("\nTesting message_history with complex nested structures...")
    
    history = MessageHistory()
    history.add_user_prompt('Test prompt')
    
    complex_input = {
        'slides': [
            {'title': 'Slide 1', 'content': ['bullet 1', 'bullet 2']},
            {'title': 'Slide 2', 'content': [{'text': 'nested', 'style': 'bold'}]}
        ],
        'metadata': {'created': '2024-01-01', 'tags': ['test', 'presentation']}
    }
    
    tool_call_complex = ToolCall(
        tool_call_id='test-789',
        tool_name='presentation',
        tool_input=complex_input
    )
    
    history.add_assistant_turn([tool_call_complex])
    
    try:
        pending_calls = history.get_pending_tool_calls()
        print(f'✅ SUCCESS: Got {len(pending_calls)} pending tool calls with complex input')
        print(f'Tool call: {pending_calls[0].tool_name}')
        return True
    except Exception as e:
        print(f'❌ ERROR: {e}')
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("MESSAGE HISTORY FIX VERIFICATION")
    print("=" * 60)
    
    success1 = test_message_history_with_list_input()
    success2 = test_message_history_with_dict_input()
    success3 = test_message_history_with_nested_structures()
    
    print("\n" + "=" * 60)
    if all([success1, success2, success3]):
        print("🎉 ALL TESTS PASSED! The message_history fix is working correctly.")
    else:
        print("❌ SOME TESTS FAILED! Check the errors above.")
    print("=" * 60) 