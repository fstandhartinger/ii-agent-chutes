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
from pathlib import Path
from typing import Dict, List, Set, Any
from dotenv import load_dotenv

load_dotenv()

import uvicorn
from fastapi import (
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
    Request,
    HTTPException,
)

from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import anyio
import base64
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

MAX_OUTPUT_TOKENS_PER_TURN = 32768
MAX_TURNS = 200


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
    await websocket.accept()
    active_connections.add(websocket)

    workspace_manager, session_uuid = create_workspace_manager_for_connection(
        global_args.workspace, global_args.use_container_workspace
    )
    print(f"Workspace manager created: {workspace_manager}")

    try:
        # Check if we should use Chutes LLM instead of Anthropic
        use_chutes = websocket.query_params.get("use_chutes", "false").lower() == "true"
        
        # Initial connection message with session info
        await websocket.send_json(
            RealtimeEvent(
                type=EventType.CONNECTION_ESTABLISHED,
                content={
                    "message": "Connected to Agent WebSocket Server",
                    "workspace_path": str(workspace_manager.root),
                },
            ).model_dump()
        )

        # Process messages from the client
        while True:
            # Receive and parse message
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                msg_type = message.get("type")
                content = message.get("content", {})

                if msg_type == "init_agent":
                    # Create a new agent for this connection
                    tool_args = content.get("tool_args", {})
                    agent = create_agent_for_connection(
                        session_uuid, workspace_manager, websocket, tool_args
                    )
                    active_agents[websocket] = agent

                    # Start message processor for this connection
                    message_processor = agent.start_message_processing()
                    message_processors[websocket] = message_processor
                    await websocket.send_json(
                        RealtimeEvent(
                            type=EventType.AGENT_INITIALIZED,
                            content={"message": "Agent initialized"},
                        ).model_dump()
                    )

                elif msg_type == "query":
                    # Check if there's an active task for this connection
                    if websocket in active_tasks and not active_tasks[websocket].done():
                        await websocket.send_json(
                            RealtimeEvent(
                                type=EventType.ERROR,
                                content={
                                    "message": "A query is already being processed"
                                },
                            ).model_dump()
                        )
                        continue

                    # Process a query to the agent
                    user_input = content.get("text", "")
                    resume = content.get("resume", False)
                    files = content.get("files", [])

                    # Send acknowledgment
                    await websocket.send_json(
                        RealtimeEvent(
                            type=EventType.PROCESSING,
                            content={"message": "Processing your request..."},
                        ).model_dump()
                    )

                    # Run the agent with the query in a separate task
                    task = asyncio.create_task(
                        run_agent_async(websocket, user_input, resume, files)
                    )
                    active_tasks[websocket] = task

                elif msg_type == "workspace_info":
                    # Send information about the current workspace
                    if workspace_manager:
                        await websocket.send_json(
                            RealtimeEvent(
                                type=EventType.WORKSPACE_INFO,
                                content={
                                    "path": str(workspace_manager.root),
                                },
                            ).model_dump()
                        )
                    else:
                        await websocket.send_json(
                            RealtimeEvent(
                                type=EventType.ERROR,
                                content={"message": "Workspace not initialized"},
                            ).model_dump()
                        )

                elif msg_type == "ping":
                    # Simple ping to keep connection alive
                    await websocket.send_json(
                        RealtimeEvent(type=EventType.PONG, content={}).model_dump()
                    )

                elif msg_type == "cancel":
                    # Cancel the current agent task if one exists
                    if websocket in active_tasks and not active_tasks[websocket].done():
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
                                content={"message": "No active query to cancel"},
                            ).model_dump()
                        )

                else:
                    # Unknown message type
                    await websocket.send_json(
                        RealtimeEvent(
                            type=EventType.ERROR,
                            content={"message": f"Unknown message type: {msg_type}"},
                        ).model_dump()
                    )

            except json.JSONDecodeError:
                await websocket.send_json(
                    RealtimeEvent(
                        type=EventType.ERROR, content={"message": "Invalid JSON format"}
                    ).model_dump()
                )
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}")
                await websocket.send_json(
                    RealtimeEvent(
                        type=EventType.ERROR,
                        content={"message": f"Error processing request: {str(e)}"},
                    ).model_dump()
                )

    except WebSocketDisconnect:
        # Handle disconnection
        logger.info("Client disconnected")
        cleanup_connection(websocket)
    except Exception as e:
        # Handle other exceptions
        logger.error(f"WebSocket error: {str(e)}")
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
        logger.error(f"Error running agent: {str(e)}")
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
    # Remove from active connections
    if websocket in active_connections:
        active_connections.remove(websocket)

    # Set websocket to None in the agent but keep the message processor running
    if websocket in active_agents:
        agent = active_agents[websocket]
        agent.websocket = (
            None  # This will prevent sending to websocket but keep processing
        )
        # Don't cancel the message processor - it will continue saving to database
        if websocket in message_processors:
            del message_processors[websocket]  # Just remove the reference

    # Cancel any running tasks
    if websocket in active_tasks and not active_tasks[websocket].done():
        active_tasks[websocket].cancel()
        del active_tasks[websocket]

    # Remove agent for this connection
    if websocket in active_agents:
        del active_agents[websocket]


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
    
    # Check if this is an Anthropic model based on model_id
    anthropic_models = ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229", "claude-3-haiku-20240307", "claude-opus-4-20250514", "claude-sonnet-4-20250514"]
    use_anthropic = model_id in anthropic_models and not use_chutes and not use_openrouter
    
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
    db_manager.create_session(
        device_id=device_id,
        session_uuid=session_id,
        workspace_path=workspace_manager.root,
    )
    logger_for_agent_logs.info(
        f"Created new session {session_id} with workspace at {workspace_manager.root}"
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

    # Start the FastAPI server
    logger.info(f"Starting WebSocket server on {args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port)


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
        # Initialize database manager
        db_manager = DatabaseManager()

        # Get all sessions for this device, sorted by created_at descending
        with db_manager.get_session() as session:
            # Use raw SQL query to get sessions with their first user message
            query = text("""
            SELECT 
                session.id AS session_id,
                session.*, 
                event.id AS first_event_id,
                event.event_payload AS first_message,
                event.timestamp AS first_event_time
            FROM session
            LEFT JOIN event ON session.id = event.session_id
            WHERE event.id IN (
                SELECT e.id
                FROM event e
                WHERE e.event_type = "user_message" 
                AND e.timestamp = (
                    SELECT MIN(e2.timestamp)
                    FROM event e2
                    WHERE e2.session_id = e.session_id
                    AND e2.event_type = "user_message"
                )
            )
            AND session.device_id = :device_id
            ORDER BY session.created_at DESC
            """)

            # Execute the raw query with parameters
            result = session.execute(query, {"device_id": device_id})

            # Convert result to a list of dictionaries
            sessions = []
            for row in result:
                session_data = {
                    "id": row.id,
                    "workspace_dir": row.workspace_dir,
                    "created_at": row.created_at,
                    "device_id": row.device_id,
                    "first_message": json.loads(row.first_message)
                    .get("content", {})
                    .get("text", "")
                    if row.first_message
                    else "",
                }
                sessions.append(session_data)

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
        # Initialize database manager
        db_manager = DatabaseManager()

        # Get all events for this session, sorted by timestamp ascending
        with db_manager.get_session() as session:
            events = (
                session.query(Event)
                .filter(Event.session_id == session_id)
                .order_by(asc(Event.timestamp))
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
                        "workspace_dir": e.session.workspace_dir,
                    }
                )

            return {"events": event_list}

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

        # Find the workspace path for this session
        workspace_path = Path(global_args.workspace).resolve() / workspace_id
        if not workspace_path.exists():
            return JSONResponse(
                status_code=404,
                content={"error": f"Workspace not found: {workspace_id}"},
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


if __name__ == "__main__":
    main()
