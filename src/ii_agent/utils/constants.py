UPLOAD_FOLDER_NAME = "uploaded_files"
COMPLETE_MESSAGE = "Completed the task."
SONNET_4 = "claude-sonnet-4-0"
OPUS_4 = "claude-opus-4-0"

# OpenRouter model identifiers for Pro plan
QWEN3_32B_FAST = "qwen/qwen3-32b:fast"
LLAMA_4_MAVERICK_FAST = "meta-llama/llama-4-maverick:fast"
R1_DISTILL_LLAMA_70B_FAST = "deepseek/deepseek-r1-distill-llama-70b:fast"

# New premium models
GEMINI_2_5_PRO = "google/gemini-2.5-pro-preview"
GPT_4_1 = "openai/gpt-4.1"
GEMINI_2_5_FLASH_THINKING = "google/gemini-2.5-flash-preview-05-20:thinking"
OPENAI_O3 = "openai/o3"

# List of new premium models that cost 1 credit
NEW_PREMIUM_MODELS_ONE_CREDIT = [
    GEMINI_2_5_PRO,
    GPT_4_1,
    GEMINI_2_5_FLASH_THINKING,
    OPENAI_O3,
]

# List of premium models that cost 3 credits
NEW_PREMIUM_MODELS_THREE_CREDITS = [
]

# Persistent data paths for render.com deployment
PERSISTENT_DATA_ROOT = "/var/data"
PERSISTENT_WORKSPACE_ROOT = f"{PERSISTENT_DATA_ROOT}/workspace"
PERSISTENT_DB_PATH = f"{PERSISTENT_DATA_ROOT}/events.db"
PERSISTENT_LOGS_PATH = f"{PERSISTENT_DATA_ROOT}/agent_logs.txt"
