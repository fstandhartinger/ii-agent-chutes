# src/ii_agent/tools/image_generate_tool.py

import os
import aiohttp
import asyncio
import json
from pathlib import Path
from typing import Any, Optional

from ii_agent.tools.base import (
    MessageHistory,
    LLMTool,
    ToolImplOutput,
)
from ii_agent.utils import WorkspaceManager


class ImageGenerateTool(LLMTool):
    name = "generate_image_from_text"
    description = """Generates an image based on a text prompt using Chutes Flux model.
The generated image will be saved to the specified local path in the workspace as a PNG file."""
    input_schema = {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "A detailed description of the image to be generated.",
            },
            "output_filename": {
                "type": "string",
                "description": "The desired relative path for the output PNG image file within the workspace (e.g., 'generated_images/my_image.png'). Must end with .png.",
            },
            "negative_prompt": {
                "type": "string",
                "default": "blur, distortion, low quality",
                "description": "Negative prompt to specify what should not be in the image.",
            },
            "guidance_scale": {
                "type": "number",
                "default": 7.5,
                "description": "How closely to follow the prompt (1.0 to 20.0).",
            },
            "width": {
                "type": "integer",
                "default": 1024,
                "description": "Width of the generated image.",
            },
            "height": {
                "type": "integer",
                "default": 1024,
                "description": "Height of the generated image.",
            },
            "num_inference_steps": {
                "type": "integer",
                "default": 50,
                "description": "Number of inference steps for generation quality.",
            },
        },
        "required": ["prompt", "output_filename"],
    }

    def __init__(self, workspace_manager: WorkspaceManager):
        super().__init__()
        self.workspace_manager = workspace_manager
        self.api_token = os.environ.get("CHUTES_API_KEY")
        if not self.api_token:
            raise ValueError("CHUTES_API_KEY environment variable not set.")

    async def _generate_image_async(self, tool_input: dict[str, Any]) -> dict:
        """Async method to generate image using Chutes API."""
        headers = {
            "Authorization": "Bearer " + self.api_token,
            "Content-Type": "application/json"
        }
        
        body = {
            "prompt": tool_input["prompt"],
            "negative_prompt": tool_input.get("negative_prompt", "blur, distortion, low quality"),
            "guidance_scale": tool_input.get("guidance_scale", 7.5),
            "width": tool_input.get("width", 1024),
            "height": tool_input.get("height", 1024),
            "num_inference_steps": tool_input.get("num_inference_steps", 50)
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://chutes-flux-1-schnell.chutes.ai/generate", 
                headers=headers,
                json=body
            ) as response:
                if response.status != 200:
                    raise Exception(f"API request failed with status {response.status}: {await response.text()}")
                
                # Collect all chunks
                image_data = b""
                async for chunk in response.content.iter_chunked(8192):
                    image_data += chunk
                
                return {"image_data": image_data}

    def run_impl(
        self,
        tool_input: dict[str, Any],
        message_history: Optional[MessageHistory] = None,
    ) -> ToolImplOutput:
        prompt = tool_input["prompt"]
        relative_output_filename = tool_input["output_filename"]

        if not relative_output_filename.lower().endswith(".png"):
            return ToolImplOutput(
                "Error: output_filename must end with .png for image generation.",
                "Invalid output filename for image.",
                {"success": False, "error": "Output filename must be .png"},
            )

        local_output_path = self.workspace_manager.workspace_path(
            Path(relative_output_filename)
        )
        local_output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Run the async function
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(self._generate_image_async(tool_input))
            finally:
                loop.close()

            # Save the image data to file
            with open(local_output_path, 'wb') as f:
                f.write(result["image_data"])

            output_url = (
                f"http://localhost:{self.workspace_manager.file_server_port}/workspace/{relative_output_filename}"
                if hasattr(self.workspace_manager, "file_server_port")
                else f"(Local path: {relative_output_filename})"
            )

            return ToolImplOutput(
                f"Successfully generated image from text and saved to '{relative_output_filename}'. View at: {output_url}",
                f"Image generated and saved to {relative_output_filename}",
                {
                    "success": True,
                    "output_path": relative_output_filename,
                    "url": output_url,
                },
            )

        except Exception as e:
            return ToolImplOutput(
                f"Error generating image from text: {str(e)}",
                "Failed to generate image from text.",
                {"success": False, "error": str(e)},
            )

    def get_tool_start_message(self, tool_input: dict[str, Any]) -> str:
        return f"Generating image from text prompt, saving to: {tool_input['output_filename']}"


if __name__ == "__main__":
    workspace_manager = WorkspaceManager(root="workspace")
    tool = ImageGenerateTool(workspace_manager)
    print(tool.run_impl({"prompt": "A photo of a cat", "output_filename": "cat.png"}))
