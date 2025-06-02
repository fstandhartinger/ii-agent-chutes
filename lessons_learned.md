# Lessons Learned

This document captures key insights and solutions discovered during development to help avoid repeating mistakes and improve our development process.

## WebSocket and Server Issues

- **WebSocket 500 errors on Render**: Server crashed due to missing app configuration - added fallback config mechanism and proper Render deployment args
- **FastAPI WebSocket ping errors**: FastAPI WebSocket doesn't have ping() method - use custom heartbeat messages instead
- **UUID type mismatch**: create_workspace_manager_for_connection returned string instead of UUID object - fixed return type consistency

## Database and Session Management

## Bug Fixes and Issues Resolved

### 1. WebSocket Management Issues (Fixed)
**Problem**: Complex retry mechanism in `useWebSocketManager.ts` was causing race conditions, memory leaks, and connection instability.
**Solution**: Simplified connection logic by removing retry attempts, adding proper timeout handling, and implementing clean disconnection procedures.
**Key Takeaway**: Keep WebSocket connection logic simple and predictable. Complex retry mechanisms often cause more problems than they solve.

### 2. Event Handler Performance Problems (Fixed)
**Problem**: Excessive dependencies in useCallback hooks in `useEventHandler.ts` causing unnecessary re-renders and performance degradation.
**Solution**: Used refs for stable references and reduced dependency arrays to only essential values.
**Key Takeaway**: Be very careful with useCallback dependencies - include only what actually needs to trigger re-creation.

### 3. Session Management Timing Issues (Fixed)
**Problem**: Session ID was set too late (only on PROCESSING event) in `useSessionManager.ts`, causing file upload and sharing functionality to fail.
**Solution**: Automatically extract session ID from workspace info when available, ensuring it's set early in the process.
**Key Takeaway**: Critical state should be set as early as possible in the data flow, not just when convenient.

### 4. Model/Settings Change Reconnection (Fixed)
**Problem**: Changing LLM model or tool calling settings didn't trigger WebSocket reconnection, leading to inconsistent behavior.
**Solution**: Added useEffect to monitor critical connection settings and reconnect when they change.
**Key Takeaway**: All settings that affect server behavior should trigger appropriate connection updates.

### 5. Import Organization and Cleanup (Fixed)
**Problem**: Dynamic imports scattered inconsistently throughout the codebase, multiple timeout references without proper cleanup.
**Solution**: Organized imports logically and centralized timeout management with proper cleanup.
**Key Takeaway**: Consistent import organization and proper resource cleanup prevent subtle bugs and improve maintainability.

### 6. JSX Parsing Error Resolution (Fixed)
**Problem**: Persistent "Unexpected token `div`. Expected jsx identifier" error preventing compilation, despite JSX appearing correct.
**Solution**: The issue was caused by missing custom hook files that were imported but didn't exist. Recreating the file with simplified state management resolved the compilation error.
**Key Takeaway**: JSX parsing errors can sometimes be caused by missing imports rather than actual JSX syntax issues. When facing persistent JSX errors, check all imports and dependencies first.

### 7. Frontend Layout and UI Functionality Restoration (Fixed)
**Problem**: Multiple UI issues broke the user experience: missing model picker and pro upgrade button, unwanted "fubea" text title, broken chat view layout, non-functional share button, poor message formatting, and missing action handlers.
**Solution**: Restored proper layout using the working version as reference while maintaining modular component structure. Fixed hook dependencies and restored proper event handling flow.
**Key Takeaway**: When refactoring complex UI components, preserve working layouts and functionality patterns. Use known-good versions as reference to ensure visual consistency and proper user experience flow.

## Development Best Practices Learned

1. **Incremental Refactoring**: When refactoring large components, maintain working state at each step rather than making all changes at once.

2. **Hook Dependencies**: Always minimize useCallback and useEffect dependencies to prevent unnecessary re-renders.

3. **State Management**: Set critical state as early as possible in the data flow.

4. **Resource Cleanup**: Always implement proper cleanup for timeouts, intervals, and event listeners.

5. **Import Management**: Keep imports organized and verify all dependencies exist before using them.

6. **Error Diagnosis**: When facing compilation errors, systematically check imports, dependencies, and file structure before assuming syntax issues.

7. **UI Consistency**: When refactoring complex UI components, always preserve working visual layouts and user experience patterns from known-good versions.

## WebSocket Management Issues (Fixed)
- **Problem**: Complex retry mechanism in WebSocket manager caused race conditions and memory leaks
- **Solution**: Simplified connection logic, removed retry attempts, added proper timeout handling and cleanup
- **Key Takeaway**: Keep WebSocket connection logic simple and rely on browser's built-in reconnection capabilities

## Event Handler Performance Issues (Fixed)  
- **Problem**: Event handler had excessive dependencies causing unnecessary re-renders
- **Solution**: Used refs for stable references to prevent dependency chains while maintaining functionality
- **Key Takeaway**: Use refs for values that need to be current but shouldn't trigger re-renders in useCallback dependencies

## Session Management Timing Issues (Fixed)
- **Problem**: Session ID was set too late (only on PROCESSING event), causing issues with file uploads and sharing
- **Solution**: Automatically extract session ID from workspace info when available for new sessions
- **Key Takeaway**: Extract session identifiers as early as possible from available data sources

## Hook Architecture Benefits (Implemented)
- **Problem**: Monolithic home.tsx component was difficult to maintain and debug
- **Solution**: Split into focused hooks: useChatState, useUIState, useSessionManager, useWebSocketManager, etc.
- **Key Takeaway**: Custom hooks enable better separation of concerns and make complex state logic more testable

## Model/Settings Change Reconnection (Fixed)
- **Problem**: Changing LLM model or tool calling settings didn't trigger WebSocket reconnection
- **Solution**: Added effect to monitor critical connection settings and reconnect when they change
- **Key Takeaway**: Monitor dependencies that affect connection initialization and handle reconnection explicitly

## Error Handling Improvements (Implemented)
- **Problem**: Generic error messages didn't help users understand what went wrong
- **Solution**: Added specific error handling for different failure scenarios (404, 500, timeout, etc.)
- **Key Takeaway**: Provide contextual error messages based on error type to improve user experience

## Dynamic Import Organization (Fixed)
- **Problem**: Dynamic imports were scattered and inconsistently structured
- **Solution**: Grouped all dynamic imports together with clear comments and consistent formatting
- **Key Takeaway**: Organize imports logically - static imports first, then dynamic imports grouped together

## Timeout and Cleanup Management (Improved)
- **Problem**: Multiple timeout references without proper cleanup could cause memory leaks
- **Solution**: Centralized timeout management with proper cleanup functions
- **Key Takeaway**: Always clean up timeouts and intervals in useEffect cleanup functions and component unmount

## WebSocket Connection Issues
- **Problem**: Infinite WebSocket reconnection loop caused by useEffect dependency chain
- **Root Cause**: isSocketReady state change triggered connect callback to change, causing useEffect cleanup to disconnect
- **Solution**: Removed isSocketReady from connect callback dependencies and simplified onmessage logic

## Frontend UI Layout Issues (Fixed)
- **Problem**: "Connecting to Server" message was not visible and "Powered by CHUTES" text was too close to input components
- **Root Cause**: CSS mobile layout priorities caused input section to overlay connection status messages  
- **Solution**: Restructured component hierarchy to place connection status as separate section above input, added proper spacing with mb-6 class
- **Key Takeaway**: Mobile CSS priorities can hide important status messages - always test connection states on mobile viewports

## WebSocket Message Type Mismatch (Fixed)
- **Problem**: Frontend sent "user_message" type but backend only accepted "query" type, causing "Unknown message type" errors
- **Root Cause**: Backend websocket_manager.py didn't handle USER_MESSAGE EventType despite it being defined in event.py
- **Solution**: Added USER_MESSAGE handling in backend that processes it the same as QUERY for backward compatibility
- **Key Takeaway**: When EventTypes are defined, ensure all message handlers support them or document which are client-only vs server-supported

## EventType Synchronization Issues (Fixed)
- **Problem**: Frontend and Backend had mismatched EventType enums and magic constants causing compatibility issues
- **Issues Found**: 
  - Frontend sent "stop_agent" but backend expected "cancel_processing"
  - Frontend AgentEvent enum was missing several EventTypes defined in backend (WORKSPACE_INFO_REQUEST, INIT_AGENT, QUERY, CANCEL_PROCESSING, PING, AGENT_INITIALIZED, HEARTBEAT)
  - Backend sent raw "heartbeat" messages instead of using EventType.HEARTBEAT
- **Solution**: 
  - Synchronized EventType enums between frontend (AgentEvent) and backend (EventType)
  - Updated frontend to send "cancel_processing" instead of "stop_agent"
  - Added proper HEARTBEAT event handling in frontend
  - Updated backend to use EventType.HEARTBEAT for heartbeat messages
- **Key Takeaway**: Maintain strict synchronization between Frontend and Backend enum definitions. Regular audits should check for mismatched constants and ensure complete compatibility

- **Bug**: File Viewer not displaying files - workspaceInfo was undefined in frontend (2025-05-30)
  - Frontend expected `data.content.path` in WORKSPACE_INFO event handler
  - Backend sent `data.content.workspace_path` in the event payload
  - Fixed by changing frontend handler to use `data.content.workspace_path`
- **Key Takeaway**: Verify property names match between frontend event handlers and backend event payloads, especially for critical state like workspace paths

## File Viewer Recursive Structure Implementation
- **Problem**: File viewer only showed flat directory structure, requiring multiple API calls for folder expansion
- **Solution**: Implemented recursive `build_file_tree_recursive()` function in backend with `children` property population
- **Key Insight**: Single API call with recursive structure provides better performance and UX than multiple lazy-loading calls
- **Security Note**: Always include max depth protection (default 10) to prevent infinite recursion and memory issues

## Pro Plan Model Implementation - Credit-Based System with OpenRouter Integration

**Issue**: Extended Pro plan to support multiple model tiers with different cost structures and free OpenRouter models.

**Solution**: Implemented a credit-based system where Sonnet 4 = 1 credit, Opus 4 = 4 credits, OpenRouter models = 0 credits (free for Pro users). Added comprehensive fallback mechanism for OpenRouter models (native tool calling → JSON workaround).

**Key Takeaways**: 
- Credit-based pricing is more flexible than request-based counting for different model costs
- OpenRouter requires robust fallback since native tool calling isn't always supported
- Database schema migrations need careful coordination between old and new column names
- Frontend model picker needs provider-specific logic for proper routing

## Model Selection Issues
- **Problem**: Model picker automatically falls back to default model when selecting new models
- **Solution**: Ensure all models in model-picker.tsx are also included in AVAILABLE_MODELS in chutes-provider.tsx
- **Key Learning**: Frontend model selection requires models to be defined in both the picker component AND the provider's available models list

## PRESENTATION Tool "unhashable type: list" Error  
- **Problem**: Python TypeError when PRESENTATION tool uses list inputs in message_history.py
- **Solution**: Implement recursive make_hashable() function to convert nested lists/dicts to hashable tuples
- **Key Learning**: Tool inputs with complex nested data structures need special handling for deduplication logic

## Debugging Complex Issues
- **Problem**: Hard to trace issues across frontend/backend boundaries
- **Solution**: Add comprehensive console.log() in frontend and logger.debug() in backend with consistent prefixes
- **Key Learning**: Extensive logging with clear prefixes ([COMPONENT_DEBUG]) makes debugging much faster
