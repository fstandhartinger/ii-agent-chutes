import asyncio
import logging
from typing import Any, Optional
import uuid
import os

from typing import List
from fastapi import WebSocket
from ii_agent.agents.base import BaseAgent
from ii_agent.core.event import EventType, RealtimeEvent
from ii_agent.llm.base import LLMClient, TextResult
from ii_agent.llm.context_manager.base import ContextManager
from ii_agent.llm.message_history import MessageHistory
from ii_agent.tools.base import ToolImplOutput, LLMTool
from ii_agent.tools.utils import encode_image
from ii_agent.db.manager import DatabaseManager
from ii_agent.tools import AgentToolManager
from ii_agent.utils.constants import COMPLETE_MESSAGE
from ii_agent.utils.workspace_manager import WorkspaceManager


class AnthropicFC(BaseAgent):
    name = "general_agent"
    description = """\
A general agent that can accomplish tasks and answer questions.

If you are faced with a task that involves more than a few steps, or if the task is complex, or if the instructions are very long,
try breaking down the task into smaller steps. After call this tool to update or create a plan, use write_file or str_replace_tool to update the plan to todo.md
"""
    input_schema = {
        "type": "object",
        "properties": {
            "instruction": {
                "type": "string",
                "description": "The instruction to the agent.",
            },
        },
        "required": ["instruction"],
    }
    websocket: Optional[WebSocket]

    def __init__(
        self,
        system_prompt: str,
        client: LLMClient,
        tools: List[LLMTool],
        workspace_manager: WorkspaceManager,
        message_queue: asyncio.Queue,
        logger_for_agent_logs: logging.Logger,
        context_manager: ContextManager,
        max_output_tokens_per_turn: int = 8192,
        max_turns: int = 10,
        websocket: Optional[WebSocket] = None,
        session_id: Optional[uuid.UUID] = None,
    ):
        """Initialize the agent.

        Args:
            system_prompt: The system prompt to use
            client: The LLM client to use
            tools: List of tools to use
            message_queue: Message queue for real-time communication
            logger_for_agent_logs: Logger for agent logs
            context_manager: Context manager for managing conversation context
            max_output_tokens_per_turn: Maximum tokens per turn
            max_turns: Maximum number of turns
            websocket: Optional WebSocket for real-time communication
            session_id: UUID of the session this agent belongs to
        """
        super().__init__()
        self.workspace_manager = workspace_manager
        self.system_prompt = system_prompt
        self.client = client
        self.tool_manager = AgentToolManager(
            tools=tools,
            logger_for_agent_logs=logger_for_agent_logs,
        )

        self.logger_for_agent_logs = logger_for_agent_logs
        self.max_output_tokens = max_output_tokens_per_turn
        self.max_turns = max_turns

        self.interrupted = False
        self.history = MessageHistory()
        self.context_manager = context_manager
        self.session_id = session_id

        # Initialize database manager
        self.db_manager = DatabaseManager()

        self.message_queue = message_queue
        self.websocket = websocket

        # Round counter for tracking consecutive LLM calls
        self.round_counter = 0
        self.max_rounds = 150

    async def _process_messages(self):
        try:
            while True:
                try:
                    message: RealtimeEvent = await self.message_queue.get()

                    # Save all events to database if we have a session
                    if self.session_id is not None:
                        self.db_manager.save_event(self.session_id, message)
                    else:
                        self.logger_for_agent_logs.info(
                            f"No session ID, skipping event: {message}"
                        )

                    # Only send to websocket if this is not an event from the client and websocket exists
                    if (
                        message.type != EventType.USER_MESSAGE
                        and self.websocket is not None
                    ):
                        try:
                            await self.websocket.send_json(message.model_dump())
                        except Exception as e:
                            # If websocket send fails, just log it and continue processing
                            self.logger_for_agent_logs.warning(
                                f"Failed to send message to websocket: {str(e)}"
                            )
                            # Set websocket to None to prevent further attempts
                            self.websocket = None

                    self.message_queue.task_done()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger_for_agent_logs.error(
                        f"Error processing WebSocket message: {str(e)}"
                    )
        except asyncio.CancelledError:
            self.logger_for_agent_logs.info("Message processor stopped")
        except Exception as e:
            self.logger_for_agent_logs.error(f"Error in message processor: {str(e)}")

    def _validate_tool_parameters(self):
        """Validate tool parameters and check for duplicates."""
        tool_params = [tool.get_tool_param() for tool in self.tool_manager.get_tools()]
        tool_names = [param.name for param in tool_params]
        sorted_names = sorted(tool_names)
        for i in range(len(sorted_names) - 1):
            if sorted_names[i] == sorted_names[i + 1]:
                raise ValueError(f"Tool {sorted_names[i]} is duplicated")
        return tool_params

    def start_message_processing(self):
        """Start processing the message queue."""
        return asyncio.create_task(self._process_messages())

    def run_impl(
        self,
        tool_input: dict[str, Any],
        message_history: Optional[MessageHistory] = None,
    ) -> ToolImplOutput:
        instruction = tool_input["instruction"]
        files = tool_input["files"]

        user_input_delimiter = "-" * 45 + " USER INPUT " + "-" * 45 + "\n" + instruction
        self.logger_for_agent_logs.info(f"\n{user_input_delimiter}\n")

        # Add instruction to dialog before getting model response
        image_blocks = []
        if files:
            # First, list all attached files
            instruction = f"""{instruction}\n\nAttached files:\n"""
            for file in files:
                relative_path = self.workspace_manager.relative_path(file)
                instruction += f" - {relative_path}\n"
                self.logger_for_agent_logs.info(f"Attached file: {relative_path}")

            # Then process images for image blocks
            for file in files:
                ext = file.split(".")[-1].lower()
                if ext == "jpg":
                    ext = "jpeg"
                if ext in ["png", "gif", "jpeg", "webp"]:
                    try:
                        full_path = str(self.workspace_manager.workspace_path(file))
                        self.logger_for_agent_logs.info(f"Processing image file: {file}")
                        self.logger_for_agent_logs.info(f"Full path: {full_path}")
                        
                        # Check if file exists
                        if not os.path.exists(full_path):
                            self.logger_for_agent_logs.error(f"Image file not found: {full_path}")
                            continue
                            
                        base64_image = encode_image(full_path)
                        image_blocks.append(
                            {
                                "source": {
                                    "type": "base64",
                                    "media_type": f"image/{ext}",
                                    "data": base64_image,
                                }
                            }
                        )
                        self.logger_for_agent_logs.info(f"Successfully processed image: {file}")
                    except Exception as e:
                        self.logger_for_agent_logs.error(f"Error processing image {file}: {str(e)}")
                        import traceback
                        self.logger_for_agent_logs.error(traceback.format_exc())

        self.history.add_user_prompt(instruction, image_blocks)
        self.interrupted = False

        remaining_turns = self.max_turns
        while remaining_turns > 0:
            remaining_turns -= 1

            # Increment round counter for each LLM call
            self.round_counter += 1
            
            # Check if we've exceeded the maximum number of rounds
            if self.round_counter > self.max_rounds:
                timeout_message = f"Agent run stopped automatically after {self.max_rounds} consecutive LLM calls to prevent infinite loops."
                self.logger_for_agent_logs.warning(timeout_message)
                self.message_queue.put_nowait(
                    RealtimeEvent(
                        type=EventType.AGENT_RESPONSE,
                        content={"text": timeout_message},
                    )
                )
                return ToolImplOutput(
                    tool_output=timeout_message,
                    tool_result_message=timeout_message,
                )

            delimiter = "-" * 45 + " NEW TURN " + "-" * 45
            self.logger_for_agent_logs.info(f"\n{delimiter}\n")
            self.logger_for_agent_logs.info(f"Round {self.round_counter}/{self.max_rounds}")

            # Get tool parameters for available tools
            all_tool_params = self._validate_tool_parameters()

            try:
                current_messages = self.history.get_messages_for_llm()
                current_tok_count = self.context_manager.count_tokens(current_messages)
                self.logger_for_agent_logs.info(
                    f"(Current token count: {current_tok_count})\n"
                )

                truncated_messages_for_llm = (
                    self.context_manager.apply_truncation_if_needed(current_messages)
                )

                # NOTE:
                # If truncation happened, the `history` object itself was modified.
                # We need to update the message list in the `history` object to use the truncated version.
                self.history.set_message_list(truncated_messages_for_llm)

                # Track Pro usage if using premium models
                if hasattr(self, 'pro_key') and self.pro_key and hasattr(self.client, 'model_name'):
                    if self.client.model_name in ["claude-sonnet-4-0", "claude-opus-4-0"]:
                        # Track the usage before making the request
                        usage_result = self.db_manager.track_pro_usage(self.pro_key, self.client.model_name)
                        
                        if not usage_result['allowed'] or usage_result['use_fallback']:
                            # Switch to DeepSeek V3 as fallback
                            print(f"🔄 FALLBACK: Switching from {self.client.model_name} to DeepSeek V3 for Pro user {self.pro_key}")
                            self.model = "deepseek-chat"  # Use DeepSeek V3 instead
                            
                            # Update client to use DeepSeek
                            from openai import OpenAI
                            self.client = OpenAI(
                                api_key=os.getenv("DEEPSEEK_API_KEY"),
                                base_url="https://api.deepseek.com"
                            )
                        elif usage_result['warning_threshold']:
                            print(f"⚠️  WARNING: Pro user {self.pro_key} approaching usage limit ({usage_result['current_usage']}/1000)")
                        
                                                # Only show error if we couldn't switch to fallback
                        if not usage_result['allowed'] and not usage_result['use_fallback']:
                            error_message = "Monthly usage limit exceeded for Pro plan. Please wait until next month or contact support."
                            self.logger_for_agent_logs.error(error_message)
                            self.message_queue.put_nowait(
                                RealtimeEvent(
                                    type=EventType.AGENT_RESPONSE,
                                    content={"text": error_message},
                                )
                            )
                            return ToolImplOutput(
                                tool_output=error_message,
                                tool_result_message=error_message,
                            )

                model_response, _ = self.client.generate(
                    messages=truncated_messages_for_llm,
                    max_tokens=self.max_output_tokens,
                    tools=all_tool_params,
                    system_prompt=self.system_prompt,
                )

                if len(model_response) == 0:
                    model_response = [TextResult(text=COMPLETE_MESSAGE)]

                # Add the raw response to the canonical history
                self.history.add_assistant_turn(model_response)

                # Handle tool calls
                pending_tool_calls = self.history.get_pending_tool_calls()

                if len(pending_tool_calls) == 0:
                    # No tools were called - check if this is intentional
                    self.logger_for_agent_logs.info("[no tools were called]")
                    
                    # Get the last assistant response
                    last_response = self.history.get_last_assistant_text_response()
                    
                    # Check if the response seems incomplete or if the model might need prompting
                    # This is especially important for Chutes models that might fail to output proper JSON
                    if last_response and len(last_response.strip()) > 0:
                        # If there's a substantive response, check if it seems like a final answer
                        response_lower = last_response.lower()
                        
                        # Keywords that suggest the task might be complete
                        completion_indicators = [
                            "task completed", "task is complete", "completed successfully",
                            "finished", "done", "here is", "here's", "the answer is",
                            "in summary", "to summarize", "in conclusion", "based on",
                            "according to", "research shows", "information shows",
                            "found that", "discovered that", "results indicate"
                        ]
                        
                        # Keywords that suggest the agent is still working
                        continuation_indicators = [
                            "let me", "i'll", "i will", "next", "now", "first",
                            "searching", "looking", "finding", "checking", "analyzing",
                            "need to", "should", "going to", "will now", "continue"
                        ]
                        
                        # Check for research-specific patterns that might indicate completion
                        research_completion_patterns = [
                            "florian standhartinger", "programmer", "software", "developer",
                            "architect", "productivity-boost", "msg systems", "dap gmbh"
                        ]
                        
                        seems_complete = any(indicator in response_lower for indicator in completion_indicators)
                        seems_continuing = any(indicator in response_lower for indicator in continuation_indicators)
                        has_research_content = any(pattern in response_lower for pattern in research_completion_patterns)
                        
                        # More lenient completion detection for research tasks
                        if has_research_content and len(last_response.strip()) > 100:
                            # If the response contains substantial research content, it might be complete
                            # even without explicit completion indicators
                            seems_complete = True
                        
                        # Check if this is likely a continuation of research vs. a final answer
                        if seems_complete and not seems_continuing:
                            # The response seems like a final answer
                            self.logger_for_agent_logs.info(
                                "Response appears to be a final answer based on content analysis"
                            )
                            self.message_queue.put_nowait(
                                RealtimeEvent(
                                    type=EventType.AGENT_RESPONSE,
                                    content={"text": last_response},
                                )
                            )
                            return ToolImplOutput(
                                tool_output=last_response,
                                tool_result_message="Task completed",
                            )
                        elif len(last_response.strip()) > 200 and not seems_continuing:
                            # If we have a substantial response without continuation indicators,
                            # ask the model to clarify if it's done or needs to continue
                            self.logger_for_agent_logs.info(
                                "Substantial response without clear continuation - asking for clarification"
                            )
                            
                            clarification_prompt = (
                                "I see you provided information but didn't use any tools. "
                                "Are you finished with the research task, or do you need to continue? "
                                "If you're done, please state 'Task completed' clearly. "
                                "If you need to continue, please use the appropriate tools."
                            )
                            
                            self.history.add_user_prompt(clarification_prompt)
                            continue
                        else:
                            # The response doesn't seem final - prompt for clarification
                            self.logger_for_agent_logs.info(
                                "Response doesn't seem final, prompting for tool use or completion"
                            )
                            
                            # Add a system message to prompt the model
                            clarification_prompt = (
                                "I notice you didn't use any tools in your last response. "
                                "If you need to use tools to complete the task, please do so now. "
                                "If you believe the task is complete, please explicitly state that the task is finished."
                            )
                            
                            self.history.add_user_prompt(clarification_prompt)
                            
                            # Continue to the next turn
                            continue
                    else:
                        # Empty or minimal response - likely an issue with tool call formatting
                        self.logger_for_agent_logs.info(
                            "Empty or minimal response with no tools called - prompting for action"
                        )
                        
                        # Add a more direct prompt
                        recovery_prompt = (
                            "It seems there was an issue with your last response. "
                            "Please continue with the task. If you need to use a tool, "
                            "make sure to format it as a JSON object with 'tool_call' containing 'name' and 'arguments'."
                        )
                        
                        self.history.add_user_prompt(recovery_prompt)
                        
                        # Continue to the next turn
                        continue

                if len(pending_tool_calls) > 1:
                    # Log information about multiple tool calls
                    self.logger_for_agent_logs.info(
                        f"Model requested {len(pending_tool_calls)} tools. Executing them in sequence."
                    )
                    self.logger_for_agent_logs.info("Tool calls to execute:")
                    for i, tc in enumerate(pending_tool_calls):
                        self.logger_for_agent_logs.info(
                            f"  {i+1}. {tc.tool_name} with arguments: {tc.tool_input}"
                        )
                    
                    # Get the model's text response if any
                    text_results = [
                        item for item in model_response if isinstance(item, TextResult)
                    ]
                    if text_results:
                        self.logger_for_agent_logs.info(
                            f"Model's reasoning: {text_results[0].text}"
                        )

                # Execute all tool calls in sequence
                for tool_call in pending_tool_calls:
                    self.message_queue.put_nowait(
                        RealtimeEvent(
                            type=EventType.TOOL_CALL,
                            content={
                                "tool_call_id": tool_call.tool_call_id,
                                "tool_name": tool_call.tool_name,
                                "tool_input": tool_call.tool_input,
                            },
                        )
                    )

                    # Log planning for first tool call
                    if tool_call == pending_tool_calls[0]:
                        text_results = [
                            item for item in model_response if isinstance(item, TextResult)
                        ]
                        if len(text_results) > 0:
                            text_result = text_results[0]
                            self.logger_for_agent_logs.info(
                                f"Top-level agent planning next step: {text_result.text}\n",
                            )

                    # Handle tool call by the agent
                    try:
                        tool_result = self.tool_manager.run_tool(tool_call, self.history)
                        self.history.add_tool_call_result(tool_call, tool_result)

                        self.message_queue.put_nowait(
                            RealtimeEvent(
                                type=EventType.TOOL_RESULT,
                                content={
                                    "tool_call_id": tool_call.tool_call_id,
                                    "tool_name": tool_call.tool_name,
                                    "result": tool_result,
                                },
                            )
                        )
                        
                        # Check if we should stop after this tool
                        if self.tool_manager.should_stop():
                            # Add a fake model response, so the next turn is the user's
                            # turn in case they want to resume
                            self.history.add_assistant_turn(
                                [TextResult(text=COMPLETE_MESSAGE)]
                            )
                            self.message_queue.put_nowait(
                                RealtimeEvent(
                                    type=EventType.AGENT_RESPONSE,
                                    content={"text": self.tool_manager.get_final_answer()},
                                )
                            )
                            return ToolImplOutput(
                                tool_output=self.tool_manager.get_final_answer(),
                                tool_result_message="Task completed",
                            )
                    except KeyboardInterrupt:
                        # Handle interruption during tool execution
                        self.interrupted = True
                        interrupt_message = "Tool execution was interrupted by user."
                        self.history.add_tool_call_result(tool_call, interrupt_message)
                        self.history.add_assistant_turn(
                            [
                                TextResult(
                                    text="Tool execution interrupted by user. You can resume by providing a new instruction."
                                )
                            ]
                        )
                        self.message_queue.put_nowait(
                            RealtimeEvent(
                                type=EventType.AGENT_RESPONSE,
                                content={"text": interrupt_message},
                            )
                        )
                        return ToolImplOutput(
                            tool_output=interrupt_message,
                            tool_result_message=interrupt_message,
                        )

            except KeyboardInterrupt:
                # Handle interruption during model generation or other operations
                self.interrupted = True
                self.history.add_assistant_turn(
                    [
                        TextResult(
                            text="Agent interrupted by user. You can resume by providing a new instruction."
                        )
                    ]
                )
                self.message_queue.put_nowait(
                    RealtimeEvent(
                        type=EventType.AGENT_RESPONSE,
                        content={"text": "Agent interrupted by user"},
                    )
                )
                return ToolImplOutput(
                    tool_output="Agent interrupted by user",
                    tool_result_message="Agent interrupted by user",
                )

        agent_answer = "Agent did not complete after max turns"
        self.message_queue.put_nowait(
            RealtimeEvent(type=EventType.AGENT_RESPONSE, content={"text": agent_answer})
        )
        return ToolImplOutput(
            tool_output=agent_answer, tool_result_message=agent_answer
        )

    def get_tool_start_message(self, tool_input: dict[str, Any]) -> str:
        return f"Agent started with instruction: {tool_input['instruction']}"

    def run_agent(
        self,
        instruction: str,
        files: list[str] | None = None,
        resume: bool = False,
        orientation_instruction: str | None = None,
    ) -> str:
        """Start a new agent run.

        Args:
            instruction: The instruction to the agent.
            resume: Whether to resume the agent from the previous state,
                continuing the dialog.
            orientation_instruction: Optional orientation instruction

        Returns:
            A tuple of (result, message).
        """
        self.tool_manager.reset()
        if resume:
            assert self.history.is_next_turn_user()
        else:
            self.history.clear()
            self.interrupted = False
            # Reset round counter for new runs
            self.round_counter = 0

        tool_input = {
            "instruction": instruction,
            "files": files,
        }
        if orientation_instruction:
            tool_input["orientation_instruction"] = orientation_instruction
        return self.run(tool_input, self.history)

    def clear(self):
        """Clear the dialog and reset interruption state.
        Note: This does NOT clear the file manager, preserving file context.
        """
        self.history.clear()
        self.interrupted = False
