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


class OpenRouterOpenAIClient(LLMClient):
    """Use OpenRouter models via OpenAI-compatible API."""

    def __init__(
        self,
        model_name="deepseek/deepseek-chat-v3-0324:free",
        max_retries=3,
        use_caching=True,
        fallback_models=None,
        test_mode=False,
        no_fallback=False,
        use_native_tool_calling=True,
        project_id=None,
        region=None,
        thinking_tokens=None,
    ):
        """Initialize the OpenRouter OpenAI-compatible client.
        
        Args:
            model_name: The model name to use.
            max_retries: Maximum number of retries for failed requests.
            use_caching: Whether to use caching (not implemented for OpenRouter).
            fallback_models: List of fallback models to try if primary fails.
            test_mode: Whether to use reduced backoff times for testing.
            no_fallback: Whether to disable fallback models.
            use_native_tool_calling: Whether to use native tool calling or JSON workaround.
            project_id: Project ID (accepted for compatibility, not used by OpenRouter).
            region: Region (accepted for compatibility, not used by OpenRouter).
            thinking_tokens: Thinking tokens (accepted for compatibility, not used by OpenRouter).
        """
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable must be set")
        
        # Log API key presence (but not the actual key)
        logging.info(f"[OPENROUTER] API key found: {len(api_key)} characters")
        
        # Initialize the OpenAI client with OpenRouter's base URL
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
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
            # Free models (don't support tools)
            self.free_fallback_models = [
                "meta-llama/llama-4-maverick:free",
                "qwen/qwen2.5-vl-32b-instruct:free",
                "deepseek/deepseek-r1:free",
                # "qwen/qwen3-32b:fast",  # (commented out)
                # "meta-llama/llama-4-maverick:fast",  # (commented out)
                # "deepseek/deepseek-r1-distill-llama-70b:fast",  # (commented out)
                "claude-opus-4-0",  # Opus 4
            ]
            
            # Paid models that support tools (affordable options)
            self.tool_capable_models = [
                "openai/gpt-4o-mini",  # Most affordable GPT model with tools
                "anthropic/claude-3-haiku",  # Fast and affordable Claude with tools
                "google/gemini-flash-1.5",  # Google's fast model with tools
                "mistralai/mistral-7b-instruct",  # Affordable Mistral with tools
                # "qwen/qwen3-32b:fast",  # (commented out)
                # "meta-llama/llama-4-maverick:fast",  # (commented out)
                # "deepseek/deepseek-r1-distill-llama-70b:fast",  # (commented out)
                "claude-opus-4-0",  # Opus 4
                "google/gemini-2.5-pro-preview", # New
                "openai/gpt-4.1", # New
                "google/gemini-2.5-flash-preview-05-20:thinking" # New
            ]
        else:
            self.free_fallback_models = fallback_models
            self.tool_capable_models = fallback_models
        
        # Determine if the primary model supports tools
        self.primary_supports_tools = not self._is_free_model(model_name)
            
        # Log provider info
        logging.info(f"=== Using OPENROUTER LLM provider with model: {model_name} ===")
        logging.info(f"=== Primary model supports tools: {self.primary_supports_tools} ===")
        logging.info(f"=== Free fallback models: {self.free_fallback_models} ===")
        logging.info(f"=== Tool-capable models: {self.tool_capable_models} ===")
        
        if self.use_native_tool_calling:
            logging.info("=== NATIVE TOOL CALLING MODE ENABLED ===")
        else:
            logging.info("=== JSON WORKAROUND MODE ===")
        if self.no_fallback:
            logging.info(f"=== Fallback models DISABLED (no_fallback=True) ===")
        else:
            logging.info(f"=== Fallback models enabled ===")
        if test_mode:
            logging.info("=== TEST MODE: Using reduced backoff times ===")

    def _is_free_model(self, model_name: str) -> bool:
        """Check if a model is a free model (doesn't support tools)."""
        return ":free" in model_name.lower()

    def _is_target_exhausted_error(self, error: Exception) -> bool:
        """Check if the error is related to exhausted targets or rate limits."""
        error_str = str(error).lower()
        return (
            "exhausted all available targets" in error_str or
            "no available targets" in error_str or
            "all targets exhausted" in error_str or
            "rate limit" in error_str or
            "quota exceeded" in error_str or
            "no endpoints found" in error_str
        )

    def _is_tool_not_supported_error(self, error: Exception) -> bool:
        """Check if the error is related to tool calling not being supported."""
        error_str = str(error).lower()
        return (
            "no endpoints found that support tool use" in error_str or
            "tool use" in error_str or
            "function calling" in error_str
        )

    def _get_backoff_time(self, retry: int, base_delay: float = 10.0) -> float:
        """Calculate exponential backoff time with jitter."""
        if self.test_mode:
            # In test mode, use very short delays (max 1 second)
            return min(1.0, 0.1 * (2 ** retry))
        
        # Shorter backoff for OpenRouter free tier
        delay = base_delay * (1.5 ** retry)
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
        
        for msg in recent_messages[-8:]:  # Check last 8 messages
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
        """Generate responses using OpenRouter OpenAI-compatible API with fallback mechanism.

        Args:
            messages: A list of messages.
            max_tokens: The maximum number of tokens to generate.
            system_prompt: A system prompt.
            temperature: The temperature.
            tools: A list of tools.
            tool_choice: A tool choice.
            thinking_tokens: Not supported in OpenAI API format.
            _retry_count: Internal retry counter for fallback mechanism.

        Returns:
            A generated response.
        """
        # Log each LLM call
        logging.info(f"[OPENROUTER LLM CALL] model={self.model_name}, max_tokens={max_tokens}, temperature={temperature}")
        logging.info(f"[OPENROUTER] Tools requested: {len(tools) > 0}")
        
        # Choose the right models based on whether tools are needed
        if tools and len(tools) > 0:
            # Tools are needed - use tool-capable models
            if self.primary_supports_tools:
                models_to_try = [self.model_name] + self.tool_capable_models
            else:
                # Primary model doesn't support tools, use tool-capable models first
                models_to_try = self.tool_capable_models + [self.model_name]
                logging.warning("[OPENROUTER] Tools requested but primary model is free - using paid models")
        else:
            # No tools needed - can use free models
            models_to_try = [self.model_name] + self.free_fallback_models
        
        # Determine models to try based on no_fallback flag
        if self.no_fallback:
            models_to_try = [self.model_name]
            logging.info(f"[OPENROUTER] Using only primary model (no_fallback=True): {self.model_name}")
        
        logging.info(f"[OPENROUTER] Models to try: {models_to_try}")
        
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
                        openai_messages.append({
                            "role": "user",
                            "content": message.text,
                        })
                elif str(type(message)) == str(TextResult):
                    message = cast(TextResult, message)
                    if role == "assistant":
                        openai_messages.append({
                            "role": "assistant",
                            "content": message.text,
                        })
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
                        logging.info(f"[OPENROUTER] Added native tool call to assistant message: {message.tool_name}")
                    else:
                        # JSON workaround mode - convert tool call to a text representation
                        if role == "assistant":
                            # Add as assistant message showing the tool was called
                            tool_call_text = f"I'll use the {message.tool_name} tool with these parameters: {json.dumps(message.tool_input, indent=2)}"
                            openai_messages.append({
                                "role": "assistant",
                                "content": tool_call_text,
                            })
                            logging.info(f"[OPENROUTER] Converted ToolCall to assistant text message: {message.tool_name}")
                        else:
                            # Skip tool calls in user messages
                            logging.warning(f"[OPENROUTER] Skipping ToolCall message in user role: {message.tool_name}")
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
                        logging.info(f"[OPENROUTER] Added native tool result message")
                    else:
                        # JSON workaround mode - convert to regular text message with clear formatting
                        if role == "user":
                            # Format tool result clearly so the model understands it's a tool result
                            result_text = f"Tool result from {message.tool_name}:\n{str(message.tool_output)}"
                            openai_messages.append({
                                "role": "user",
                                "content": result_text,
                            })
                            logging.info(f"[OPENROUTER] Converted ToolFormattedResult to formatted user message")

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
                logging.info(f"[OPENROUTER] Using native tool calling for {len(tools)} tools")
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
                
                logging.info(f"[OPENROUTER] Added {len(openai_tools)} tools to payload for native calling")
            else:
                logging.info(f"[OPENROUTER] Implementing JSON workaround for {len(tools)} tools")
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
                
                logging.info(f"[OPENROUTER] Added enhanced tool instructions to system prompt")

        response = None
        
        # Try each model with its own retry logic
        for model_idx, current_model in enumerate(models_to_try):
            if model_idx > 0:
                logging.warning(f"[OPENROUTER] Falling back to model: {current_model}")
            
            # Update model in payload
            payload["model"] = current_model
            
            # Check if this model supports tools when tools are needed
            model_supports_tools = not self._is_free_model(current_model)
            
            # If model doesn't support tools but we're in native mode, try without tools
            if tools and not model_supports_tools and self.use_native_tool_calling:
                logging.warning(f"[OPENROUTER] Model {current_model} doesn't support tools - removing tools from payload")
                payload_without_tools = payload.copy()
                payload_without_tools.pop("tools", None)
                payload_without_tools.pop("tool_choice", None)
                current_payload = payload_without_tools
            else:
                current_payload = payload

            # Retry logic for current model
            for retry in range(self.max_retries):
                try:
                    # Create extra headers for OpenRouter
                    extra_headers = {
                        "HTTP-Referer": "https://fubea.ai",  # Optional but recommended
                        "X-Title": "fubea.ai Agent",  # Optional but recommended
                    }
                    
                    logging.info(f"[OPENROUTER] Attempting request to model: {current_model} (tools: {'tools' in current_payload})")
                    
                    response = self.client.chat.completions.create(
                        **current_payload,
                        extra_headers=extra_headers,
                    )
                    
                    logging.info(f"[OPENROUTER] Successfully received response from model: {current_model}")
                    
                    # Success! Update the model name to reflect which one worked
                    if model_idx > 0:
                        logging.info(f"[OPENROUTER] Successfully used fallback model: {current_model}")
                        self.model_name = current_model
                    break
                    
                except Exception as e:
                    logging.error(f"[OPENROUTER] Error for model {current_model}: {e}")
                    logging.error(f"[OPENROUTER] Error type: {type(e)}")
                    
                    # If this is the first attempt and we're using native tool calling, try JSON workaround
                    if retry == 0 and self.use_native_tool_calling and tools and "tools" in current_payload:
                        logging.warning(f"[OPENROUTER] Native tool calling failed, trying JSON workaround mode")
                        # Switch to JSON workaround mode for this attempt
                        return self.generate(
                            messages=messages,
                            max_tokens=max_tokens,
                            system_prompt=system_prompt,
                            temperature=temperature,
                            tools=tools,
                            tool_choice=tool_choice,
                            thinking_tokens=thinking_tokens,
                            _retry_count=_retry_count + 1,
                        )
                    
                    # Handle specific error types
                    if isinstance(e, (OpenAI_InternalServerError, OpenAI_APIConnectionError, OpenAI_RateLimitError)):
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
                    elif isinstance(e, OpenAI_BadRequestError):
                        # Handle specific authentication/authorization errors
                        if "no auth credentials found" in str(e).lower() or "401" in str(e):
                            logging.error(f"[OPENROUTER] Authentication error for model {current_model}: {e}")
                            logging.error("[OPENROUTER] Please check your OPENROUTER_API_KEY environment variable")
                            break
                        elif "404" in str(e) or "no endpoints found" in str(e).lower():
                            if self._is_tool_not_supported_error(e):
                                logging.error(f"[OPENROUTER] Model {current_model} doesn't support tool calling")
                                break
                            else:
                                logging.error(f"[OPENROUTER] Model not found or no endpoints available: {current_model}")
                                break
                        else:
                            logging.error(f"[OPENROUTER] Bad request error for model {current_model}: {e}")
                            break
                    else:
                        # For other errors, break to try next model
                        logging.error(f"[OPENROUTER] Unexpected error for model {current_model}: {e}")
                        break
            
            # If we got a response, break out of the model loop
            if response:
                break
        
        # If all models failed, try retry with enhanced prompt if within retry limit
        if not response:
            if _retry_count < 3:
                logging.warning(f"[OPENROUTER] All models failed, attempting retry {_retry_count + 1}/3 with enhanced prompt")
                
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
                logging.error(f"[OPENROUTER] {error_msg}")
                logging.error("[OPENROUTER] Please check:")
                logging.error("1. OPENROUTER_API_KEY environment variable is set correctly")
                logging.error("2. Your OpenRouter account has sufficient credits")
                logging.error("3. Your privacy settings allow free models: https://openrouter.ai/settings/privacy")
                if tools and len(tools) > 0:
                    logging.error("4. For tool calling, you need paid models with sufficient credits")
                    logging.error("5. Free models (:free) don't support function calling")
                raise Exception(error_msg)

        # Check if response is valid and has content
        if response and (not response.choices or not response.choices[0].message):
            if _retry_count < 3:
                logging.warning(f"[OPENROUTER] Received malformed response (no choices/message), attempting retry {_retry_count + 1}/3")
                
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
                logging.error(f"[OPENROUTER] Received malformed response after {_retry_count + 1} attempts")
                raise Exception(f"Received malformed response after {_retry_count + 1} attempts")

        # Convert response back to internal format
        internal_messages = []
        if response and response.choices:
            choice = response.choices[0]
            message = choice.message
            
            # Log the raw response for debugging
            logging.info(f"[OPENROUTER DEBUG] Raw response message: {message}")
            logging.info(f"[OPENROUTER DEBUG] Message content: {message.content}")
            logging.info(f"[OPENROUTER DEBUG] Message tool_calls: {message.tool_calls}")
            
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
                
                # Initialize tool_calls_found before processing
                tool_calls_found = 0
                
                if json_matches:
                    logging.info(f"[OPENROUTER] Found {len(json_matches)} potential JSON tool calls in content")
                    
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
                                logging.info(f"[OPENROUTER] Extracted tool call from JSON: {tool_call_data}")
                                
                                # Validate tool call data
                                if not tool_call_data.get("name"):
                                    logging.warning(f"[OPENROUTER] Tool call missing name, skipping")
                                    continue
                                
                                # Check if this is a valid tool name
                                valid_tool_names = [tool.name for tool in tools]
                                if tool_call_data.get("name") not in valid_tool_names:
                                    logging.warning(f"[OPENROUTER] Invalid tool name '{tool_call_data.get('name')}', valid tools are: {valid_tool_names}")
                                    continue
                                    
                                # Prevent tool call loops by checking recent history
                                if self._is_tool_call_loop(tool_call_data, openai_messages):
                                    logging.warning(f"[OPENROUTER] Detected potential tool call loop for {tool_call_data.get('name')}, skipping")
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
                            logging.error(f"[OPENROUTER] Failed to parse JSON tool call: {e}")
                            logging.error(f"[OPENROUTER] Problematic JSON: {json_str[:200]}...")
                            continue
                        except Exception as e:
                            logging.error(f"[OPENROUTER] Unexpected error processing tool call: {e}")
                            continue
                
                # Add remaining content as TextResult if any
                if message.content and message.content.strip():
                    internal_messages.append(TextResult(text=message.content))
            elif self.use_native_tool_calling and message.tool_calls:
                # Native tool calling mode - process tool calls directly
                logging.info(f"[OPENROUTER] Processing {len(message.tool_calls)} native tool calls")
                for i, tool_call in enumerate(message.tool_calls):
                    logging.info(f"[OPENROUTER] Native tool call {i}: id={tool_call.id}, name={tool_call.function.name}")
                    
                    # Parse the tool arguments properly
                    try:
                        # Try to parse as JSON if it's a string
                        if isinstance(tool_call.function.arguments, str):
                            tool_input = json.loads(tool_call.function.arguments)
                            logging.info(f"[OPENROUTER] Native tool call {i} parsed JSON: {tool_input}")
                        else:
                            tool_input = tool_call.function.arguments
                            logging.info(f"[OPENROUTER] Native tool call {i} using direct arguments: {tool_input}")
                    except (json.JSONDecodeError, TypeError) as e:
                        # If parsing fails, wrap the string in a dict
                        tool_input = {"arguments": str(tool_call.function.arguments)}
                        logging.error(f"[OPENROUTER] Native tool call {i} JSON parsing failed: {e}, wrapped in dict: {tool_input}")
                    
                    # Apply recursively_remove_invoke_tag and log the result
                    final_tool_input = recursively_remove_invoke_tag(tool_input)
                    logging.info(f"[OPENROUTER] Native tool call {i} final tool_input: {final_tool_input}")
                    
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

        logging.info(f"[OPENROUTER DEBUG] Final internal_messages: {internal_messages}")
        
        # Check if we got empty internal messages and retry if needed
        if not internal_messages and _retry_count < 3:
            logging.warning(f"[OPENROUTER] Received empty internal messages, attempting retry {_retry_count + 1}/3")
            
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
            logging.warning("[OPENROUTER] Response or usage information is missing, using default token counts")
        
        message_metadata = {
            "raw_response": response,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        }

        return internal_messages, message_metadata 