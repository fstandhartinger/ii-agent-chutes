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


class OpenRouterOpenAIClient(LLMClient):
    """Use OpenRouter models via OpenAI-compatible API."""

    def __init__(
        self,
        model_name="deepseek/deepseek-chat-v3-0324:free",
        max_retries=3,
        use_caching=True,
        fallback_models=None,
    ):
        """Initialize the OpenRouter OpenAI-compatible client."""
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable must be set")
            
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            max_retries=1,
            timeout=60 * 5,
        )
        self.model_name = model_name
        self.max_retries = max_retries
        self.use_caching = use_caching
        
        # Default fallback models for different scenarios
        if fallback_models is None:
            self.fallback_models = [
                "meta-llama/llama-4-maverick:free",
                "qwen/qwen2.5-vl-32b-instruct:free",
                "deepseek/deepseek-r1:free",
            ]
        else:
            self.fallback_models = fallback_models
            
        # Log provider info
        logging.info(f"=== Using OPENROUTER LLM provider with model: {model_name} ===")
        logging.info(f"=== Fallback models: {self.fallback_models} ===")

    def _is_target_exhausted_error(self, error: Exception) -> bool:
        """Check if the error is related to exhausted targets or rate limits."""
        error_str = str(error).lower()
        return (
            "exhausted all available targets" in error_str or
            "no available targets" in error_str or
            "all targets exhausted" in error_str or
            "rate limit" in error_str or
            "quota exceeded" in error_str
        )

    def _get_backoff_time(self, retry: int, base_delay: float = 10.0) -> float:
        """Calculate exponential backoff time with jitter."""
        # Shorter backoff for OpenRouter free tier
        delay = base_delay * (1.5 ** retry)
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
        """Generate responses using OpenRouter OpenAI-compatible API.

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
        logging.info(f"[OPENROUTER LLM CALL] model={self.model_name}, max_tokens={max_tokens}, temperature={temperature}")
        
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
        models_to_try = [self.model_name] + self.fallback_models
        
        # Try each model with its own retry logic
        for model_idx, current_model in enumerate(models_to_try):
            if model_idx > 0:
                logging.warning(f"[OPENROUTER] Falling back to model: {current_model}")
            
            # Retry logic for current model
            for retry in range(self.max_retries):
                try:
                    # Add OpenRouter specific headers
                    extra_headers = {
                        "HTTP-Referer": "https://fubea.ai",
                        "X-Title": "fubea.ai Agent"
                    }
                    
                    response = self.client.chat.completions.create(
                        model=current_model,
                        messages=openai_messages,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        tools=openai_tools if tools else None,
                        tool_choice=openai_tool_choice,
                        extra_headers=extra_headers,
                    )
                    # Success! Update the model name to reflect which one worked
                    if model_idx > 0:
                        logging.info(f"[OPENROUTER] Successfully used fallback model: {current_model}")
                        self.model_name = current_model
                    break
                    
                except OpenAI_InternalServerError as e:
                    if self._is_target_exhausted_error(e):
                        backoff_time = self._get_backoff_time(retry)
                        logging.warning(
                            f"[OPENROUTER] Rate limit/exhausted error for model {current_model} "
                            f"(attempt {retry + 1}/{self.max_retries}). "
                            f"Waiting {backoff_time:.1f}s before retry..."
                        )
                        if retry < self.max_retries - 1:
                            time.sleep(backoff_time)
                            continue
                        else:
                            logging.error(f"[OPENROUTER] Model {current_model} exhausted after {self.max_retries} retries")
                            break
                    else:
                        # For other internal server errors, use shorter backoff
                        if retry < self.max_retries - 1:
                            backoff_time = 5 * random.uniform(0.8, 1.2)
                            logging.warning(f"[OPENROUTER] Internal server error, retrying in {backoff_time:.1f}s...")
                            time.sleep(backoff_time)
                            continue
                        else:
                            logging.error(f"[OPENROUTER] Model {current_model} failed with internal server error")
                            break
                            
                except (OpenAI_APIConnectionError, OpenAI_RateLimitError) as e:
                    if retry < self.max_retries - 1:
                        backoff_time = self._get_backoff_time(retry)
                        logging.warning(
                            f"[OPENROUTER] {type(e).__name__} for model {current_model} "
                            f"(attempt {retry + 1}/{self.max_retries}). "
                            f"Retrying in {backoff_time:.1f}s..."
                        )
                        time.sleep(backoff_time)
                        continue
                    else:
                        logging.error(f"[OPENROUTER] Model {current_model} failed with {type(e).__name__}")
                        break
                        
                except Exception as e:
                    logging.error(f"[OPENROUTER] Unexpected error for model {current_model}: {e}")
                    break
            
            # If we got a response, break out of the model loop
            if response:
                break
        
        # If all models failed, raise the last error
        if not response:
            error_msg = f"All models failed: {models_to_try}"
            logging.error(f"[OPENROUTER] {error_msg}")
            raise Exception(error_msg)

        # Convert response back to internal format
        internal_messages = []
        if response and response.choices:
            choice = response.choices[0]
            message = choice.message
            
            # Log the raw response for debugging
            logging.info(f"[OPENROUTER DEBUG] Raw response message: {message}")
            logging.info(f"[OPENROUTER DEBUG] Message content: {message.content}")
            logging.info(f"[OPENROUTER DEBUG] Message tool_calls: {message.tool_calls}")
            
            if message.content:
                internal_messages.append(TextResult(text=message.content))
            
            if message.tool_calls:
                logging.info(f"[OPENROUTER DEBUG] Processing {len(message.tool_calls)} tool calls")
                for i, tool_call in enumerate(message.tool_calls):
                    logging.info(f"[OPENROUTER DEBUG] Tool call {i}: id={tool_call.id}, name={tool_call.function.name}")
                    logging.info(f"[OPENROUTER DEBUG] Tool call {i} arguments type: {type(tool_call.function.arguments)}")
                    logging.info(f"[OPENROUTER DEBUG] Tool call {i} arguments raw: {tool_call.function.arguments}")
                    
                    # Parse the tool arguments properly
                    try:
                        # Try to parse as JSON if it's a string
                        if isinstance(tool_call.function.arguments, str):
                            import json
                            tool_input = json.loads(tool_call.function.arguments)
                            logging.info(f"[OPENROUTER DEBUG] Tool call {i} parsed JSON: {tool_input}")
                        else:
                            tool_input = tool_call.function.arguments
                            logging.info(f"[OPENROUTER DEBUG] Tool call {i} using direct arguments: {tool_input}")
                    except (json.JSONDecodeError, TypeError) as e:
                        # If parsing fails, wrap the string in a dict
                        tool_input = {"arguments": str(tool_call.function.arguments)}
                        logging.error(f"[OPENROUTER DEBUG] Tool call {i} JSON parsing failed: {e}, wrapped in dict: {tool_input}")
                    
                    # Apply recursively_remove_invoke_tag and log the result
                    final_tool_input = recursively_remove_invoke_tag(tool_input)
                    logging.info(f"[OPENROUTER DEBUG] Tool call {i} final tool_input after recursively_remove_invoke_tag: {final_tool_input}")
                    logging.info(f"[OPENROUTER DEBUG] Tool call {i} final tool_input type: {type(final_tool_input)}")
                    
                    internal_messages.append(
                        ToolCall(
                            tool_call_id=tool_call.id,
                            tool_name=tool_call.function.name,
                            tool_input=final_tool_input,
                        )
                    )

        logging.info(f"[OPENROUTER DEBUG] Final internal_messages: {internal_messages}")
        
        message_metadata = {
            "raw_response": response,
            "input_tokens": response.usage.prompt_tokens if response else 0,
            "output_tokens": response.usage.completion_tokens if response else 0,
        }

        return internal_messages, message_metadata 