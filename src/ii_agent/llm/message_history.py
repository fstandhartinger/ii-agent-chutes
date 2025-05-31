import json
from typing import Optional, cast, Any
from ii_agent.llm.base import (
    AssistantContentBlock,
    GeneralContentBlock,
    LLMMessages,
    TextPrompt,
    TextResult,
    ToolCall,
    ToolCallParameters,
    ToolFormattedResult,
    ImageBlock,
)


class MessageHistory:
    """Stores the sequence of messages in a dialog."""

    def _make_hashable(self, item: Any) -> Any:
        """Converts an item into a hashable type."""
        if isinstance(item, list):
            return tuple(self._make_hashable(x) for x in item)
        if isinstance(item, dict):
            return tuple(
                sorted((k, self._make_hashable(v)) for k, v in item.items())
            )
        # Check for basic hashable types explicitly.
        # This includes str, int, float, bool, NoneType, and tuple (if elements are hashable).
        # collections.abc.Hashable is a more general check but might be too broad
        # if we want to strictly control the types we consider "natively hashable"
        # for this specific conversion.
        if isinstance(item, (str, int, float, bool, type(None))):
            return item
        if isinstance(item, tuple):
            # Ensure all elements in the tuple are hashable
            return tuple(self._make_hashable(x) for x in item)

        # If the item is not one of the above, and not already hashable by default,
        # it might be an unhandled complex type.
        # For now, we'll raise a TypeError, but one could also convert to str(item)
        # as a fallback, though that might lose semantic meaning for equality.
        try:
            hash(item)
            return item
        except TypeError:
            # Fallback for unhandled types: convert to string.
            # This is a pragmatic choice for now, but might not be ideal for all cases.
            # Consider if a more specific error or handling is needed based on expected data.
            # print(f"Warning: Converting unhashable type {type(item)} to string for hashing.")
            return str(item)

    def __init__(self):
        self._message_lists: list[list[GeneralContentBlock]] = []

    def add_user_prompt(
        self, prompt: str, image_blocks: list[dict[str, Any]] | None = None
    ):
        """Adds a user prompt."""
        user_turn = []
        if image_blocks is not None:
            for img_block in image_blocks:
                user_turn.append(ImageBlock(type="image", source=img_block["source"]))

        user_turn.append(TextPrompt(prompt))
        self.add_user_turn(user_turn)

    def add_user_turn(self, messages: list[GeneralContentBlock]):
        """Adds a user turn (prompts and/or tool results)."""
        if not self.is_next_turn_user():
            raise ValueError("Cannot add user turn, expected assistant turn next.")
        # Ensure all messages are valid user-side types
        for msg in messages:
            if not isinstance(msg, (TextPrompt, ToolFormattedResult, ImageBlock)):
                raise TypeError(f"Invalid message type for user turn: {type(msg)}")
        self._message_lists.append(messages)

    def add_assistant_turn(self, messages: list[AssistantContentBlock]):
        """Adds an assistant turn (text response and/or tool calls)."""
        if not self.is_next_turn_assistant():
            raise ValueError("Cannot add assistant turn, expected user turn next.")
        self._message_lists.append(cast(list[GeneralContentBlock], messages))

    def get_messages_for_llm(self) -> LLMMessages:  # TODO: change name to get_messages
        """Returns messages formatted for the LLM client."""
        # Return a copy to prevent modification
        return list(self._message_lists)

    def get_pending_tool_calls(self) -> list[ToolCallParameters]:
        """Returns tool calls from the last assistant turn, if any."""
        if self.is_next_turn_assistant() or not self._message_lists:
            return []  # No pending calls if it's user turn or history is empty

        last_turn = self._message_lists[-1]
        tool_calls = []
        seen_calls = set()  # Track unique tool calls
        
        for message in last_turn:
            if isinstance(message, ToolCall):
                # Create a unique key based on tool name and arguments
                hashable_tool_name = self._make_hashable(message.tool_name)
                hashable_tool_input = self._make_hashable(message.tool_input)
                tool_key = (hashable_tool_name, hashable_tool_input)
                
                # Only add if we haven't seen this exact call before
                if tool_key not in seen_calls:
                    seen_calls.add(tool_key)
                    tool_calls.append(
                        ToolCallParameters(
                            tool_call_id=message.tool_call_id,
                            tool_name=message.tool_name, # Keep original for ToolCallParameters
                            tool_input=message.tool_input, # Keep original for ToolCallParameters
                        )
                    )
        return tool_calls

    def add_tool_call_result(self, parameters: ToolCallParameters, result: str):
        """Add the result of a tool call to the dialog."""
        self.add_tool_call_results([parameters], [result])

    def add_tool_call_results(
        self, parameters: list[ToolCallParameters], results: list[str]
    ):
        """Add the result of a tool call to the dialog."""
        assert self.is_next_turn_user(), (
            "Cannot add tool call results, expected user turn next."
        )
        self._message_lists.append(
            [
                ToolFormattedResult(
                    tool_call_id=params.tool_call_id,
                    tool_name=params.tool_name,
                    tool_output=result,
                )
                for params, result in zip(parameters, results)
            ]
        )

    def get_last_assistant_text_response(self) -> Optional[str]:  # TODO:: remove get
        """Returns the text part of the last assistant response, if any."""
        if self.is_next_turn_assistant() or not self._message_lists:
            return None  # No assistant response yet or not the last turn

        last_turn = self._message_lists[-1]
        for message in reversed(last_turn):  # Check from end
            if isinstance(message, TextResult):
                return message.text
        return None

    def clear(self):
        """Removes all messages."""
        self._message_lists = []

    def is_next_turn_user(self) -> bool:
        """Checks if the next turn should be from the user."""
        # User turn is 0, 2, 4... (even indices in a 0-indexed list)
        return len(self._message_lists) % 2 == 0

    def is_next_turn_assistant(self) -> bool:
        """Checks if the next turn should be from the assistant."""
        return not self.is_next_turn_user()

    def __len__(self) -> int:
        """Returns the number of turns."""
        return len(self._message_lists)

    def __str__(self) -> str:
        """JSON representation of the history."""
        try:
            json_serializable = [
                [message.to_dict() for message in message_list]
                for message_list in self._message_lists
            ]
            return json.dumps(json_serializable, indent=2)
        except Exception as e:
            return f"[Error serializing history: {e}]"

    def get_summary(self, max_str_len: int = 100) -> str:
        """Returns a summarized JSON representation."""

        def truncate_strings(obj):
            if isinstance(obj, str):
                return obj[:max_str_len] + "..." if len(obj) > max_str_len else obj
            elif isinstance(obj, dict):
                return {k: truncate_strings(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [truncate_strings(item) for item in obj]
            return obj

        try:
            json_serializable = truncate_strings(
                [
                    [message.to_dict() for message in message_list]
                    for message_list in self._message_lists
                ]
            )
            return json.dumps(json_serializable, indent=2)
        except Exception as e:
            return f"[Error serializing summary: {e}]"

    def set_message_list(self, message_list: list[list[GeneralContentBlock]]):
        """Sets the message list."""
        self._message_lists = message_list
