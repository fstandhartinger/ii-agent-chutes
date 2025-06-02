#!/bin/bash
# Startup script that runs both the main application and code-server

set -e

echo "Starting application with VS Code server..."

# Ensure code-server is in PATH
export PATH="$HOME/.local/bin:$PATH"

# Start code-server in the background
echo "Starting code-server..."
cd /opt/render/project/src/workspace
code-server --bind-addr 0.0.0.0:8080 --auth none &
CODE_SERVER_PID=$!

echo "Code-server started with PID: $CODE_SERVER_PID"

# Wait a moment for code-server to start
sleep 2

# Start the main application
echo "Starting main application..."
cd /opt/render/project/src
exec python -m uvicorn ws_server:app --host 0.0.0.0 --port ${PORT:-8000} 