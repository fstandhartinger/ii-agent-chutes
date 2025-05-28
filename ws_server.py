#!/usr/bin/env python3
"""
FastAPI WebSocket Server for the Agent.

This script provides a WebSocket interface for interacting with the Agent,
allowing real-time communication with a frontend application.
"""

import os
import argparse
import asyncio
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Any, Optional, Tuple
from dotenv import load_dotenv

load_dotenv()

import uvicorn
from fastapi import (
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
    Request,
    HTTPException,
    Header,
    Depends,
)

from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import anyio
import base64
import shutil
from sqlalchemy import asc, text

from ii_agent.core.event import RealtimeEvent, EventType
from ii_agent.db.models import Event
from ii_agent.utils.constants import DEFAULT_MODEL, UPLOAD_FOLDER_NAME, PERSISTENT_DATA_ROOT, PERSISTENT_WORKSPACE_ROOT
from utils import parse_common_args, create_workspace_manager_for_connection, get_persistent_path
from ii_agent.agents.anthropic_fc import AnthropicFC
from ii_agent.agents.base import BaseAgent
from ii_agent.utils import WorkspaceManager
from ii_agent.llm import get_client

from fastapi.staticfiles import StaticFiles

from ii_agent.llm.context_manager.file_based import FileBasedContextManager
from ii_agent.llm.context_manager.standard import StandardContextManager
from ii_agent.llm.token_counter import TokenCounter
from ii_agent.db.manager import DatabaseManager
from ii_agent.tools import get_system_tools
from ii_agent.prompts.system_prompt import SYSTEM_PROMPT

import zipfile
import tempfile
from urllib.parse import quote
import subprocess
import requests
import time

MAX_OUTPUT_TOKENS_PER_TURN = 32768
MAX_TURNS = 200

# Set up Playwright browsers path if persistent storage is available
persistent_playwright = Path("/var/data/playwright")
if persistent_playwright.exists():
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(persistent_playwright)
    print(f"Using persistent Playwright browsers at {persistent_playwright}")

app = FastAPI(title="Agent WebSocket API")

# Add CORS middleware with explicit configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"],
    allow_headers=["*"],  # Allows all headers
    expose_headers=["*"],  # Expose all headers to the client
)

# Add explicit OPTIONS handler for additional CORS support
@app.options("/{full_path:path}")
async def options_handler(request: Request):
    """Handle preflight OPTIONS requests for CORS."""
    headers = CORS_HEADERS.copy()
    headers["Access-Control-Max-Age"] = "86400"
    return JSONResponse(content={}, headers=headers)


# Create a logger
logger = logging.getLogger("websocket_server")
logger.setLevel(logging.INFO)

# CORS headers for API responses
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, HEAD, PATCH",
    "Access-Control-Allow-Headers": "*",
}

def create_cors_response(content: dict, status_code: int = 200):
    """Create a JSONResponse with CORS headers."""
    return JSONResponse(
        content=content,
        status_code=status_code,
        headers=CORS_HEADERS
    )

# Active WebSocket connections
active_connections: Set[WebSocket] = set()

# Connection limit to prevent resource exhaustion
MAX_CONCURRENT_CONNECTIONS = 50

# Active agents for each connection
active_agents: Dict[WebSocket, BaseAgent] = {}

# Active agent tasks
active_tasks: Dict[WebSocket, asyncio.Task] = {}

# Store message processors for each connection
message_processors: Dict[WebSocket, asyncio.Task] = {}

# Store global args for use in endpoint
global_args = None


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time communication with the client."""
    client_ip = websocket.client.host if websocket.client else "unknown"
    connection_id = id(websocket)
    
    logger.info(f"BACKEND_WS_DEBUG: New WebSocket connection attempt from {client_ip}, connection_id: {connection_id}")
    
    # Check connection limit before accepting
    if len(active_connections) >= MAX_CONCURRENT_CONNECTIONS:
        logger.warning(f"BACKEND_WS_DEBUG: Connection limit reached ({MAX_CONCURRENT_CONNECTIONS}). Rejecting new connection from {client_ip}")
        await websocket.close(code=1013, reason="Server overloaded - too many concurrent connections")
        return
    
    try:
        await websocket.accept()
        active_connections.add(websocket)
        logger.info(f"BACKEND_WS_DEBUG: WebSocket connection {connection_id} accepted from {client_ip}. Active connections: {len(active_connections)}")

        # Measure workspace creation time
        start_time = time.time()
        
        workspace_manager, session_uuid = create_workspace_manager_for_connection(
            global_args.workspace, global_args.use_container_workspace
        )
        
        workspace_creation_time = time.time() - start_time
        logger.info(f"BACKEND_WS_DEBUG: Workspace manager created for connection {connection_id} in {workspace_creation_time:.3f} seconds: {workspace_manager}")

        # Check if we should use Chutes LLM instead of Anthropic
        use_chutes = websocket.query_params.get("use_chutes", "false").lower() == "true"
        use_openrouter = websocket.query_params.get("use_openrouter", "false").lower() == "true"
        use_native_tool_calling = websocket.query_params.get("use_native_tool_calling", "false").lower() == "true"
        model_id = websocket.query_params.get("model_id", "deepseek-ai/DeepSeek-V3-0324")
        
        logger.info(f"BACKEND_WS_DEBUG: Connection {connection_id} - use_chutes: {use_chutes}, model_id: {model_id}, device_id: {websocket.query_params.get('device_id', 'unknown')}")
        
        # Initial connection message with session info
        connection_response = RealtimeEvent(
            type=EventType.CONNECTION_ESTABLISHED,
            content={
                "message": "Connected to Agent WebSocket Server",
                "workspace_path": str(workspace_manager.root),
                "connection_id": str(connection_id),
                "active_connections": len(active_connections),
                "server_ready": True,
            },
        )
        logger.info(f"BACKEND_WS_DEBUG: Sending connection established message to {connection_id}")
        await websocket.send_json(connection_response.model_dump())

        # Start heartbeat task to keep connection alive
        async def heartbeat():
            try:
                while True:
                    await asyncio.sleep(30)  # Send ping every 30 seconds
                    if websocket.client_state.name == "DISCONNECTED":
                        break
                    try:
                        await websocket.ping()
                        logger.debug(f"BACKEND_WS_DEBUG: Sent ping to connection {connection_id}")
                    except Exception as e:
                        logger.debug(f"BACKEND_WS_DEBUG: Failed to ping connection {connection_id}: {e}")
                        break
            except asyncio.CancelledError:
                logger.debug(f"BACKEND_WS_DEBUG: Heartbeat cancelled for connection {connection_id}")
        
        heartbeat_task = asyncio.create_task(heartbeat())

        # Process messages from the client
        while True:
            try:
                # Add timeout to prevent hanging connections
                logger.debug(f"BACKEND_WS_DEBUG: Waiting for message from connection {connection_id}")
                data = await asyncio.wait_for(websocket.receive_text(), timeout=300.0)  # 5 minute timeout
                logger.info(f"BACKEND_WS_DEBUG: Received message from {connection_id}: {data[:100]}...")
            except asyncio.TimeoutError:
                logger.warning(f"BACKEND_WS_DEBUG: WebSocket timeout for connection {connection_id} from {client_ip}. Active connections: {len(active_connections)}")
                break
            except Exception as e:
                # Improved error handling for different disconnect types
                error_str = str(e)
                
                # Check for normal disconnect codes
                if "(1001," in error_str:  # Going away (normal browser close/refresh)
                    logger.info(f"BACKEND_WS_DEBUG: Client {connection_id} ({client_ip}) closed connection normally (going away). Active connections: {len(active_connections)}")
                elif "(1000," in error_str:  # Normal closure
                    logger.info(f"BACKEND_WS_DEBUG: Client {connection_id} ({client_ip}) closed connection normally. Active connections: {len(active_connections)}")
                elif "1006" in error_str:  # Abnormal closure - this needs attention
                    logger.warning(f"BACKEND_WS_DEBUG: Abnormal connection closure for {connection_id} ({client_ip}): {e}. This may indicate network issues or proxy timeouts. Active connections: {len(active_connections)}")
                else:
                    logger.error(f"BACKEND_WS_DEBUG: Error receiving WebSocket message from connection {connection_id} ({client_ip}): {e}. Connection state: {websocket.client_state.name if hasattr(websocket, 'client_state') else 'unknown'}")
                break
                
            try:
                message = json.loads(data)
                msg_type = message.get("type")
                content = message.get("content", {})
                
                logger.info(f"BACKEND_WS_DEBUG: Processing message type '{msg_type}' from connection {connection_id}")

                if msg_type == "init_agent":
                    logger.info(f"BACKEND_WS_DEBUG: Initializing agent for connection {connection_id}")
                    # Create a new agent for this connection
                    tool_args = content.get("tool_args", {})
                    agent = create_agent_for_connection(
                        session_uuid, workspace_manager, websocket, tool_args
                    )
                    active_agents[websocket] = agent

                    # Start message processor for this connection
                    message_processor = agent.start_message_processing()
                    message_processors[websocket] = message_processor
                    
                    agent_init_response = RealtimeEvent(
                        type=EventType.AGENT_INITIALIZED,
                        content={"message": "Agent initialized", "server_ready": True},
                    )
                    logger.info(f"BACKEND_WS_DEBUG: Agent initialized for connection {connection_id}, sending confirmation")
                    await websocket.send_json(agent_init_response.model_dump())

                elif msg_type == "query":
                    # Check if there's an active task for this connection
                    if websocket in active_tasks and not active_tasks[websocket].done():
                        logger.warning(f"BACKEND_WS_DEBUG: Query rejected for connection {connection_id}: already processing a query")
                        await websocket.send_json(
                            RealtimeEvent(
                                type=EventType.ERROR,
                                content={
                                    "message": "A query is already being processed",
                                    "error_code": "QUERY_IN_PROGRESS", 
                                    "user_friendly": "Please wait for the current request to complete before sending a new one."
                                },
                            ).model_dump()
                        )
                        continue

                    # Check if agent is initialized for this connection
                    if websocket not in active_agents:
                        logger.warning(f"BACKEND_WS_DEBUG: Query received for connection {connection_id} but agent not initialized. Auto-initializing...")
                        # Auto-initialize agent if not present
                        agent = create_agent_for_connection(
                            session_uuid, workspace_manager, websocket, {}
                        )
                        active_agents[websocket] = agent
                        
                        message_processor = agent.start_message_processing()
                        message_processors[websocket] = message_processor
                        
                        logger.info(f"BACKEND_WS_DEBUG: Agent auto-initialized for connection {connection_id}")

                    # Process a query to the agent
                    user_input = content.get("text", "")
                    resume = content.get("resume", False)
                    files = content.get("files", [])

                    logger.info(f"BACKEND_WS_DEBUG: Processing query for connection {connection_id}: '{user_input[:100]}{'...' if len(user_input) > 100 else ''}'")

                    # Send acknowledgment
                    await websocket.send_json(
                        RealtimeEvent(
                            type=EventType.PROCESSING,
                            content={"message": "Query received and processing started"},
                        ).model_dump()
                    )

                    # Run the agent in a task to handle potential disconnections
                    task = asyncio.create_task(
                        run_agent_async(websocket, user_input, resume, files)
                    )
                    active_tasks[websocket] = task

                elif msg_type == "workspace_info":
                    logger.info(f"BACKEND_WS_DEBUG: Workspace info request from connection {connection_id}")
                    try:
                        # Ensure workspace is properly initialized before responding
                        if workspace_manager and workspace_manager.root:
                            workspace_info = {
                                "workspace_path": str(workspace_manager.root),
                                "session_id": str(session_uuid),
                                "server_ready": True,
                                "connection_ready": True,
                            }
                            logger.info(f"BACKEND_WS_DEBUG: Sending workspace info to connection {connection_id}: {workspace_info}")
                            await websocket.send_json(
                                RealtimeEvent(
                                    type=EventType.WORKSPACE_INFO,
                                    content=workspace_info,
                                ).model_dump()
                            )
                        else:
                            logger.error(f"BACKEND_WS_DEBUG: Workspace not initialized for connection {connection_id}")
                            await websocket.send_json(
                                RealtimeEvent(
                                    type=EventType.ERROR,
                                    content={
                                        "message": "Workspace not initialized",
                                        "error_code": "WORKSPACE_NOT_INITIALIZED",
                                        "user_friendly": "The workspace is not ready yet. Please try again in a moment."
                                    },
                                ).model_dump()
                            )
                    except Exception as e:
                        logger.error(f"BACKEND_WS_DEBUG: Error handling workspace_info for connection {connection_id}: {e}")
                        await websocket.send_json(
                            RealtimeEvent(
                                type=EventType.ERROR,
                                content={
                                    "message": f"Error getting workspace info: {str(e)}",
                                    "error_code": "WORKSPACE_ERROR",
                                    "user_friendly": "There was an issue with the workspace. Please refresh and try again."
                                },
                            ).model_dump()
                        )

                elif msg_type == "cancel":
                    # Cancel the current agent task if one exists
                    if websocket in active_tasks and not active_tasks[websocket].done():
                        logger.info(f"BACKEND_WS_DEBUG: Cancelling query for connection {connection_id}")
                        active_tasks[websocket].cancel()
                        await websocket.send_json(
                            RealtimeEvent(
                                type=EventType.SYSTEM,
                                content={"message": "Query canceled"},
                            ).model_dump()
                        )
                    else:
                        await websocket.send_json(
                            RealtimeEvent(
                                type=EventType.ERROR,
                                content={
                                    "message": "No active query to cancel",
                                    "error_code": "NO_ACTIVE_QUERY",
                                    "user_friendly": "There is no active request to cancel.",
                                },
                            ).model_dump()
                        )

                elif msg_type == "ping":
                    # Simple ping to keep connection alive
                    await websocket.send_json(
                        RealtimeEvent(type=EventType.PONG, content={}).model_dump()
                    )

                else:
                    # Unknown message type
                    logger.warning(f"BACKEND_WS_DEBUG: Unknown message type '{msg_type}' from connection {connection_id}")
                    await websocket.send_json(
                        RealtimeEvent(
                            type=EventType.ERROR,
                            content={
                                "message": f"Unknown message type: {msg_type}",
                                "error_code": "UNKNOWN_MESSAGE_TYPE",
                                "user_friendly": "The request format was not recognized. Please refresh the page and try again.",
                            },
                        ).model_dump()
                    )

            except json.JSONDecodeError as e:
                logger.error(f"BACKEND_WS_DEBUG: JSON decode error from connection {connection_id}: {e}")
                await websocket.send_json(
                    RealtimeEvent(
                        type=EventType.ERROR, 
                        content={
                            "message": "Invalid JSON format",
                            "error_code": "INVALID_JSON",
                            "user_friendly": "The request format was invalid. Please refresh the page and try again.",
                        }
                    ).model_dump()
                )
            except Exception as e:
                logger.error(f"BACKEND_WS_DEBUG: Error processing message from connection {connection_id}: {str(e)}")
                import traceback
                traceback.print_exc()
                await websocket.send_json(
                    RealtimeEvent(
                        type=EventType.ERROR,
                        content={
                            "message": f"Error processing request: {str(e)}",
                            "error_code": "PROCESSING_ERROR",
                            "user_friendly": "There was an error processing your request. This might be due to high server load. Please try again in a moment.",
                        },
                    ).model_dump()
                )

    except WebSocketDisconnect:
        # Handle disconnection
        logger.info(f"BACKEND_WS_DEBUG: Client {connection_id} ({client_ip}) disconnected normally. Active connections: {len(active_connections) - 1}")
        if 'heartbeat_task' in locals():
            heartbeat_task.cancel()
        cleanup_connection(websocket)
    except Exception as e:
        # Handle other exceptions
        logger.error(f"BACKEND_WS_DEBUG: WebSocket error for connection {connection_id} ({client_ip}): {str(e)}. Active connections: {len(active_connections)}")
        import traceback
        traceback.print_exc()
        if 'heartbeat_task' in locals():
            heartbeat_task.cancel()
        cleanup_connection(websocket)


async def run_agent_async(
    websocket: WebSocket, user_input: str, resume: bool = False, files: List[str] = []
):
    """Run the agent asynchronously and send results back to the websocket."""
    agent = active_agents.get(websocket)

    if not agent:
        await websocket.send_json(
            RealtimeEvent(
                type=EventType.ERROR,
                content={"message": "Agent not initialized for this connection"},
            ).model_dump()
        )
        return

    try:
        # Add user message to the event queue to save to database
        agent.message_queue.put_nowait(
            RealtimeEvent(type=EventType.USER_MESSAGE, content={"text": user_input})
        )
        # Run the agent with the query
        await anyio.to_thread.run_sync(agent.run_agent, user_input, files, resume)

    except Exception as e:
        logger.error(f"BACKEND_WS_DEBUG: Error running agent: {str(e)}")
        import traceback

        traceback.print_exc()
        await websocket.send_json(
            RealtimeEvent(
                type=EventType.ERROR,
                content={"message": f"Error running agent: {str(e)}"},
            ).model_dump()
        )
    finally:
        # Clean up the task reference
        if websocket in active_tasks:
            del active_tasks[websocket]


def cleanup_connection(websocket: WebSocket):
    """Clean up resources associated with a websocket connection."""
    try:
        logger.info(f"BACKEND_WS_DEBUG: Cleaning up connection for websocket {id(websocket)}")
        
        # Remove from active connections
        if websocket in active_connections:
            active_connections.remove(websocket)
            logger.info(f"BACKEND_WS_DEBUG: Removed websocket {id(websocket)} from active connections")

        # Cancel any running tasks first
        if websocket in active_tasks:
            task = active_tasks[websocket]
            if not task.done():
                logger.info(f"BACKEND_WS_DEBUG: Cancelling active task for websocket {id(websocket)}")
                task.cancel()
            del active_tasks[websocket]

        # Handle message processors
        if websocket in message_processors:
            processor = message_processors[websocket]
            if not processor.done():
                logger.info(f"BACKEND_WS_DEBUG: Cancelling message processor for websocket {id(websocket)}")
                processor.cancel()
            del message_processors[websocket]

        # Clean up agent resources
        if websocket in active_agents:
            agent = active_agents[websocket]
            try:
                # Set websocket to None to prevent further sending
                agent.websocket = None
                logger.info(f"BACKEND_WS_DEBUG: Set agent websocket to None for websocket {id(websocket)}")
                
                # Close any open file handles or resources in the agent
                if hasattr(agent, 'cleanup'):
                    agent.cleanup()
                    
            except Exception as e:
                logger.error(f"BACKEND_WS_DEBUG: Error cleaning up agent for websocket {id(websocket)}: {e}")
            
            # Remove agent from active agents
            del active_agents[websocket]
            logger.info(f"BACKEND_WS_DEBUG: Removed agent for websocket {id(websocket)}")

        # Force close the websocket connection if it's still open
        try:
            if websocket.client_state.name != "DISCONNECTED":
                logger.info(f"BACKEND_WS_DEBUG: Force closing websocket {id(websocket)}")
                # Don't await this as it might hang
                asyncio.create_task(websocket.close())
        except Exception as e:
            logger.error(f"BACKEND_WS_DEBUG: Error force closing websocket {id(websocket)}: {e}")

        logger.info(f"BACKEND_WS_DEBUG: Cleanup completed for websocket {id(websocket)}")
        
    except Exception as e:
        logger.error(f"BACKEND_WS_DEBUG: Error during connection cleanup for websocket {id(websocket)}: {e}")
        import traceback
        traceback.print_exc()


def create_agent_for_connection(
    session_id: uuid.UUID,
    workspace_manager: WorkspaceManager,
    websocket: WebSocket,
    tool_args: Dict[str, Any],
):
    """Create a new agent instance for a websocket connection."""
    global global_args
    device_id = websocket.query_params.get("device_id")
    use_chutes = websocket.query_params.get("use_chutes", "false").lower() == "true"
    use_openrouter = websocket.query_params.get("use_openrouter", "false").lower() == "true"
    use_native_tool_calling = websocket.query_params.get("use_native_tool_calling", "false").lower() == "true"
    model_id = websocket.query_params.get("model_id", "deepseek-ai/DeepSeek-V3-0324")
    
    # Check for Pro access
    from ii_agent.utils.pro_utils import extract_pro_key_from_query
    pro_key = extract_pro_key_from_query(dict(websocket.query_params))
    has_pro_access = pro_key is not None
    
    # Check if this is an Anthropic model based on model_id
    anthropic_models = ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229", "claude-3-haiku-20240307", "claude-sonnet-4-20250514"]
    use_anthropic = model_id in anthropic_models and not use_chutes and not use_openrouter
    
    # Check if user is trying to use Sonnet 4 without Pro access
    if model_id == "claude-sonnet-4-20250514" and not has_pro_access:
        logger_for_agent_logs = logging.getLogger(f"agent_logs_{id(websocket)}")
        logger_for_agent_logs.error(f"Access denied: Sonnet 4 requires Pro access. Model ID: {model_id}")
        # Fall back to default model
        model_id = "deepseek-ai/DeepSeek-V3-0324"
        use_anthropic = False
        use_chutes = True
    
    # Setup logging
    logger_for_agent_logs = logging.getLogger(f"agent_logs_{id(websocket)}")
    logger_for_agent_logs.setLevel(logging.DEBUG)
    # Prevent propagation to root logger to avoid duplicate logs
    logger_for_agent_logs.propagate = False

    # Ensure we don't duplicate handlers
    if not logger_for_agent_logs.handlers:
        logger_for_agent_logs.addHandler(logging.FileHandler(global_args.logs_path))
        if not global_args.minimize_stdout_logs:
            logger_for_agent_logs.addHandler(logging.StreamHandler())

    # Initialize database manager
    db_manager = DatabaseManager()

    # Create a new session and get its workspace directory
    db_start_time = time.time()
    
    actual_session_id, actual_workspace_path = db_manager.create_session(
        device_id=device_id,
        session_uuid=session_id,
        workspace_path=workspace_manager.root,
    )
    
    db_creation_time = time.time() - db_start_time
    logger_for_agent_logs.info(
        f"Using session {actual_session_id} with workspace at {actual_workspace_path} (DB operation took {db_creation_time:.3f} seconds)"
    )

    # Initialize LLM client
    if use_anthropic:
        logger_for_agent_logs.info("=========================================")
        logger_for_agent_logs.info("USING ANTHROPIC LLM PROVIDER")
        logger_for_agent_logs.info(f"Model: {model_id}")
        logger_for_agent_logs.info("=========================================")
        client = get_client(
            "anthropic-direct",
            model_name=model_id,
            use_caching=False,
            project_id=global_args.project_id,
            region=global_args.region,
        )
    elif use_chutes:
        logger_for_agent_logs.info("=========================================")
        logger_for_agent_logs.info("USING CHUTES LLM PROVIDER")
        logger_for_agent_logs.info(f"Model: {model_id}")
        if use_native_tool_calling:
            logger_for_agent_logs.info("Native Tool Calling: ENABLED")
        else:
            logger_for_agent_logs.info("Native Tool Calling: DISABLED (using JSON workaround)")
        logger_for_agent_logs.info("=========================================")
        client = get_client(
            "chutes-openai",
            model_name=model_id,
            use_caching=False,
            use_native_tool_calling=use_native_tool_calling,
        )
    elif use_openrouter:
        logger_for_agent_logs.info("=========================================")
        logger_for_agent_logs.info("USING OPENROUTER LLM PROVIDER")
        logger_for_agent_logs.info(f"Model: {model_id}")
        logger_for_agent_logs.info("=========================================")
        client = get_client(
            "openrouter-openai",
            model_name=model_id,
            use_caching=False,
        )
    else:
        # Default to Anthropic if no provider is specified
        logger_for_agent_logs.info("=========================================")
        logger_for_agent_logs.info("USING ANTHROPIC LLM PROVIDER (DEFAULT)")
        logger_for_agent_logs.info(f"Model: {DEFAULT_MODEL}")
        logger_for_agent_logs.info("=========================================")
        client = get_client(
            "anthropic-direct",
            model_name=DEFAULT_MODEL,
            use_caching=False,
            project_id=global_args.project_id,
            region=global_args.region,
        )

    # Initialize token counter
    token_counter = TokenCounter()

    # Create context manager based on argument
    if global_args.context_manager == "file-based":
        context_manager = FileBasedContextManager(
            workspace_manager=workspace_manager,
            token_counter=token_counter,
            logger=logger_for_agent_logs,
            token_budget=120_000,
        )
    else:  # standard
        context_manager = StandardContextManager(
            token_counter=token_counter,
            logger=logger_for_agent_logs,
            token_budget=120_000,
        )

    # Initialize agent with websocket
    queue = asyncio.Queue()
    tools = get_system_tools(
        client=client,
        workspace_manager=workspace_manager,
        message_queue=queue,
        container_id=global_args.docker_container_id,
        ask_user_permission=global_args.needs_permission,
        tool_args=tool_args,
    )
    agent = AnthropicFC(
        system_prompt=SYSTEM_PROMPT,
        client=client,
        tools=tools,
        workspace_manager=workspace_manager,
        message_queue=queue,
        logger_for_agent_logs=logger_for_agent_logs,
        context_manager=context_manager,
        max_output_tokens_per_turn=MAX_OUTPUT_TOKENS_PER_TURN,
        max_turns=MAX_TURNS,
        websocket=websocket,
        session_id=session_id,  # Pass the session_id from database manager
    )

    # Store the session ID in the agent for event tracking
    agent.session_id = session_id
    
    # Store the Pro key in the agent for usage tracking
    if pro_key:
        agent.pro_key = pro_key
        logger_for_agent_logs.info(f"Pro access enabled for key: {pro_key[:4]}****")

    return agent


def setup_workspace(app, workspace_path):
    """Setup workspace directory for static file serving.
    
    Uses persistent storage if available, otherwise falls back to local storage.
    """
    # Ensure the workspace directory exists
    os.makedirs(workspace_path, exist_ok=True)
    
    try:
        app.mount(
            "/workspace",
            StaticFiles(directory=workspace_path, html=True),
            name="workspace",
        )
        logger.info(f"Workspace mounted at: {workspace_path}")
        
        # Log whether we're using persistent storage
        if workspace_path.startswith(PERSISTENT_DATA_ROOT):
            logger.info("Using persistent storage for workspace files")
        else:
            logger.info("Using local storage for workspace files")
            
    except RuntimeError:
        # Directory might not exist yet
        os.makedirs(workspace_path, exist_ok=True)
        app.mount(
            "/workspace",
            StaticFiles(directory=workspace_path, html=True),
            name="workspace",
        )


async def periodic_cleanup():
    """Periodic cleanup task to remove stale connections and resources."""
    while True:
        try:
            await asyncio.sleep(60)  # Run every minute
            
            # Check for stale connections
            stale_connections = []
            for websocket in list(active_connections):
                try:
                    if websocket.client_state.name == "DISCONNECTED":
                        stale_connections.append(websocket)
                except Exception:
                    # If we can't check the state, consider it stale
                    stale_connections.append(websocket)
            
            # Clean up stale connections
            for websocket in stale_connections:
                logger.info(f"Cleaning up stale connection {id(websocket)}")
                cleanup_connection(websocket)
            
            if stale_connections:
                logger.info(f"Cleaned up {len(stale_connections)} stale connections. Active: {len(active_connections)}")
                
        except Exception as e:
            logger.error(f"Error in periodic cleanup: {e}")


def main():
    """Main entry point for the WebSocket server."""
    global global_args

    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="WebSocket Server for interacting with the Agent"
    )
    parser = parse_common_args(parser)
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to run the server on",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to run the server on",
    )
    args = parser.parse_args()
    global_args = args

    # Set the static file base URL if not already set
    if not os.getenv("STATIC_FILE_BASE_URL"):
        static_base_url = f"http://localhost:{args.port}"
        os.environ["STATIC_FILE_BASE_URL"] = static_base_url
        logger.info(f"Set STATIC_FILE_BASE_URL to {static_base_url}")

    setup_workspace(app, args.workspace)

    # Start periodic cleanup task
    @app.on_event("startup")
    async def startup_event():
        asyncio.create_task(periodic_cleanup())
        logger.info("Started periodic cleanup task")

    # Start the FastAPI server
    logger.info(f"Starting WebSocket server on {args.host}:{args.port}")
    try:
        uvicorn.run(app, host=args.host, port=args.port)
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise


@app.post("/api/upload")
async def upload_file_endpoint(request: Request):
    """API endpoint for uploading a single file to the workspace.

    Expects a JSON payload with:
    - session_id: UUID of the session/workspace
    - file: Object with path and content properties
    """
    try:
        data = await request.json()
        session_id = data.get("session_id")
        file_info = data.get("file")

        if not session_id:
            return JSONResponse(
                status_code=400, content={"error": "session_id is required"}
            )

        if not file_info:
            return JSONResponse(
                status_code=400, content={"error": "No file provided for upload"}
            )

        # Find the workspace path for this session
        workspace_path = Path(global_args.workspace).resolve() / session_id
        if not workspace_path.exists():
            return JSONResponse(
                status_code=404,
                content={"error": f"Workspace not found for session: {session_id}"},
            )

        # Create the upload directory if it doesn't exist
        upload_dir = workspace_path / UPLOAD_FOLDER_NAME
        upload_dir.mkdir(parents=True, exist_ok=True)

        file_path = file_info.get("path", "")
        file_content = file_info.get("content", "")

        if not file_path:
            return JSONResponse(
                status_code=400, content={"error": "File path is required"}
            )

        # Ensure the file path is relative to the workspace
        if Path(file_path).is_absolute():
            file_path = Path(file_path).name

        # Create the full path within the upload directory
        original_path = upload_dir / file_path
        full_path = original_path

        # Handle filename collision by adding a suffix
        if full_path.exists():
            base_name = full_path.stem
            extension = full_path.suffix
            counter = 1

            # Keep incrementing counter until we find a unique filename
            while full_path.exists():
                new_filename = f"{base_name}_{counter}{extension}"
                full_path = upload_dir / new_filename
                counter += 1

            # Update the file_path to reflect the new name
            file_path = f"{full_path.relative_to(upload_dir)}"

        # Ensure any subdirectories exist
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Check if content is base64 encoded (for binary files)
        if file_content.startswith("data:"):
            # Handle data URLs (e.g., "data:application/pdf;base64,...")
            # Split the header from the base64 content
            header, encoded = file_content.split(",", 1)

            # Decode the content
            decoded = base64.b64decode(encoded)

            # Write binary content
            with open(full_path, "wb") as f:
                f.write(decoded)
        else:
            # Write text content
            with open(full_path, "w") as f:
                f.write(file_content)

        # Log the upload
        logger.info(f"File uploaded to {full_path}")

        # Return the path relative to the workspace for client use
        relative_path = f"/{UPLOAD_FOLDER_NAME}/{file_path}"

        return {
            "message": "File uploaded successfully",
            "file": {"path": relative_path, "saved_path": str(full_path)},
        }

    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        return JSONResponse(
            status_code=500, content={"error": f"Error uploading file: {str(e)}"}
        )


@app.post("/api/transcribe")
async def transcribe_audio_endpoint(request: Request):
    """API endpoint for transcribing audio using Chutes Whisper API.

    Expects a JSON payload with:
    - audio_b64: Base64 encoded audio data
    """
    try:
        data = await request.json()
        audio_b64 = data.get("audio_b64")

        if not audio_b64:
            logger.error('Transcription API: No audio data provided')
            return create_cors_response({"error": "Audio data is required"}, 400)

        logger.info(f'Transcription API: Received audio data, length: {len(audio_b64)}')

        # Use CHUTES API to transcribe audio
        api_token = os.getenv("CHUTES_API_KEY")
        
        logger.info('Transcription API: Checking for CHUTES_API_KEY...')
        if not api_token:
            logger.error('Transcription API: CHUTES_API_KEY environment variable not found')
            available_chutes_vars = [key for key in os.environ.keys() if 'CHUTES' in key]
            logger.error(f'Available CHUTES env vars: {available_chutes_vars}')
            return create_cors_response({"error": "CHUTES API token not configured"}, 500)

        logger.info('Transcription API: Found API key, making request to Chutes...')
        
        import requests
        response = requests.post(
            'https://chutes-whisper-large-v3.chutes.ai/transcribe',
            headers={
                'Authorization': f'Bearer {api_token}',
                'Content-Type': 'application/json',
            },
            json={
                'audio_b64': audio_b64,
            },
            timeout=30
        )

        logger.info(f'Transcription API: Chutes response status: {response.status_code}')
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f'Transcription API: Chutes response data: {data}')
            transcription = data[0].get('text', '') if data and len(data) > 0 else ''
            transcription = transcription.strip()  # Trim whitespace
            logger.info(f'Transcription API: Extracted transcription: {transcription}')
            return create_cors_response({"transcription": transcription})
        else:
            error_text = response.text
            logger.error(f'CHUTES transcription failed: {response.status_code} {response.reason} {error_text}')
            return create_cors_response({"error": "Transcription failed"}, 500)

    except Exception as e:
        logger.error(f'Error in transcription API: {str(e)}')
        import traceback
        traceback.print_exc()
        return create_cors_response({"error": "Internal server error"}, 500)


@app.get("/api/sessions/{device_id}")
async def get_sessions_by_device_id(device_id: str):
    """Get all sessions for a specific device ID, sorted by creation time descending.
    For each session, also includes the first user message if available.

    Args:
        device_id: The device identifier to look up sessions for

    Returns:
        A list of sessions with their details and first user message, sorted by creation time descending
    """
    try:
        # Log start time for performance monitoring
        start_time = time.time()
        
        # Initialize database manager
        db_manager = DatabaseManager()

        # Get all sessions for this device, sorted by created_at descending
        with db_manager.get_session() as session:
            # First, get all sessions for this device
            from ii_agent.db.models import Session
            sessions_query = session.query(Session).filter(
                Session.device_id == device_id
            ).order_by(Session.created_at.desc()).limit(50)  # Limit to 50 most recent sessions
            
            sessions_list = sessions_query.all()
            
            # Convert to list of dictionaries with basic info first
            sessions = []
            for sess in sessions_list:
                session_data = {
                    "id": sess.id,
                    "workspace_dir": sess.workspace_dir,
                    "created_at": sess.created_at.isoformat() if sess.created_at else None,
                    "device_id": sess.device_id,
                    "first_message": "",  # Will be populated if found
                }
                sessions.append(session_data)
            
            # Now get first messages for these sessions in a more efficient way
            if sessions:
                session_ids = [s["id"] for s in sessions]
                
                # Build placeholders for the IN clause
                placeholders = ','.join(['?' for _ in session_ids])
                
                # Get first user message for each session using a more efficient query
                first_messages_query = text(f"""
                SELECT 
                    session_id,
                    event_payload,
                    MIN(timestamp) as first_timestamp
                FROM event
                WHERE session_id IN ({placeholders})
                AND event_type = 'user_message'
                GROUP BY session_id
                """)
                
                # Execute with positional parameters
                result = session.execute(first_messages_query, session_ids)
                
                # Create a map of session_id to first message
                first_messages_map = {}
                for row in result:
                    try:
                        payload = json.loads(row.event_payload) if row.event_payload else {}
                        first_message = payload.get("content", {}).get("text", "")
                        first_messages_map[row.session_id] = first_message
                    except:
                        first_messages_map[row.session_id] = ""
                
                # Update sessions with first messages
                for sess in sessions:
                    sess["first_message"] = first_messages_map.get(sess["id"], "")
            
            query_time = time.time() - start_time
            logger.info(f"get_sessions_by_device_id completed in {query_time:.3f} seconds for device {device_id}")
            
            return {"sessions": sessions}

    except Exception as e:
        logger.error(f"Error retrieving sessions: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error retrieving sessions: {str(e)}"
        )


@app.get("/api/sessions/{session_id}/events")
async def get_session_events(session_id: str):
    """Get all events for a specific session ID, sorted by timestamp ascending.

    Args:
        session_id: The session identifier to look up events for

    Returns:
        A list of events with their details, sorted by timestamp ascending
    """
    try:
        # Log start time for performance monitoring
        start_time = time.time()
        
        # Initialize database manager
        db_manager = DatabaseManager()

        # Get all events for this session, sorted by timestamp ascending
        with db_manager.get_session() as session:
            # Count total events first
            total_count = session.query(Event).filter(Event.session_id == session_id).count()
            logger.info(f"Session {session_id} has {total_count} total events")
            
            # Limit to last 1000 events to prevent timeout
            events = (
                session.query(Event)
                .filter(Event.session_id == session_id)
                .order_by(asc(Event.timestamp))
                .limit(1000)
                .all()
            )

            # Convert events to a list of dictionaries
            event_list = []
            for e in events:
                event_list.append(
                    {
                        "id": e.id,
                        "session_id": e.session_id,
                        "timestamp": e.timestamp.isoformat(),
                        "event_type": e.event_type,
                        "event_payload": e.event_payload,
                        "workspace_dir": e.session.workspace_dir if e.session else None,
                    }
                )

            query_time = time.time() - start_time
            logger.info(f"get_session_events completed in {query_time:.3f} seconds for session {session_id} (returned {len(event_list)} of {total_count} events)")
            
            return {"events": event_list, "total_count": total_count, "returned_count": len(event_list)}

    except Exception as e:
        logger.error(f"Error retrieving events: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error retrieving events: {str(e)}"
        )


@app.post("/api/files/list")
async def list_files_endpoint(request: Request):
    """API endpoint for listing files in a workspace directory.

    Expects a JSON payload with:
    - workspace_id: UUID of the workspace
    - path: Optional path within the workspace (defaults to root)
    """
    try:
        data = await request.json()
        workspace_id = data.get("workspace_id")
        path = data.get("path", "")

        if not workspace_id:
            return JSONResponse(
                status_code=400, content={"error": "workspace_id is required"}
            )

        if not path:
            return JSONResponse(
                status_code=400, content={"error": "path is required"}
            )

        # Find the workspace path for this session
        workspace_path = Path(global_args.workspace).resolve() / workspace_id
        if not workspace_path.exists():
            return JSONResponse(
                status_code=404,
                content={"error": f"Workspace not found for session: {workspace_id}"},
            )

        # Determine the target directory
        if path and path != "/var/data":
            # Remove /var/data prefix if present and use relative path
            relative_path = path.replace("/var/data/", "").replace("/var/data", "")
            target_path = workspace_path / relative_path if relative_path else workspace_path
        else:
            target_path = workspace_path

        if not target_path.exists():
            return JSONResponse(
                status_code=404,
                content={"error": f"Path not found: {path}"},
            )

        # List directory contents
        files = []
        try:
            for item in target_path.iterdir():
                if item.name.startswith('.'):
                    continue  # Skip hidden files
                
                file_info = {
                    "name": item.name,
                    "type": "folder" if item.is_dir() else "file",
                    "path": str(item),
                }
                
                if item.is_file():
                    file_info["language"] = item.suffix[1:] if item.suffix else "plaintext"
                
                if item.is_dir():
                    # Recursively get children for folders
                    children = []
                    try:
                        for child in item.iterdir():
                            if child.name.startswith('.'):
                                continue
                            child_info = {
                                "name": child.name,
                                "type": "folder" if child.is_dir() else "file",
                                "path": str(child),
                            }
                            if child.is_file():
                                child_info["language"] = child.suffix[1:] if child.suffix else "plaintext"
                            children.append(child_info)
                    except PermissionError:
                        pass  # Skip directories we can't read
                    file_info["children"] = children
                
                files.append(file_info)
        except PermissionError:
            return JSONResponse(
                status_code=403,
                content={"error": f"Permission denied accessing: {path}"},
            )

        return {"files": files}

    except Exception as e:
        logger.error(f"Error listing files: {str(e)}")
        return JSONResponse(
            status_code=500, content={"error": f"Error listing files: {str(e)}"}
        )


@app.post("/api/files/content")
async def get_file_content_endpoint(request: Request):
    """API endpoint for getting file content from a workspace.

    Expects a JSON payload with:
    - workspace_id: UUID of the workspace
    - path: Path to the file within the workspace
    """
    try:
        data = await request.json()
        workspace_id = data.get("workspace_id")
        file_path = data.get("path")

        if not workspace_id:
            return JSONResponse(
                status_code=400, content={"error": "workspace_id is required"}
            )

        if not file_path:
            return JSONResponse(
                status_code=400, content={"error": "path is required"}
            )

        # Find the workspace path for this session
        workspace_path = Path(global_args.workspace).resolve() / workspace_id
        if not workspace_path.exists():
            return JSONResponse(
                status_code=404,
                content={"error": f"Workspace not found: {workspace_id}"},
            )

        # Remove /var/data prefix if present and construct full path
        relative_path = file_path.replace("/var/data/", "").replace("/var/data", "")
        full_path = workspace_path / relative_path if relative_path else workspace_path

        if not full_path.exists():
            return JSONResponse(
                status_code=404,
                content={"error": f"File not found: {file_path}"},
            )

        if not full_path.is_file():
            return JSONResponse(
                status_code=400,
                content={"error": f"Path is not a file: {file_path}"},
            )

        # Read file content
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # Try reading as binary and return base64 encoded
            with open(full_path, 'rb') as f:
                binary_content = f.read()
                content = base64.b64encode(binary_content).decode('utf-8')
                return {"content": content, "encoding": "base64"}

        return {"content": content}

    except Exception as e:
        logger.error(f"Error reading file: {str(e)}")
        return JSONResponse(
            status_code=500, content={"error": f"Error reading file: {str(e)}"}
        )


@app.post("/api/files/download")
async def download_file_endpoint(request: Request):
    """API endpoint for downloading a single file from a workspace.

    Expects a JSON payload with:
    - workspace_id: UUID of the workspace
    - path: Path to the file within the workspace
    """
    try:
        data = await request.json()
        workspace_id = data.get("workspace_id")
        file_path = data.get("path")

        if not workspace_id:
            return JSONResponse(
                status_code=400, content={"error": "workspace_id is required"}
            )

        if not file_path:
            return JSONResponse(
                status_code=400, content={"error": "path is required"}
            )

        # Find the workspace path for this session
        workspace_path = Path(global_args.workspace).resolve() / workspace_id
        if not workspace_path.exists():
            return JSONResponse(
                status_code=404,
                content={"error": f"Workspace not found: {workspace_id}"},
            )

        # Remove /var/data prefix if present and construct full path
        relative_path = file_path.replace("/var/data/", "").replace("/var/data", "")
        full_path = workspace_path / relative_path if relative_path else workspace_path

        if not full_path.exists():
            return JSONResponse(
                status_code=404,
                content={"error": f"File not found: {file_path}"},
            )

        if not full_path.is_file():
            return JSONResponse(
                status_code=400,
                content={"error": f"Path is not a file: {file_path}"},
            )

        # Return the file for download
        filename = full_path.name
        return FileResponse(
            path=str(full_path),
            filename=filename,
            media_type='application/octet-stream'
        )

    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}")
        return JSONResponse(
            status_code=500, content={"error": f"Error downloading file: {str(e)}"}
        )


@app.post("/api/files/download-zip")
async def download_zip_endpoint(request: Request):
    """API endpoint for downloading a folder as a zip file from a workspace.

    Expects a JSON payload with:
    - workspace_id: UUID of the workspace
    - path: Path to the folder within the workspace
    """
    try:
        data = await request.json()
        workspace_id = data.get("workspace_id")
        folder_path = data.get("path")

        if not workspace_id:
            return JSONResponse(
                status_code=400, content={"error": "workspace_id is required"}
            )

        if not folder_path:
            return JSONResponse(
                status_code=400, content={"error": "path is required"}
            )

        # Find the workspace path for this session
        workspace_path = Path(global_args.workspace).resolve() / workspace_id
        if not workspace_path.exists():
            return JSONResponse(
                status_code=404,
                content={"error": f"Workspace not found: {workspace_id}"},
            )

        # Remove /var/data prefix if present and construct full path
        relative_path = folder_path.replace("/var/data/", "").replace("/var/data", "")
        full_path = workspace_path / relative_path if relative_path else workspace_path

        if not full_path.exists():
            return JSONResponse(
                status_code=404,
                content={"error": f"Path not found: {folder_path}"},
            )

        if not full_path.is_dir():
            return JSONResponse(
                status_code=400,
                content={"error": f"Path is not a directory: {folder_path}"},
            )

        # Create a temporary zip file
        temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        temp_zip.close()

        try:
            with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Walk through the directory and add all files
                for root, dirs, files in os.walk(full_path):
                    # Skip hidden directories
                    dirs[:] = [d for d in dirs if not d.startswith('.')]
                    
                    for file in files:
                        # Skip hidden files
                        if file.startswith('.'):
                            continue
                            
                        file_path = Path(root) / file
                        # Calculate the archive name (relative to the folder being zipped)
                        arcname = file_path.relative_to(full_path)
                        zipf.write(file_path, arcname)

            # Determine the zip filename
            folder_name = full_path.name if full_path.name else "workspace"
            zip_filename = f"{folder_name}.zip"

            # Return the zip file for download
            return FileResponse(
                path=temp_zip.name,
                filename=zip_filename,
                media_type='application/zip',
                background=lambda: os.unlink(temp_zip.name)  # Clean up temp file after response
            )

        except Exception as e:
            # Clean up temp file on error
            if os.path.exists(temp_zip.name):
                os.unlink(temp_zip.name)
            raise e

    except Exception as e:
        logger.error(f"Error creating zip download: {str(e)}")
        return JSONResponse(
            status_code=500, content={"error": f"Error creating zip download: {str(e)}"}
        )


@app.post("/api/pro/generate-key")
async def generate_pro_key_endpoint():
    """Generate a new Pro key for testing purposes."""
    try:
        from ii_agent.utils.pro_utils import generate_pro_key
        
        new_key = generate_pro_key()
        logger.info(f"Generated new Pro key: {new_key}")
        
        return {
            "pro_key": new_key,
            "url_example": f"/?pro_user_key={new_key}",
            "message": "Pro key generated successfully"
        }
    except Exception as e:
        logger.error(f"Error generating Pro key: {str(e)}")
        return JSONResponse(
            status_code=500, content={"error": f"Error generating Pro key: {str(e)}"}
        )


@app.get("/api/pro/usage/{pro_key}")
async def get_pro_usage_endpoint(pro_key: str):
    """Get usage statistics for a Pro key."""
    try:
        from ii_agent.utils.pro_utils import validate_pro_key
        
        if not validate_pro_key(pro_key):
            return JSONResponse(
                status_code=400, content={"error": "Invalid Pro key"}
            )
        
        db_manager = DatabaseManager()
        usage_stats = db_manager.get_pro_usage(pro_key)
        
        return usage_stats
    except Exception as e:
        logger.error(f"Error getting Pro usage: {str(e)}")
        return JSONResponse(
            status_code=500, content={"error": f"Error getting Pro usage: {str(e)}"}
        )


@app.post("/api/gaia/run")
async def run_gaia_benchmark(request: Request):
    """API endpoint to run GAIA benchmark evaluation."""
    try:
        # Check if GAIA dependencies are available
        try:
            import datasets
            import huggingface_hub
        except ImportError as e:
            return create_cors_response({
                "status": "error", 
                "message": f"GAIA dependencies not installed. Missing: {str(e)}. Please install with: pip install datasets huggingface-hub"
            }, 400)
        
        data = await request.json()
        set_to_run = data.get("set_to_run", "validation")
        run_name = data.get("run_name", f"api-run-{uuid.uuid4()}")
        max_tasks = data.get("max_tasks", 5)  # Limit for demo/testing
        model_id = data.get("model_id", None)
        model_provider = data.get("model_provider", None)
        
        # Create output directory
        output_dir = Path("output") / set_to_run
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create logs directory
        logs_dir = Path("logs")
        logs_dir.mkdir(parents=True, exist_ok=True)
        log_file = logs_dir / f"{run_name}.log"
        
        # Get workspace path from global args
        workspace_path = global_args.workspace if global_args else "workspace"
        
        # Run the benchmark with all required arguments
        cmd = [
            "python", "run_gaia.py",
            "--run-name", run_name,
            "--set-to-run", set_to_run,
            "--end-index", str(max_tasks),
            "--minimize-stdout-logs",
            "--workspace", workspace_path,
            "--logs-path", str(log_file)
        ]
        
        # Add model parameters if provided
        if model_id and model_provider:
            cmd.extend(["--model-id", model_id, "--model-provider", model_provider])
        
        logger.info(f"Running GAIA benchmark: {' '.join(cmd)}")
        
        # Run in background and capture output with environment variables
        env = os.environ.copy()
        # Disable progress bars in huggingface_hub
        env["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
        env["TQDM_DISABLE"] = "1"
        
        try:
            # Run with a longer timeout and capture both stdout and stderr
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=3600,  # 60 minutes timeout
                env=env,
                cwd=os.getcwd()  # Ensure we run in the correct directory
            )
            
            # Log the output for debugging
            if result.stdout:
                logger.info(f"GAIA stdout: {result.stdout[:1000]}...")  # Log first 1000 chars
            if result.stderr:
                logger.error(f"GAIA stderr: {result.stderr[:1000]}...")  # Log first 1000 chars
            
            if result.returncode == 0:
                # Read results file
                results_file = output_dir / f"{run_name}.jsonl"
                if results_file.exists():
                    results = []
                    with open(results_file, 'r') as f:
                        for line in f:
                            if line.strip():
                                try:
                                    results.append(json.loads(line))
                                except json.JSONDecodeError as e:
                                    logger.warning(f"Failed to parse result line: {e}")
                    
                    # Calculate basic statistics
                    total_tasks = len(results)
                    completed_tasks = len([r for r in results if r.get('prediction')])
                    
                    response_data = {
                        "status": "success", 
                        "results": results,
                        "summary": {
                            "total_tasks": total_tasks,
                            "completed_tasks": completed_tasks,
                            "completion_rate": completed_tasks / total_tasks if total_tasks > 0 else 0,
                            "run_name": run_name,
                            "set_to_run": set_to_run
                        }
                    }
                    return create_cors_response(response_data)
                else:
                    error_msg = "Results file not found. "
                    if result.stderr:
                        error_msg += f"Process error: {result.stderr}"
                    return create_cors_response({"status": "error", "message": error_msg}, 404)
            else:
                error_msg = f"GAIA benchmark failed with return code {result.returncode}. "
                if result.stderr:
                    error_msg += f"Error: {result.stderr}"
                elif result.stdout:
                    error_msg += f"Output: {result.stdout}"
                logger.error(error_msg)
                return create_cors_response({"status": "error", "message": error_msg}, 500)
                
        except subprocess.TimeoutExpired:
            return create_cors_response({"status": "error", "message": "Benchmark execution timed out (60 minutes)"}, 408)
        except FileNotFoundError:
            return create_cors_response({"status": "error", "message": "run_gaia.py script not found. Make sure you're running from the correct directory."}, 500)
        except Exception as e:
            logger.error(f"Subprocess error: {str(e)}")
            return create_cors_response({"status": "error", "message": f"Failed to run benchmark: {str(e)}"}, 500)
        
    except Exception as e:
        logger.error(f"Error running GAIA benchmark: {str(e)}")
        import traceback
        traceback.print_exc()
        return create_cors_response({"status": "error", "message": f"Error running GAIA benchmark: {str(e)}"}, 500)


@app.post("/api/generate-summary")
async def generate_summary_endpoint(request: Request):
    """Generate a short task summary using Chutes API."""
    try:
        data = await request.json()
        message = data.get("message")
        model_id = data.get("modelId", "deepseek-ai/DeepSeek-V3-0324")

        if not message:
            return create_cors_response({"error": "Message is required"}, 400)

        # Get Chutes API key
        api_key = os.getenv("CHUTES_API_KEY")
        
        logger.info('Transcription API: Checking for CHUTES_API_KEY...')
        if not api_key:
            logger.error('Transcription API: CHUTES_API_KEY environment variable not found')
            available_chutes_vars = [key for key in os.environ.keys() if 'CHUTES' in key]
            logger.error(f'Available CHUTES env vars: {available_chutes_vars}')
            return create_cors_response({"error": "API key not configured"}, 500)

        logger.info('Transcription API: Found API key, making request to Chutes...')
        
        import requests
        response = requests.post(
            "https://api.chutes.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model_id,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that creates very short, concise summaries of user tasks. Your summaries should be 3-7 words maximum, capturing the essence of what the user wants to do. Be specific but brief. You must respond with a JSON object in the format: {\"summary\": \"your short summary here\"}"
                    },
                    {
                        "role": "user",
                        "content": f"Create a very short summary (3-7 words) of this task: \"{message}\""
                    }
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.3,
                "max_tokens": 50,
            },
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            summary = "Task in progress"
            try:
                parsed = json.loads(content)
                summary = parsed.get("summary", "Task in progress")
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse summary JSON: {content}")
            
            return create_cors_response({"summary": summary})
        else:
            logger.error(f"Chutes API error: {response.status_code} {response.text}")
            return create_cors_response({"error": "Failed to generate summary"}, response.status_code)

    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}")
        return create_cors_response({"error": "Internal server error"}, 500)


# Admin endpoints for server management
try:
    import psutil
except ImportError:
    psutil = None
    logger.warning("psutil module not found. System statistics will be limited.")

# Get admin key from environment
ADMIN_KEY_ENV = os.getenv("ADMIN_KEY")

async def verify_admin_key(authorization: str = Header(None)):
    """Verify admin authentication via Bearer token"""
    if not ADMIN_KEY_ENV:
        logger.error("ADMIN_KEY environment variable is not set. Admin endpoints are disabled.")
        raise HTTPException(status_code=503, detail="Admin functionality not configured.")
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or token != ADMIN_KEY_ENV:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    return True

def get_folder_size(folder_path: str) -> int:
    """Calculate total size of a folder in bytes"""
    total_size = 0
    try:
        for dirpath, _, filenames in os.walk(folder_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if not os.path.islink(fp):
                    total_size += os.path.getsize(fp)
    except Exception as e:
        logger.error(f"Error calculating folder size for {folder_path}: {e}")
    return total_size

def format_bytes(size_bytes: int) -> str:
    """Convert bytes to human-readable format"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024**2:
        return f"{size_bytes/1024:.2f} KB"
    elif size_bytes < 1024**3:
        return f"{size_bytes/1024**2:.2f} MB"
    else:
        return f"{size_bytes/1024**3:.2f} GB"

@app.get("/admin/stats", dependencies=[Depends(verify_admin_key)])
async def get_admin_stats():
    """Get comprehensive server statistics"""
    stats = {"server_time": datetime.utcnow().isoformat() + "Z"}

    # System Stats (if psutil is available)
    if psutil:
        try:
            cpu_usage = psutil.cpu_percent(interval=0.1)
            memory_info = psutil.virtual_memory()
            disk_info = psutil.disk_usage('/')
            stats["system"] = {
                "cpu_usage_percent": cpu_usage,
                "memory_total": format_bytes(memory_info.total),
                "memory_used": format_bytes(memory_info.used),
                "memory_percent": memory_info.percent,
                "disk_total": format_bytes(disk_info.total),
                "disk_used": format_bytes(disk_info.used),
                "disk_percent": disk_info.percent,
            }
        except Exception as e:
            logger.error(f"Error getting system stats with psutil: {e}")
            stats["system"] = {"error": str(e)}
    else:
        stats["system"] = {"status": "psutil not available, system stats limited"}

    # Database Stats
    try:
        db_manager = DatabaseManager()
        db_path_actual = db_manager.db_path
        
        db_size_bytes = 0
        if Path(db_path_actual).exists():
            db_size_bytes = Path(db_path_actual).stat().st_size
        
        with db_manager.get_session() as db_sess:
            event_count = db_sess.query(Event).count()
            unique_sessions = db_sess.query(Event.session_id).distinct().count()

        stats["database"] = {
            "db_path": db_path_actual,
            "db_size": format_bytes(db_size_bytes),
            "event_count": event_count,
            "unique_sessions": unique_sessions,
        }
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        stats["database"] = {"error": str(e)}

    # Workspace Stats
    try:
        workspace_root = PERSISTENT_WORKSPACE_ROOT
        num_workspaces = 0
        total_workspace_size_bytes = 0
        if Path(workspace_root).exists() and Path(workspace_root).is_dir():
            workspaces = [d for d in Path(workspace_root).iterdir() if d.is_dir()]
            num_workspaces = len(workspaces)
            total_workspace_size_bytes = get_folder_size(workspace_root)
        
        stats["workspace"] = {
            "path": workspace_root,
            "num_workspaces": num_workspaces,
            "total_size": format_bytes(total_workspace_size_bytes),
        }
    except Exception as e:
        logger.error(f"Error getting workspace stats: {e}")
        stats["workspace"] = {"error": str(e)}

    # Log Stats
    try:
        log_file_path = Path(PERSISTENT_DATA_ROOT) / "agent_logs.txt"
        log_size_bytes = 0
        if log_file_path.exists():
            log_size_bytes = log_file_path.stat().st_size
        stats["logs"] = {
            "path": str(log_file_path),
            "size": format_bytes(log_size_bytes),
        }
    except Exception as e:
        logger.error(f"Error getting log stats: {e}")
        stats["logs"] = {"error": str(e)}
        
    return create_cors_response(stats)

@app.post("/admin/cleanup", dependencies=[Depends(verify_admin_key)])
async def cleanup_data():
    """Clean up old workspaces and database entries"""
    MAX_WORKSPACES_TO_DELETE = 1000
    MAX_DB_ROWS_TO_DELETE = 1000
    TARGET_WORKSPACE_BYTES_TO_DELETE = 200 * 1024 * 1024  # 200 MB

    report = {
        "workspaces_deleted": 0,
        "bytes_freed_from_workspaces": 0,
        "db_rows_deleted": 0,
        "errors": []
    }

    # Workspace Cleanup
    try:
        workspace_root = Path(PERSISTENT_WORKSPACE_ROOT)
        if workspace_root.exists() and workspace_root.is_dir():
            workspaces_info = []
            for item in workspace_root.iterdir():
                if item.is_dir():
                    try:
                        mtime = item.stat().st_mtime
                        size = get_folder_size(str(item))
                        workspaces_info.append({"path": item, "mtime": mtime, "size": size})
                    except Exception as e:
                        logger.warning(f"Could not stat workspace {item}: {e}")
            
            # Sort by modification time (oldest first)
            workspaces_info.sort(key=lambda x: x["mtime"])

            deleted_count = 0
            deleted_size = 0
            for ws_info in workspaces_info:
                if deleted_count >= MAX_WORKSPACES_TO_DELETE or deleted_size >= TARGET_WORKSPACE_BYTES_TO_DELETE:
                    break
                try:
                    shutil.rmtree(ws_info["path"])
                    logger.info(f"Admin Cleanup: Deleted workspace {ws_info['path']} (size: {format_bytes(ws_info['size'])})")
                    deleted_size += ws_info["size"]
                    deleted_count += 1
                except Exception as e:
                    err_msg = f"Error deleting workspace {ws_info['path']}: {e}"
                    logger.error(err_msg)
                    report["errors"].append(err_msg)
            
            report["workspaces_deleted"] = deleted_count
            report["bytes_freed_from_workspaces"] = deleted_size
    except Exception as e:
        err_msg = f"Error during workspace cleanup: {e}"
        logger.error(err_msg)
        report["errors"].append(err_msg)

    # Database Cleanup
    try:
        db_manager = DatabaseManager()
        with db_manager.get_session() as session:
            oldest_events = session.query(Event).order_by(Event.timestamp.asc()).limit(MAX_DB_ROWS_TO_DELETE).all()
            
            num_to_delete = len(oldest_events)
            if num_to_delete > 0:
                for event_record in oldest_events:
                    session.delete(event_record)
                session.commit()
                report["db_rows_deleted"] = num_to_delete
                logger.info(f"Admin Cleanup: Deleted {num_to_delete} oldest rows from Event table.")
            else:
                logger.info("Admin Cleanup: No old rows found in Event table to delete.")
                
    except Exception as e:
        err_msg = f"Error during database cleanup: {e}"
        logger.error(err_msg)
        report["errors"].append(err_msg)

    return create_cors_response(report)

@app.get("/admin/download_data", dependencies=[Depends(verify_admin_key)])
async def download_data():
    """Download server data as ZIP file (excluding workspaces due to size)"""
    # Create a temporary file instead of directory to avoid premature deletion
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
    zip_filename = f"server_data_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.zip"
    
    try:
        with zipfile.ZipFile(temp_file.name, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add database file
            db_manager = DatabaseManager()
            actual_db_path = Path(db_manager.db_path)
            if actual_db_path.exists():
                zf.write(actual_db_path, arcname=actual_db_path.name)
                logger.info(f"Admin Download: Added database {actual_db_path.name} to zip.")

            # Skip workspace folder to reduce size and server load
            # Workspaces need to be backed up separately due to their large size
            logger.info("Admin Download: Skipping workspace folder (too large for direct download)")

            # Add log files
            log_file_path = Path(PERSISTENT_DATA_ROOT) / "agent_logs.txt"
            if log_file_path.exists():
                zf.write(log_file_path, arcname=log_file_path.name)
                logger.info(f"Admin Download: Added log file to zip.")
            
            # Add a README about the missing workspaces
            readme_content = f"""Server Data Backup - {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC

This backup contains:
- Database file (agent.db)
- Log files (agent_logs.txt)

NOT included (due to size constraints):
- Workspace folders

To backup workspaces, use a different method such as:
- Direct server access
- Incremental sync tools
- Cloud storage solutions
"""
            # Write README directly to zip without creating a temp file
            zf.writestr("README.txt", readme_content)
        
        # Close the temp file to ensure all data is written
        temp_file.close()
        
        return FileResponse(
            path=temp_file.name,
            filename=zip_filename,
            media_type='application/zip',
            background=lambda: os.unlink(temp_file.name)  # Clean up after response
        )
    except Exception as e:
        # Clean up on error
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)
        logger.error(f"Error creating data zip for download: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create data zip: {str(e)}")


if __name__ == "__main__":
    main()
