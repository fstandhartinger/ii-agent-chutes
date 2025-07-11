"""
Manages WebSocket connections, agent lifecycle, and message processing for the server.
"""
import asyncio
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Any, Optional, Tuple
import time
import os # For os.getenv

import anyio
from fastapi import WebSocket, WebSocketDisconnect

# Imports from original ws_server.py that are relevant here
from ii_agent.core.event import RealtimeEvent, EventType
from ii_agent.db.models import Event as DBEvent # Alias to avoid conflict if EventType.EVENT is used
from ii_agent.utils.constants import SONNET_4, UPLOAD_FOLDER_NAME, PERSISTENT_DATA_ROOT, PERSISTENT_WORKSPACE_ROOT
from utils import parse_common_args, create_workspace_manager_for_connection # Assuming utils.py is in PYTHONPATH
from ii_agent.agents.anthropic_fc import AnthropicFC
from ii_agent.agents.base import BaseAgent
from ii_agent.utils import WorkspaceManager
from ii_agent.llm import get_client
from ii_agent.llm.context_manager.file_based import FileBasedContextManager
from ii_agent.llm.context_manager.standard import StandardContextManager
from ii_agent.llm.token_counter import TokenCounter
from ii_agent.db.manager import DatabaseManager
from ii_agent.tools import get_system_tools
from ii_agent.prompts.system_prompt import SYSTEM_PROMPT
from ii_agent.utils.pro_utils import extract_pro_key_from_query


from .config import app_config # Relative import

logger = logging.getLogger(__name__)

# Constants from original ws_server.py
MAX_OUTPUT_TOKENS_PER_TURN = 32768 # Or get from config if it becomes configurable
MAX_TURNS = 200 # Or get from config

# WebSocket connection management
active_connections: Set[WebSocket] = set()
connection_timestamps: Dict[WebSocket, datetime] = {}
MAX_CONCURRENT_CONNECTIONS = 500 # Or get from config
active_agents: Dict[WebSocket, BaseAgent] = {}
active_tasks: Dict[WebSocket, asyncio.Task] = {} # For agent query tasks
message_processors: Dict[WebSocket, asyncio.Task] = {} # For agent's internal message processing loop

# This task will be started by the main app's startup event
periodic_cleanup_task: Optional[asyncio.Task] = None


async def safe_websocket_send_json(websocket: WebSocket, data: dict, connection_id: Optional[str] = None) -> bool:
    """
    Safely send JSON data over WebSocket with proper error handling.
    Returns True if sent successfully, False otherwise.
    """
    if not connection_id:
        connection_id = str(id(websocket))
    
    try:
        # Check if WebSocket is still in a sendable state
        if websocket.client_state.name == "DISCONNECTED":
            logger.debug(f"WS_SAFE_SEND ({connection_id}): WebSocket already disconnected, skipping send.")
            return False
        
        await websocket.send_json(data)
        return True
        
    except RuntimeError as e:
        if "Cannot call \"send\" once a close message has been sent" in str(e):
            logger.debug(f"WS_SAFE_SEND ({connection_id}): WebSocket already closed, skipping send.")
        else:
            logger.warning(f"WS_SAFE_SEND ({connection_id}): RuntimeError sending message: {e}")
        return False
        
    except Exception as e:
        logger.error(f"WS_SAFE_SEND ({connection_id}): Error sending WebSocket message: {e}")
        return False


def cleanup_connection(websocket: WebSocket):
    """Clean up resources associated with a websocket connection."""
    connection_id = id(websocket)
    logger.info(f"WS_CLEANUP ({connection_id}): Starting cleanup.")
    try:
        if websocket in active_connections:
            active_connections.remove(websocket)
            logger.info(f"WS_CLEANUP ({connection_id}): Removed from active_connections.")
        if websocket in connection_timestamps:
            del connection_timestamps[websocket]
            logger.info(f"WS_CLEANUP ({connection_id}): Removed from connection_timestamps.")

        if websocket in active_tasks:
            task = active_tasks[websocket]
            if not task.done():
                logger.info(f"WS_CLEANUP ({connection_id}): Cancelling active query task.")
                task.cancel()
            del active_tasks[websocket]
            logger.info(f"WS_CLEANUP ({connection_id}): Removed from active_tasks.")

        if websocket in message_processors:
            processor = message_processors[websocket]
            if not processor.done():
                logger.info(f"WS_CLEANUP ({connection_id}): Cancelling message processor task.")
                processor.cancel()
            del message_processors[websocket]
            logger.info(f"WS_CLEANUP ({connection_id}): Removed from message_processors.")

        if websocket in active_agents:
            agent = active_agents[websocket]
            logger.info(f"WS_CLEANUP ({connection_id}): Cleaning up agent {type(agent).__name__}.")
            try:
                agent.websocket = None # Prevent further sends
                if hasattr(agent, 'cleanup'): # If agent has a specific cleanup method
                    agent.cleanup()
                    logger.info(f"WS_CLEANUP ({connection_id}): Agent's custom cleanup called.")
            except Exception as e_agent_cleanup:
                logger.error(f"WS_CLEANUP ({connection_id}): Error during agent resource cleanup: {e_agent_cleanup}", exc_info=True)
            del active_agents[websocket]
            logger.info(f"WS_CLEANUP ({connection_id}): Removed from active_agents.")

        # Attempt to close WebSocket if not already disconnected
        # This part can be tricky as the state might be hard to determine reliably
        # and closing an already closed/broken socket can raise exceptions.
        try:
            if websocket.client_state.name != "DISCONNECTED": # Check if client_state exists and is not DISCONNECTED
                logger.info(f"WS_CLEANUP ({connection_id}): WebSocket state is {websocket.client_state.name}. Attempting to close.")
                # Schedule close, don't await, as it might hang if client is unresponsive
                asyncio.create_task(websocket.close(code=1001)) # 1001: Going Away
            else:
                logger.info(f"WS_CLEANUP ({connection_id}): WebSocket already in DISCONNECTED state.")
        except AttributeError: # websocket.client_state might not exist if connection broke abruptly
            logger.warning(f"WS_CLEANUP ({connection_id}): WebSocket client_state attribute not found, cannot check state for close.")
        except RuntimeError as e_runtime_close: # E.g., "Cannot call 'close' once a close frame has been sent/received."
            logger.warning(f"WS_CLEANUP ({connection_id}): Runtime error attempting to close WebSocket (likely already closing/closed): {e_runtime_close}")
        except Exception as e_close:
            logger.error(f"WS_CLEANUP ({connection_id}): Error force closing WebSocket: {e_close}", exc_info=True)
        
        logger.info(f"WS_CLEANUP ({connection_id}): Cleanup completed. Active connections: {len(active_connections)}")

    except Exception as e:
        logger.error(f"WS_CLEANUP ({connection_id}): General error during connection cleanup: {e}", exc_info=True)


async def run_agent_async(
    websocket: WebSocket, user_input: str, resume: bool = False, files: List[str] = []
):
    """Run the agent asynchronously and send results back to the websocket."""
    agent = active_agents.get(websocket)
    connection_id = id(websocket)

    if not agent:
        logger.error(f"AGENT_RUN ({connection_id}): Agent not initialized for this connection.")
        await safe_websocket_send_json(
            websocket,
            RealtimeEvent(
                type=EventType.ERROR,
                content={"message": "Agent not initialized for this connection", "error_code": "AGENT_NOT_INITIALIZED"},
            ).model_dump(),
            str(connection_id)
        )
        return

    logger.info(f"AGENT_RUN ({connection_id}): Starting agent run. Input: '{user_input[:50]}...', Resume: {resume}, Files: {len(files)}")
    try:
        # Add user message to the agent's internal queue (which should handle DB persistence)
        if agent.message_queue: # Check if queue exists
            agent.message_queue.put_nowait(
                RealtimeEvent(type=EventType.USER_MESSAGE, content={"text": user_input, "files": files}) # Include files in user message
            )
        else:
            logger.warning(f"AGENT_RUN ({connection_id}): Agent message_queue not found. User message not queued for DB.")

        # Run the agent's main processing logic
        await anyio.to_thread.run_sync(agent.run_agent, user_input, files, resume)
        logger.info(f"AGENT_RUN ({connection_id}): Agent run completed for input: '{user_input[:50]}...'")

    except asyncio.CancelledError:
        logger.info(f"AGENT_RUN ({connection_id}): Agent task was cancelled for input: '{user_input[:50]}...'")
        await safe_websocket_send_json(
            websocket,
            RealtimeEvent(
                type=EventType.SYSTEM, # Or a more specific CANCELED type
                content={"message": "Processing was canceled by the user."},
            ).model_dump(),
            str(connection_id)
        )
    except Exception as e:
        logger.error(f"AGENT_RUN ({connection_id}): Error running agent: {str(e)}", exc_info=True)
        await safe_websocket_send_json(
            websocket,
            RealtimeEvent(
                type=EventType.ERROR,
                content={"message": f"Error running agent: {str(e)}", "error_code": "AGENT_RUNTIME_ERROR"},
            ).model_dump(),
            str(connection_id)
        )
    finally:
        if websocket in active_tasks: # Clean up task reference if it's this one
            del active_tasks[websocket]
            logger.debug(f"AGENT_RUN ({connection_id}): Removed task from active_tasks.")


def create_agent_for_connection(
    session_uuid: uuid.UUID, # Changed from session_id to session_uuid for clarity
    workspace_manager: WorkspaceManager,
    websocket: WebSocket,
    tool_args: Dict[str, Any],
):
    """Create a new agent instance for a websocket connection."""
    current_app_args = app_config.get_args()
    if not current_app_args:
        # This should ideally not happen if app is configured correctly at startup
        logger.error("AGENT_CREATE: Application arguments not set. Cannot create agent.")
        raise ValueError("Application configuration (args) not available.")

    connection_id = id(websocket)
    device_id = websocket.query_params.get("device_id", "unknown_device")
    use_chutes_str = websocket.query_params.get("use_chutes", "false")
    use_chutes = use_chutes_str.lower() == "true"
    
    use_openrouter_str = websocket.query_params.get("use_openrouter", "false")
    use_openrouter = use_openrouter_str.lower() == "true"
    
    use_moonshot_str = websocket.query_params.get("use_moonshot", "false")
    use_moonshot = use_moonshot_str.lower() == "true"

    use_native_tool_calling_str = websocket.query_params.get("use_native_tool_calling", "false")
    use_native_tool_calling = use_native_tool_calling_str.lower() == "true"
    
    model_id_param = websocket.query_params.get("model_id", SONNET_4) # Use constant default

    pro_key = extract_pro_key_from_query(dict(websocket.query_params))
    has_pro_access = pro_key is not None
    
    # Model selection logic
    anthropic_models = ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229", "claude-3-haiku-20240307", "claude-sonnet-4-0", "claude-opus-4-0"]
    moonshot_models = ["kimi-k2"]
    is_anthropic_model_selected = model_id_param in anthropic_models
    is_moonshot_model_selected = model_id_param in moonshot_models
    
    # Determine provider and final model_id
    llm_provider_type = "anthropic-direct" # Default
    final_model_id = model_id_param

    if model_id_param in ["claude-sonnet-4-0", "claude-opus-4-0"] and not has_pro_access:
        logger.warning(f"AGENT_CREATE ({connection_id}): Premium model ({model_id_param}) access denied for non-Pro user. Falling back to Chutes/DeepSeek.")
        final_model_id = "deepseek-ai/DeepSeek-V3-0324" # Fallback model
        llm_provider_type = "chutes-openai" # Fallback provider
        # Ensure native tool calling is sensible for fallback
        # use_native_tool_calling might need to be re-evaluated if fallback model doesn't support it well
    elif use_chutes:
        llm_provider_type = "chutes-openai"
        # final_model_id is already model_id_param
    elif use_openrouter:
        llm_provider_type = "openrouter-openai"
        # final_model_id is already model_id_param
    elif use_moonshot or is_moonshot_model_selected:
        llm_provider_type = "moonshot-direct"
        # For Moonshot, we use the default model they specify
        final_model_id = "claude-opus-4-20250514"  # Default model as specified by user
    elif is_anthropic_model_selected:
        llm_provider_type = "anthropic-direct"
        # final_model_id is already model_id_param
    else: # Default case if no specific flags and not an anthropic model by id
        logger.info(f"AGENT_CREATE ({connection_id}): Defaulting to Chutes provider for model '{model_id_param}'.")
        llm_provider_type = "chutes-openai" # Or some other sensible default provider for unknown models
        final_model_id = model_id_param # Keep the user's model_id if possible

    # Setup agent-specific logger
    agent_logger = logging.getLogger(f"agent_logs_{connection_id}")
    agent_logger.setLevel(logging.DEBUG if not current_app_args.minimize_stdout_logs else logging.INFO)
    agent_logger.propagate = False # Avoid duplicate logs to root
    if not agent_logger.handlers:
        if hasattr(current_app_args, 'logs_path') and current_app_args.logs_path:
            try:
                # Ensure log directory exists
                log_file_path_obj = Path(current_app_args.logs_path)
                log_file_path_obj.parent.mkdir(parents=True, exist_ok=True)
                agent_logger.addHandler(logging.FileHandler(current_app_args.logs_path))
            except Exception as e_log_handler:
                logger.error(f"AGENT_CREATE ({connection_id}): Failed to set up file handler for agent logger at {current_app_args.logs_path}: {e_log_handler}")
        if not current_app_args.minimize_stdout_logs:
            agent_logger.addHandler(logging.StreamHandler()) # Add console output if not minimized

    agent_logger.info(f"AGENT_CREATE ({connection_id}): Initializing agent. Provider: {llm_provider_type}, Model: {final_model_id}, Native Tools: {use_native_tool_calling}, Pro: {has_pro_access}")

    db_manager = DatabaseManager()
    # The session_uuid passed in is the one generated by create_workspace_manager_for_connection
    # This should be used to create/retrieve the DB session record.
    actual_db_session_id, actual_workspace_path = db_manager.create_session(
        session_uuid=session_uuid, # This is the key link
        workspace_path=workspace_manager.root, # workspace_manager.root should be correct
        device_id=device_id,
    )
    agent_logger.info(f"AGENT_CREATE ({connection_id}): DB Session ID: {actual_db_session_id}, Workspace: {actual_workspace_path}")

    client_params = {
        "model_name": final_model_id,
        "use_caching": getattr(current_app_args, 'use_caching', False), # Default to False if not in args
    }
    if llm_provider_type == "anthropic-direct":
        client_params.update({
            "project_id": getattr(current_app_args, 'project_id', None),
            "region": getattr(current_app_args, 'region', None),
        })
    elif llm_provider_type == "chutes-openai":
        client_params["use_native_tool_calling"] = use_native_tool_calling
    
    llm_client = get_client(llm_provider_type, **client_params)
    token_counter = TokenCounter() # Assuming default initialization

    context_manager_type = getattr(current_app_args, 'context_manager', "standard")
    if context_manager_type == "file-based":
        context_manager = FileBasedContextManager(
            workspace_manager=workspace_manager, token_counter=token_counter, logger=agent_logger, token_budget=120_000
        )
    else:
        context_manager = StandardContextManager(
            token_counter=token_counter, logger=agent_logger, token_budget=120_000
        )

    message_relay_queue = asyncio.Queue()
    agent_tools = get_system_tools(
        client=llm_client,
        workspace_manager=workspace_manager,
        message_queue=message_relay_queue,
        container_id=getattr(current_app_args, 'docker_container_id', None),
        ask_user_permission=getattr(current_app_args, 'needs_permission', False),
        tool_args=tool_args,
    )

    agent_instance = AnthropicFC( # Assuming AnthropicFC is the primary agent type
        system_prompt=SYSTEM_PROMPT, # Use imported constant
        client=llm_client,
        tools=agent_tools,
        workspace_manager=workspace_manager,
        message_queue=message_relay_queue,
        logger_for_agent_logs=agent_logger,
        context_manager=context_manager,
        max_output_tokens_per_turn=MAX_OUTPUT_TOKENS_PER_TURN,
        max_turns=MAX_TURNS,
        websocket=websocket,
        session_id=actual_db_session_id, # Use the ID from the database session record
    )
    
    if pro_key:
        agent_instance.pro_key = pro_key
        agent_logger.info(f"AGENT_CREATE ({connection_id}): Pro access enabled for key: {pro_key[:4]}****")

    agent_logger.info(f"AGENT_CREATE ({connection_id}): Agent fully initialized: {type(agent_instance).__name__}")
    return agent_instance


async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time communication with the client."""
    client_ip = websocket.client.host if websocket.client else "unknown_ip"
    connection_id = id(websocket)
    logger.info(f"WS_ENDPOINT ({connection_id}): New connection attempt from {client_ip}.")

    try:
        current_app_args = app_config.get_args()
        if not current_app_args:
            logger.error(f"WS_ENDPOINT ({connection_id}): Server not configured (args missing). Rejecting.")
            await websocket.close(code=1011, reason="Server configuration error") # Internal server error
            return
    except Exception as e:
        logger.error(f"WS_ENDPOINT ({connection_id}): Error getting app config: {e}", exc_info=True)
        try:
            await websocket.close(code=1011, reason="Server configuration error")
        except Exception:
            pass
        return

    if len(active_connections) >= MAX_CONCURRENT_CONNECTIONS:
        logger.warning(f"WS_ENDPOINT ({connection_id}): Connection limit ({MAX_CONCURRENT_CONNECTIONS}) reached. Rejecting.")
        await websocket.close(code=1013, reason="Server overloaded") # Try again later
        return
    
    # Simple periodic cleanup of very old connections if many are active
    if len(active_connections) > 200: # Threshold for this specific check
        logger.info(f"WS_ENDPOINT ({connection_id}): Active connections ({len(active_connections)}) > 200, checking for very old connections.")
        current_time_utc = datetime.utcnow()
        old_connections_to_gc = [
            ws for ws, ts in list(connection_timestamps.items()) # Iterate over a copy
            if (current_time_utc - ts).total_seconds() > 1800 # 30 minutes
        ]
        for ws_old in old_connections_to_gc:
            old_conn_id = id(ws_old)
            logger.info(f"WS_ENDPOINT ({connection_id}): Cleaning up very old connection {old_conn_id} (older than 30 mins).")
            cleanup_connection(ws_old) # This handles internal state
            try:
                await ws_old.close(code=1001, reason="Connection idle too long")
            except Exception: pass # Might already be closed
        if old_connections_to_gc:
            logger.info(f"WS_ENDPOINT ({connection_id}): Cleaned up {len(old_connections_to_gc)} very old connections.")

    heartbeat_task_local = None # Define before try block
    try:
        await websocket.accept()
        active_connections.add(websocket)
        connection_timestamps[websocket] = datetime.utcnow()
        logger.info(f"WS_ENDPOINT ({connection_id}): Connection accepted from {client_ip}. Active: {len(active_connections)}")

        try:
            ws_creation_start_time = time.time()
            # workspace_scope can be 'persistent' or 'session' based on args
            # use_container_workspace also from args
            workspace_manager, session_uuid_for_connection = create_workspace_manager_for_connection(
                workspace_root=current_app_args.workspace, # From global args
                use_container_workspace=current_app_args.use_container_workspace # From global args
            )
            logger.info(f"WS_ENDPOINT ({connection_id}): Workspace manager created in {time.time() - ws_creation_start_time:.3f}s. Session UUID: {session_uuid_for_connection}, Root: {workspace_manager.root}")
        except Exception as e:
            logger.error(f"WS_ENDPOINT ({connection_id}): Error creating workspace manager: {e}", exc_info=True)
            await safe_websocket_send_json(websocket, RealtimeEvent(
                type=EventType.ERROR,
                content={"message": f"Error creating workspace: {str(e)}", "error_code": "WORKSPACE_CREATION_ERROR"}
            ).model_dump(), str(connection_id))
            return

        await safe_websocket_send_json(websocket, RealtimeEvent(
            type=EventType.CONNECTION_ESTABLISHED,
            content={
                "message": "Connected to Agent WebSocket Server",
                "workspace_path": str(workspace_manager.root), # Path of this specific session's workspace
                "connection_id": str(connection_id),
                "session_uuid": str(session_uuid_for_connection), # Send the unique session UUID
                "active_connections": len(active_connections),
                "server_ready": True,
            },
        ).model_dump(), str(connection_id))

        async def heartbeat_sender():
            try:
                while True:
                    await asyncio.sleep(30)
                    if websocket.client_state.name == "DISCONNECTED": 
                        logger.debug(f"WS_HEARTBEAT ({connection_id}): WebSocket disconnected, stopping heartbeat.")
                        break
                    # FastAPI WebSocket doesn't have a ping method, so we send a custom ping message
                    success = await safe_websocket_send_json(websocket, RealtimeEvent(
                        type=EventType.HEARTBEAT,
                        content={}
                    ).model_dump(), str(connection_id))
                    if not success:
                        logger.debug(f"WS_HEARTBEAT ({connection_id}): Failed to send heartbeat, stopping.")
                        break
            except asyncio.CancelledError:
                logger.debug(f"WS_HEARTBEAT ({connection_id}): Cancelled.")
            except Exception as e_hb: # Catch errors during ping
                logger.warning(f"WS_HEARTBEAT ({connection_id}): Error sending heartbeat: {e_hb}. Stopping heartbeat.")
                # Don't call cleanup_connection here as it creates race conditions
                # Just stop the heartbeat and let the main loop handle cleanup

        heartbeat_task_local = asyncio.create_task(heartbeat_sender())

        while True:
            try:
                raw_data = await asyncio.wait_for(websocket.receive_text(), timeout=300.0) # 5 min read timeout
                logger.debug(f"WS_RECEIVE ({connection_id}): Received raw data (len: {len(raw_data)}): {raw_data[:100]}...")
            except asyncio.TimeoutError:
                logger.warning(f"WS_RECEIVE ({connection_id}): Timeout waiting for message. Closing.")
                break # Goes to finally, then cleanup
            except WebSocketDisconnect as e_disconnect: # Handle explicit disconnect type
                logger.info(f"WS_RECEIVE ({connection_id}): WebSocketDisconnect received (code: {e_disconnect.code}, reason: '{e_disconnect.reason}').")
                break # Goes to finally, then cleanup
            except Exception as e_recv: # Other receive errors
                logger.error(f"WS_RECEIVE ({connection_id}): Error receiving message: {e_recv}. State: {websocket.client_state.name if hasattr(websocket, 'client_state') else 'unknown'}", exc_info=True)
                break # Goes to finally, then cleanup
            
            try:
                message_json = json.loads(raw_data)
                msg_type = message_json.get("type")
                content = message_json.get("content", {})
                logger.info(f"WS_PROCESS ({connection_id}): Processing message type '{msg_type}'.")

                if msg_type == EventType.INIT_AGENT.value: # Compare with Enum.value
                    if websocket in active_agents:
                        logger.warning(f"WS_PROCESS ({connection_id}): Agent already initialized. Re-initializing.")
                        # Potentially clean up old agent before creating new one
                        # For now, overwriting, create_agent_for_connection will make a new one
                    
                    try:
                        tool_args_param = content.get("tool_args", {})
                        logger.info(f"WS_PROCESS ({connection_id}): Creating agent with tool_args: {tool_args_param}")
                        
                        agent = create_agent_for_connection(
                            session_uuid_for_connection, workspace_manager, websocket, tool_args_param
                        )
                        logger.info(f"WS_PROCESS ({connection_id}): Agent created successfully")
                        
                        active_agents[websocket] = agent
                        logger.info(f"WS_PROCESS ({connection_id}): Agent added to active_agents")
                        
                        message_processors[websocket] = agent.start_message_processing() # Start agent's internal queue processor
                        logger.info(f"WS_PROCESS ({connection_id}): Message processor started")
                        
                        await safe_websocket_send_json(websocket, RealtimeEvent(
                            type=EventType.AGENT_INITIALIZED,
                            content={"message": "Agent initialized", "server_ready": True} # server_ready might be redundant here
                        ).model_dump(), str(connection_id))
                        logger.info(f"WS_PROCESS ({connection_id}): AGENT_INITIALIZED response sent")
                        
                    except Exception as e_init_agent:
                        logger.error(f"WS_PROCESS ({connection_id}): Error during INIT_AGENT processing: {e_init_agent}", exc_info=True)
                        await safe_websocket_send_json(websocket, RealtimeEvent(
                            type=EventType.ERROR,
                            content={"message": f"Error initializing agent: {str(e_init_agent)}", "error_code": "AGENT_INIT_ERROR"}
                        ).model_dump(), str(connection_id))
                        continue

                elif msg_type == EventType.WORKSPACE_INFO_REQUEST.value: # Assuming an enum value for this
                    # This provides info about the specific session's workspace
                    await safe_websocket_send_json(websocket, RealtimeEvent(
                        type=EventType.WORKSPACE_INFO,
                        content={
                            "workspace_path": str(workspace_manager.root), # This session's workspace
                            "session_uuid": str(session_uuid_for_connection),
                            "server_ready": True, # General server status
                            "connection_ready": True # This specific connection is ready
                        }
                    ).model_dump(), str(connection_id))
                
                elif msg_type in [EventType.QUERY.value, EventType.USER_MESSAGE.value]:
                    logger.info(f"WS_PROCESS ({connection_id}): Received {msg_type}, treating as QUERY.")
                    if websocket in active_tasks and not active_tasks[websocket].done():
                        logger.warning(f"WS_PROCESS ({connection_id}): Query rejected, another is active.")
                        await safe_websocket_send_json(websocket, RealtimeEvent(
                            type=EventType.ERROR,
                            content={"message": "A query is already being processed", "error_code": "QUERY_IN_PROGRESS"}
                        ).model_dump(), str(connection_id))
                        continue

                    if websocket not in active_agents: # Auto-initialize if not done explicitly
                        logger.info(f"WS_PROCESS ({connection_id}): Agent not initialized. Auto-initializing.")
                        tool_args_for_auto_init = content.get("tool_args", {})
                        agent = create_agent_for_connection(
                            session_uuid_for_connection, workspace_manager, websocket, tool_args_for_auto_init
                        )
                        active_agents[websocket] = agent
                        message_processors[websocket] = agent.start_message_processing()
                        await safe_websocket_send_json(websocket, RealtimeEvent(
                            type=EventType.AGENT_INITIALIZED,
                            content={"message": "Agent auto-initialized", "server_ready": True}
                        ).model_dump(), str(connection_id))
                        await asyncio.sleep(0.1)

                    user_input_text = content.get("text", "")
                    resume_flag = content.get("resume", False)
                    files_list = content.get("files", [])
                    
                    await safe_websocket_send_json(websocket, RealtimeEvent(
                        type=EventType.PROCESSING,
                        content={"message": "Query received, processing started."}
                    ).model_dump(), str(connection_id))

                    agent_task = asyncio.create_task(
                        run_agent_async(websocket, user_input_text, resume_flag, files_list)
                    )
                    active_tasks[websocket] = agent_task
                
                elif msg_type == EventType.CANCEL_PROCESSING.value: # Assuming an enum value
                    if websocket in active_tasks and not active_tasks[websocket].done():
                        logger.info(f"WS_PROCESS ({connection_id}): Cancelling active query task upon user request.")
                        active_tasks[websocket].cancel()
                        # run_agent_async's CancelledError handler will send confirmation
                    else:
                        await safe_websocket_send_json(websocket, RealtimeEvent(
                            type=EventType.ERROR,
                            content={"message": "No active query to cancel", "error_code": "NO_ACTIVE_QUERY"}
                        ).model_dump(), str(connection_id))
                
                elif msg_type == EventType.PING.value: # Simple keep-alive from client
                    await safe_websocket_send_json(websocket, {"type": "pong"}, str(connection_id))

                elif msg_type == EventType.TERMINAL_COMMAND.value:
                    content = message_json.get("content", {})
                    command = content.get("command")
                    if not command:
                        logger.error(f"WS_PROCESS ({connection_id}): No command provided for TERMINAL_COMMAND.")
                        await safe_websocket_send_json(websocket, RealtimeEvent(
                            type=EventType.ERROR,
                            content={"message": "Terminal command is required", "error_code": "MISSING_COMMAND"}
                        ).model_dump(), str(connection_id))
                        continue

                    if websocket not in active_agents:
                        logger.error(f"WS_PROCESS ({connection_id}): Agent not initialized for TERMINAL_COMMAND.")
                        await safe_websocket_send_json(websocket, RealtimeEvent(
                            type=EventType.ERROR,
                            content={"message": "Agent not initialized for terminal commands", "error_code": "AGENT_NOT_INITIALIZED"}
                        ).model_dump(), str(connection_id))
                        continue

                    agent = active_agents[websocket]
                    bash_tool = next((tool for tool in agent.tools if tool.name.lower() == 'bash'), None)

                    if not bash_tool:
                        logger.error(f"WS_PROCESS ({connection_id}): Bash tool not found in agent's tools.")
                        await safe_websocket_send_json(websocket, RealtimeEvent(
                            type=EventType.ERROR,
                            content={"message": "Terminal functionality is not available", "error_code": "BASH_TOOL_UNAVAILABLE"}
                        ).model_dump(), str(connection_id))
                        continue
                    
                    logger.info(f"WS_PROCESS ({connection_id}): Executing terminal command via agent's bash tool: {command}")
                    
                    try:
                        # The tool's run method might be async or sync. We assume it can be awaited.
                        # If run_impl is synchronous, it should be wrapped with to_thread.run_sync
                        # Based on tool definition, it seems to be sync. Let's stick to that.
                        result = await anyio.to_thread.run_sync(
                            bash_tool.run_impl, {"command": command}
                        )
                        
                        output_content = result.output if hasattr(result, 'output') else str(result)
                        
                        await safe_websocket_send_json(websocket, RealtimeEvent(
                            type=EventType.TERMINAL_OUTPUT,
                            content={
                                "command": command,
                                "output": output_content,
                                "success": True # Assuming run_impl would raise exception on failure
                            }
                        ).model_dump(), str(connection_id))
                        
                    except Exception as e_terminal:
                        logger.error(f"WS_PROCESS ({connection_id}): Error executing terminal command '{command}': {e_terminal}", exc_info=True)
                        await safe_websocket_send_json(websocket, RealtimeEvent(
                            type=EventType.TERMINAL_OUTPUT,
                            content={
                                "command": command,
                                "output": f"Error: {str(e_terminal)}",
                                "success": False
                            }
                        ).model_dump(), str(connection_id))

                else:
                    logger.warning(f"WS_PROCESS ({connection_id}): Unknown message type '{msg_type}'.")
                    await safe_websocket_send_json(websocket, RealtimeEvent(
                        type=EventType.ERROR,
                        content={"message": f"Unknown message type: {msg_type}", "error_code": "UNKNOWN_MESSAGE_TYPE"}
                    ).model_dump(), str(connection_id))

            except json.JSONDecodeError:
                logger.error(f"WS_PROCESS ({connection_id}): Invalid JSON received: {raw_data[:200]}...")
                await safe_websocket_send_json(websocket, RealtimeEvent(
                    type=EventType.ERROR, content={"message": "Invalid JSON format", "error_code": "INVALID_JSON"}
                ).model_dump(), str(connection_id))
            except Exception as e_process_msg:
                logger.error(f"WS_PROCESS ({connection_id}): Error processing message: {e_process_msg}", exc_info=True)
                await safe_websocket_send_json(websocket, RealtimeEvent(
                    type=EventType.ERROR, content={"message": f"Error processing request: {str(e_process_msg)}", "error_code": "MESSAGE_PROCESSING_ERROR"}
                ).model_dump(), str(connection_id))

    except WebSocketDisconnect as e_main_disconnect: # Catch disconnect at the outer loop too
        logger.info(f"WS_ENDPOINT ({connection_id}): WebSocket disconnected (code: {e_main_disconnect.code}, reason: '{e_main_disconnect.reason}') from {client_ip}.")
    except Exception as e_main:
        logger.error(f"WS_ENDPOINT ({connection_id}): Unhandled WebSocket error from {client_ip}: {e_main}", exc_info=True)
        # Try to close gracefully if possible
        try:
            if websocket.client_state.name != "DISCONNECTED":
                await websocket.close(code=1011) # Internal server error
        except Exception: pass # Ignore errors during this emergency close
    finally:
        logger.info(f"WS_ENDPOINT ({connection_id}): Finalizing connection from {client_ip}.")
        if heartbeat_task_local and not heartbeat_task_local.done():
            heartbeat_task_local.cancel()
            logger.debug(f"WS_ENDPOINT ({connection_id}): Heartbeat task cancelled.")
        cleanup_connection(websocket) # Ensure cleanup is always called


async def periodic_connection_cleanup_task():
    """Periodically cleans up stale WebSocket connections."""
    logger.info("PERIODIC_CLEANUP_TASK: Started.")
    while True:
        await asyncio.sleep(60) # Run every minute
        logger.debug(f"PERIODIC_CLEANUP_TASK: Running check. Active connections: {len(active_connections)}")
        
        stale_ws_connections = []
        current_time_utc = datetime.utcnow()

        # Iterate over a copy of active_connections set for safe removal
        for ws_conn in list(active_connections):
            conn_id = id(ws_conn)
            try:
                # Check 1: WebSocket state is DISCONNECTED (e.g., client closed abruptly)
                if ws_conn.client_state.name == "DISCONNECTED":
                    logger.info(f"PERIODIC_CLEANUP_TASK: Found stale connection {conn_id} (state: DISCONNECTED).")
                    stale_ws_connections.append(ws_conn)
                    continue # Move to next connection

                # Check 2: Connection is very old (e.g., > 1 hour) - a safety net
                if ws_conn in connection_timestamps:
                    age_seconds = (current_time_utc - connection_timestamps[ws_conn]).total_seconds()
                    if age_seconds > 3600: # 1 hour
                        logger.info(f"PERIODIC_CLEANUP_TASK: Found very old connection {conn_id} (age: {age_seconds/60:.1f} mins). Marking for cleanup.")
                        stale_ws_connections.append(ws_conn)
                        # Try to close it politely first
                        try: await ws_conn.close(code=1001, reason="Extended inactivity")
                        except: pass
                
                # Check 3: Ping failure might have already triggered cleanup, but double check if task is still there but agent gone
                if ws_conn not in active_agents and ws_conn not in active_tasks:
                    logger.info(f"PERIODIC_CLEANUP_TASK: Found connection {conn_id} with no associated agent or task. Marking for cleanup.")
                    stale_ws_connections.append(ws_conn)


            except AttributeError: # client_state might not exist if connection broke very badly
                 logger.warning(f"PERIODIC_CLEANUP_TASK: Connection {conn_id} missing client_state, likely broken. Marking stale.")
                 stale_ws_connections.append(ws_conn)
            except Exception as e_check: # Catch-all for errors during check phase for a single connection
                logger.error(f"PERIODIC_CLEANUP_TASK: Error checking connection {conn_id}: {e_check}. Marking stale as precaution.", exc_info=True)
                stale_ws_connections.append(ws_conn)
        
        if stale_ws_connections:
            logger.info(f"PERIODIC_CLEANUP_TASK: Found {len(stale_ws_connections)} stale connections to process.")
            for ws_stale in stale_ws_connections:
                stale_id = id(ws_stale)
                logger.info(f"PERIODIC_CLEANUP_TASK: Processing cleanup for stale connection {stale_id}.")
                cleanup_connection(ws_stale) # This handles all internal state removal
                # The close attempt is now part of cleanup_connection or handled by WebSocketDisconnect
            logger.info(f"PERIODIC_CLEANUP_TASK: Finished processing stale connections. Active now: {len(active_connections)}")
        else:
            logger.debug("PERIODIC_CLEANUP_TASK: No stale connections found in this cycle.")

def start_periodic_cleanup():
    """Starts the periodic cleanup task."""
    global periodic_cleanup_task
    if periodic_cleanup_task is None or periodic_cleanup_task.done():
        periodic_cleanup_task = asyncio.create_task(periodic_connection_cleanup_task())
        logger.info("Periodic connection cleanup task started.")
    else:
        logger.info("Periodic connection cleanup task already running.")

def stop_periodic_cleanup():
    """Stops the periodic cleanup task if running."""
    global periodic_cleanup_task
    if periodic_cleanup_task and not periodic_cleanup_task.done():
        periodic_cleanup_task.cancel()
        logger.info("Periodic connection cleanup task cancellation requested.")
        periodic_cleanup_task = None
    else:
        logger.info("Periodic connection cleanup task not running or already stopped.")
