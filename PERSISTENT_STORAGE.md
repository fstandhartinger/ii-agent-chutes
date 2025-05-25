# Persistent Storage Implementation

This document describes the persistent storage implementation for ii-agent-chutes, which allows data to persist across deployments when using Render.com's persistent disk feature.

## Overview

The application now supports persistent storage at `/var/data` for production deployments. When this directory is available (e.g., on Render.com with a persistent disk), all important data will be stored there instead of in local directories that get wiped on each deployment.

## What Gets Stored Persistently

### 1. Session Database (`events.db`)
- **Local path**: `./events.db`
- **Persistent path**: `/var/data/events.db`
- Contains all session metadata, events, and conversation history

### 2. Workspace Files
- **Local path**: `./workspace/{session_uuid}/`
- **Persistent path**: `/var/data/workspace/{session_uuid}/`
- Contains all files created, uploaded, or generated during sessions:
  - Uploaded files (`uploaded_files/`)
  - Generated images, audio, videos
  - Code files created by the agent
  - Agent memory files (`agent_memory/`)

### 3. Application Logs
- **Local path**: `./agent_logs.txt`
- **Persistent path**: `/var/data/agent_logs.txt`
- Contains application and agent execution logs

## How It Works

### Automatic Detection
The application automatically detects if persistent storage is available by checking for the existence of `/var/data`. If found, it uses persistent paths; otherwise, it falls back to local storage.

### Path Resolution
The `get_persistent_path()` function in `utils.py` handles path resolution:

```python
def get_persistent_path(default_path: str, persistent_path: str) -> str:
    """Get the appropriate path based on whether persistent storage is available."""
    if os.path.exists(PERSISTENT_DATA_ROOT):
        os.makedirs(os.path.dirname(persistent_path), exist_ok=True)
        return persistent_path
    return default_path
```

### Components Updated

1. **Database Manager** (`src/ii_agent/db/manager.py`)
   - Automatically uses persistent database path when available

2. **Workspace Manager** (`src/ii_agent/utils/workspace_manager.py`)
   - Handles workspace paths for both local and persistent storage

3. **CLI and Server** (`cli.py`, `ws_server.py`)
   - Use persistent paths for workspace and logs

4. **GAIA Evaluation** (`run_gaia.py`)
   - Uses persistent storage for evaluation workspaces

## File Storage Functionalities

### Static Deploy Tool (`TOOL.STATIC_DEPLOY`)
- Serves files from workspace directories via HTTP
- Automatically works with persistent storage paths
- URLs remain consistent regardless of storage location

### Sessions (Left Drawer)
- Session metadata stored in persistent database
- Session history preserved across deployments
- Workspace files remain accessible

### Share Button
- Shared session URLs continue to work
- Session replay functionality preserved
- All shared content remains available

## Setup and Migration

### For New Deployments
No additional setup required. The application will automatically use persistent storage if `/var/data` exists.

### For Existing Deployments
Use the migration script to move existing data to persistent storage:

```bash
python scripts/setup_persistent_storage.py
```

This script will:
1. Check if persistent storage is available
2. Create necessary directory structure
3. Migrate existing database, workspace files, and logs
4. Update database paths to use persistent storage

### Manual Setup
If you need to manually set up persistent storage:

1. Ensure `/var/data` exists and is writable
2. Create directory structure:
   ```bash
   mkdir -p /var/data/workspace
   ```
3. Move existing files:
   ```bash
   mv events.db /var/data/
   mv workspace/* /var/data/workspace/
   mv agent_logs.txt /var/data/
   ```

## Environment Variables

No environment variables are required. The application automatically detects and uses persistent storage when available.

## Render.com Configuration

To use persistent storage on Render.com:

1. Add a persistent disk to your service
2. Mount it at `/var/data`
3. Deploy your application

The application will automatically detect and use the persistent disk.

## Monitoring

### Logs
Check application logs for storage type being used:
- `"Using persistent storage for workspace files"`
- `"Using local storage for workspace files"`

### File Locations
Verify files are being created in the correct locations:
- Database: `/var/data/events.db` (persistent) or `./events.db` (local)
- Workspaces: `/var/data/workspace/` (persistent) or `./workspace/` (local)
- Logs: `/var/data/agent_logs.txt` (persistent) or `./agent_logs.txt` (local)

## Troubleshooting

### Persistent Storage Not Detected
- Verify `/var/data` exists and is writable
- Check file permissions
- Review application logs for error messages

### Migration Issues
- Ensure sufficient disk space
- Check file permissions on source and destination
- Run migration script with appropriate privileges

### Session History Missing
- Verify database was migrated correctly
- Check database file exists at persistent path
- Ensure workspace directories were migrated

## Benefits

1. **Data Persistence**: Sessions, files, and history survive deployments
2. **Seamless Experience**: Users can continue conversations after deployments
3. **File Availability**: Generated content remains accessible
4. **Automatic Fallback**: Works in both local development and production
5. **Zero Configuration**: No manual setup required for new deployments

## Technical Details

### Constants
All persistent storage paths are defined in `src/ii_agent/utils/constants.py`:

```python
PERSISTENT_DATA_ROOT = "/var/data"
PERSISTENT_WORKSPACE_ROOT = f"{PERSISTENT_DATA_ROOT}/workspace"
PERSISTENT_DB_PATH = f"{PERSISTENT_DATA_ROOT}/events.db"
PERSISTENT_LOGS_PATH = f"{PERSISTENT_DATA_ROOT}/agent_logs.txt"
```

### Database Schema
No changes to the database schema were required. The existing session and event tables work seamlessly with persistent storage.

### File Structure
```
/var/data/
├── events.db                 # Session database
├── agent_logs.txt           # Application logs
└── workspace/               # Session workspaces
    ├── {session-uuid-1}/
    │   ├── uploaded_files/  # User uploads
    │   ├── agent_memory/    # Context manager files
    │   └── ...              # Generated content
    └── {session-uuid-2}/
        └── ...
``` 