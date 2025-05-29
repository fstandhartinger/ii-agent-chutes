"""
Handles API routes for file browsing, content retrieval, and downloads within workspaces.
"""
import logging
import base64
from pathlib import Path
import os
import tempfile
import zipfile
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse, FileResponse

from .common import create_cors_response # Relative import
from .config import app_config # Relative import

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/api/files/list")
async def list_files_endpoint(request: Request):
    """API endpoint for listing files in a workspace directory."""
    try:
        data = await request.json()
        workspace_id = data.get("workspace_id")
        path_str = data.get("path", "") # Renamed to path_str to avoid conflict with Path module

        logger.info(f"[FILE_BROWSER] List files - workspace_id: {workspace_id}, path: {path_str}")

        if not workspace_id:
            logger.error("[FILE_BROWSER] Missing workspace_id")
            return create_cors_response({"error": "workspace_id is required"}, 400)

        # Path can be empty, meaning root of workspace_id
        # if not path_str:
        #     logger.error("[FILE_BROWSER] Missing path")
        #     return create_cors_response({"error": "path is required"}, 400)

        current_args = app_config.get_args()
        if not current_args or not hasattr(current_args, 'workspace'):
            logger.error("[FILE_BROWSER] Workspace root path not configured.")
            return create_cors_response({"error": "Server configuration error: Workspace root missing."}, 500)

        workspace_root_path = Path(current_args.workspace).resolve()
        workspace_path = workspace_root_path / workspace_id
        logger.info(f"[FILE_BROWSER] Workspace root: {workspace_root_path}, session workspace: {workspace_path}")
        
        if not workspace_path.exists() or not workspace_path.is_dir():
            logger.error(f"[FILE_BROWSER] Workspace not found or not a directory: {workspace_path}")
            return create_cors_response(
                {"error": f"Workspace not found for session: {workspace_id}"}, 404
            )

        target_path = workspace_path
        if path_str and path_str != "/": # Handle cases where path_str might be just "/"
            # Sanitize path_str: remove leading/trailing slashes, prevent directory traversal
            relative_path_str = path_str.strip('/')
            # Prevent path traversal attacks
            if ".." in relative_path_str.split(os.path.sep):
                logger.error(f"[FILE_BROWSER] Invalid path (directory traversal attempt): {path_str}")
                return create_cors_response({"error": "Invalid path"}, 400)
            target_path = (workspace_path / relative_path_str).resolve()
            logger.info(f"[FILE_BROWSER] Relative path: {relative_path_str}, target: {target_path}")

            # Security check: ensure target_path is still within workspace_path
            if not str(target_path).startswith(str(workspace_path)):
                logger.error(f"[FILE_BROWSER] Access denied: {target_path} is outside workspace {workspace_path}")
                return create_cors_response({"error": "Access denied to path"}, 403)


        if not target_path.exists() or not target_path.is_dir():
            logger.error(f"[FILE_BROWSER] Target path not found or not a directory: {target_path}")
            return create_cors_response(
                {"error": f"Path not found: {path_str}"}, 404
            )

        files = []
        try:
            for item in sorted(list(target_path.iterdir()), key=lambda p: (p.is_file(), p.name.lower())): # Sort for consistency
                if item.name.startswith('.'): # Skip hidden files/folders
                    logger.debug(f"[FILE_BROWSER] Skipping hidden item: {item.name}")
                    continue
                
                # Construct path relative to the workspace_id directory for client-side display
                display_path = str(item.relative_to(workspace_path))

                file_info = {
                    "name": item.name,
                    "type": "folder" if item.is_dir() else "file",
                    "path": display_path, # Use relative path for client
                    "absolute_path_for_server": str(item) # Keep absolute for server-side ops if needed later
                }
                
                if item.is_file():
                    file_info["language"] = item.suffix[1:].lower() if item.suffix else "plaintext"
                
                # Optionally, list children for folders (can be heavy, consider if needed by default)
                # For now, not listing children recursively to keep it simple and performant.
                # Client can make new requests for subfolders.

                files.append(file_info)
            logger.info(f"[FILE_BROWSER] Returning {len(files)} visible items from {target_path}")
                
        except PermissionError:
            logger.error(f"[FILE_BROWSER] Permission denied accessing: {target_path}")
            return create_cors_response(
                {"error": f"Permission denied accessing: {path_str}"}, 403
            )

        return create_cors_response({"files": files})

    except Exception as e:
        logger.error(f"[FILE_BROWSER] Error listing files: {str(e)}", exc_info=True)
        return create_cors_response(
            {"error": f"Error listing files: {str(e)}"}, 500
        )


@router.post("/api/files/content")
async def get_file_content_endpoint(request: Request):
    """API endpoint for getting file content from a workspace."""
    try:
        data = await request.json()
        workspace_id = data.get("workspace_id")
        file_path_str = data.get("path") # Renamed to file_path_str

        logger.info(f"[FILE_CONTENT] Get content - workspace_id: {workspace_id}, path: {file_path_str}")

        if not workspace_id:
            logger.error("[FILE_CONTENT] Missing workspace_id")
            return create_cors_response({"error": "workspace_id is required"}, 400)
        if not file_path_str:
            logger.error("[FILE_CONTENT] Missing path")
            return create_cors_response({"error": "path is required"}, 400)

        current_args = app_config.get_args()
        if not current_args or not hasattr(current_args, 'workspace'):
            logger.error("[FILE_CONTENT] Workspace root path not configured.")
            return create_cors_response({"error": "Server configuration error: Workspace root missing."}, 500)

        workspace_root_path = Path(current_args.workspace).resolve()
        workspace_path = workspace_root_path / workspace_id

        if not workspace_path.exists() or not workspace_path.is_dir():
            logger.error(f"[FILE_CONTENT] Workspace not found: {workspace_path}")
            return create_cors_response(
                {"error": f"Workspace not found for session: {workspace_id}"}, 404
            )

        # Construct the full path to the file, ensuring it's within the workspace
        # file_path_str is expected to be relative to the workspace_id directory
        target_file = (workspace_path / file_path_str).resolve()

        # Security check: ensure target_file is within workspace_path
        if not str(target_file).startswith(str(workspace_path)):
            logger.error(f"[FILE_CONTENT] Access denied: {target_file} is outside workspace {workspace_path}")
            return create_cors_response({"error": "Access denied to file"}, 403)

        if not target_file.exists() or not target_file.is_file():
            logger.error(f"[FILE_CONTENT] File not found or not a file: {target_file}")
            return create_cors_response(
                {"error": f"File not found: {file_path_str}"}, 404
            )

        try:
            with open(target_file, "r", encoding='utf-8') as f:
                content = f.read()
            logger.info(f"[FILE_CONTENT] Read text file: {target_file}, length: {len(content)}")
            return create_cors_response({"content": content, "encoding": "utf-8"})
        except UnicodeDecodeError:
            logger.info(f"[FILE_CONTENT] File {target_file} is not UTF-8 text, attempting binary read.")
            with open(target_file, "rb") as f:
                binary_content = f.read()
            content_b64 = base64.b64encode(binary_content).decode("utf-8")
            logger.info(f"[FILE_CONTENT] Read binary file as base64: {target_file}, size: {len(binary_content)} bytes")
            return create_cors_response({"content": content_b64, "encoding": "base64"})
        except PermissionError:
            logger.error(f"[FILE_CONTENT] Permission denied accessing file: {target_file}")
            return create_cors_response(
                {"error": f"Permission denied accessing: {file_path_str}"}, 403
            )

    except Exception as e:
        logger.error(f"[FILE_CONTENT] Error getting file content: {str(e)}", exc_info=True)
        return create_cors_response(
            {"error": f"Error getting file content: {str(e)}"}, 500
        )


@router.post("/api/files/download")
async def download_file_endpoint(request: Request):
    """API endpoint for downloading a single file from a workspace."""
    try:
        data = await request.json()
        workspace_id = data.get("workspace_id")
        file_path_str = data.get("path") # Renamed

        logger.info(f"[FILE_DOWNLOAD] Download file - workspace_id: {workspace_id}, path: {file_path_str}")

        if not workspace_id: return create_cors_response({"error": "workspace_id is required"}, 400)
        if not file_path_str: return create_cors_response({"error": "path is required"}, 400)

        current_args = app_config.get_args()
        if not current_args or not hasattr(current_args, 'workspace'):
            logger.error("[FILE_DOWNLOAD] Workspace root path not configured.")
            return create_cors_response({"error": "Server configuration error."}, 500)

        workspace_path = Path(current_args.workspace).resolve() / workspace_id
        if not workspace_path.exists():
            return create_cors_response({"error": f"Workspace not found: {workspace_id}"}, 404)

        target_file = (workspace_path / file_path_str).resolve()

        if not str(target_file).startswith(str(workspace_path)): # Security check
            return create_cors_response({"error": "Access denied"}, 403)

        if not target_file.exists():
            return create_cors_response({"error": f"File not found: {file_path_str}"}, 404)
        if not target_file.is_file():
            return create_cors_response({"error": f"Path is not a file: {file_path_str}"}, 400)

        logger.info(f"[FILE_DOWNLOAD] Preparing file for download: {target_file}")
        return FileResponse(
            path=str(target_file),
            filename=target_file.name,
            media_type='application/octet-stream'
        )

    except Exception as e:
        logger.error(f"[FILE_DOWNLOAD] Error downloading file: {str(e)}", exc_info=True)
        return create_cors_response({"error": f"Error downloading file: {str(e)}"}, 500)


@router.post("/api/files/download-zip")
async def download_zip_endpoint(request: Request):
    """API endpoint for downloading a folder as a zip file from a workspace."""
    try:
        data = await request.json()
        workspace_id = data.get("workspace_id")
        folder_path_str = data.get("path") # Renamed

        logger.info(f"[ZIP_DOWNLOAD] Download folder as zip - workspace_id: {workspace_id}, path: {folder_path_str}")

        if not workspace_id: return create_cors_response({"error": "workspace_id is required"}, 400)
        if not folder_path_str: return create_cors_response({"error": "path is required"}, 400) # Path to folder is required

        current_args = app_config.get_args()
        if not current_args or not hasattr(current_args, 'workspace'):
            logger.error("[ZIP_DOWNLOAD] Workspace root path not configured.")
            return create_cors_response({"error": "Server configuration error."}, 500)

        workspace_path = Path(current_args.workspace).resolve() / workspace_id
        if not workspace_path.exists():
            return create_cors_response({"error": f"Workspace not found: {workspace_id}"}, 404)

        # folder_path_str is relative to workspace_id
        target_folder = (workspace_path / folder_path_str.strip('/')).resolve()

        if not str(target_folder).startswith(str(workspace_path)): # Security check
            return create_cors_response({"error": "Access denied"}, 403)
        
        if not target_folder.exists():
            return create_cors_response({"error": f"Path not found: {folder_path_str}"}, 404)
        if not target_folder.is_dir():
            return create_cors_response({"error": f"Path is not a directory: {folder_path_str}"}, 400)

        # Create a temporary zip file
        # tempfile.NamedTemporaryFile is better as it handles cleanup more robustly
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_zip_file:
            zip_file_path = tmp_zip_file.name
        
        logger.info(f"[ZIP_DOWNLOAD] Creating zip file at {zip_file_path} for folder {target_folder}")

        try:
            with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(target_folder):
                    # Skip hidden directories by modifying dirs in place
                    dirs[:] = [d for d in dirs if not d.startswith('.')]
                    
                    for file_item in files: # Renamed to file_item
                        if file_item.startswith('.'): # Skip hidden files
                            continue
                            
                        file_full_path = Path(root) / file_item
                        arcname = file_full_path.relative_to(target_folder)
                        zipf.write(file_full_path, arcname)
            
            zip_filename = f"{target_folder.name or 'workspace'}.zip"
            logger.info(f"[ZIP_DOWNLOAD] Zip file created: {zip_filename}, size: {Path(zip_file_path).stat().st_size} bytes")

            return FileResponse(
                path=zip_file_path,
                filename=zip_filename,
                media_type='application/zip',
                background=lambda: os.unlink(zip_file_path) # Ensure temp file is deleted
            )
        except Exception as e_zip:
            logger.error(f"[ZIP_DOWNLOAD] Error during zip creation for {target_folder}: {e_zip}", exc_info=True)
            if os.path.exists(zip_file_path): # Cleanup on error during zipping
                os.unlink(zip_file_path)
            raise HTTPException(status_code=500, detail=f"Error creating zip file: {str(e_zip)}")

    except Exception as e:
        logger.error(f"[ZIP_DOWNLOAD] Error processing zip download request: {str(e)}", exc_info=True)
        return create_cors_response({"error": f"Error creating zip download: {str(e)}"}, 500)
