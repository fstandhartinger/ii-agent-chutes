"""
Handles administrative API routes for server management, Pro key generation, and statistics.
"""
import os
import logging
import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from fastapi.responses import JSONResponse, FileResponse

from ii_agent.db.manager import DatabaseManager
from ii_agent.db.models import Event # Assuming Event model might be used in stats or cleanup
from ii_agent.utils.pro_utils import generate_pro_key as util_generate_pro_key, validate_pro_key
from ii_agent.utils.constants import PERSISTENT_WORKSPACE_ROOT, PERSISTENT_DATA_ROOT

from .common import create_cors_response # Relative import

# Attempt to import psutil for system stats, but allow it to be optional
try:
    import psutil
except ImportError:
    psutil = None
    logging.getLogger(__name__).warning("psutil module not found. System statistics will be limited.")


logger = logging.getLogger(__name__)
router = APIRouter()

# Admin Key Management
ADMIN_KEY_ENV = os.getenv("ADMIN_KEY")

async def verify_admin_key(authorization: str = Header(None), admin_key_query: str = Query(None, alias="admin_key")):
    """
    Verify admin authentication via Bearer token or query parameter.
    Query parameter is checked first, then Bearer token.
    """
    if not ADMIN_KEY_ENV:
        logger.error("ADMIN_KEY environment variable is not set. Admin endpoints are disabled.")
        raise HTTPException(status_code=503, detail="Admin functionality not configured.")

    provided_key = admin_key_query # Check query param first

    if not provided_key and authorization: # If not in query, check header
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer":
            provided_key = token
        else: # If header is present but not Bearer, it might be the key directly
            provided_key = authorization


    if not provided_key:
        logger.warning("Admin access attempt without key.")
        raise HTTPException(status_code=401, detail="Not authenticated: Admin key required.")
    
    if provided_key != ADMIN_KEY_ENV:
        logger.warning("Admin access attempt with invalid key.")
        raise HTTPException(status_code=401, detail="Invalid authentication credentials.")
    
    logger.info("Admin access verified.")
    return True

# Helper functions for stats
def get_folder_size(folder_path: str) -> int:
    total_size = 0
    try:
        for dirpath, _, filenames in os.walk(folder_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if not os.path.islink(fp):
                    try:
                        total_size += os.path.getsize(fp)
                    except FileNotFoundError:
                        logger.warning(f"File not found during size calculation: {fp}")
    except Exception as e:
        logger.error(f"Error calculating folder size for {folder_path}: {e}")
    return total_size

def format_bytes(size_bytes: int) -> str:
    if size_bytes < 1024: return f"{size_bytes} B"
    if size_bytes < 1024**2: return f"{size_bytes/1024:.2f} KB"
    if size_bytes < 1024**3: return f"{size_bytes/1024**2:.2f} MB"
    return f"{size_bytes/1024**3:.2f} GB"


@router.get("/admin/generate_pro_key", dependencies=[Depends(verify_admin_key)])
async def generate_pro_key_admin_endpoint():
    """Generate a new Pro key (admin only)."""
    try:
        new_key = util_generate_pro_key()
        logger.info(f"Admin: Generated new Pro key: {new_key}")
        
        email_text = f"""Hey NAME!

Thank you for signing up for the Pro account!

Open the app using this url and the device will be registered as a Pro-Account-Device:
https://fubea.cloud?pro_user_key={new_key}

Let me know how everything works for you – or if something doesn’t.

Have a nice day, best regards

Florian"""
        
        return Response(content=email_text, media_type="text/plain")
    except Exception as e:
        logger.error(f"Admin: Error generating Pro key: {str(e)}", exc_info=True)
        # Return a plain text error response as well, for consistency
        return Response(content=f"Error generating Pro key: {str(e)}", media_type="text/plain", status_code=500)


@router.get("/api/pro/usage/{pro_key}") # No admin lock, user-facing
async def get_pro_usage_endpoint(pro_key: str):
    """Get usage statistics for a Pro key."""
    try:
        if not validate_pro_key(pro_key): # Assuming validate_pro_key checks format/existence
            logger.warning(f"Pro Usage API: Invalid Pro key format or key not found: {pro_key}")
            return create_cors_response({"error": "Invalid Pro key"}, 400)
        
        db_manager = DatabaseManager()
        usage_stats = db_manager.get_pro_usage(pro_key) # Assuming this method exists
        
        logger.info(f"Pro Usage API: Retrieved usage for key {pro_key[:4]}****: {usage_stats}")
        return create_cors_response(usage_stats)
    except Exception as e:
        logger.error(f"Pro Usage API: Error getting Pro usage for key {pro_key[:4]}****: {str(e)}", exc_info=True)
        return create_cors_response({"error": f"Error getting Pro usage: {str(e)}"}, 500)


@router.get("/admin/stats", dependencies=[Depends(verify_admin_key)])
async def get_admin_stats_endpoint():
    """Get comprehensive server statistics (admin only)."""
    stats = {"server_time": datetime.utcnow().isoformat() + "Z"}

    if psutil:
        try:
            cpu_usage = psutil.cpu_percent(interval=0.1)
            memory_info = psutil.virtual_memory()
            # Check if root path '/' is appropriate or if a specific persistent volume mount point should be used
            disk_usage_path = PERSISTENT_DATA_ROOT if Path(PERSISTENT_DATA_ROOT).exists() else '/'
            disk_info = psutil.disk_usage(disk_usage_path)
            stats["system"] = {
                "cpu_usage_percent": cpu_usage,
                "memory_total": format_bytes(memory_info.total),
                "memory_used": format_bytes(memory_info.used),
                "memory_percent": memory_info.percent,
                "disk_path_checked": disk_usage_path,
                "disk_total": format_bytes(disk_info.total),
                "disk_used": format_bytes(disk_info.used),
                "disk_percent": disk_info.percent,
            }
        except Exception as e:
            logger.error(f"Admin Stats: Error getting system stats with psutil: {e}", exc_info=True)
            stats["system"] = {"error": str(e)}
    else:
        stats["system"] = {"status": "psutil not available, system stats limited"}

    try:
        db_manager = DatabaseManager()
        db_path_actual = db_manager.db_path # This should be the actual path from the manager
        
        db_size_bytes = 0
        if Path(db_path_actual).exists():
            db_size_bytes = Path(db_path_actual).stat().st_size
        
        with db_manager.get_session() as db_sess:
            event_count = db_sess.query(Event).count()
            # Assuming Session model exists and is imported
            from ii_agent.db.models import Session as DBSessionModel
            unique_db_sessions = db_sess.query(DBSessionModel.id).distinct().count()

        stats["database"] = {
            "db_path": str(db_path_actual),
            "db_size": format_bytes(db_size_bytes),
            "event_count": event_count,
            "unique_sessions_in_db": unique_db_sessions,
        }
    except Exception as e:
        logger.error(f"Admin Stats: Error getting database stats: {e}", exc_info=True)
        stats["database"] = {"error": str(e)}

    try:
        workspace_root = Path(PERSISTENT_WORKSPACE_ROOT)
        num_workspaces = 0
        total_workspace_size_bytes = 0
        if workspace_root.exists() and workspace_root.is_dir():
            workspaces = [d for d in workspace_root.iterdir() if d.is_dir()]
            num_workspaces = len(workspaces)
            # Consider sampling size calculation if too slow for many workspaces
            total_workspace_size_bytes = get_folder_size(str(workspace_root))
        
        stats["workspace"] = {
            "path": str(workspace_root),
            "num_workspaces": num_workspaces,
            "total_size": format_bytes(total_workspace_size_bytes),
        }
    except Exception as e:
        logger.error(f"Admin Stats: Error getting workspace stats: {e}", exc_info=True)
        stats["workspace"] = {"error": str(e)}

    try:
        # Assuming logs are in a known location, adjust if necessary
        log_file_path = Path(PERSISTENT_DATA_ROOT) / "agent_logs.txt" # Example path
        log_size_bytes = 0
        if log_file_path.exists() and log_file_path.is_file():
            log_size_bytes = log_file_path.stat().st_size
        stats["logs"] = {
            "path": str(log_file_path),
            "size": format_bytes(log_size_bytes),
            "note": "This is an example log path, actual path might differ."
        }
    except Exception as e:
        logger.error(f"Admin Stats: Error getting log stats: {e}", exc_info=True)
        stats["logs"] = {"error": str(e)}
        
    logger.info("Admin Stats: Successfully retrieved server statistics.")
    return create_cors_response(stats)


@router.post("/admin/cleanup", dependencies=[Depends(verify_admin_key)])
async def cleanup_data_endpoint():
    """Clean up old workspaces and database entries (admin only)."""
    MAX_WORKSPACES_TO_DELETE = int(os.getenv("ADMIN_CLEANUP_MAX_WORKSPACES", "1000"))
    MAX_DB_ROWS_TO_DELETE = int(os.getenv("ADMIN_CLEANUP_MAX_DB_ROWS", "10000"))
    # Target bytes to free, e.g., 200MB. Set to 0 to disable size-based limit.
    TARGET_WORKSPACE_BYTES_TO_DELETE = int(os.getenv("ADMIN_CLEANUP_TARGET_BYTES", f"{200 * 1024 * 1024}"))


    report = {
        "workspaces_deleted_count": 0,
        "bytes_freed_from_workspaces": 0,
        "db_event_rows_deleted": 0,
        "errors": []
    }
    logger.info(f"Admin Cleanup: Starting. Max WS: {MAX_WORKSPACES_TO_DELETE}, Max DB Rows: {MAX_DB_ROWS_TO_DELETE}, Target Bytes: {TARGET_WORKSPACE_BYTES_TO_DELETE}")

    # Workspace Cleanup
    try:
        workspace_root = Path(PERSISTENT_WORKSPACE_ROOT)
        if workspace_root.exists() and workspace_root.is_dir():
            workspaces_info = []
            for item in workspace_root.iterdir():
                if item.is_dir():
                    try:
                        mtime = item.stat().st_mtime
                        # Size calculation can be slow, consider sampling or skipping for many small workspaces
                        # For now, calculating size for each.
                        size = get_folder_size(str(item)) 
                        workspaces_info.append({"path": item, "mtime": mtime, "size": size})
                    except Exception as e_stat:
                        logger.warning(f"Admin Cleanup: Could not stat/size workspace {item}: {e_stat}")
            
            workspaces_info.sort(key=lambda x: x["mtime"]) # Oldest first

            for ws_info in workspaces_info:
                if report["workspaces_deleted_count"] >= MAX_WORKSPACES_TO_DELETE: break
                if TARGET_WORKSPACE_BYTES_TO_DELETE > 0 and report["bytes_freed_from_workspaces"] >= TARGET_WORKSPACE_BYTES_TO_DELETE: break
                
                try:
                    shutil.rmtree(ws_info["path"])
                    logger.info(f"Admin Cleanup: Deleted workspace {ws_info['path']} (size: {format_bytes(ws_info['size'])}, mtime: {datetime.fromtimestamp(ws_info['mtime'])})")
                    report["bytes_freed_from_workspaces"] += ws_info["size"]
                    report["workspaces_deleted_count"] += 1
                except Exception as e_del_ws:
                    err_msg = f"Admin Cleanup: Error deleting workspace {ws_info['path']}: {e_del_ws}"
                    logger.error(err_msg)
                    report["errors"].append(err_msg)
    except Exception as e_ws_clean:
        err_msg = f"Admin Cleanup: Error during workspace cleanup process: {e_ws_clean}"
        logger.error(err_msg, exc_info=True)
        report["errors"].append(err_msg)

    # Database Cleanup (Events table)
    try:
        db_manager = DatabaseManager()
        with db_manager.get_session() as session:
            # Delete oldest events
            oldest_events_query = session.query(Event).order_by(Event.timestamp.asc()).limit(MAX_DB_ROWS_TO_DELETE)
            
            # For bulk delete, more efficient to get IDs then delete by IDs if ORM supports it well,
            # or use a direct delete statement. For now, iterating.
            events_to_delete = oldest_events_query.all()
            num_to_delete = len(events_to_delete)

            if num_to_delete > 0:
                for event_record in events_to_delete:
                    session.delete(event_record)
                session.commit()
                report["db_event_rows_deleted"] = num_to_delete
                logger.info(f"Admin Cleanup: Deleted {num_to_delete} oldest rows from Event table.")
            else:
                logger.info("Admin Cleanup: No old rows found in Event table to delete based on current limits.")
                
    except Exception as e_db_clean:
        err_msg = f"Admin Cleanup: Error during database cleanup: {e_db_clean}"
        logger.error(err_msg, exc_info=True)
        report["errors"].append(err_msg)

    logger.info(f"Admin Cleanup: Finished. Report: {report}")
    return create_cors_response(report)


@router.get("/admin/download_data", dependencies=[Depends(verify_admin_key)])
async def download_data_endpoint():
    """Download server data as ZIP file (excluding workspaces due to size, admin only)."""
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_zip_file_obj:
        zip_file_path = tmp_zip_file_obj.name # Get path from the temp file object
    
    zip_filename = f"server_data_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.zip"
    logger.info(f"Admin Download: Preparing data zip: {zip_filename} at temp path {zip_file_path}")
    
    try:
        with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Database
            db_manager = DatabaseManager()
            actual_db_path = Path(db_manager.db_path)
            if actual_db_path.exists() and actual_db_path.is_file():
                zf.write(actual_db_path, arcname=actual_db_path.name)
                logger.info(f"Admin Download: Added database '{actual_db_path.name}' to zip.")
            else:
                logger.warning(f"Admin Download: Database file not found at {actual_db_path}")

            # Logs (example path, adjust if your logging setup is different)
            # This assumes global_args is set and has logs_path. If not, this needs adjustment.
            # from .config import app_config
            # current_args = app_config.get_args()
            # log_file_path_str = getattr(current_args, 'logs_path', None)
            # A more robust way might be to have a known log file location.
            # For now, using a common persistent path.
            log_file_path = Path(PERSISTENT_DATA_ROOT) / "agent_logs.txt" # Example
            if log_file_path.exists() and log_file_path.is_file():
                zf.write(log_file_path, arcname=log_file_path.name)
                logger.info(f"Admin Download: Added log file '{log_file_path.name}' to zip.")
            else:
                logger.warning(f"Admin Download: Log file not found at {log_file_path}")
            
            readme_content = f"""Server Data Backup - {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
This backup contains:
- Database file (e.g., agent.db)
- Log files (e.g., agent_logs.txt)

NOT included (due to size constraints and potential server load):
- Workspace folders from {PERSISTENT_WORKSPACE_ROOT}

Backup workspaces separately (e.g., via rsync, cloud sync, or direct server access).
"""
            zf.writestr("README_backup_contents.txt", readme_content)
        
        logger.info(f"Admin Download: Zip file created successfully: {zip_file_path}")
        return FileResponse(
            path=zip_file_path,
            filename=zip_filename,
            media_type='application/zip',
            background=lambda: os.unlink(zip_file_path) # Cleanup after response sent
        )
    except Exception as e:
        logger.error(f"Admin Download: Error creating data zip: {e}", exc_info=True)
        if os.path.exists(zip_file_path): # Ensure cleanup on error
            os.unlink(zip_file_path)
        raise HTTPException(status_code=500, detail=f"Failed to create data zip: {str(e)}")
