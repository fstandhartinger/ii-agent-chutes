"""
Common utilities and constants shared across server components.
"""
import logging
from fastapi.responses import JSONResponse
from typing import Dict, Any

# Create a logger for this module
logger = logging.getLogger(__name__)

# CORS headers for API responses
CORS_HEADERS: Dict[str, str] = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, HEAD, PATCH",
    "Access-Control-Allow-Headers": "*",
}

def create_cors_response(content: Dict[str, Any], status_code: int = 200) -> JSONResponse:
    """
    Create a JSONResponse with CORS headers.
    """
    return JSONResponse(
        content=content,
        status_code=status_code,
        headers=CORS_HEADERS
    )

# Placeholder for other common utilities that might be identified during refactoring
# For example, constants related to WebSocket event types if they are used across modules.
