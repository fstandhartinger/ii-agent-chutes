from pydantic import BaseModel
from typing import Any
import enum


class EventType(str, enum.Enum):
    CONNECTION_ESTABLISHED = "connection_established"
    AGENT_INITIALIZED = "agent_initialized"
    WORKSPACE_INFO = "workspace_info"
    WORKSPACE_INFO_REQUEST = "workspace_info_request"
    PROCESSING = "processing"
    AGENT_THINKING = "agent_thinking"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    AGENT_RESPONSE = "agent_response"
    STREAM_COMPLETE = "stream_complete"
    ERROR = "error"
    SYSTEM = "system"
    PING = "ping"
    PONG = "pong"
    UPLOAD_SUCCESS = "upload_success"
    BROWSER_USE = "browser_use"
    FILE_EDIT = "file_edit"
    USER_MESSAGE = "user_message"
    INIT_AGENT = "init_agent"
    QUERY = "query"
    CANCEL_PROCESSING = "cancel_processing"
    HEARTBEAT = "heartbeat"
    TERMINAL_COMMAND = "terminal_command"
    TERMINAL_OUTPUT = "terminal_output"


class RealtimeEvent(BaseModel):
    type: EventType
    content: dict[str, Any]
