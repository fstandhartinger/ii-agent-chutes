# Static Deploy Tool Workflow

## Problem Description

The agent was incorrectly including fake JSON tool calls in the `complete` tool's answer instead of actually calling the `static_deploy` tool to get real URLs.

## Correct Workflow

When the agent needs to provide a downloadable file (PDF, HTML, etc.), it should follow this sequence:

### Step 1: Create the file
```bash
# Example: Create a PDF report
python generate_report.py > report.pdf
```

### Step 2: Call static_deploy tool
```json
{
  "tool_call": {
    "id": "call_123",
    "name": "static_deploy",
    "arguments": {
      "file_path": "report.pdf"
    }
  }
}
```

### Step 3: Get the real URL
The static_deploy tool returns a real HTTP URL like:
```
http://localhost:8000/workspace/a7979cc1-f209-489e-b42b-9a58c447bdcd/report.pdf
```

### Step 4: Complete with real URL
```json
{
  "tool_call": {
    "id": "call_124", 
    "name": "complete",
    "arguments": {
      "answer": "Analysis complete. Download the full report: [Download PDF](http://localhost:8000/workspace/a7979cc1-f209-489e-b42b-9a58c447bdcd/report.pdf)"
    }
  }
}
```

## What Was Wrong

The agent was doing this incorrectly:

```json
{
  "tool_call": {
    "id": "call_103",
    "name": "complete", 
    "arguments": {
      "answer": "Analysis complete. Download: [Download PDF](static-deploy-url/report.pdf)\n\n```json\n{\"tool_call\": {\"id\": \"call_103\", \"name\": \"static_deploy\", \"arguments\": {\"file_path\": \"llm-cost-analysis-report.pdf\"}}}\n```"
    }
  }
}
```

## Fixes Applied

1. **Updated system prompt** to explicitly instruct the agent to call `static_deploy` first
2. **Fixed default base URL** in StaticDeployTool from `file://` to `http://localhost:8000`
3. **Added automatic environment setup** in WebSocket server to set `STATIC_FILE_BASE_URL`
4. **Improved tool description** to make it clearer when to use the tool

## Environment Variables

The `STATIC_FILE_BASE_URL` environment variable should be set to:
```
STATIC_FILE_BASE_URL=http://localhost:8000
```

If not set, the WebSocket server will automatically set it based on the port it's running on. 