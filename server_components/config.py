"""
Manages global application configuration, primarily command-line arguments.
"""
import argparse
import logging
from typing import Optional
from pathlib import Path
import os

logger = logging.getLogger(__name__)

class AppConfig:
    """
    Singleton-like class to hold application configuration, primarily command-line arguments.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(AppConfig, cls).__new__(cls, *args, **kwargs)
            cls._instance.args = None
        return cls._instance

    def set_args(self, args: argparse.Namespace):
        """
        Sets the command-line arguments. This should be called once at startup.
        """
        if self.args is not None:
            logger.warning("Application arguments are being re-set. This is unusual.")
        self.args = args
        logger.info(f"Application arguments set: {args}")

    def get_args(self) -> Optional[argparse.Namespace]:
        """
        Retrieves the stored command-line arguments.
        """
        if self.args is None:
            logger.error("Application arguments accessed before being set. Creating fallback default args.")
            # Create fallback default arguments to prevent server crash
            self.args = self._create_fallback_args()
            logger.info(f"Fallback arguments created: {self.args}")
        return self.args
    
    def _create_fallback_args(self) -> argparse.Namespace:
        """Create fallback default arguments if none were set during startup."""
        # Use persistent storage if available, otherwise local directories
        if os.path.exists("/var/data"):
            workspace_default = "/var/data/workspaces"
            logs_default = "/var/data/logs/agent_logs.txt"
        else:
            workspace_default = "./workspace"
            logs_default = "agent_logs.txt"
        
        # Ensure directories exist
        os.makedirs(workspace_default, exist_ok=True)
        os.makedirs(os.path.dirname(logs_default), exist_ok=True)
        
        fallback_args = argparse.Namespace()
        fallback_args.workspace = workspace_default
        fallback_args.logs_path = logs_default
        fallback_args.needs_permission = False
        fallback_args.use_container_workspace = None
        fallback_args.docker_container_id = None
        fallback_args.minimize_stdout_logs = True
        fallback_args.project_id = None
        fallback_args.region = None
        fallback_args.context_manager = "file-based"
        fallback_args.use_caching = False
        
        return fallback_args

# Global instance of AppConfig
app_config = AppConfig()
