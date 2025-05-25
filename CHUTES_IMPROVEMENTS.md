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

1. **Add to your build script:**
```bash
# Install Playwright browsers during build
python -m playwright install chromium
python -m playwright install-deps chromium || echo "Warning: Could not install system dependencies"
```

2. **Or use the provided script:**
```bash
chmod +x scripts/setup_deployment.sh
./scripts/setup_deployment.sh
```

3. **For Python-based deployment:**
```python
# Run during deployment
python scripts/install_playwright.py
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

### Performance Issues
1. Monitor token usage and context length
2. Check for excessive tool call loops
3. Verify browser resource usage 