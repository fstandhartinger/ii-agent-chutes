import { useState, useCallback, useEffect, useRef } from 'react';
import { toast } from 'sonner';
import { v4 as uuidv4 } from 'uuid';
import type { LLMModel } from '@/providers/chutes-provider'; // Corrected type
import type { WebSocketMessage, Message } from '@/typings/agent'; // Corrected import path if needed, assuming it's now exported

// Props for the hook
interface UseWebSocketManagerProps {
  deviceId: string | null;
  isReplayMode: boolean;
  selectedModel: LLMModel; // Corrected type
  useNativeToolCalling: boolean;
  onEventReceived: (event: { id: string; type: string; content: Record<string, unknown> }) => void;
  getProKey: () => string | null;
  isLoading: boolean; // Added for timeout logic
  currentMessages: Message[]; // Added to check last message for "thinking"
}

// Return type of the hook
interface UseWebSocketManagerReturn {
  socket: WebSocket | null;
  isSocketConnected: boolean;
  isSocketReady: boolean;
  sendMessage: (message: WebSocketMessage, maxRetries?: number) => Promise<boolean>;
  connect: () => void;
  disconnect: () => void;
}

export const useWebSocketManager = ({
  deviceId,
  isReplayMode,
  selectedModel,
  useNativeToolCalling,
  onEventReceived,
  getProKey,
  isLoading,
  currentMessages,
}: UseWebSocketManagerProps): UseWebSocketManagerReturn => {
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [isSocketConnected, setIsSocketConnected] = useState(false);
  const [isSocketReady, setIsSocketReady] = useState(false);
  const [messageQueue, setMessageQueue] = useState<WebSocketMessage[]>([]);
  const [retryAttempt, setRetryAttempt] = useState(0);
  const thinkingTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Refs for callbacks and props to avoid stale closures in WebSocket event handlers
  const onEventReceivedRef = useRef(onEventReceived);
  useEffect(() => {
    onEventReceivedRef.current = onEventReceived;
  }, [onEventReceived]);

  const selectedModelRef = useRef(selectedModel);
  useEffect(() => {
    selectedModelRef.current = selectedModel;
  }, [selectedModel]);

  const useNativeToolCallingRef = useRef(useNativeToolCalling);
  useEffect(() => {
    useNativeToolCallingRef.current = useNativeToolCalling;
  }, [useNativeToolCalling]);

  const getProKeyRef = useRef(getProKey);
  useEffect(() => {
    getProKeyRef.current = getProKey;
  }, [getProKey]);

  const handleWebSocketError = useCallback((error: Event | Error | unknown, context: string) => {
    console.error(`WEBSOCKET_DEBUG: WebSocket ${context}:`, error);
    // Simplified error handling for the hook.
    // The main component can observe isSocketConnected/isSocketReady for more detailed UI.
    if (context === "connection_error") {
      toast.error("WebSocket connection error. Please check the console.");
    } else if (context === "connection_closed") {
      toast.info("WebSocket connection closed.");
    } else {
      toast.error(`WebSocket issue: ${context}. Check console.`);
    }
    // The original handleWebSocketError in home.tsx is more complex and uses Home's state.
    // This simplified version avoids tight coupling for now.
  }, []);

  const processMessageQueue = useCallback(() => {
    if (socket && socket.readyState === WebSocket.OPEN && isSocketReady && messageQueue.length > 0) {
      console.log(`WEBSOCKET_DEBUG: Processing ${messageQueue.length} queued messages`);
      messageQueue.forEach((message, index) => {
        console.log(`WEBSOCKET_DEBUG: Sending queued message ${index + 1}:`, message);
        socket.send(JSON.stringify(message));
      });
      setMessageQueue([]);
    }
  }, [socket, isSocketReady, messageQueue]); // isSocketConnected removed as socket.readyState check is better

  const sendMessage = useCallback(async (message: WebSocketMessage, maxRetries: number = 3): Promise<boolean> => {
    console.log(`WEBSOCKET_DEBUG: Attempting to send message (retry attempt ${retryAttempt}/${maxRetries}):`, message);

    if (!socket || socket.readyState !== WebSocket.OPEN) {
      console.warn(`WEBSOCKET_DEBUG: Socket not open (state: ${socket?.readyState}), queuing message`);
      setMessageQueue(prev => [...prev, message]);
      return false;
    }

    if (!isSocketReady) {
      console.log(`WEBSOCKET_DEBUG: Server not ready, waiting before retry (attempt ${retryAttempt + 1}/${maxRetries + 1})`);
      if (retryAttempt < maxRetries) {
        setRetryAttempt(prev => prev + 1);
        const delay = Math.min(500 * Math.pow(2, retryAttempt), 2000);
        await new Promise(resolve => setTimeout(resolve, delay));
        return sendMessage(message, maxRetries);
      } else {
        console.warn(`WEBSOCKET_DEBUG: Max retries reached for server readiness, queuing message`);
        setMessageQueue(prev => [...prev, message]);
        setRetryAttempt(0);
        return false;
      }
    }

    try {
      socket.send(JSON.stringify(message));
      console.log(`WEBSOCKET_DEBUG: Message sent successfully`);
      setRetryAttempt(0);
      return true;
    } catch (error) {
      console.error(`WEBSOCKET_DEBUG: Error sending message:`, error);
      if (retryAttempt < maxRetries) {
        setRetryAttempt(prev => prev + 1);
        const delay = Math.min(1000 * Math.pow(2, retryAttempt), 4000);
        await new Promise(resolve => setTimeout(resolve, delay));
        return sendMessage(message, maxRetries);
      } else {
        console.error(`WEBSOCKET_DEBUG: Max retries reached for sending, message failed`);
        setRetryAttempt(0);
        handleWebSocketError(error, "send_message_failure");
        return false;
      }
    }
  }, [socket, isSocketReady, retryAttempt, handleWebSocketError]);


  const connect = useCallback(() => {
    // Prevent multiple connections or connection attempts under invalid conditions
    if (socket || !deviceId || isReplayMode) {
      if (socket) console.log("WEBSOCKET_DEBUG: Connection attempt skipped, socket already exists.");
      if (!deviceId) console.log("WEBSOCKET_DEBUG: Connection attempt skipped, no device ID.");
      if (isReplayMode) console.log("WEBSOCKET_DEBUG: Connection attempt skipped, in replay mode.");
      return;
    }

    console.log("WEBSOCKET_DEBUG: Starting WebSocket connection process (from hook)");
    
    let wsUrl = `${process.env.NEXT_PUBLIC_API_URL}/ws`.replace(/^http/, 'ws');

    wsUrl += `?device_id=${deviceId}`;
    
    const currentSelectedModel = selectedModelRef.current;
    const currentUseNativeToolCalling = useNativeToolCallingRef.current;
    const currentGetProKey = getProKeyRef.current;

    if (currentSelectedModel.provider === 'anthropic') {
      wsUrl += `&model_id=${encodeURIComponent(currentSelectedModel.id)}`;
    } else if (currentSelectedModel.provider === 'openrouter') {
      wsUrl += `&use_openrouter=true&model_id=${encodeURIComponent(currentSelectedModel.id)}`;
    } else { // Default to 'chutes'
      wsUrl += `&use_chutes=true&model_id=${encodeURIComponent(currentSelectedModel.id)}`;
    }
    
    if (currentUseNativeToolCalling) {
      wsUrl += `&use_native_tool_calling=true`;
    }
    
    const proKey = currentGetProKey();
    if (proKey) {
      wsUrl += `&pro_user_key=${encodeURIComponent(proKey)}`;
    }
    
    console.log(`WEBSOCKET_DEBUG: Connecting to: ${wsUrl}`);
    const wsInstance = new WebSocket(wsUrl);

    wsInstance.onopen = () => {
      console.log("WEBSOCKET_DEBUG: ✅ WebSocket connection established - waiting for server ready signal");
      setIsSocketConnected(true);
      // setIsSocketReady(false); // Server will confirm readiness

      console.log("WEBSOCKET_DEBUG: Sending workspace_info request");
      try {
        wsInstance.send(JSON.stringify({ type: "workspace_info_request", content: {} }));
      } catch (error) {
        console.error("WEBSOCKET_DEBUG: Error sending workspace_info:", error);
        handleWebSocketError(error, "sending_workspace_info_on_open");
      }
    };

    wsInstance.onmessage = (event) => {
      console.log("WEBSOCKET_DEBUG: Received message (in hook):", event.data);
      try {
        const data = JSON.parse(event.data as string);
        
        if (data.type === "connection_established" || data.type === "workspace_info") {
          if (!isSocketReady) { // Set ready only once on first relevant signal
             console.log("WEBSOCKET_DEBUG: Server ready signal received, setting isSocketReady=true");
             setIsSocketReady(true);
          }
        }
        onEventReceivedRef.current({ ...data, id: data.id || uuidv4() });
      } catch (error) {
        console.error("WEBSOCKET_DEBUG: Error parsing WebSocket data (in hook):", error);
        handleWebSocketError(error, "message_parsing");
      }
    };

    wsInstance.onerror = (event) => {
      console.error("WEBSOCKET_DEBUG: ❌ WebSocket error event (in hook):", event);
      handleWebSocketError(event, "connection_error");
      // State updates will be handled by onclose
    };

    wsInstance.onclose = (event) => {
      console.log("WEBSOCKET_DEBUG: 🔌 WebSocket connection closed (in hook)", `Code: ${event.code}`, `Reason: ${event.reason}`, `WasClean: ${event.wasClean}`);
      handleWebSocketError(event, "connection_closed");
      setSocket(null);
      setIsSocketConnected(false);
      setIsSocketReady(false);
      setMessageQueue([]); 
      setRetryAttempt(0); // Reset retry attempts on close
    };

    setSocket(wsInstance);
  }, [deviceId, isReplayMode, handleWebSocketError]); // Removed isSocketReady and socket from dependencies to prevent cycles

  const disconnect = useCallback(() => {
    if (socket) {
      console.log("WEBSOCKET_DEBUG: Closing WebSocket connection (from hook)");
      socket.onopen = null;
      socket.onmessage = null;
      socket.onerror = null;
      socket.onclose = null;
      socket.close();
      setSocket(null);
      setIsSocketConnected(false);
      setIsSocketReady(false);
      setMessageQueue([]);
    }
  }, [socket]);

  // Effect for initial connection and reconnection if critical parameters change
  useEffect(() => {
    if (deviceId && !isReplayMode) {
      // If critical parameters (selectedModel, useNativeToolCalling) change,
      // we need to disconnect the old socket and connect a new one.
      if (socket) {
        // Check if model or tool calling has changed compared to when the current socket was established.
        // This requires storing the params used for the current socket, or simply always reconnecting.
        // For simplicity, if `selectedModel` or `useNativeToolCalling` props change,
        // the `Home` component should manage calling `disconnect` then `connect`.
        // This effect primarily handles initial connect and cleanup.
        // However, if `connect` itself changes (e.g. due to `selectedModelRef` not being used and `selectedModel` being a direct dep of `connect`),
        // then this effect structure would handle it.
        // The current `connect` uses refs, so it won't change due to model/tool prop changes.
        // Thus, `Home` must manage explicit reconnects for model/tool changes.
      } else {
        // No socket, or socket was explicitly closed, try to connect.
        connect();
      }
    } else {
      // Conditions not met for connection (no deviceId or in replayMode), ensure disconnected.
      disconnect();
    }
    // Cleanup function for when the component unmounts or dependencies change forcing a re-run
    return () => {
      disconnect();
    };
  }, [deviceId, isReplayMode, connect, disconnect, socket]);
  // Removed selectedModel, useNativeToolCalling from deps to prevent reconnect cycles
  // since they are handled through refs and should not trigger automatic reconnects

  // Process message queue when socket becomes ready
  useEffect(() => {
    if (isSocketReady) {
      processMessageQueue();
    }
  }, [isSocketReady, processMessageQueue]);

  // Effect for "fubea is thinking..." timeout
  useEffect(() => {
    if (isLoading) {
      // Check if the last message is an assistant message (implicitly "thinking")
      // This is a proxy, a more direct "isThinking" state from chatState might be better
      // but isLoading is the primary indicator provided.
      const lastMessage = currentMessages[currentMessages.length - 1];
      const isAssistantThinking = lastMessage?.role === 'assistant' && !lastMessage.action; // A simple check

      if (isAssistantThinking || currentMessages.length === 0) { // Also consider initial loading
        console.log("WEBSOCKET_DEBUG: isLoading is true, starting 1-minute thinking timeout.");
        if (thinkingTimeoutRef.current) {
          clearTimeout(thinkingTimeoutRef.current);
        }
        thinkingTimeoutRef.current = setTimeout(() => {
          console.warn("WEBSOCKET_DEBUG: \"fubea is thinking...\" timeout (1 minute) reached.");
          console.log(`WEBSOCKET_DEBUG: Current WebSocket state: ${socket?.readyState === WebSocket.OPEN ? 'OPEN' : socket?.readyState === WebSocket.CONNECTING ? 'CONNECTING' : socket?.readyState === WebSocket.CLOSING ? 'CLOSING' : socket?.readyState === WebSocket.CLOSED ? 'CLOSED' : 'UNKNOWN'}`);
          
          toast.info("Agent seems stuck, attempting to reconnect and continue...");

          // Attempt to reconnect
          disconnect(); 
          // connect(); // connect() will be called by the useEffect that watches [deviceId, isReplayMode, socket]
          // Need to ensure connect() is called. A small delay might be needed if disconnect is async.
          // The existing useEffect for connect/disconnect should handle this.
          // We might need to trigger it if deviceId/isReplayMode haven't changed.
          // Forcing a reconnect sequence:
          setTimeout(() => {
            if (!socket) { // Only connect if disconnect actually nulled the socket
                console.log("WEBSOCKET_DEBUG: Re-triggering connect after thinking timeout.");
                connect();
            }
          }, 100); // Short delay to allow disconnect to process

          // Send "Continue" message after a delay to allow reconnection
          setTimeout(() => {
            if (isSocketReady) { // Check if reconnected
              console.log("WEBSOCKET_DEBUG: Sending 'Continue' message after timeout and reconnect attempt.");
              sendMessage({
                type: 'query',
                content: {
                  text: 'Continue',
                  session_id: '', // session_id might be needed, or handled by server
                  message_id: uuidv4(),
                  attachments: [], // Assuming no attachments for a "Continue"
                  model_id: selectedModelRef.current.id, // Pass current model
                  use_native_tool_calling: useNativeToolCallingRef.current, // Pass current setting
                  // pro_user_key: getProKeyRef.current() // Pro key is added in connect() URL
                },
              });
            } else {
              console.warn("WEBSOCKET_DEBUG: Socket not ready after reconnect attempt, 'Continue' message not sent.");
              toast.error("Failed to reconnect after timeout. Please try refreshing or sending a new message.");
            }
          }, 3000); // Wait 3 seconds for reconnection
        }, 60000); // 60 seconds
      }
    } else {
      if (thinkingTimeoutRef.current) {
        console.log("WEBSOCKET_DEBUG: isLoading is false, clearing thinking timeout.");
        clearTimeout(thinkingTimeoutRef.current);
        thinkingTimeoutRef.current = null;
      }
    }

    return () => {
      if (thinkingTimeoutRef.current) {
        clearTimeout(thinkingTimeoutRef.current);
      }
    };
  }, [isLoading, currentMessages, socket, disconnect, connect, sendMessage, isSocketReady]);


  return {
    socket,
    isSocketConnected,
    isSocketReady,
    sendMessage,
    connect,
    disconnect,
  };
};
