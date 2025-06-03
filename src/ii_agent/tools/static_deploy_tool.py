from typing import Any, Optional
from pathlib import Path
import os

from ii_agent.tools.base import (
    ToolImplOutput,
    LLMTool,
)
from ii_agent.llm.message_history import MessageHistory
from ii_agent.utils import WorkspaceManager


class StaticDeployTool(LLMTool):
    """Tool for managing static file deployments"""

    name = "static_deploy"
    description = "Get the public URL for static files or directories in the workspace. Use this tool to make files accessible via HTTP URLs for download or viewing. Always call this tool when you need to provide a file URL to the user. For directories, all files within will be made accessible."

    input_schema = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the static file or directory (relative to workspace). For directories, all contained files will be made accessible.",
            }
        },
        "required": ["file_path"],
    }

    def __init__(self, workspace_manager: WorkspaceManager):
        super().__init__()
        self.workspace_manager = workspace_manager
        # Use a proper default base URL that works with the WebSocket server
        default_base_url = "http://localhost:8000"
        self.base_url = os.getenv("STATIC_FILE_BASE_URL", default_base_url)

    def run_impl(
        self,
        tool_input: dict[str, Any],
        message_history: Optional[MessageHistory] = None,
    ) -> ToolImplOutput:
        file_path = tool_input["file_path"]
        ws_path = self.workspace_manager.workspace_path(Path(file_path))

        # Validate path exists
        if not ws_path.exists():
            return ToolImplOutput(
                f"Path does not exist: {file_path}",
                f"Path does not exist: {file_path}",
            )

        # Get the UUID from the workspace path (it's the last directory in the path)
        connection_uuid = self.workspace_manager.root.name

        # Handle both files and directories
        if ws_path.is_file():
            # Single file deployment
            rel_path = ws_path.relative_to(self.workspace_manager.root)
            public_url = f"{self.base_url}/workspace/{connection_uuid}/{rel_path}"
            
            return ToolImplOutput(
                public_url,
                f"Static file available at: {public_url}",
            )
            
        elif ws_path.is_dir():
            # Directory deployment - make all files accessible
            rel_path = ws_path.relative_to(self.workspace_manager.root)
            base_public_url = f"{self.base_url}/workspace/{connection_uuid}/{rel_path}"
            
            # Count files in directory for reporting
            file_count = sum(1 for p in ws_path.rglob('*') if p.is_file())
            
            # For directories, return the base URL where files can be accessed
            return ToolImplOutput(
                base_public_url,
                f"Static directory deployed: {base_public_url} (contains {file_count} files - all files within this directory are now accessible via HTTP)",
            )
        
        else:
            return ToolImplOutput(
                f"Path is neither a file nor directory: {file_path}",
                f"Path is neither a file nor directory: {file_path}",
            )
