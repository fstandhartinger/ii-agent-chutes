# Chutes Tool Calling and Browser Improvements

This document outlines the improvements made to address tool calling reliability issues with Chutes models and Playwright/Chrome browser problems.

## Issues Addressed

### 1. Tool Call Reliability Issues

**Problems identified:**
- Inconsistent JSON parsing of tool calls from Chutes models
- Tool call loops where models get stuck calling the same tool repeatedly
- Poor tool call format leading to parsing failures
- Models not making progress when using `sequential_thinking` tool

**Solutions implemented:**

#### Enhanced JSON Parsing
- **Multiple JSON patterns**: Added support for various JSON formats including:
  - Standard JSON blocks: ````json {...} ````
  - JSON blocks without label: ````{...}````
  - Inline JSON with tool_call: `{..."tool_call"...}`
- **Better error handling**: Improved error recovery and logging for failed JSON parsing
- **Validation**: Added validation to ensure tool calls have required fields

#### Loop Detection
- **Tool call loop prevention**: Added `_is_tool_call_loop()` method to detect repeated tool calls
- **Special handling for sequential_thinking**: More aggressive loop detection for this tool
- **Recent history analysis**: Checks last 6 messages for repeated patterns

#### Improved Instructions
- **Enhanced system prompts**: More explicit instructions about tool usage
- **Anti-loop rules**: Clear guidelines about not repeating failed tool calls
- **Single tool call enforcement**: Prevents multiple tool calls in one response

### 2. Playwright/Chrome Browser Issues

**Problems identified:**
- Missing Playwright browsers on deployment servers
- `BrowserType.launch: Executable doesn't exist` errors
- No fallback for headless mode when GUI mode fails

**Solutions implemented:**

#### Browser Launch Improvements
- **Fallback to headless mode**: If GUI mode fails, automatically try headless mode
- **Better error messages**: Clear instructions about running `playwright install chromium`
- **Additional browser arguments**: Added `--disable-dev-shm-usage` and `--disable-gpu` for server environments

#### Deployment Scripts
- **`scripts/install_playwright.py`**: Python script to install Playwright browsers
- **`scripts/setup_deployment.sh`**: Shell script for deployment environments
- **Automated installation**: Can be integrated into build/deployment processes

## Code Changes

### 1. Enhanced Chutes OpenAI Client (`src/ii_agent/llm/chutes_openai.py`)

```python
# Improved tool instructions with anti-loop rules
tool_instructions = """
IMPORTANT: When you need to use a tool, you MUST output a JSON object in the following EXACT format:
```json
{
  "tool_call": {
    "id": "call_<unique_id>",
    "name": "<tool_name>",
    "arguments": {<tool_arguments>}
  }
}
```

RULES:
- Use ONLY ONE tool call per response
- Do NOT call the same tool repeatedly without making progress
- For sequential_thinking: Only use when you need to break down a complex problem. Do NOT use for simple tasks.
- Always provide substantive reasoning in your response along with the tool call
- If a tool fails, try a different approach rather than repeating the same call
"""

# Multiple JSON parsing patterns
json_patterns = [
    r'```json\s*(\{.*?\})\s*```',  # Standard JSON blocks
    r'```\s*(\{.*?"tool_call".*?\})\s*```',  # JSON blocks without json label
    r'(\{[^{}]*"tool_call"[^{}]*\{[^{}]*\}[^{}]*\})',  # Inline JSON with tool_call
]

# Loop detection method
def _is_tool_call_loop(self, tool_call_data: dict, recent_messages: list) -> bool:
    """Detect if this tool call would create a loop."""
    # Special handling for sequential_thinking and other tools
    # Returns True if a loop is detected
```

### 2. Enhanced Browser Launch (`src/ii_agent/browser/browser.py`)

```python
try:
    self.playwright_browser = await self.playwright.chromium.launch(
        headless=False,
        args=[...],
    )
except Exception as e:
    logger.error(f"Failed to launch browser with headless=False: {e}")
    logger.info("Attempting to launch browser in headless mode as fallback")
    try:
        self.playwright_browser = await self.playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                ...
            ],
        )
    except Exception as e2:
        raise BrowserError(
            f"Failed to launch browser. Please run 'playwright install chromium'. "
            f"Original error: {e2}"
        ) from e2
```

## Deployment Instructions

### For Render.com or Similar Platforms

**Recommended Build Commands:**

1. **Shell script (recommended):**
```bash
chmod +x scripts/render_build_safe.sh && ./scripts/render_build_safe.sh
```

2. **Python script (alternative):**
```bash
python scripts/safe_build.py
```

**Alternative Build Commands:**

3. **Simple approach (may fail on system dependencies):**
```bash
pip install --upgrade pip && pip install . && python -m playwright install chromium && python -m playwright install-deps chromium
```

4. **Safe inline approach:**
```bash
pip install --upgrade pip && pip install . && python -m playwright install chromium && python -m playwright install-deps chromium 2>/dev/null || echo "Warning: System dependencies not available"
```

5. **Using the general deployment script:**
```bash
chmod +x scripts/setup_deployment.sh && ./scripts/setup_deployment.sh
```

### Environment Variables

Ensure these environment variables are set:
- `CHUTES_API_KEY`: Your Chutes API key
- Any other required API keys for tools

## Testing

Run the test suite to verify improvements:

```bash
# Quick test
python tests/test_chutes_fast.py

# Comprehensive test
python tests/test_final.py
```

## Monitoring

The improvements include enhanced logging to help monitor tool calling behavior:

- `[CHUTES] Found X potential JSON tool calls in content`
- `[CHUTES] Detected potential tool call loop for X, skipping`
- `[CHUTES] Successfully launched browser in headless mode`

## Future Improvements

1. **Tool Call Reliability:**
   - Implement more sophisticated loop detection
   - Add tool call success/failure tracking
   - Implement adaptive retry strategies

2. **Browser Support:**
   - Add support for other browsers (Firefox, Safari)
   - Implement browser pool for better performance
   - Add browser health checks

3. **Deployment:**
   - Create Docker images with pre-installed browsers
   - Add automated browser update mechanisms
   - Implement browser caching strategies

## Troubleshooting

### Tool Calls Not Working
1. Check logs for JSON parsing errors
2. Verify tool instructions are being added to system prompt
3. Look for loop detection warnings

### Browser Launch Failures
1. Ensure Playwright browsers are installed: `python -m playwright install chromium`
2. Check for missing system dependencies
3. Try headless mode explicitly
4. Verify sufficient disk space and memory

### Build Failures on Render.com
**Error: "su: Authentication failure" during Playwright installation**

This error occurs when Playwright tries to install system dependencies but doesn't have root privileges. This is expected on hosting platforms.

**Solutions:**
1. **Use the safe build script** (recommended):
   ```bash
   chmod +x scripts/render_build_safe.sh && ./scripts/render_build_safe.sh
   ```

2. **Modify your build command** to handle the failure gracefully:
   ```bash
   pip install --upgrade pip && pip install . && python -m playwright install chromium && python -m playwright install-deps chromium 2>/dev/null || echo "System dependencies not available - using fallback mode"
   ```

3. **The application will automatically fall back** to minimal browser configuration when system dependencies are missing.

**What happens when system dependencies are missing:**
- The browser will launch in headless mode with minimal arguments
- Some advanced browser features may not work
- Basic web browsing and screenshot functionality will still work
- The application logs will show fallback mode activation

### Performance Issues
1. Monitor token usage and context length
2. Check for excessive tool call loops
3. Verify browser resource usage

## VS Code Server Integration

### Overview

The frontend includes a disabled "Open in VS Code" button that can be enabled by running a VS Code server (code-server) alongside your application. This provides a web-based VS Code interface accessible through the browser.

### Implementation Options

#### Option 1: Enhanced Build Script (Recommended)

Use the enhanced build script that includes code-server installation:

```bash
chmod +x scripts/render_build_with_vscode.sh && ./scripts/render_build_with_vscode.sh
```

This script:
- Installs all dependencies (Python packages, Playwright browsers)
- Downloads and installs code-server
- Configures code-server for web access
- Creates startup scripts

#### Option 2: Separate Installation

Install code-server separately during build:

```bash
# Your existing build command
pip install --upgrade pip && pip install . && python -m playwright install chromium

# Add code-server installation
curl -fsSL https://code-server.dev/install.sh | sh && python scripts/install_code_server.py
```

#### Option 3: Runtime Installation

Install code-server at runtime using the Python script:

```bash
python scripts/install_code_server.py
```

### Startup Configuration

#### Option 1: Combined Startup Script

Use the combined startup script that runs both your application and code-server:

```bash
chmod +x scripts/start_with_vscode.sh && ./scripts/start_with_vscode.sh
```

#### Option 2: Separate Processes

Start code-server separately:

```bash
# Start code-server in background
./start-code-server.sh

# Start your main application
python -m uvicorn ws_server:app --host 0.0.0.0 --port ${PORT:-8000}
```

### Environment Variables

Update your environment variables:

```bash
# Frontend environment
NEXT_PUBLIC_VSCODE_URL=https://your-app-name.onrender.com:8080

# Or for local development
NEXT_PUBLIC_VSCODE_URL=http://127.0.0.1:8080
```

### Render.com Configuration

#### Build Command
```bash
chmod +x scripts/render_build_with_vscode.sh && ./scripts/render_build_with_vscode.sh
```

**Note:** This script also handles the Playwright system dependencies issue gracefully, so it's safe to use on Render.com.

#### Start Command
```bash
chmod +x scripts/start_with_vscode.sh && ./scripts/start_with_vscode.sh
```

### Security Considerations

**Important**: The current configuration disables authentication for simplicity. For production use, consider:

1. **Enable authentication**:
```yaml
# ~/.config/code-server/config.yaml
bind-addr: 0.0.0.0:8080
auth: password
password: your-secure-password
cert: false
```

2. **Use HTTPS**:
```yaml
bind-addr: 0.0.0.0:8080
auth: password
password: your-secure-password
cert: true
cert-key: /path/to/key.pem
cert-cert: /path/to/cert.pem
```

3. **Restrict access** by IP or use a reverse proxy with authentication.

### Frontend Integration

The VS Code button is automatically enabled when `NEXT_PUBLIC_VSCODE_URL` is set. The button:

- Opens code-server in a new tab
- Automatically navigates to the current workspace folder
- Provides full VS Code functionality in the browser

### Troubleshooting VS Code Integration

#### Code-server not starting
1. Check if code-server is installed: `code-server --version`
2. Verify the startup script has execute permissions
3. Check port 8080 is available
4. Review code-server logs

#### Button not appearing
1. Verify `NEXT_PUBLIC_VSCODE_URL` environment variable is set
2. Rebuild the frontend after setting the environment variable
3. Check browser console for errors

#### Connection issues
1. Ensure code-server is running on the correct port
2. Check firewall settings
3. Verify the URL in `NEXT_PUBLIC_VSCODE_URL` is accessible

### Alternative: VS Code Tunnels

For a simpler setup without running code-server, you could use VS Code tunnels:

1. Install VS Code CLI on your server
2. Run `code tunnel` to create a secure tunnel
3. Access VS Code through the provided URL

This approach doesn't require additional server configuration but requires a GitHub account for authentication. 