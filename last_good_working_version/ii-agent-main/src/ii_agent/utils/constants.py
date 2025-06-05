UPLOAD_FOLDER_NAME = "uploaded_files"
COMPLETE_MESSAGE = "Completed the task."
DEFAULT_MOPUS_4 = "claude-opus-4-0"

# New Google and OpenAI Models (Pro, cost 1 sonnet_request)
GEMINI_2_5_PRO = "google/gemini-2.5-pro-preview"
GPT_4_1 = "openai/gpt-4.1"
GEMINI_2_5_FLASH_THINKING = "google/gemini-2.5-flash-preview-05-20:thinking"

# OpenRouter model identifiers for Pro plan (cost 0 sonnet_requests)
PERSISTENT_DATA_ROOT = "/var/data"
PERSISTENT_WORKSPACE_ROOT = f"{PERSISTENT_DATA_ROOT}/workspace"
PERSISTENT_DB_PATH = f"{PERSISTENT_DATA_ROOT}/events.db"
PERSISTENT_LOGS_PATH = f"{PERSISTENT_DATA_ROOT}/agent_logs.txt"
