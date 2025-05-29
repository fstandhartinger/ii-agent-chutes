from argparse import ArgumentParser
import uuid
import os
from pathlib import Path
from ii_agent.utils import WorkspaceManager
from ii_agent.utils.constants import (
    PERSISTENT_DATA_ROOT,
    PERSISTENT_WORKSPACE_ROOT,
    PERSISTENT_DB_PATH,
    PERSISTENT_LOGS_PATH,
)


def get_persistent_path(default_path: str, persistent_path: str) -> str:
    """Get the appropriate path based on whether persistent storage is available.
    
    Args:
        default_path: The default local path
        persistent_path: The persistent storage path
        
    Returns:
        The path to use (persistent if available, otherwise default)
    """
    if os.path.exists(PERSISTENT_DATA_ROOT):
        # Ensure the persistent directory exists
        os.makedirs(os.path.dirname(persistent_path), exist_ok=True)
        return persistent_path
    return default_path


def parse_common_args(parser: ArgumentParser):
    # Determine workspace path based on persistent storage availability
    default_workspace = get_persistent_path("./workspace", PERSISTENT_WORKSPACE_ROOT)
    default_logs = get_persistent_path("agent_logs.txt", PERSISTENT_LOGS_PATH)
    
    parser.add_argument(
        "--workspace",
        type=str,
        default=default_workspace,
        help="Path to the workspace",
    )
    parser.add_argument(
        "--logs-path",
        type=str,
        default=default_logs,
        help="Path to save logs",
    )
    parser.add_argument(
        "--needs-permission",
        "-p",
        help="Ask for permission before executing commands",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--use-container-workspace",
        type=str,
        default=None,
        help="(Optional) Path to the container workspace to run commands in.",
    )
    parser.add_argument(
        "--docker-container-id",
        type=str,
        default=None,
        help="(Optional) Docker container ID to run commands in.",
    )
    parser.add_argument(
        "--minimize-stdout-logs",
        help="Minimize the amount of logs printed to stdout.",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--project-id",
        type=str,
        default=None,
        help="Project ID to use for Anthropic",
    )
    parser.add_argument(
        "--region",
        type=str,
        default=None,
        help="Region to use for Anthropic",
    )
    parser.add_argument(
        "--context-manager",
        type=str,
        default="file-based",
        choices=["file-based", "standard"],
        help="Type of context manager to use (file-based or standard)",
    )
    return parser


def create_workspace_manager_for_connection(
    workspace_root: str, use_container_workspace: bool = False
):
    """Create a new workspace manager instance for a websocket connection."""
    # Create unique subdirectory for this connection
    connection_uuid = uuid.uuid4()  # Keep as UUID object
    workspace_path = Path(workspace_root).resolve()
    connection_workspace = workspace_path / str(connection_uuid)  # Convert to string only for path
    connection_workspace.mkdir(parents=True, exist_ok=True)

    # Initialize workspace manager with connection-specific subdirectory
    workspace_manager = WorkspaceManager(
        root=connection_workspace,
        container_workspace=use_container_workspace,
    )

    return workspace_manager, connection_uuid  # Return UUID object
