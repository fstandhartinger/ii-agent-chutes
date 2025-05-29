"""
Handles server startup, argument parsing, and initial workspace setup.
"""
import os
import argparse
import logging
import asyncio # For startup/shutdown events if needed for websocket_manager cleanup
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from utils import parse_common_args # Assuming utils.py is in PYTHONPATH
from ii_agent.utils.constants import PERSISTENT_DATA_ROOT # For logging workspace type

from .config import app_config # Relative import
# Import the periodic cleanup start/stop functions from websocket_manager
from .websocket_manager import start_periodic_cleanup, stop_periodic_cleanup

logger = logging.getLogger(__name__)

# Custom log filter to suppress /sw.js access logs
class SwJsFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # For uvicorn.access, record.args is typically a tuple like:
        # (client_addr (str), method (str), path (str), http_version (str), status_code (int))
        # Example: ('127.0.0.1:12345', 'GET', '/sw.js', 'HTTP/1.1', 200)
        if hasattr(record, 'args') and isinstance(record.args, tuple) and len(record.args) >= 3:
            path = record.args[2]
            if isinstance(path, str) and path.endswith("/sw.js"):
                return False  # Do not log this record
        return True  # Log all other records

def setup_workspace_static_files(app: FastAPI, workspace_path_str: str):
    """
    Sets up the static file serving for the workspace directory.
    The workspace_path_str should be the root path where session workspaces are created.
    In the original code, this mounted the main workspace arg.
    If individual session workspaces need to be directly accessible via static files,
    this approach might need refinement (e.g. a wildcard route or individual mounts).
    For now, mirroring the original behavior of mounting the base workspace path.
    """
    workspace_path = Path(workspace_path_str)
    # Ensure the base workspace directory exists
    os.makedirs(workspace_path, exist_ok=True)
    
    try:
        # This makes the content of args.workspace available under /workspace URL
        app.mount(
            "/workspace", # The URL path
            StaticFiles(directory=workspace_path, html=True), # The filesystem path
            name="workspace_files", # A name for this static mount
        )
        logger.info(f"Static file serving for base workspace mounted at /workspace, from directory: {workspace_path}")
        
        if str(workspace_path).startswith(PERSISTENT_DATA_ROOT):
            logger.info("Workspace files are being served from persistent storage.")
        else:
            logger.info("Workspace files are being served from local/ephemeral storage.")
            
    except RuntimeError as e:
        logger.error(f"Failed to mount workspace static files at {workspace_path}: {e}", exc_info=True)
        # Depending on severity, might re-raise or attempt to create and mount again
        # For now, logging the error. The application might still run but file serving from workspace might fail.


def main_server_start(app: FastAPI):
    """
    Main entry point for parsing arguments and starting the Uvicorn server.
    The FastAPI app instance is passed in.
    """
    parser = argparse.ArgumentParser(
        description="Agent WebSocket Server"
    )
    # Use the parse_common_args from the existing utils.py
    # This function is expected to add arguments like --workspace, --use-container-workspace etc.
    parser = parse_common_args(parser) 
    parser.add_argument(
        "--host", type=str, default="0.0.0.0", help="Host to run the server on"
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="Port to run the server on"
    )
    # Add any other server-specific arguments here if they were in the original main()

    args = parser.parse_args()
    
    # Store parsed args in the global AppConfig instance
    app_config.set_args(args)
    logger.info(f"Application arguments parsed and stored: {args}")

    # Set STATIC_FILE_BASE_URL environment variable if not already set
    # This is used by some tools to construct full URLs to workspace files
    if not os.getenv("STATIC_FILE_BASE_URL"):
        static_base_url = f"http://{args.host}:{args.port}" # Use parsed host and port
        os.environ["STATIC_FILE_BASE_URL"] = static_base_url
        logger.info(f"STATIC_FILE_BASE_URL automatically set to: {static_base_url}")
    else:
        logger.info(f"STATIC_FILE_BASE_URL already set: {os.getenv('STATIC_FILE_BASE_URL')}")

    # Setup static file serving for the main workspace directory
    # args.workspace is expected from parse_common_args
    if hasattr(args, 'workspace') and args.workspace:
        setup_workspace_static_files(app, args.workspace)
    else:
        logger.warning("Workspace argument not found in parsed args. Static file serving for workspace might not be set up.")

    # Define startup and shutdown events for the FastAPI app
    @app.on_event("startup")
    async def on_app_startup():
        logger.info("FastAPI application startup event triggered.")
        start_periodic_cleanup() # Start the WebSocket connection cleanup task

    @app.on_event("shutdown")
    async def on_app_shutdown():
        logger.info("FastAPI application shutdown event triggered.")
        stop_periodic_cleanup() # Stop the WebSocket connection cleanup task
        # Add any other global resource cleanup here if necessary

    # Add filter to uvicorn.access logger to suppress /sw.js logs
    access_logger = logging.getLogger("uvicorn.access")
    access_logger.addFilter(SwJsFilter())
    logger.info("Added SwJsFilter to uvicorn.access logger to suppress /sw.js logs.")

    logger.info(f"Starting Uvicorn server on {args.host}:{args.port}")
    try:
        uvicorn.run(
            app, # The FastAPI app instance
            host=args.host,
            port=args.port,
            # Consider adding log_level from args if needed, e.g., uvicorn_log_level=args.log_level.lower()
        )
    except KeyboardInterrupt:
        logger.info("Server shutdown requested (KeyboardInterrupt).")
    except Exception as e:
        logger.critical(f"Uvicorn server failed to start or crashed: {e}", exc_info=True)
        # Potentially re-raise or exit with error code
        raise # Re-raise the exception to ensure failure is visible
