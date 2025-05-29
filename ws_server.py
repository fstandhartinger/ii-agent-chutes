#!/usr/bin/env python3
"""
FastAPI WebSocket Server for the Agent.
This script initializes the FastAPI application, registers API and WebSocket routes
from modular components, and starts the server.
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv() # Load environment variables at the very beginning

# Set up Playwright browsers path if persistent storage is available
# This needs to be done early, before Playwright might be imported by tools
persistent_playwright = Path("/var/data/playwright") # Consider making this configurable
if persistent_playwright.exists():
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(persistent_playwright)
    print(f"Using persistent Playwright browsers at {persistent_playwright}") # Use print for early startup info
else:
    print(f"Persistent Playwright path {persistent_playwright} not found. Using default Playwright browser path.")


from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routers and handlers from the server_components package
from server_components import api_admin_routes
from server_components import api_file_routes
from server_components import api_gaia_routes
from server_components import api_general_routes
from server_components import api_session_routes
from server_components import websocket_manager
from server_components import server_setup

# Initialize a basic logger for this main script
# More specific loggers are used within each component.
logging.basicConfig(level=logging.INFO) # Configure basic logging for startup messages
logger = logging.getLogger(__name__) # Logger for ws_server.py itself

# Initialize FastAPI application
app = FastAPI(title="Agent WebSocket and API Server")

# Add CORS middleware - this is a global middleware
# Specific CORS headers for responses are handled by create_cors_response in common.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"], # Allow all common methods
    allow_headers=["*"],  # Allows all headers
    expose_headers=["*"], # Expose all headers to the client (e.g., for custom headers)
    # max_age=86400 # Optional: How long the results of a preflight request can be cached
)

# Include API routers from different modules
# The OPTIONS handler is now in api_general_routes.py, covering all paths.
app.include_router(api_general_routes.router)
app.include_router(api_session_routes.router)
app.include_router(api_file_routes.router)
app.include_router(api_admin_routes.router)
app.include_router(api_gaia_routes.router)

# Register the WebSocket endpoint
# The actual implementation is in websocket_manager.py
app.add_websocket_route("/ws", websocket_manager.websocket_endpoint)
logger.info("WebSocket endpoint /ws registered.")

# The main server startup logic, including argument parsing and Uvicorn run,
# is now handled by server_setup.main_server_start.
# The FastAPI app instance `app` is passed to it.
# Startup and shutdown events (for periodic cleanup) are also registered within main_server_start.

if __name__ == "__main__":
    logger.info("Starting server via __main__ block...")
    # server_setup.main_server_start will parse args, configure app_config,
    # set up static files, register app lifecycle events, and run uvicorn.
    server_setup.main_server_start(app)
    logger.info("Server has shut down.")
