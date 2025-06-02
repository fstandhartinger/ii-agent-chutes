# src/ii_agent/tools/video_generate_from_text_tool.py
import os
from pathlib import Path
from typing import Any, Optional

from ii_agent.tools.base import (
    MessageHistory,
    LLMTool,
    ToolImplOutput,
)
from ii_agent.utils import WorkspaceManager


class VideoGenerateFromTextTool(LLMTool):
    name = "generate_video_from_text"
    description = """Generates a short video based on a text prompt. Currently not supported."""
    input_schema = {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "A detailed description of the video to be generated.",
            },
            "output_filename": {
                "type": "string",
                "description": "The desired relative path for the output MP4 video file within the workspace (e.g., 'generated_videos/my_video.mp4'). Must end with .mp4.",
            },
        },
        "required": ["prompt", "output_filename"],
    }

    def __init__(self, workspace_manager: WorkspaceManager):
        super().__init__()
        self.workspace_manager = workspace_manager

    def run_impl(
        self,
        tool_input: dict[str, Any],
        message_history: Optional[MessageHistory] = None,
    ) -> ToolImplOutput:
        return ToolImplOutput(
            "Error: Video generation is currently not supported.",
            "Video generation not supported.",
            {"success": False, "error": "Video generation is currently not supported"},
        )

    def get_tool_start_message(self, tool_input: dict[str, Any]) -> str:
        return f"Video generation is not supported"


class VideoGenerateFromImageTool(LLMTool):
    name = "generate_video_from_image"
    description = """Generates a short video by adding motion to an input image. Currently not supported."""
    input_schema = {
        "type": "object",
        "properties": {
            "image_file_path": {
                "type": "string",
                "description": "The relative path to the input image file within the workspace (e.g., 'uploads/my_image.png').",
            },
            "output_filename": {
                "type": "string",
                "description": "The desired relative path for the output MP4 video file within the workspace (e.g., 'generated_videos/animated_image.mp4'). Must end with .mp4.",
            },
        },
        "required": ["image_file_path", "output_filename"],
    }

    def __init__(self, workspace_manager: WorkspaceManager):
        super().__init__()
        self.workspace_manager = workspace_manager

    def run_impl(
        self,
        tool_input: dict[str, Any],
        message_history: Optional[MessageHistory] = None,
    ) -> ToolImplOutput:
        return ToolImplOutput(
            "Error: Video generation is currently not supported.",
            "Video generation not supported.",
            {"success": False, "error": "Video generation is currently not supported"},
        )

    def get_tool_start_message(self, tool_input: dict[str, Any]) -> str:
        return f"Video generation is not supported"
