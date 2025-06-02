import os
import random
import time
import logging
import json
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
from ii_agent.utils.constants import SONNET_4


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
        use_native_tool_calling=False,
        project_id=None,
        region=None,
        thinking_tokens=None,
    ):
        """Initialize the Chutes OpenAI-compatible client.
        
        Args:
            model_name: The model name to use.
            max_retries: Maximum number of retries for failed requests.
            use_caching: Whether to use caching (not implemented for Chutes).
            fallback_models: List of fallback models to try if primary fails.
            test_mode: Whether to use reduced backoff times for testing.
            no_fallback: Whether to disable fallback models.
            use_native_tool_calling: Whether to use native tool calling or JSON workaround.
            project_id: Project ID (accepted for compatibility, not used by Chutes).
            region: Region (accepted for compatibility, not used by Chutes).
            thinking_tokens: Thinking tokens (accepted for compatibility, not used by Chutes).
        """
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
        self.use_native_tool_calling = use_native_tool_calling
        
        # Initialize logger_for_agent_logs to use standard logging
        self.logger_for_agent_logs = logging.getLogger(__name__)
        
        # Default fallback models for different scenarios
        if fallback_models is None:
            self.fallback_models = [
                "NVIDIA/Nemotron-4-340B-Chat",  # Ultra large
                "deepseek-ai/DeepSeek-V3-Chat",  # Large
                "Qwen/Qwen3-72B-Instruct",  # Large
                "chutesai/Llama-4-Maverick-17B-128E-Instruct-FP8",  # Vision capable
                "Qwen/Qwen2.5-VL-32B-Instruct",  # Vision capable
                "deepseek-ai/DeepSeek-R1",  # Text only
                "deepseek-ai/DeepSeek-R1-0528",  # Text only (new model)
            ]
        else:
            self.fallback_models = fallback_models
            
        # Log provider info
        logging.info(f"=== Using CHUTES LLM provider with model: {model_name} ===")
        
        # Check if model supports native tool calling
        models_without_native_tools = ["Qwen/Qwen3-235B-A22B", "Qwen/Qwen2.5-VL-32B-Instruct"]
        if self.use_native_tool_calling and model_name in models_without_native_tools:
            logging.warning(f"=== Model {model_name} may not support native tool calling properly ===")
            logging.warning(f"=== Consider using JSON workaround mode instead ===")
        
        if self.use_native_tool_calling:
            logging.info("=== NATIVE TOOL CALLING MODE ENABLED ===")
        else:
            logging.info("=== JSON WORKAROUND MODE (default) ===")
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

    def _is_tool_call_loop(self, tool_call_data: dict, recent_messages: list) -> bool:
        """Detect if this tool call would create a loop."""
        tool_name = tool_call_data.get("name", "")
        tool_args = tool_call_data.get("arguments", {})
        
        # Check the last few messages for repeated tool calls
        recent_tool_calls = []
        recent_tool_details = []
        
        for msg in recent_messages[-8:]:  # Check last 8 messages (increased from 6)
            if msg.get("role") == "assistant":
                content = str(msg.get("content", ""))
                if "tool_call" in content:
                    # Try to extract tool name from the content
                    import re
                    name_match = re.search(r'"name"\s*:\s*"([^"]+)"', content)
                    if name_match:
                        extracted_name = name_match.group(1)
                        recent_tool_calls.append(extracted_name)
                        
                        # Also extract arguments for more detailed comparison
                        args_match = re.search(r'"arguments"\s*:\s*(\{[^}]*\})', content)
                        if args_match:
                            try:
                                args = json.loads(args_match.group(1))
                                recent_tool_details.append((extracted_name, args))
                            except:
                                recent_tool_details.append((extracted_name, {}))
                        else:
                            recent_tool_details.append((extracted_name, {}))
        
        # Count occurrences of this tool
        tool_count = recent_tool_calls.count(tool_name)
        
        # Special handling for different tools
        if tool_name == "sequential_thinking":
            # Allow sequential thinking but prevent excessive repetition
            if tool_count >= 3:
                self.logger_for_agent_logs.info(f"[LOOP DETECTION] Blocking sequential_thinking after {tool_count} recent uses")
                return True
        elif tool_name in ["web_search", "visit_webpage"]:
            # For research tools, be more lenient but check for identical arguments
            if tool_count >= 4:
                # Check if we're making the exact same call repeatedly
                current_call = (tool_name, tool_args)
                identical_calls = sum(1 for name, args in recent_tool_details 
                                    if name == tool_name and args == tool_args)
                if identical_calls >= 2:
                    self.logger_for_agent_logs.info(f"[LOOP DETECTION] Blocking {tool_name} - identical call repeated {identical_calls} times")
                    return True
                elif tool_count >= 5:
                    self.logger_for_agent_logs.info(f"[LOOP DETECTION] Blocking {tool_name} after {tool_count} recent uses")
                    return True
        else:
            # For other tools, use moderate limits
            if tool_count >= 3:
                self.logger_for_agent_logs.info(f"[LOOP DETECTION] Blocking {tool_name} after {tool_count} recent uses")
                return True
                
        return False

    def generate(
        self,
        messages: LLMMessages,
        max_tokens: int,
        system_prompt: str | None = None,
        temperature: float = 0.0,
        tools: list[ToolParam] = [],
        tool_choice: dict[str, str] | None = None,
        thinking_tokens: int | None = None,
        _retry_count: int = 0,
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
        # Check for maximum retry limit to prevent infinite recursion
        if _retry_count > 3:
            raise Exception(f"Maximum retry limit exceeded: {_retry_count}")
        
        # Log each LLM call
        retry_info = f" (retry {_retry_count}/3)" if _retry_count > 0 else ""
        logging.info(f"[CHUTES LLM CALL] model={self.model_name}, max_tokens={max_tokens}, temperature={temperature}{retry_info}")
        
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
                    # Handle image blocks for vision models
                    message = cast(ImageBlock, message)
                    if role == "user":
                        # Check if this is a vision-capable model
                        vision_models = [
                            "deepseek-ai/DeepSeek-V3-0324", 
                            "chutesai/Llama-4-Maverick-17B-128E-Instruct-FP8",
                            "Qwen/Qwen2.5-VL-32B-Instruct"
                        ]
                        if self.model_name in vision_models:
                            # Convert to OpenAI vision format
                            image_content = {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{message.source['media_type']};base64,{message.source['data']}"
                                }
                            }
                            
                            # Find the last user message and convert it to multi-modal format
                            if openai_messages and openai_messages[-1]["role"] == "user":
                                # Convert existing text content to multi-modal format
                                existing_content = openai_messages[-1]["content"]
                                if isinstance(existing_content, str):
                                    openai_messages[-1]["content"] = [
                                        {"type": "text", "text": existing_content},
                                        image_content
                                    ]
                                elif isinstance(existing_content, list):
                                    openai_messages[-1]["content"].append(image_content)
                            else:
                                # Create new message with just the image
                                openai_messages.append({
                                    "role": "user",
                                    "content": [image_content]
                                })
                            logging.info(f"[CHUTES] Added image to message for vision model: {self.model_name}")
                        else:
                            logging.warning(f"[CHUTES] Model {self.model_name} does not support vision, skipping image...")
                            continue
                elif str(type(message)) == str(ToolCall):
                    message = cast(ToolCall, message)
                    if self.use_native_tool_calling and role == "assistant":
                        # Native tool calling mode - add tool call to assistant message
                        tool_call_dict = {
                            "id": message.tool_call_id,
                            "type": "function",
                            "function": {
                                "name": message.tool_name,
                                "arguments": json.dumps(message.tool_input),
                            }
                        }
                        
                        # Check if we need to append to existing assistant message
                        if openai_messages and openai_messages[-1]["role"] == "assistant":
                            # Append to existing assistant message
                            if "tool_calls" not in openai_messages[-1]:
                                openai_messages[-1]["tool_calls"] = []
                            openai_messages[-1]["tool_calls"].append(tool_call_dict)
                        else:
                            # Create new assistant message with tool call
                            openai_messages.append({
                                "role": "assistant",
                                "content": None,
                                "tool_calls": [tool_call_dict]
                            })
                        logging.info(f"[CHUTES] Added native tool call to assistant message: {message.tool_name}")
                    else:
                        # JSON workaround mode - convert tool call to a text representation
                        # This helps maintain context even without native tool calling
                        if role == "assistant":
                            # Add as assistant message showing the tool was called
                            tool_call_text = f"I'll use the {message.tool_name} tool with these parameters: {json.dumps(message.tool_input, indent=2)}"
                            openai_messages.append({
                                "role": "assistant",
                                "content": tool_call_text,
                            })
                            logging.info(f"[CHUTES] Converted ToolCall to assistant text message: {message.tool_name}")
                        else:
                            # Skip tool calls in user messages
                            logging.warning(f"[CHUTES] Skipping ToolCall message in user role: {message.tool_name}")
                            continue
                elif str(type(message)) == str(ToolFormattedResult):
                    message = cast(ToolFormattedResult, message)
                    if self.use_native_tool_calling and role == "user":
                        # Native tool calling mode - add tool result message
                        openai_messages.append({
                            "role": "tool",
                            "tool_call_id": message.tool_call_id,
                            "content": str(message.tool_output)
                        })
                        logging.info(f"[CHUTES] Added native tool result message")
                    else:
                        # JSON workaround mode - convert to regular text message with clear formatting
                        if role == "user":
                            # Format tool result clearly so the model understands it's a tool result
                            result_text = f"Tool result from {message.tool_name}:\n{str(message.tool_output)}"
                            openai_messages.append({
                                "role": "user",
                                "content": result_text,
                            })
                            logging.info(f"[CHUTES] Converted ToolFormattedResult to formatted user message")

        # Build the request payload - only include what's needed
        payload = {
            "model": self.model_name,
            "messages": openai_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        
        # Handle tools based on the mode
        if tools:
            if self.use_native_tool_calling:
                logging.info(f"[CHUTES] Using native tool calling for {len(tools)} tools")
                # Convert tools to OpenAI format for native tool calling
                openai_tools = []
                for tool in tools:
                    openai_tool = {
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": tool.input_schema
                        }
                    }
                    openai_tools.append(openai_tool)
                
                # Add tools to payload
                payload["tools"] = openai_tools
                
                # Set tool choice if provided
                if tool_choice:
                    payload["tool_choice"] = tool_choice
                else:
                    payload["tool_choice"] = "auto"
                
                logging.info(f"[CHUTES] Added {len(openai_tools)} tools to payload for native calling")
            else:
                logging.info(f"[CHUTES] Implementing JSON workaround for {len(tools)} tools")
                # Add a system message that instructs the model to output tool calls as JSON
                tool_instructions = "\n\nIMPORTANT: When you need to use a tool, you MUST output a JSON object in the following EXACT format:\n```json\n{\n  \"tool_call\": {\n    \"id\": \"call_<unique_id>\",\n    \"name\": \"<tool_name>\",\n    \"arguments\": {<tool_arguments>}\n  }\n}\n```\n\nRULES:\n- Use ONLY ONE tool call per response\n- Do NOT call the same tool repeatedly without making progress\n- For sequential_thinking: Only use when you need to break down a complex problem. Do NOT use for simple tasks.\n- Always provide substantive reasoning in your response along with the tool call\n- If a tool fails, try a different approach rather than repeating the same call\n- The JSON block MUST be properly formatted and complete\n- Always include the closing braces and backticks\n- For research tasks: Continue using tools until you have comprehensive information, then provide a complete summary\n- When you have sufficient information to answer the question, provide your final answer WITHOUT using tools\n\nAvailable tools:\n"
                for tool in tools:
                    tool_instructions += f"- {tool.name}: {tool.description}\n"
                    tool_instructions += f"  Parameters: {tool.input_schema}\n"
                
                # Add examples for common tools
                tool_instructions += "\n\nEXAMPLES:\n"
                tool_instructions += "For web search:\n```json\n{\n  \"tool_call\": {\n    \"id\": \"call_123\",\n    \"name\": \"web_search\",\n    \"arguments\": {\"query\": \"your search query here\"}\n  }\n}\n```\n"
                tool_instructions += "For sequential thinking:\n```json\n{\n  \"tool_call\": {\n    \"id\": \"call_456\",\n    \"name\": \"sequential_thinking\",\n    \"arguments\": {\"thought\": \"your thought here\", \"nextThoughtNeeded\": true, \"thoughtNumber\": 1, \"totalThoughts\": 3}\n  }\n}\n```\n"
                tool_instructions += "\nIMPORTANT for sequential_thinking: Do NOT include optional fields (isRevision, revisesThought, branchFromThought, branchId, needsMoreThoughts) unless you're actually using them. Never set them to 0 or empty strings.\n"
                
                # Append to system prompt or create new one
                if openai_messages and openai_messages[0]["role"] == "system":
                    openai_messages[0]["content"] += tool_instructions
                else:
                    openai_messages.insert(0, {"role": "system", "content": tool_instructions})
                
                logging.info(f"[CHUTES] Added enhanced tool instructions to system prompt")

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
                    
                    # Log successful response details
                    logging.info(f"[CHUTES] API call successful for model: {current_model}")
                    if response:
                        logging.info(f"[CHUTES] Response received - has choices: {hasattr(response, 'choices') and response.choices is not None}")
                        if hasattr(response, 'choices') and response.choices:
                            logging.info(f"[CHUTES] Number of choices: {len(response.choices)}")
                            if len(response.choices) > 0:
                                logging.info(f"[CHUTES] First choice has message: {hasattr(response.choices[0], 'message') and response.choices[0].message is not None}")
                    else:
                        logging.warning(f"[CHUTES] Response is None or falsy immediately after API call")
                    
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

                except OpenAI_BadRequestError as e:
                    # Explicitly handle token/context length errors to trigger fallback
                    error_message = str(e)
                    logging.error(f"[CHUTES] BadRequestError for model {current_model}: {error_message}")
                    if (
                        "maximum context length" in error_message.lower()
                        or "maximum token" in error_message.lower()
                        or "too many tokens" in error_message.lower()
                        or "context length" in error_message.lower()
                        or "token limit" in error_message.lower()
                        or "reduce the length" in error_message.lower()
                    ):
                        logging.warning(f"[CHUTES] Token/context limit error for model {current_model}, falling back to next model.")
                        # Break to outer loop to try next model
                        break
                    else:
                        # For other BadRequestErrors, treat as generic failure
                        if retry < self.max_retries - 1:
                            backoff_time = 1.0 if self.test_mode else 5 * random.uniform(0.8, 1.2)
                            logging.warning(f"[CHUTES] BadRequestError, retrying in {backoff_time:.1f}s...")
                            time.sleep(backoff_time)
                            continue
                        else:
                            logging.error(f"[CHUTES] Model {current_model} failed with BadRequestError")
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
                    logging.error(f"[CHUTES] Error type: {type(e)}")
                    logging.error(f"[CHUTES] Error details: {str(e)}")
                    
                    # Log the full traceback for debugging
                    import traceback
                    logging.error(f"[CHUTES] Full traceback:\n{traceback.format_exc()}")
                    
                    # If this is a JSON decode error or similar, it might be a response format issue
                    if "json" in str(e).lower() or "decode" in str(e).lower():
                        logging.error(f"[CHUTES] Possible response format issue detected")
                    
                    break
            
            # If we got a response, break out of the model loop
            if response:
                break
        
        # If all models failed, try retry with enhanced prompt if within retry limit
        if not response:
            if _retry_count < 3:
                logging.warning(f"[CHUTES] All models failed, attempting retry {_retry_count + 1}/3 with enhanced prompt")
                
                # Add a clarifying instruction to the system prompt for retry
                enhanced_system_prompt = system_prompt or ""
                if tools:
                    enhanced_system_prompt += "\n\nIMPORTANT: Please ensure you provide a complete and valid response. If using tools, format them correctly as JSON."
                else:
                    enhanced_system_prompt += "\n\nIMPORTANT: Please provide a complete and helpful response to the user's request."
                
                # Recursive retry with enhanced prompt
                return self.generate(
                    messages=messages,
                    max_tokens=max_tokens,
                    system_prompt=enhanced_system_prompt,
                    temperature=temperature,
                    tools=tools,
                    tool_choice=tool_choice,
                    thinking_tokens=thinking_tokens,
                    _retry_count=_retry_count + 1
                )
            else:
                error_msg = f"All models failed after {_retry_count + 1} attempts: {models_to_try}"
                logging.error(f"[CHUTES] {error_msg}")
                raise Exception(error_msg)

        # Check if response is valid and has content
        if response and (not response.choices or not response.choices[0].message):
            if _retry_count < 3:
                # Enhanced logging to understand the malformed response
                logging.warning(f"[CHUTES] Received malformed response (no choices/message), attempting retry {_retry_count + 1}/3")
                
                # Log detailed response structure for debugging
                if response:
                    logging.error(f"[CHUTES] Malformed response details:")
                    logging.error(f"[CHUTES] - Response type: {type(response)}")
                    logging.error(f"[CHUTES] - Has choices: {hasattr(response, 'choices')}")
                    if hasattr(response, 'choices'):
                        logging.error(f"[CHUTES] - Choices: {response.choices}")
                        logging.error(f"[CHUTES] - Choices length: {len(response.choices) if response.choices else 0}")
                        if response.choices and len(response.choices) > 0:
                            logging.error(f"[CHUTES] - First choice: {response.choices[0]}")
                            logging.error(f"[CHUTES] - Has message: {hasattr(response.choices[0], 'message')}")
                            if hasattr(response.choices[0], 'message'):
                                logging.error(f"[CHUTES] - Message: {response.choices[0].message}")
                    
                    # Log other response attributes
                    logging.error(f"[CHUTES] - Response attributes: {dir(response)}")
                    
                    # Try to log the raw response if possible
                    try:
                        if hasattr(response, 'model_dump'):
                            logging.error(f"[CHUTES] - Raw response dump: {response.model_dump()}")
                        elif hasattr(response, '__dict__'):
                            logging.error(f"[CHUTES] - Raw response dict: {response.__dict__}")
                    except Exception as e:
                        logging.error(f"[CHUTES] - Could not dump raw response: {e}")
                else:
                    logging.error(f"[CHUTES] - Response is None or falsy")
                
                # Add a clarifying instruction to the system prompt for retry
                enhanced_system_prompt = system_prompt or ""
                enhanced_system_prompt += "\n\nIMPORTANT: Please provide a complete response with proper content."
                
                # Recursive retry with enhanced prompt
                return self.generate(
                    messages=messages,
                    max_tokens=max_tokens,
                    system_prompt=enhanced_system_prompt,
                    temperature=temperature,
                    tools=tools,
                    tool_choice=tool_choice,
                    thinking_tokens=thinking_tokens,
                    _retry_count=_retry_count + 1
                )
            else:
                logging.error(f"[CHUTES] Received malformed response after {_retry_count + 1} attempts")
                raise Exception(f"Received malformed response after {_retry_count + 1} attempts")

        # Convert response back to internal format
        internal_messages = []
        if response and response.choices:
            choice = response.choices[0]
            message = choice.message
            
            # Log the raw response for debugging
            logging.info(f"[CHUTES DEBUG] Raw response message: {message}")
            logging.info(f"[CHUTES DEBUG] Message content: {message.content}")
            logging.info(f"[CHUTES DEBUG] Message tool_calls: {message.tool_calls}")
            
            # Check if message content is None and no tool calls
            if message.content is None and not message.tool_calls:
                logging.warning(f"[CHUTES] Response has null content and no tool calls")
                # Try to extract any useful information from the response
                if hasattr(message, '__dict__'):
                    logging.warning(f"[CHUTES] Message attributes: {message.__dict__}")
            
            # Handle tool calls based on the mode
            if tools and not self.use_native_tool_calling:
                # JSON workaround mode - check if content contains JSON tool calls
                if message.content:
                    import re
                    
                    # Look for JSON blocks in the content with multiple patterns
                    json_patterns = [
                        r'```json\s*(\{.*?\})\s*```',  # Standard JSON blocks
                        r'```\s*(\{.*?"tool_call".*?\})\s*```',  # JSON blocks without json label
                        r'(\{[^{}]*"tool_call"[^{}]*\{[^{}]*\}[^{}]*\})',  # Inline JSON with tool_call
                    ]
                    
                    json_matches = []
                    for pattern in json_patterns:
                        matches = re.findall(pattern, message.content, re.DOTALL | re.IGNORECASE)
                        json_matches.extend(matches)
                
                # Also try to find incomplete JSON blocks (missing closing braces)
                if not json_matches:
                    incomplete_patterns = [
                        r'```json\s*(\{.*?)"tool_call".*?```',  # Incomplete JSON in code block
                        r'(\{[^{}]*"tool_call"[^{}]*"name"[^{}]*"[^"]+"\s*[^{}]*)',  # Partial JSON with tool_call and name
                    ]
                    for pattern in incomplete_patterns:
                        matches = re.findall(pattern, message.content, re.DOTALL | re.IGNORECASE)
                        if matches:
                            logging.warning(f"[CHUTES] Found incomplete JSON tool call, attempting to fix")
                            for match in matches:
                                # Try to fix common issues
                                fixed_json = match
                                if not fixed_json.rstrip().endswith('}'):
                                    # Count opening and closing braces
                                    open_braces = fixed_json.count('{')
                                    close_braces = fixed_json.count('}')
                                    missing_braces = open_braces - close_braces
                                    if missing_braces > 0:
                                        fixed_json += '}' * missing_braces
                                json_matches.append(fixed_json)
                
                # Initialize tool_calls_found before processing
                tool_calls_found = 0
                
                if json_matches:
                    logging.info(f"[CHUTES] Found {len(json_matches)} potential JSON tool calls in content")
                    
                    # Process each JSON block
                    for json_str in json_matches:
                        try:
                            # Clean up the JSON string
                            json_str = json_str.strip()
                            if not json_str.startswith('{'):
                                continue
                                
                            # Try to fix common JSON issues
                            # Remove trailing commas before closing braces
                            json_str = re.sub(r',\s*}', '}', json_str)
                            json_str = re.sub(r',\s*]', ']', json_str)
                            
                            json_data = json.loads(json_str)
                            if "tool_call" in json_data:
                                tool_call_data = json_data["tool_call"]
                                logging.info(f"[CHUTES] Extracted tool call from JSON: {tool_call_data}")
                                
                                # Validate tool call data
                                if not tool_call_data.get("name"):
                                    logging.warning(f"[CHUTES] Tool call missing name, skipping")
                                    continue
                                
                                # Check if this is a valid tool name
                                valid_tool_names = [tool.name for tool in tools]
                                if tool_call_data.get("name") not in valid_tool_names:
                                    logging.warning(f"[CHUTES] Invalid tool name '{tool_call_data.get('name')}', valid tools are: {valid_tool_names}")
                                    continue
                                    
                                # Prevent tool call loops by checking recent history
                                if self._is_tool_call_loop(tool_call_data, openai_messages):
                                    logging.warning(f"[CHUTES] Detected potential tool call loop for {tool_call_data.get('name')}, skipping")
                                    continue
                                
                                # Create a ToolCall from the JSON data
                                internal_messages.append(
                                    ToolCall(
                                        tool_call_id=tool_call_data.get("id", f"call_{int(time.time() * 1000)}"),
                                        tool_name=tool_call_data.get("name", ""),
                                        tool_input=tool_call_data.get("arguments", {}),
                                    )
                                )
                                tool_calls_found += 1
                                
                                # Remove the JSON block from the content
                                message.content = message.content.replace(f"```json\n{json_str}\n```", "").strip()
                                message.content = message.content.replace(f"```\n{json_str}\n```", "").strip()
                                message.content = message.content.replace(json_str, "").strip()
                                
                                # Only process the first valid tool call to prevent multiple calls
                                if tool_calls_found >= 1:
                                    break
                                    
                        except json.JSONDecodeError as e:
                            logging.error(f"[CHUTES] Failed to parse JSON tool call: {e}")
                            logging.error(f"[CHUTES] Problematic JSON: {json_str[:200]}...")
                            # Try to extract tool name for better debugging
                            name_match = re.search(r'"name"\s*:\s*"([^"]+)"', json_str)
                            if name_match:
                                logging.error(f"[CHUTES] Attempted tool call was for: {name_match.group(1)}")
                            continue
                        except Exception as e:
                            logging.error(f"[CHUTES] Unexpected error processing tool call: {e}")
                            continue
                
                # If no tool calls were found but we expected them, log helpful debug info
                if tool_calls_found == 0 and "tool_call" in message.content.lower():
                    logging.warning(f"[CHUTES] Content mentions 'tool_call' but no valid JSON was extracted")
                    logging.warning(f"[CHUTES] Response excerpt: {message.content[:500]}...")
                
                    # Add remaining content as TextResult if any
                    if message.content.strip():
                        internal_messages.append(TextResult(text=message.content))
            elif self.use_native_tool_calling and message.tool_calls:
                # Native tool calling mode - process tool calls directly
                logging.info(f"[CHUTES] Processing {len(message.tool_calls)} native tool calls")
                for i, tool_call in enumerate(message.tool_calls):
                    logging.info(f"[CHUTES] Native tool call {i}: id={tool_call.id}, name={tool_call.function.name}")
                    
                    # Parse the tool arguments properly
                    try:
                        # Try to parse as JSON if it's a string
                        if isinstance(tool_call.function.arguments, str):
                            tool_input = json.loads(tool_call.function.arguments)
                            logging.info(f"[CHUTES] Native tool call {i} parsed JSON: {tool_input}")
                        else:
                            tool_input = tool_call.function.arguments
                            logging.info(f"[CHUTES] Native tool call {i} using direct arguments: {tool_input}")
                    except (json.JSONDecodeError, TypeError) as e:
                        # If parsing fails, wrap the string in a dict
                        tool_input = {"arguments": str(tool_call.function.arguments)}
                        logging.error(f"[CHUTES] Native tool call {i} JSON parsing failed: {e}, wrapped in dict: {tool_input}")
                    
                    # Apply recursively_remove_invoke_tag and log the result
                    final_tool_input = recursively_remove_invoke_tag(tool_input)
                    logging.info(f"[CHUTES] Native tool call {i} final tool_input: {final_tool_input}")
                    
                    internal_messages.append(
                        ToolCall(
                            tool_call_id=tool_call.id,
                            tool_name=tool_call.function.name,
                            tool_input=final_tool_input,
                        )
                    )
                
                # Add content as TextResult if any
                if message.content and message.content.strip():
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
        
        # Check if we got empty internal messages and retry if needed
        if not internal_messages and _retry_count < 3:
            logging.warning(f"[CHUTES] Received empty internal messages, attempting retry {_retry_count + 1}/3")
            
            # Add a clarifying instruction to the system prompt for retry
            enhanced_system_prompt = system_prompt or ""
            enhanced_system_prompt += "\n\nIMPORTANT: Please provide a substantive response to the user's request. Do not return empty content."
            
            # Recursive retry with enhanced prompt
            return self.generate(
                messages=messages,
                max_tokens=max_tokens,
                system_prompt=enhanced_system_prompt,
                temperature=temperature,
                tools=tools,
                tool_choice=tool_choice,
                thinking_tokens=thinking_tokens,
                _retry_count=_retry_count + 1
            )
        
        # Safely extract token usage information
        input_tokens = 0
        output_tokens = 0
        
        if response and hasattr(response, 'usage') and response.usage:
            input_tokens = getattr(response.usage, 'prompt_tokens', 0) or 0
            output_tokens = getattr(response.usage, 'completion_tokens', 0) or 0
        else:
            logging.warning("[CHUTES] Response or usage information is missing, using default token counts")
        
        message_metadata = {
            "raw_response": response,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        }

        return internal_messages, message_metadata 