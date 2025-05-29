# Lessons Learned

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
