"""
Handles general API routes like file uploads and transcription.
"""
import os
import logging
import base64
from pathlib import Path
import requests # Added for transcribe_audio_endpoint
import json # Added for transcribe_audio_endpoint

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

from ii_agent.utils.constants import UPLOAD_FOLDER_NAME
from .common import create_cors_response, CORS_HEADERS # Relative import
from .config import app_config # Relative import

logger = logging.getLogger(__name__)
router = APIRouter()

@router.options("/{full_path:path}")
async def options_handler(request: Request):
    """Handle preflight OPTIONS requests for CORS."""
    headers = CORS_HEADERS.copy()
    headers["Access-Control-Max-Age"] = "86400" # Typically 24 hours
    return JSONResponse(content={}, headers=headers)

@router.post("/api/upload")
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
            logger.error("Upload API: session_id is required")
            return create_cors_response({"error": "session_id is required"}, 400)

        if not file_info:
            logger.error("Upload API: No file provided for upload")
            return create_cors_response({"error": "No file provided for upload"}, 400)

        current_args = app_config.get_args()
        if not current_args or not hasattr(current_args, 'workspace'):
            logger.error("Upload API: Workspace path not configured in app_config.")
            return create_cors_response({"error": "Server configuration error: Workspace path missing."}, 500)

        workspace_path = Path(current_args.workspace).resolve() / session_id
        if not workspace_path.exists():
            logger.error(f"Upload API: Workspace not found for session: {session_id} at {workspace_path}")
            return create_cors_response(
                {"error": f"Workspace not found for session: {session_id}"}, 404
            )

        upload_dir = workspace_path / UPLOAD_FOLDER_NAME
        upload_dir.mkdir(parents=True, exist_ok=True)

        file_path_str = file_info.get("path", "")
        file_content = file_info.get("content", "")

        if not file_path_str:
            logger.error("Upload API: File path is required")
            return create_cors_response({"error": "File path is required"}, 400)

        # Ensure the file path is relative to the workspace
        if Path(file_path_str).is_absolute():
            file_path_str = Path(file_path_str).name

        original_path = upload_dir / file_path_str
        full_path = original_path
        final_file_path_str = file_path_str # Store the potentially modified path

        if full_path.exists():
            base_name = full_path.stem
            extension = full_path.suffix
            counter = 1
            while full_path.exists():
                new_filename = f"{base_name}_{counter}{extension}"
                full_path = upload_dir / new_filename
                counter += 1
            final_file_path_str = str(full_path.relative_to(upload_dir))


        full_path.parent.mkdir(parents=True, exist_ok=True)

        if file_content.startswith("data:"):
            header, encoded = file_content.split(",", 1)
            decoded = base64.b64decode(encoded)
            with open(full_path, "wb") as f:
                f.write(decoded)
        else:
            with open(full_path, "w", encoding='utf-8') as f: # Specify encoding
                f.write(file_content)

        logger.info(f"Upload API: File uploaded to {full_path}")
        relative_path = f"/{UPLOAD_FOLDER_NAME}/{final_file_path_str}"

        return create_cors_response({
            "message": "File uploaded successfully",
            "file": {"path": relative_path, "saved_path": str(full_path)},
        })

    except Exception as e:
        logger.error(f"Upload API: Error uploading file: {str(e)}", exc_info=True)
        return create_cors_response(
            {"error": f"Error uploading file: {str(e)}"}, 500
        )

@router.post("/api/transcribe")
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

        api_token = os.getenv("CHUTES_API_KEY")
        
        logger.info('Transcription API: Checking for CHUTES_API_KEY...')
        if not api_token:
            logger.error('Transcription API: CHUTES_API_KEY environment variable not found')
            available_chutes_vars = [key for key in os.environ.keys() if 'CHUTES' in key]
            logger.error(f'Available CHUTES env vars: {available_chutes_vars}')
            return create_cors_response({"error": "CHUTES API token not configured"}, 500)

        logger.info('Transcription API: Found API key, making request to Chutes...')
        
        response = requests.post(
            'https://chutes-whisper-large-v3.chutes.ai/transcribe',
            headers={
                'Authorization': f'Bearer {api_token}',
                'Content-Type': 'application/json',
            },
            json={'audio_b64': audio_b64},
            timeout=30
        )

        logger.info(f'Transcription API: Chutes response status: {response.status_code}')
        
        if response.status_code == 200:
            response_data = response.json()
            logger.info(f'Transcription API: Chutes response data: {response_data}')
            transcription = response_data[0].get('text', '') if response_data and len(response_data) > 0 else ''
            transcription = transcription.strip()
            logger.info(f'Transcription API: Extracted transcription: {transcription}')
            return create_cors_response({"transcription": transcription})
        else:
            error_text = response.text
            logger.error(f'CHUTES transcription failed: {response.status_code} {response.reason} {error_text}')
            return create_cors_response({"error": "Transcription failed"}, 500)

    except Exception as e:
        logger.error(f'Error in transcription API: {str(e)}', exc_info=True)
        return create_cors_response({"error": "Internal server error"}, 500)

@router.post("/api/generate-summary")
async def generate_summary_endpoint(request: Request):
    """Generate a short task summary using Chutes API."""
    try:
        data = await request.json()
        message = data.get("message")
        # Always use a known supported model for summary generation
        model_id = "deepseek-ai/DeepSeek-V3-0324" # Use a model we know works with Chutes API

        if not message:
            logger.error("Generate Summary API: Message is required")
            return create_cors_response({"error": "Message is required"}, 400)

        api_key = os.getenv("CHUTES_API_KEY")
        
        logger.info('Generate Summary API: Checking for CHUTES_API_KEY...')
        if not api_key:
            logger.error('Generate Summary API: CHUTES_API_KEY environment variable not found')
            return create_cors_response({"error": "API key not configured"}, 500)

        logger.info(f'Generate Summary API: Found API key, making request to Chutes with model {model_id}...')
        
        api_url = "https://llm.chutes.ai/v1/chat/completions"
        
        response = requests.post(
            api_url,
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

        logger.info(f'Generate Summary API: Response status code: {response.status_code}')
        
        if response.status_code == 200:
            response_data = response.json()
            content = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            logger.info(f'Generate Summary API: Raw response content: {content}')
            
            summary = "Task in progress" # Default summary
            try:
                parsed_content = json.loads(content)
                summary = parsed_content.get("summary", summary) # Use default if key missing
                logger.info(f'Generate Summary API: Parsed summary: {summary}')
            except json.JSONDecodeError as e:
                logger.warning(f"Generate Summary API: Failed to parse summary JSON: {content}, error: {e}")
            
            return create_cors_response({"summary": summary})
        else:
            error_text = response.text
            logger.error(f"Generate Summary API: Chutes API error: {response.status_code} {error_text}")
            error_detail = "Failed to generate summary"
            try:
                error_data = response.json()
                error_detail = error_data.get("detail", error_data.get("error", {"message": error_detail}).get("message", error_detail))
            except:
                pass # Keep default error_detail
            return create_cors_response({"error": error_detail}, response.status_code)

    except Exception as e:
        logger.error(f"Generate Summary API: Error generating summary: {str(e)}", exc_info=True)
        return create_cors_response({"error": "Internal server error"}, 500)

MAINTENANCE_FILE_PATH = Path("data/maintenance.txt")

@router.get("/api/maintenance_message")
async def get_maintenance_message_endpoint(request: Request):
    """
    API endpoint to get the maintenance message.
    Checks for a maintenance.txt file in the data directory.
    """
    try:
        message_content = None
        if MAINTENANCE_FILE_PATH.exists() and MAINTENANCE_FILE_PATH.is_file():
            try:
                message_content = MAINTENANCE_FILE_PATH.read_text(encoding="utf-8").strip()
                logger.info(f"Maintenance message found: {message_content[:100]}...") # Log first 100 chars
            except Exception as e:
                logger.error(f"Error reading maintenance file {MAINTENANCE_FILE_PATH}: {str(e)}", exc_info=True)
                # If file exists but can't be read, we might still want to indicate no specific message
                # or return an error. For now, let's treat it as no message.
                message_content = None
        
        return create_cors_response({"message": message_content})

    except Exception as e:
        logger.error(f"Maintenance Message API: Error: {str(e)}", exc_info=True)
        return create_cors_response(
            {"error": "Error retrieving maintenance message"}, 500
        )
