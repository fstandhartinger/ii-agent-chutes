import { useState, useCallback, useEffect, useRef } from 'react';
import { toast } from 'sonner';
import { v4 as uuidv4 } from 'uuid';
import type { LLMModel } from '@/providers/chutes-provider'; // Corrected type
import type { WebSocketMessage } from '@/typings/agent'; // Corrected import path

// Props for the hook
interface UseWebSocketManagerProps {
  deviceId: string | null;
  isReplayMode: boolean;
  selectedModel: LLMModel; // Corrected type
  useNativeToolCalling: boolean;
  onEventReceived: (event: { id: string; type: string; content: Record<string, unknown> }) => void;
  getProKey: () => string | null;
  isLoading: boolean; // For timeout logic
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
}: UseWebSocketManagerProps): UseWebSocketManagerReturn => {
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [isSocketConnected, setIsSocketConnected] = useState(false);
  const [isSocketReady, setIsSocketReady] = useState(false);
  const [messageQueue, setMessageQueue] = useState<WebSocketMessage[]>([]);
  const thinkingTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const connectionTimeoutRef = useRef<NodeJS.Timeout | null>(null);

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
    
    if (context === "connection_error") {
      toast.error("WebSocket connection error. Please check your connection.");
    } else if (context === "connection_closed") {
      // Only show toast if it was an unexpected closure
      if (socket && socket.readyState !== WebSocket.CLOSING) {
        toast.info("Connection lost. Attempting to reconnect...");
      }
    } else if (context === "connection_timeout") {
      toast.error("Connection timeout. Please refresh the page.");
    } else {
      toast.error(`Connection issue: ${context}. Please try refreshing.`);
    }
  }, [socket]);

  const clearAllTimeouts = useCallback(() => {
    if (thinkingTimeoutRef.current) {
      clearTimeout(thinkingTimeoutRef.current);
      thinkingTimeoutRef.current = null;
    }
    if (connectionTimeoutRef.current) {
      clearTimeout(connectionTimeoutRef.current);
      connectionTimeoutRef.current = null;
    }
  }, []);

  const processMessageQueue = useCallback(() => {
    if (socket && socket.readyState === WebSocket.OPEN && isSocketReady && messageQueue.length > 0) {
      console.log(`WEBSOCKET_DEBUG: Processing ${messageQueue.length} queued messages`);
      const queuedMessages = [...messageQueue];
      setMessageQueue([]);
      
      queuedMessages.forEach((message, index) => {
        try {
          console.log(`WEBSOCKET_DEBUG: Sending queued message ${index + 1}:`, message);
          socket.send(JSON.stringify(message));
        } catch (error) {
          console.error(`WEBSOCKET_DEBUG: Error sending queued message ${index + 1}:`, error);
          // Re-queue failed message
          setMessageQueue(prev => [...prev, message]);
        }
      });
    }
  }, [socket, isSocketReady, messageQueue]);

  const sendMessage = useCallback(async (message: WebSocketMessage): Promise<boolean> => {
    console.log(`WEBSOCKET_DEBUG: Attempting to send message:`, message);

    if (!socket || socket.readyState !== WebSocket.OPEN) {
      console.warn(`WEBSOCKET_DEBUG: Socket not open (state: ${socket?.readyState}), queuing message`);
      setMessageQueue(prev => [...prev, message]);
      return false;
    }

    if (!isSocketReady) {
      console.warn(`WEBSOCKET_DEBUG: Server not ready, queuing message`);
      setMessageQueue(prev => [...prev, message]);
      return false;
    }

    try {
      socket.send(JSON.stringify(message));
      console.log(`WEBSOCKET_DEBUG: Message sent successfully`);
      return true;
    } catch (error) {
      console.error(`WEBSOCKET_DEBUG: Error sending message:`, error);
      setMessageQueue(prev => [...prev, message]);
      handleWebSocketError(error, "send_message_failure");
      return false;
    }
  }, [socket, isSocketReady, handleWebSocketError]);

  const connect = useCallback(() => {
    // Prevent multiple connections or connection attempts under invalid conditions
    if (socket || !deviceId || isReplayMode) {
      if (socket) console.log("WEBSOCKET_DEBUG: Connection attempt skipped, socket already exists.");
      if (!deviceId) console.log("WEBSOCKET_DEBUG: Connection attempt skipped, no device ID.");
      if (isReplayMode) console.log("WEBSOCKET_DEBUG: Connection attempt skipped, in replay mode.");
      return;
    }

    console.log("WEBSOCKET_DEBUG: Starting WebSocket connection process");
    clearAllTimeouts();
    
    const wsUrl = new URL(`${process.env.NEXT_PUBLIC_API_URL || 'https://ii-agent-chutes.onrender.com'}/ws`.replace(/^http/, 'ws'));
    wsUrl.searchParams.append('device_id', deviceId);
    
    const currentSelectedModel = selectedModelRef.current;
    const currentUseNativeToolCalling = useNativeToolCallingRef.current;
    const currentGetProKey = getProKeyRef.current;

    if (currentSelectedModel.provider === 'anthropic') {
      wsUrl.searchParams.append('model_id', currentSelectedModel.id);
    } else if (currentSelectedModel.provider === 'openrouter') {
      wsUrl.searchParams.append('use_openrouter', 'true');
      wsUrl.searchParams.append('model_id', currentSelectedModel.id);
    } else { // Default to 'chutes'
      wsUrl.searchParams.append('use_chutes', 'true');
      wsUrl.searchParams.append('model_id', currentSelectedModel.id);
    }
    
    if (currentUseNativeToolCalling) {
      wsUrl.searchParams.append('use_native_tool_calling', 'true');
    }
    
    const proKey = currentGetProKey();
    if (proKey) {
      wsUrl.searchParams.append('pro_user_key', proKey);
    }
    
    console.log(`WEBSOCKET_DEBUG: Connecting to: ${wsUrl.toString()}`);
    const wsInstance = new WebSocket(wsUrl.toString());

    // Set up connection timeout
    connectionTimeoutRef.current = setTimeout(() => {
      console.error("WEBSOCKET_DEBUG: Connection timeout");
      handleWebSocketError(new Error("Connection timeout"), "connection_timeout");
      wsInstance.close();
    }, 10000); // 10 second timeout

    wsInstance.onopen = () => {
      console.log("WEBSOCKET_DEBUG: ✅ WebSocket connection established");
      clearAllTimeouts();
      setIsSocketConnected(true);
      setIsSocketReady(false); // Wait for server ready signal

      console.log("WEBSOCKET_DEBUG: Sending workspace_info request");
      try {
        wsInstance.send(JSON.stringify({ type: "workspace_info_request", content: {} }));
      } catch (error) {
        console.error("WEBSOCKET_DEBUG: Error sending workspace_info:", error);
        handleWebSocketError(error, "sending_workspace_info_on_open");
      }
    };

    wsInstance.onmessage = (event) => {
      console.log("WEBSOCKET_DEBUG: Received message:", event.data);
      try {
        const data = JSON.parse(event.data as string);
        const { type, content } = data;

        switch (type) {
          case "connection_established":
          case "workspace_info":
            console.log("WEBSOCKET_DEBUG: Server ready signal received");
            setIsSocketReady(true);
            break;
          // Other cases will be handled by the generic event receiver below
        }
        
        onEventReceivedRef.current({ ...data, id: data.id || uuidv4() });

      } catch (error) {
        console.error("WEBSOCKET_DEBUG: Error parsing WebSocket data:", error);
        handleWebSocketError(error, "message_parsing");
      }
    };

    wsInstance.onerror = (event) => {
      console.error("WEBSOCKET_DEBUG: ❌ WebSocket error event:", event);
      clearAllTimeouts();
      handleWebSocketError(event, "connection_error");
    };

    wsInstance.onclose = (event) => {
      console.log("WEBSOCKET_DEBUG: 🔌 WebSocket connection closed", `Code: ${event.code}`, `Reason: ${event.reason}`);
      clearAllTimeouts();
      
      // Only show error for unexpected closures
      if (event.code !== 1000 && event.code !== 1001) {
        handleWebSocketError(event, "connection_closed");
      }
      
      setSocket(null);
      setIsSocketConnected(false);
      setIsSocketReady(false);
      setMessageQueue([]);
    };

    setSocket(wsInstance);
  }, [deviceId, isReplayMode, handleWebSocketError, clearAllTimeouts, socket]);

  const disconnect = useCallback(() => {
    if (socket) {
      console.log("WEBSOCKET_DEBUG: Closing WebSocket connection");
      clearAllTimeouts();
      
      // Clean up event handlers to prevent further events
      socket.onopen = null;
      socket.onmessage = null;
      socket.onerror = null;
      socket.onclose = null;
      
      if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
        socket.close(1000, "Normal closure");
      }
      
      setSocket(null);
      setIsSocketConnected(false);
      setIsSocketReady(false);
      setMessageQueue([]);
    }
  }, [socket, clearAllTimeouts]);

  // Effect for initial connection
  useEffect(() => {
    if (deviceId && !isReplayMode && !socket) {
      connect();
    } else if ((!deviceId || isReplayMode) && socket) {
      disconnect();
    }

    return () => {
      disconnect();
    };
  }, [deviceId, isReplayMode, socket, connect, disconnect]);

  // Process message queue when socket becomes ready
  useEffect(() => {
    if (isSocketReady && messageQueue.length > 0) {
      processMessageQueue();
    }
  }, [isSocketReady, processMessageQueue, messageQueue.length]);

  // Effect for "thinking" timeout - simplified
  useEffect(() => {
    if (isLoading && isSocketConnected) {
      console.log("WEBSOCKET_DEBUG: Starting thinking timeout");
      
      if (thinkingTimeoutRef.current) {
        clearTimeout(thinkingTimeoutRef.current);
      }
      
      thinkingTimeoutRef.current = setTimeout(() => {
        // Removed taking longer info toast per user request
        // toast.info("Taking longer than expected. You can try sending 'continue' or refresh the page.");
      }, 60000); // 60 seconds
    } else {
      if (thinkingTimeoutRef.current) {
        console.log("WEBSOCKET_DEBUG: Clearing thinking timeout");
        clearTimeout(thinkingTimeoutRef.current);
        thinkingTimeoutRef.current = null;
      }
    }

    return () => {
      if (thinkingTimeoutRef.current) {
        clearTimeout(thinkingTimeoutRef.current);
      }
    };
  }, [isLoading, isSocketConnected]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      clearAllTimeouts();
      disconnect();
    };
  }, [clearAllTimeouts, disconnect]);

  return {
    socket,
    isSocketConnected,
    isSocketReady,
    sendMessage,
    connect,
    disconnect,
  };
};
