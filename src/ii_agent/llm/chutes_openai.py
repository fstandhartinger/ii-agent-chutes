import os
import random
import time
import logging
from typing import Any, Tuple, cast, Dict, List, Optional

from openai import OpenAI
from openai.types.chat import ChatCompletion, ChatCompletionMessage, ChatCompletionChunk
from openai.types.chat import ChatCompletionToolChoiceOptionParam as ToolChoice
from openai.types.chat import ChatCompletionToolParam as Tool

from ii_agent.llm.base import (
    LLMClient,
    AssistantContentBlock,
    ToolParam,
    TextPrompt,
    ToolCall,
    TextResult,
    LLMMessages,
    ToolFormattedResult,
    recursively_remove_invoke_tag,
    ImageBlock,
)
from ii_agent.utils.constants import DEFAULT_MODEL


class ChutesOpenAIClient(LLMClient):
    """Use Chutes models via OpenAI-compatible API."""

    def __init__(
        self,
        model_name="deepseek-ai/DeepSeek-V3-0324",
        max_retries=2,
        use_caching=True,
    ):
        """Initialize the Chutes OpenAI-compatible client."""
        api_key = os.getenv("CHUTES_API_KEY")
        if not api_key:
            raise ValueError("CHUTES_API_KEY environment variable must be set")
            
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://llm.chutes.ai/v1",
            max_retries=1,
            timeout=60 * 5,
        )
        self.model_name = model_name
        self.max_retries = max_retries
        self.use_caching = use_caching
        # Log provider info
        logging.info(f"=== Using CHUTES LLM provider with model: {model_name} ===")

    def generate(
        self,
        messages: LLMMessages,
        max_tokens: int,
        system_prompt: str | None = None,
        temperature: float = 0.0,
        tools: list[ToolParam] = [],
        tool_choice: dict[str, str] | None = None,
        thinking_tokens: int | None = None,
    ) -> Tuple[list[AssistantContentBlock], dict[str, Any]]:
        """Generate responses using Chutes OpenAI-compatible API.

        Args:
            messages: A list of messages.
            max_tokens: The maximum number of tokens to generate.
            system_prompt: A system prompt.
            temperature: The temperature.
            tools: A list of tools.
            tool_choice: A tool choice.
            thinking_tokens: Not supported in OpenAI API format.

        Returns:
            A generated response.
        """
        # Log each LLM call
        logging.info(f"[CHUTES LLM CALL] model={self.model_name}, max_tokens={max_tokens}, temperature={temperature}")
        
        # Convert messages to OpenAI format
        openai_messages = []
        
        # Add system prompt if provided
        if system_prompt:
            openai_messages.append({"role": "system", "content": system_prompt})
        
        # Process the conversation history
        for idx, message_list in enumerate(messages):
            role = "user" if idx % 2 == 0 else "assistant"
            message_content = []
            
            for message in message_list:
                if str(type(message)) == str(TextPrompt):
                    message = cast(TextPrompt, message)
                    if role == "user":
                        message_content.append({"type": "text", "text": message.text})
                elif str(type(message)) == str(TextResult):
                    message = cast(TextResult, message)
                    if role == "assistant":
                        message_content.append({"type": "text", "text": message.text})
                elif str(type(message)) == str(ToolCall):
                    # Convert ToolCall to OpenAI format
                    message = cast(ToolCall, message)
                    if role == "assistant":
                        tool_calls = [{
                            "id": message.tool_call_id,
                            "type": "function",
                            "function": {
                                "name": message.tool_name,
                                "arguments": str(message.tool_input),
                            },
                        }]
                        openai_messages.append({"role": "assistant", "tool_calls": tool_calls})
                        continue
                elif str(type(message)) == str(ToolFormattedResult):
                    # Convert ToolFormattedResult to OpenAI format
                    message = cast(ToolFormattedResult, message)
                    if role == "user":
                        openai_messages.append({
                            "role": "tool",
                            "tool_call_id": message.tool_call_id,
                            "content": str(message.tool_output),
                        })
                        continue
            
            # Add content if not empty
            if message_content:
                openai_messages.append({"role": role, "content": message_content})

        # Convert tools to OpenAI format
        openai_tools = []
        if tools:
            for tool in tools:
                openai_tools.append(
                    Tool(
                        type="function",
                        function={
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": tool.input_schema,
                        },
                    )
                )

        # Handle tool_choice
        openai_tool_choice = None
        if tool_choice:
            if tool_choice["type"] == "any":
                openai_tool_choice = ToolChoice(type="any")
            elif tool_choice["type"] == "auto":
                openai_tool_choice = ToolChoice(type="auto")
            elif tool_choice["type"] == "tool":
                openai_tool_choice = ToolChoice(
                    type="function", function={"name": tool_choice["name"]}
                )

        response = None
        
        # Retry logic
        for retry in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=openai_messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    tools=openai_tools if tools else None,
                    tool_choice=openai_tool_choice,
                )
                break
            except Exception as e:
                if retry == self.max_retries - 1:
                    print(f"Failed Chutes OpenAI request after {retry + 1} retries")
                    raise e
                else:
                    print(f"Retrying LLM request: {retry + 1}/{self.max_retries}")
                    # Sleep 12-18 seconds with jitter to avoid thundering herd
                    time.sleep(15 * random.uniform(0.8, 1.2))

        # Convert response back to internal format
        internal_messages = []
        if response and response.choices:
            choice = response.choices[0]
            message = choice.message
            
            # Log the raw response for debugging
            logging.info(f"[CHUTES DEBUG] Raw response message: {message}")
            logging.info(f"[CHUTES DEBUG] Message content: {message.content}")
            logging.info(f"[CHUTES DEBUG] Message tool_calls: {message.tool_calls}")
            
            if message.content:
                internal_messages.append(TextResult(text=message.content))
            
            if message.tool_calls:
                logging.info(f"[CHUTES DEBUG] Processing {len(message.tool_calls)} tool calls")
                for i, tool_call in enumerate(message.tool_calls):
                    logging.info(f"[CHUTES DEBUG] Tool call {i}: id={tool_call.id}, name={tool_call.function.name}")
                    logging.info(f"[CHUTES DEBUG] Tool call {i} arguments type: {type(tool_call.function.arguments)}")
                    logging.info(f"[CHUTES DEBUG] Tool call {i} arguments raw: {tool_call.function.arguments}")
                    
                    # Parse the tool arguments properly
                    try:
                        # Try to parse as JSON if it's a string
                        if isinstance(tool_call.function.arguments, str):
                            import json
                            tool_input = json.loads(tool_call.function.arguments)
                            logging.info(f"[CHUTES DEBUG] Tool call {i} parsed JSON: {tool_input}")
                        else:
                            tool_input = tool_call.function.arguments
                            logging.info(f"[CHUTES DEBUG] Tool call {i} using direct arguments: {tool_input}")
                    except (json.JSONDecodeError, TypeError) as e:
                        # If parsing fails, wrap the string in a dict
                        tool_input = {"arguments": str(tool_call.function.arguments)}
                        logging.error(f"[CHUTES DEBUG] Tool call {i} JSON parsing failed: {e}, wrapped in dict: {tool_input}")
                    
                    # Apply recursively_remove_invoke_tag and log the result
                    final_tool_input = recursively_remove_invoke_tag(tool_input)
                    logging.info(f"[CHUTES DEBUG] Tool call {i} final tool_input after recursively_remove_invoke_tag: {final_tool_input}")
                    logging.info(f"[CHUTES DEBUG] Tool call {i} final tool_input type: {type(final_tool_input)}")
                    
                    internal_messages.append(
                        ToolCall(
                            tool_call_id=tool_call.id,
                            tool_name=tool_call.function.name,
                            tool_input=final_tool_input,
                        )
                    )

        logging.info(f"[CHUTES DEBUG] Final internal_messages: {internal_messages}")
        
        message_metadata = {
            "raw_response": response,
            "input_tokens": response.usage.prompt_tokens if response else 0,
            "output_tokens": response.usage.completion_tokens if response else 0,
        }

        return internal_messages, message_metadata 