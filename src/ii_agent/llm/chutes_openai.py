import os
import random
import time
import logging
from typing import Any, Tuple, cast, Dict, List, Optional

from openai import OpenAI
from openai import (
    APIConnectionError as OpenAI_APIConnectionError,
    InternalServerError as OpenAI_InternalServerError,
    RateLimitError as OpenAI_RateLimitError,
    BadRequestError as OpenAI_BadRequestError,
)
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
        max_retries=3,
        use_caching=True,
        fallback_models=None,
        test_mode=False,
        no_fallback=False,
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
        self.test_mode = test_mode
        self.no_fallback = no_fallback
        
        # Default fallback models for different scenarios
        if fallback_models is None:
            self.fallback_models = [
                "chutesai/Llama-4-Maverick-17B-128E-Instruct-FP8",
                "Qwen/Qwen2.5-VL-32B-Instruct",
                "deepseek-ai/DeepSeek-R1",
            ]
        else:
            self.fallback_models = fallback_models
            
        # Log provider info
        logging.info(f"=== Using CHUTES LLM provider with model: {model_name} ===")
        if self.no_fallback:
            logging.info(f"=== Fallback models DISABLED (no_fallback=True) ===")
        else:
            logging.info(f"=== Fallback models: {self.fallback_models} ===")
        if test_mode:
            logging.info("=== TEST MODE: Using reduced backoff times ===")

    def _is_target_exhausted_error(self, error: Exception) -> bool:
        """Check if the error is related to exhausted targets."""
        error_str = str(error).lower()
        return (
            "exhausted all available targets" in error_str or
            "no available targets" in error_str or
            "all targets exhausted" in error_str
        )

    def _get_backoff_time(self, retry: int, base_delay: float = 30.0) -> float:
        """Calculate exponential backoff time with jitter."""
        if self.test_mode:
            # In test mode, use very short delays (max 1 second)
            return min(1.0, 0.1 * (2 ** retry))
        
        # Exponential backoff: base_delay * 2^retry with jitter
        delay = base_delay * (2 ** retry)
        # Add jitter to avoid thundering herd
        jitter = random.uniform(0.8, 1.2)
        return delay * jitter

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
            
            for message in message_list:
                if str(type(message)) == str(TextPrompt):
                    message = cast(TextPrompt, message)
                    if role == "user":
                        # Use simple string format for Chutes compatibility
                        openai_messages.append({"role": role, "content": message.text})
                elif str(type(message)) == str(TextResult):
                    message = cast(TextResult, message)
                    if role == "assistant":
                        # Use simple string format for Chutes compatibility
                        openai_messages.append({"role": role, "content": message.text})
                elif str(type(message)) == str(ImageBlock):
                    # Handle image blocks - for now, skip them as Chutes may not support vision
                    message = cast(ImageBlock, message)
                    logging.warning("[CHUTES] Image blocks are not supported, skipping...")
                    continue
                elif str(type(message)) == str(ToolCall):
                    # Chutes doesn't support tool calls - skip them with warning
                    message = cast(ToolCall, message)
                    logging.warning(f"[CHUTES] Skipping ToolCall message (tool_name: {message.tool_name}) - not supported by Chutes API")
                    continue
                elif str(type(message)) == str(ToolFormattedResult):
                    # Chutes doesn't support tool results - convert to regular text message
                    message = cast(ToolFormattedResult, message)
                    logging.warning(f"[CHUTES] Converting ToolFormattedResult to text message - Chutes doesn't support tool results")
                    if role == "user":
                        # Convert tool result to a regular user message
                        openai_messages.append({
                            "role": "user",
                            "content": f"Tool result: {str(message.tool_output)}",
                        })

        # Build the request payload - only include what's needed
        payload = {
            "model": self.model_name,
            "messages": openai_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        
        # JSON Workaround for tools when they are provided
        if tools:
            logging.info(f"[CHUTES] Implementing JSON workaround for {len(tools)} tools")
            # Add a system message that instructs the model to output tool calls as JSON
            tool_instructions = "\n\nWhen you need to use a tool, output a JSON object in the following format:\n```json\n{\n  \"tool_call\": {\n    \"id\": \"call_<unique_id>\",\n    \"name\": \"<tool_name>\",\n    \"arguments\": {<tool_arguments>}\n  }\n}\n```\n\nAvailable tools:\n"
            for tool in tools:
                tool_instructions += f"- {tool.name}: {tool.description}\n"
                tool_instructions += f"  Parameters: {tool.input_schema}\n"
            
            # Append to system prompt or create new one
            if openai_messages and openai_messages[0]["role"] == "system":
                openai_messages[0]["content"] += tool_instructions
            else:
                openai_messages.insert(0, {"role": "system", "content": tool_instructions})
            
            logging.info(f"[CHUTES] Added tool instructions to system prompt")

        response = None
        
        # Determine models to try based on no_fallback flag
        if self.no_fallback:
            models_to_try = [self.model_name]
            logging.info(f"[CHUTES] Using only primary model (no_fallback=True): {self.model_name}")
        else:
            models_to_try = [self.model_name] + self.fallback_models
        
        # Log the messages being sent
        logging.info(f"[CHUTES DEBUG] Sending messages to OpenAI API:")
        for msg in openai_messages:
            logging.info(f"[CHUTES DEBUG] Message: {msg}")
        logging.info(f"[CHUTES DEBUG] Payload keys: {list(payload.keys())}")
        
        # Try each model with its own retry logic
        for model_idx, current_model in enumerate(models_to_try):
            if model_idx > 0:
                logging.warning(f"[CHUTES] Falling back to model: {current_model}")
            
            # Update model in payload
            payload["model"] = current_model
            
            # Retry logic for current model
            for retry in range(self.max_retries):
                try:
                    response = self.client.chat.completions.create(**payload)
                    # Success! Update the model name to reflect which one worked
                    if model_idx > 0:
                        logging.info(f"[CHUTES] Successfully used fallback model: {current_model}")
                        self.model_name = current_model
                    break
                    
                except OpenAI_InternalServerError as e:
                    # Log the full error details
                    logging.error(f"[CHUTES] Full error details: {e}")
                    logging.error(f"[CHUTES] Error response body: {e.response.text if hasattr(e, 'response') else 'No response body'}")
                    
                    if self._is_target_exhausted_error(e):
                        backoff_time = self._get_backoff_time(retry)
                        logging.warning(
                            f"[CHUTES] Target exhausted error for model {current_model} "
                            f"(attempt {retry + 1}/{self.max_retries}). "
                            f"Waiting {backoff_time:.1f}s before retry..."
                        )
                        if retry < self.max_retries - 1:
                            time.sleep(backoff_time)
                            continue
                        else:
                            logging.error(f"[CHUTES] Model {current_model} exhausted after {self.max_retries} retries")
                            break
                    else:
                        # For other internal server errors, use shorter backoff
                        if retry < self.max_retries - 1:
                            backoff_time = 1.0 if self.test_mode else 10 * random.uniform(0.8, 1.2)
                            logging.warning(f"[CHUTES] Internal server error, retrying in {backoff_time:.1f}s...")
                            time.sleep(backoff_time)
                            continue
                        else:
                            logging.error(f"[CHUTES] Model {current_model} failed with internal server error")
                            break
                            
                except (OpenAI_APIConnectionError, OpenAI_RateLimitError) as e:
                    if retry < self.max_retries - 1:
                        backoff_time = 1.0 if self.test_mode else 15 * random.uniform(0.8, 1.2)
                        logging.warning(
                            f"[CHUTES] {type(e).__name__} for model {current_model} "
                            f"(attempt {retry + 1}/{self.max_retries}). "
                            f"Retrying in {backoff_time:.1f}s..."
                        )
                        time.sleep(backoff_time)
                        continue
                    else:
                        logging.error(f"[CHUTES] Model {current_model} failed with {type(e).__name__}")
                        break
                        
                except Exception as e:
                    logging.error(f"[CHUTES] Unexpected error for model {current_model}: {e}")
                    break
            
            # If we got a response, break out of the model loop
            if response:
                break
        
        # If all models failed, raise the last error
        if not response:
            error_msg = f"All models failed: {models_to_try}"
            logging.error(f"[CHUTES] {error_msg}")
            raise Exception(error_msg)

        # Convert response back to internal format
        internal_messages = []
        if response and response.choices:
            choice = response.choices[0]
            message = choice.message
            
            # Log the raw response for debugging
            logging.info(f"[CHUTES DEBUG] Raw response message: {message}")
            logging.info(f"[CHUTES DEBUG] Message content: {message.content}")
            logging.info(f"[CHUTES DEBUG] Message tool_calls: {message.tool_calls}")
            
            # Check if content contains JSON tool calls (our workaround)
            if message.content and tools:
                import json
                import re
                
                # Look for JSON blocks in the content
                json_pattern = r'```json\s*(\{.*?\})\s*```'
                json_matches = re.findall(json_pattern, message.content, re.DOTALL)
                
                if json_matches:
                    logging.info(f"[CHUTES] Found {len(json_matches)} potential JSON tool calls in content")
                    
                    # Process each JSON block
                    for json_str in json_matches:
                        try:
                            json_data = json.loads(json_str)
                            if "tool_call" in json_data:
                                tool_call_data = json_data["tool_call"]
                                logging.info(f"[CHUTES] Extracted tool call from JSON: {tool_call_data}")
                                
                                # Create a ToolCall from the JSON data
                                internal_messages.append(
                                    ToolCall(
                                        tool_call_id=tool_call_data.get("id", f"call_{int(time.time() * 1000)}"),
                                        tool_name=tool_call_data.get("name", ""),
                                        tool_input=tool_call_data.get("arguments", {}),
                                    )
                                )
                                
                                # Remove the JSON block from the content
                                message.content = message.content.replace(f"```json\n{json_str}\n```", "").strip()
                        except json.JSONDecodeError as e:
                            logging.error(f"[CHUTES] Failed to parse JSON tool call: {e}")
                
                # Add remaining content as TextResult if any
                if message.content.strip():
                    internal_messages.append(TextResult(text=message.content))
            elif message.content:
                internal_messages.append(TextResult(text=message.content))
            
            # Process native tool calls if any (unlikely with Chutes)
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