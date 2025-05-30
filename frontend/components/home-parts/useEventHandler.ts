import { useState, useCallback, useRef, useEffect } from 'react';
import { cloneDeep } from 'lodash';
import { toast } from 'sonner';
import { AgentEvent, TOOL, ActionStep, Message, TAB } from '@/typings/agent';
import type { LLMModel } from '@/providers/chutes-provider';
import type { TerminalRef } from '@/components/terminal';

// Props for the hook
export interface UseEventHandlerProps {
  // From useChatState
  messages: Message[];
  userPrompt: string;
  taskSummary: string;
  isLoading: boolean; // For error context
  addMessage: (message: Message) => void;
  updateLastMessage: (updater: (lastMessage: Message) => Message) => void;
  setIsLoading: (loading: boolean) => void;
  setIsCompleted: (completed: boolean) => void;
  setFileContent: (filePath: string, content: string) => void;
  setShowUpgradePrompt: (prompt: "success" | "error" | "timeout" | null) => void;
  setUserPrompt: (prompt: string) => void; // Needed if generateTaskSummary is called from here
  addUploadedFile: (filePath: string) => void; // For UPLOAD_SUCCESS

  // From useUIState
  setActiveTab: (tab: TAB) => void;
  setDeployedUrl: (url: string) => void;
  // handleClickAction is separate

  // From useSessionManager
  workspaceInfo: string;
  setWorkspaceInfo: (info: string) => void;
  setSessionId: (id: string | null) => void; // Added to set session ID

  // From useActionHandler (passed directly)
  handleClickAction: (data: ActionStep | undefined, showTabOnly?: boolean) => void;

  // From useChutes (via Home props)
  selectedModel: LLMModel;

  // Utility functions (passed via Home props)
  generateTaskSummaryFn: (firstUserMessage: string) => Promise<void>;
  // getRemoteURLFn: (path: string | undefined) => string; // This was used for ImageBrowser, might be handled differently
  hasProAccessFn: () => boolean;

  // Terminal ref for handling terminal output
  terminalRef?: React.RefObject<TerminalRef | null>;
}

export const useEventHandler = ({
  messages,
  userPrompt,
  taskSummary,
  isLoading,
  addMessage,
  updateLastMessage,
  setIsLoading,
  setIsCompleted,
  setFileContent,
  setShowUpgradePrompt,
  // setUserPrompt, // Not directly setting, but using userPrompt
  addUploadedFile,
  setActiveTab,
  setDeployedUrl,
  workspaceInfo,
  setWorkspaceInfo,
  setSessionId, // Added
  handleClickAction,
  selectedModel,
  generateTaskSummaryFn,
  hasProAccessFn,
  terminalRef,
}: UseEventHandlerProps) => {
  const [timeoutCheckInterval, setTimeoutCheckInterval] = useState<NodeJS.Timeout | null>(null);
  const [hasSetSessionId, setHasSetSessionId] = useState(false); // Track if sessionId has been set
  const [pendingConnectionId, setPendingConnectionId] = useState<string | null>(null); // Store connection_id from CONNECTION_ESTABLISHED

  // Use refs for stable references to prevent unnecessary re-renders
  const selectedModelRef = useRef(selectedModel);
  const hasProAccessRef = useRef(hasProAccessFn);
  const userPromptRef = useRef(userPrompt);
  const taskSummaryRef = useRef(taskSummary);
  const isLoadingRef = useRef(isLoading);
  const messagesLengthRef = useRef(messages.length);
  const workspaceInfoRef = useRef(workspaceInfo);
  const generateTaskSummaryRef = useRef(generateTaskSummaryFn);

  // Update refs when values change
  useEffect(() => {
    selectedModelRef.current = selectedModel;
    hasProAccessRef.current = hasProAccessFn;
    userPromptRef.current = userPrompt;
    taskSummaryRef.current = taskSummary;
    isLoadingRef.current = isLoading;
    messagesLengthRef.current = messages.length;
    workspaceInfoRef.current = workspaceInfo;
    generateTaskSummaryRef.current = generateTaskSummaryFn;
  });

  const clearTimeoutCheck = useCallback(() => {
    if (timeoutCheckInterval) {
      clearInterval(timeoutCheckInterval);
      setTimeoutCheckInterval(null);
    }
  }, [timeoutCheckInterval]);

  // Reset function to be called when a new chat starts
  const resetEventHandler = useCallback(() => {
    setHasSetSessionId(false);
    setPendingConnectionId(null);
    clearTimeoutCheck();
  }, [clearTimeoutCheck]);

  const handleEvent = useCallback((data: { id: string; type: string; content: Record<string, unknown> }) => {
    console.log(`EVENT_HANDLER_DEBUG: Received event type: ${data.type}`, data);

    switch (data.type) {
      case AgentEvent.CONNECTION_ESTABLISHED:
        console.log("Connection established (event handler):", data.content.message);
        // Store connection_id for later use when chat actually starts
        if (data.content.connection_id) {
          setPendingConnectionId(data.content.connection_id as string);
          console.log("EVENT_HANDLER_DEBUG: Stored connection_id for later use:", data.content.connection_id);
        }
        // Also, workspace_path often comes with this event.
        if (data.content.workspace_path) {
            setWorkspaceInfo(data.content.workspace_path as string);
            console.log("EVENT_HANDLER_DEBUG: Workspace info set from CONNECTION_ESTABLISHED:", data.content.workspace_path);
            
            // DO NOT automatically set session ID here - only set it when a chat actually starts
            // This was causing the issue where the chat view would open immediately
        }
        break;

      case AgentEvent.USER_MESSAGE: // Should be handled by chat input logic primarily
        // SessionId setting moved to PROCESSING event
        addMessage({
          id: data.id,
          role: "user",
          content: data.content.text as string,
          timestamp: Date.now(),
        });
        break;

      case AgentEvent.PROCESSING:
        // Set sessionId when processing starts - this indicates a real chat session has begun
        if (pendingConnectionId && !hasSetSessionId) {
          setSessionId(pendingConnectionId);
          setHasSetSessionId(true);
          console.log("EVENT_HANDLER_DEBUG: Session ID set from PROCESSING event using stored connection_id:", pendingConnectionId);
        }
        setIsLoading(true);
        setIsCompleted(false);
        clearTimeoutCheck(); // Clear any existing interval
        
        const startTime = Date.now();
        const interval = setInterval(() => {
          const currentSelectedModel = selectedModelRef.current;
          const currentHasProAccess = hasProAccessRef.current;
          
          if (Date.now() - startTime > 60000) { // 1 minute timeout
            if (currentSelectedModel.id !== "claude-sonnet-4-20250514" && !currentHasProAccess()) {
              setShowUpgradePrompt("timeout");
            }
            clearInterval(interval);
            setTimeoutCheckInterval(null);
          }
        }, 5000);
        setTimeoutCheckInterval(interval);
        break;

      case AgentEvent.WORKSPACE_INFO:
        setWorkspaceInfo(data.content.path as string);
        break;

      case AgentEvent.AGENT_THINKING:
        addMessage({
          id: data.id,
          role: "assistant",
          content: data.content.text as string,
          timestamp: Date.now(),
        });
        break;

      case AgentEvent.TOOL_CALL:
        if (data.content.tool_name === TOOL.SEQUENTIAL_THINKING) {
          addMessage({
            id: data.id,
            role: "assistant",
            content: (data.content.tool_input as { thought: string }).thought as string,
            timestamp: Date.now(),
          });
        } else {
          const message: Message = {
            id: data.id,
            role: "assistant",
            action: {
              type: data.content.tool_name as TOOL,
              data: data.content,
            },
            timestamp: Date.now(),
          };
          addMessage(message);
          handleClickAction(message.action);
        }
        break;

      case AgentEvent.FILE_EDIT:
        updateLastMessage((lastMessage) => {
          const newLastMessage = cloneDeep(lastMessage);
          if (newLastMessage.action && newLastMessage.action.type === TOOL.STR_REPLACE_EDITOR) {
            newLastMessage.action.data.content = data.content.content as string;
            newLastMessage.action.data.path = data.content.path as string;
            const currentWorkspaceInfo = workspaceInfoRef.current;
            const filePath = (data.content.path as string)?.includes(currentWorkspaceInfo)
              ? (data.content.path as string)
              : `${currentWorkspaceInfo}/${data.content.path}`;
            setFileContent(filePath, data.content.content as string);
          }
          
          setTimeout(() => {
             if (newLastMessage.action) handleClickAction(newLastMessage.action);
          }, 500);
          return newLastMessage;
        });
        break;

      case AgentEvent.TOOL_RESULT:
        if (data.content.tool_name === TOOL.BROWSER_USE) {
          addMessage({
            id: data.id,
            role: "assistant",
            content: data.content.result as string,
            timestamp: Date.now(),
          });
        } else if (data.content.tool_name !== TOOL.SEQUENTIAL_THINKING && data.content.tool_name !== TOOL.PRESENTATION) {
          if (data.content.tool_name === TOOL.STATIC_DEPLOY) {
            const result = data.content.result as string;
            if (result && result.startsWith('http')) {
              setDeployedUrl(result);
              setActiveTab(TAB.WEBSITE);
            }
          }
          
          updateLastMessage((lastMessage) => {
            const newLastMessage = cloneDeep(lastMessage);
            if (newLastMessage?.action && newLastMessage.action?.type === data.content.tool_name) {
              newLastMessage.action.data.result = `${data.content.result}`;
              if (
                [
                  TOOL.BROWSER_VIEW, TOOL.BROWSER_CLICK, TOOL.BROWSER_ENTER_TEXT,
                  TOOL.BROWSER_PRESS_KEY, TOOL.BROWSER_GET_SELECT_OPTIONS,
                  TOOL.BROWSER_SELECT_DROPDOWN_OPTION, TOOL.BROWSER_SWITCH_TAB,
                  TOOL.BROWSER_OPEN_NEW_TAB, TOOL.BROWSER_WAIT, TOOL.BROWSER_SCROLL_DOWN,
                  TOOL.BROWSER_SCROLL_UP, TOOL.BROWSER_NAVIGATION, TOOL.BROWSER_RESTART,
                ].includes(data.content.tool_name as TOOL)
              ) {
                // Special handling for browser tools that return image data in result
                newLastMessage.action.data.result =
                  data.content.result && Array.isArray(data.content.result)
                    ? data.content.result.find((item: { type: string; source?: { data?: string } }) => item.type === "image")?.source?.data
                    : undefined;
              }
              newLastMessage.action.data.isResult = true;
              setTimeout(() => {
                if (newLastMessage.action) handleClickAction(newLastMessage.action);
              }, 500);
              return newLastMessage;
            } else {
              console.warn("TOOL_RESULT received but last message action doesn't match:", { lastMessageAction: lastMessage?.action, toolName: data.content.tool_name });
              return lastMessage;
            }
          });
        }
        break;

      case AgentEvent.AGENT_RESPONSE:
        addMessage({
          id: Date.now().toString(),
          role: "assistant",
          content: data.content.text as string,
          timestamp: Date.now(),
        });
        setIsCompleted(true);
        setIsLoading(false);
        clearTimeoutCheck();
        
        const currentSelectedModel = selectedModelRef.current;
        const currentHasProAccess = hasProAccessRef.current;
        const currentUserPrompt = userPromptRef.current;
        const currentTaskSummary = taskSummaryRef.current;
        const currentGenerateTaskSummary = generateTaskSummaryRef.current;
        
        if (currentSelectedModel.id !== "claude-sonnet-4-20250514" && !currentHasProAccess()) {
          setShowUpgradePrompt("success");
        }
        if (currentUserPrompt && !currentTaskSummary) {
          currentGenerateTaskSummary(currentUserPrompt);
        }
        break;

      case AgentEvent.UPLOAD_SUCCESS:
        if (data.content.file && typeof data.content.file === 'object' && 'path' in data.content.file) {
          addUploadedFile((data.content.file as { path: string }).path);
        }
        break;

      case "terminal_output":
        // Handle terminal output events
        if (data.content.output && terminalRef?.current) {
          terminalRef.current.writeOutput(data.content.output as string);
          console.log("EVENT_HANDLER_DEBUG: Sent terminal output to terminal component:", data.content.output);
        } else {
          console.log("EVENT_HANDLER_DEBUG: Received terminal output but terminal ref not available:", data.content.output);
        }
        break;

      case AgentEvent.ERROR:
        const errorMessage = data.content.message as string;
        const errorCode = data.content.error_code as string;
        const userFriendlyMessage = data.content.user_friendly as string;
        
        clearTimeoutCheck();
        
        console.group("🚨 Server Error Details (event handler)");
        console.log("Error message:", errorMessage);
        console.log("Error code:", errorCode);
        console.log("User friendly message:", userFriendlyMessage);
        console.log("Current state:", { 
          isLoading: isLoadingRef.current, 
          messagesLength: messagesLengthRef.current 
        });
        console.groupEnd();
        
        const displayMessage = userFriendlyMessage || errorMessage;
        
        if (errorMessage.includes("Error running agent") && isLoadingRef.current && messagesLengthRef.current > 0) {
          toast.error("Sorry, a new version was just released. This caused the current run to be interrupted. We're working extremely hard on this software. Sorry and thank you for your understanding!");
        } else {
          toast.error(displayMessage);
          const currentSelectedModel = selectedModelRef.current;
          const currentHasProAccess = hasProAccessRef.current;
          if (currentSelectedModel.id !== "claude-sonnet-4-20250514" && !currentHasProAccess() && isLoadingRef.current) {
            setShowUpgradePrompt("error");
          }
        }
        setIsLoading(false);
        break;
      
      case AgentEvent.HEARTBEAT:
        // Heartbeat from server - no action needed, just keep alive
        console.debug("EVENT_HANDLER_DEBUG: Received heartbeat from server");
        break;
      
      default:
        console.warn("Unhandled event type in handleEvent:", data.type, data);
        break;
    }
  }, [
    // Stable dependencies only
    addMessage, updateLastMessage, setIsLoading, setIsCompleted, setFileContent,
    setShowUpgradePrompt, addUploadedFile, setActiveTab, setDeployedUrl,
    setWorkspaceInfo, setSessionId, handleClickAction, clearTimeoutCheck, 
    hasSetSessionId, pendingConnectionId
  ]);

  return { handleEvent, clearTimeoutCheck, resetEventHandler };
};
