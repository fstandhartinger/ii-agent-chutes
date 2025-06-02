UPLOAD_FOLDER_NAME = "uploaded_files"
COMPLETE_MESSAGE = "Completed the task."
SONNET_4 = "claude-sonnet-4-0"
OPUS_4 = "claude-opus-4-0"

# OpenRouter model identifiers for Pro plan
QWEN3_32B_FAST = "qwen/qwen3-32b:fast"
LLAMA_4_MAVERICK_FAST = "meta-llama/llama-4-maverick:fast"
R1_DISTILL_LLAMA_70B_FAST = "deepseek/deepseek-r1-distill-llama-70b:fast"

# Persistent data paths for render.com deployment
PERSISTENT_DATA_ROOT = "/var/data"
PERSISTENT_WORKSPACE_ROOT = f"{PERSISTENT_DATA_ROOT}/workspace"
PERSISTENT_DB_PATH = f"{PERSISTENT_DATA_ROOT}/events.db"
PERSISTENT_LOGS_PATH = f"{PERSISTENT_DATA_ROOT}/agent_logs.txt"
