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
  const [pendingSessionUuid, setPendingSessionUuid] = useState<string | null>(null); // Store session_uuid from CONNECTION_ESTABLISHED

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
    setPendingSessionUuid(null);
    clearTimeoutCheck();
  }, [clearTimeoutCheck]);

  const handleEvent = useCallback((data: { id: string; type: string; content: Record<string, unknown> }) => {
    console.log("EVENT_HANDLER_DEBUG: Received event type:", data.type, data);
    
    switch (data.type) {
      case AgentEvent.USER_MESSAGE:
        console.log("EVENT_HANDLER_DEBUG: User message received, setting sessionId if needed");
        
        // Set sessionId when the first user message is received (indicating chat has started)
        if (pendingSessionUuid && !hasSetSessionId) {
          console.log("EVENT_HANDLER_DEBUG: Setting sessionId from pending:", pendingSessionUuid);
          setSessionId(pendingSessionUuid);
          setHasSetSessionId(true);
        }
        
        addMessage({
          id: data.id,
          role: "user",
          content: data.content.text as string,
          timestamp: Date.now(),
        });
        break;

      case AgentEvent.CONNECTION_ESTABLISHED:
        console.log("EVENT_HANDLER_DEBUG: Connection established with session:", data.content.session_uuid);
        
        const sessionUuid = data.content.session_uuid as string;
        // Don't automatically set sessionId on connection - only set it when a user actually starts a chat
        // Store the session UUID for when it's needed
        setPendingSessionUuid(sessionUuid);
        
        // Store connection ID for potential cleanup
        setPendingConnectionId(data.content.connection_id as string);
        break;

      case AgentEvent.AGENT_INITIALIZED:
        console.log("EVENT_HANDLER_DEBUG: Agent initialized:", data.content.message);
        
        // Set sessionId when agent is initialized (indicating chat is starting)
        if (pendingSessionUuid && !hasSetSessionId) {
          console.log("EVENT_HANDLER_DEBUG: Setting sessionId from pending (agent initialized):", pendingSessionUuid);
          setSessionId(pendingSessionUuid);
          setHasSetSessionId(true);
        }
        break;

      case AgentEvent.PROCESSING:
        console.log("EVENT_HANDLER_DEBUG: Processing started:", data.content.message);
        setIsLoading(true);
        setIsCompleted(false);
        
        // Set sessionId when processing starts (indicating chat has started)
        if (pendingSessionUuid && !hasSetSessionId) {
          console.log("EVENT_HANDLER_DEBUG: Setting sessionId from pending (processing):", pendingSessionUuid);
          setSessionId(pendingSessionUuid);
          setHasSetSessionId(true);
        }
        
        // Set a timeout to check if the agent is stuck
        const processingInterval = setInterval(() => {
          console.log("EVENT_HANDLER_DEBUG: Checking if agent is stuck after processing timeout");
          if (isLoadingRef.current) {
            console.log("EVENT_HANDLER_DEBUG: Agent appears to be stuck, showing upgrade prompt");
            
            const currentSelectedModel = selectedModelRef.current;
            const currentHasProAccess = hasProAccessRef.current;
            if (currentSelectedModel.id !== "claude-sonnet-4-0" && !currentHasProAccess()) {
              setShowUpgradePrompt("timeout");
            }
            clearInterval(processingInterval);
            setTimeoutCheckInterval(null);
          }
        }, 15000); // 15 seconds timeout
        setTimeoutCheckInterval(processingInterval);
        break;

      case "thinking":
        setIsLoading(true);
        // Set a timeout to check if the agent is stuck
        const interval = setInterval(() => {
          console.log("EVENT_HANDLER_DEBUG: Checking if agent is stuck after 15 seconds");
          if (isLoadingRef.current) {
            console.log("EVENT_HANDLER_DEBUG: Agent appears to be stuck, showing upgrade prompt");
            
            const currentSelectedModel = selectedModelRef.current;
            const currentHasProAccess = hasProAccessRef.current;
            if (currentSelectedModel.id !== "claude-sonnet-4-0" && !currentHasProAccess()) {
              setShowUpgradePrompt("timeout");
            }
            clearInterval(interval);
            setTimeoutCheckInterval(null);
          }
        }, 5000);
        setTimeoutCheckInterval(interval);
        break;

      case AgentEvent.WORKSPACE_INFO:
        console.log("EVENT_HANDLER_DEBUG: Received workspace info:", data.content.workspace_path);
        setWorkspaceInfo(data.content.workspace_path as string);
        break;

      case AgentEvent.AGENT_THINKING:
        console.log("EVENT_HANDLER_DEBUG: Agent thinking:", data.content.text);
        addMessage({
          id: data.id,
          role: "assistant",
          content: data.content.text as string,
          timestamp: Date.now(),
        });
        break;

      case AgentEvent.TOOL_CALL:
        console.log("EVENT_HANDLER_DEBUG: Tool call received:", {
          tool_name: data.content.tool_name,
          tool_input: data.content.tool_input,
          tool_call_id: data.content.tool_call_id
        });
        
        if (data.content.tool_name === TOOL.SEQUENTIAL_THINKING) {
          console.log("EVENT_HANDLER_DEBUG: Processing SEQUENTIAL_THINKING tool");
          addMessage({
            id: data.id,
            role: "assistant",
            content: (data.content.tool_input as { thought: string }).thought as string,
            timestamp: Date.now(),
          });
        } else if (data.content.tool_name === TOOL.PRESENTATION) {
          console.log("EVENT_HANDLER_DEBUG: Processing PRESENTATION tool call");
          // Handle PRESENTATION tool specially to avoid the UI action
          addMessage({
            id: data.id,
            role: "assistant", 
            content: `Creating presentation: ${JSON.stringify(data.content.tool_input)}`,
            timestamp: Date.now(),
          });
        } else {
          console.log("EVENT_HANDLER_DEBUG: Processing regular tool call:", data.content.tool_name);
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
        console.log("EVENT_HANDLER_DEBUG: File edit event:", {
          path: data.content.path,
          contentLength: (data.content.content as string)?.length
        });
        
        updateLastMessage((lastMessage) => {
          const newLastMessage = cloneDeep(lastMessage);
          if (newLastMessage.action && newLastMessage.action.type === TOOL.STR_REPLACE_EDITOR) {
            newLastMessage.action.data.content = data.content.content as string;
            newLastMessage.action.data.path = data.content.path as string;
            const currentWorkspaceInfo = workspaceInfoRef.current;
            const filePath = (data.content.path as string)?.includes(currentWorkspaceInfo)
              ? (data.content.path as string)
              : `${currentWorkspaceInfo}/${data.content.path}`;
            
            console.log("FILE_EDIT_DEBUG: Setting file content", {
              originalPath: data.content.path,
              computedFilePath: filePath,
              workspaceInfo: currentWorkspaceInfo,
              contentLength: (data.content.content as string)?.length || 0
            });
            
            setFileContent(filePath, data.content.content as string);
          }
          
          setTimeout(() => {
             if (newLastMessage.action) handleClickAction(newLastMessage.action);
          }, 500);
          return newLastMessage;
        });
        break;

      case AgentEvent.TOOL_RESULT:
        console.log("EVENT_HANDLER_DEBUG: Tool result received:", {
          tool_name: data.content.tool_name,
          resultType: typeof data.content.result,
          resultLength: typeof data.content.result === 'string' ? (data.content.result as string).length : 'N/A'
        });
        
        if (data.content.tool_name === TOOL.BROWSER_USE) {
          console.log("EVENT_HANDLER_DEBUG: Processing BROWSER_USE result");
          addMessage({
            id: data.id,
            role: "assistant",
            content: data.content.result as string,
            timestamp: Date.now(),
          });
        } else if (data.content.tool_name === TOOL.PRESENTATION) {
          console.log("EVENT_HANDLER_DEBUG: Processing PRESENTATION tool result - NOT updating UI");
          // For PRESENTATION tool, just add a simple message indicating completion
          addMessage({
            id: data.id,
            role: "assistant",
            content: `Presentation created successfully: ${data.content.result}`,
            timestamp: Date.now(),
          });
        } else if (data.content.tool_name !== TOOL.SEQUENTIAL_THINKING) {
          console.log("EVENT_HANDLER_DEBUG: Processing regular tool result for:", data.content.tool_name);
          
          if (data.content.tool_name === TOOL.STATIC_DEPLOY) {
            console.log("EVENT_HANDLER_DEBUG: Processing STATIC_DEPLOY result");
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
                console.log("EVENT_HANDLER_DEBUG: Processing browser tool result");
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
        } else {
          console.log("EVENT_HANDLER_DEBUG: Skipping SEQUENTIAL_THINKING result");
        }
        break;

      case AgentEvent.AGENT_RESPONSE:
        console.log("EVENT_HANDLER_DEBUG: Agent response received, setting sessionId if needed");
        
        // Set sessionId when agent response is received (indicating chat has started)
        if (pendingSessionUuid && !hasSetSessionId) {
          console.log("EVENT_HANDLER_DEBUG: Setting sessionId from pending (agent response):", pendingSessionUuid);
          setSessionId(pendingSessionUuid);
          setHasSetSessionId(true);
        }
        
        console.log("EVENT_HANDLER_DEBUG: Agent response content:", data.content.text);
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
        
        if (currentSelectedModel.id !== "claude-sonnet-4-0" && !currentHasProAccess()) {
          setShowUpgradePrompt("success");
        }
        if (currentUserPrompt && !currentTaskSummary) {
          currentGenerateTaskSummary(currentUserPrompt);
        }
        break;

      case AgentEvent.UPLOAD_SUCCESS:
        console.log("EVENT_HANDLER_DEBUG: Upload success:", data.content.file);
        if (data.content.file && typeof data.content.file === 'object' && 'path' in data.content.file) {
          addUploadedFile((data.content.file as { path: string }).path);
        }
        break;

      case "terminal_output":
        console.log("EVENT_HANDLER_DEBUG: Terminal output received:", data.content.output);
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
        
        clearTimeoutCheck();
        
        console.log("🚨 Server Error (event handler):", errorMessage);
        
        toast.error(errorMessage);
        setIsLoading(false);
        break;
      
      case "error":
        console.log("🚨 Server Error (event handler):", data.content.message);
        toast.error(data.content.message as string);
        setIsLoading(false);
        break;
      
      case AgentEvent.HEARTBEAT:
        // Heartbeat from server - no action needed, just keep alive
        console.debug("EVENT_HANDLER_DEBUG: Received heartbeat from server");
        break;
      
      default:
        console.warn("EVENT_HANDLER_DEBUG: Unhandled event type:", data.type, data);
        break;
    }
  }, [
    // Stable dependencies only
    addMessage, updateLastMessage, setIsLoading, setIsCompleted, setFileContent,
    setShowUpgradePrompt, addUploadedFile, setActiveTab, setDeployedUrl,
    setWorkspaceInfo, setSessionId, handleClickAction, clearTimeoutCheck, 
    hasSetSessionId, pendingConnectionId, pendingSessionUuid
  ]);

  return { handleEvent, clearTimeoutCheck, resetEventHandler };
};
