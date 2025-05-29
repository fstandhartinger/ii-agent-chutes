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

## Development Best Practices Learned

1. **Incremental Refactoring**: When refactoring large components, maintain working state at each step rather than making all changes at once.

2. **Hook Dependencies**: Always minimize useCallback and useEffect dependencies to prevent unnecessary re-renders.

3. **State Management**: Set critical state as early as possible in the data flow.

4. **Resource Cleanup**: Always implement proper cleanup for timeouts, intervals, and event listeners.

5. **Import Management**: Keep imports organized and verify all dependencies exist before using them.

6. **Error Diagnosis**: When facing compilation errors, systematically check imports, dependencies, and file structure before assuming syntax issues.

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
