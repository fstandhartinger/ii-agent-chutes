import { useState, useCallback } from 'react';
import { cloneDeep } from 'lodash';
import { toast } from 'sonner';
import { AgentEvent, TOOL, ActionStep, Message, TAB } from '@/typings/agent';
import type { LLMModel } from '@/providers/chutes-provider';

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
  setTaskSummary: (summary: string) => void;
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
  setTaskSummary,
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
}: UseEventHandlerProps) => {
  const [timeoutCheckInterval, setTimeoutCheckInterval] = useState<NodeJS.Timeout | null>(null);

  const clearTimeoutCheck = useCallback(() => {
    if (timeoutCheckInterval) {
      clearInterval(timeoutCheckInterval);
      setTimeoutCheckInterval(null);
    }
  }, [timeoutCheckInterval]);

  const handleEvent = useCallback((data: { id: string; type: AgentEvent; content: Record<string, unknown> }) => {
    // console.log(`EVENT_HANDLER_DEBUG: Received event type: ${data.type}`, data);

    switch (data.type) {
      case AgentEvent.CONNECTION_ESTABLISHED:
        console.log("Connection established (event handler):", data.content.message);
        if (data.content.connection_id) {
          setSessionId(data.content.connection_id as string);
          console.log("EVENT_HANDLER_DEBUG: Session ID set from connection_id:", data.content.connection_id);
        }
        // Also, workspace_path often comes with this event.
        if (data.content.workspace_path) {
            setWorkspaceInfo(data.content.workspace_path as string);
            console.log("EVENT_HANDLER_DEBUG: Workspace info set from CONNECTION_ESTABLISHED:", data.content.workspace_path);
        }
        break;

      case AgentEvent.USER_MESSAGE: // Should be handled by chat input logic primarily
        addMessage({
          id: data.id,
          role: "user",
          content: data.content.text as string,
          timestamp: Date.now(),
        });
        break;

      case AgentEvent.PROCESSING:
        setIsLoading(true);
        setIsCompleted(false);
        clearTimeoutCheck(); // Clear any existing interval
        const startTime = Date.now();
        const interval = setInterval(() => {
          if (Date.now() - startTime > 60000) { // 1 minute timeout
            if (selectedModel.id !== "claude-sonnet-4-20250514" && !hasProAccessFn()) {
              setShowUpgradePrompt("timeout");
            }
            clearInterval(interval);
            setTimeoutCheckInterval(null); // Ensure it's cleared
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
          // const url = (data.content.tool_input as { url: string })?.url as string;
          // if (url) {
          //   setBrowserUrl(url); // This was in Home, setBrowserUrl is part of useUIState
          // }
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
            const filePath = (data.content.path as string)?.includes(workspaceInfo)
              ? (data.content.path as string)
              : `${workspaceInfo}/${data.content.path}`;
            setFileContent(filePath, data.content.content as string);
          }
          // No direct call to handleClickAction here as per original logic,
          // it was called after a timeout in the original setMessages callback.
          // This might need adjustment if the original setTimeout was crucial for UI updates.
          // For now, replicating the structure. The original setTimeout was 500ms.
          // The handleClickAction in the original was called on `lastMessage.action` which is `newLastMessage.action` here.
          // This implies the action data itself was updated.
          setTimeout(() => {
             if (newLastMessage.action) handleClickAction(newLastMessage.action);
          }, 500);
          return newLastMessage;
        });
        break;
      
      // BROWSER_USE event was commented out in original Home, seems it's handled by TOOL_RESULT for browser actions
      // case AgentEvent.BROWSER_USE:
      //   break;

      case AgentEvent.TOOL_RESULT:
        if (data.content.tool_name === TOOL.BROWSER_USE) { // This was specific for BROWSER_USE result
          addMessage({
            id: data.id,
            role: "assistant",
            content: data.content.result as string, // Assuming result is a string for this specific tool
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
              newLastMessage.action.data.result = `${data.content.result}`; // Ensure it's a string or handle appropriately
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
              // This case means the last message wasn't an action or didn't match the tool name.
              // This might indicate an issue or an unexpected sequence of events.
              // The original code would add a new message here.
              // For now, we'll log and potentially add as a new message if that's the desired fallback.
              console.warn("TOOL_RESULT received but last message action doesn't match:", { lastMessageAction: lastMessage?.action, toolName: data.content.tool_name });
              // Fallback: add as a new message with the action data. This might not be ideal.
              // Consider if this should be an error or a different kind of message.
              // The original code had: return [...prev, { ...lastMessage, action: data.content as ActionStep }];
              // This implies it would create a new message if the last one didn't match.
              // Let's try to replicate that, but it's a bit odd.
              // A better approach might be to ensure actions are always correctly paired.
              // For now, if no matching action, we might just log or add a simple text message.
              // The original logic was inside a setMessages(prev => ...), so it had access to 'prev'.
              // Here, we'd need to decide if we add a new message or if this state is erroneous.
              // Let's assume for now that if the last message doesn't match, we log and don't update.
              // This part of the original logic was complex and might need careful review.
              // The original `else` branch was: return [...prev, { ...lastMessage, action: data.content as ActionStep }];
              // This is problematic as `lastMessage` might not be what we want to duplicate.
              // A safer approach if no match:
              // addMessage({ id: data.id, role: "assistant", content: `Result for ${data.content.tool_name}: ${JSON.stringify(data.content.result)}`, timestamp: Date.now() });
              return lastMessage; // No change if no matching action
            }
          });
        }
        break;

      case AgentEvent.AGENT_RESPONSE:
        addMessage({
          id: Date.now().toString(), // Original used Date.now()
          role: "assistant",
          content: data.content.text as string,
          timestamp: Date.now(),
        });
        setIsCompleted(true);
        setIsLoading(false);
        clearTimeoutCheck();
        if (selectedModel.id !== "claude-sonnet-4-20250514" && !hasProAccessFn()) {
          setShowUpgradePrompt("success");
        }
        if (userPrompt && !taskSummary) {
          generateTaskSummaryFn(userPrompt);
        }
        break;

      case AgentEvent.UPLOAD_SUCCESS:
        // setIsUploading(false); // This should be handled by the upload function itself
        const newFiles = data.content.files as { path: string; saved_path: string }[];
        const paths = newFiles.map((f) => f.path);
        paths.forEach(p => addUploadedFile(p)); // Add to uploadedFiles state
        break;

      case AgentEvent.ERROR: // Renamed from "error" to AgentEvent.ERROR for consistency
        const errorMessage = data.content.message as string;
        const errorCode = data.content.error_code as string;
        const userFriendlyMessage = data.content.user_friendly as string;
        
        clearTimeoutCheck();
        
        console.group("🚨 Server Error Details (event handler)");
        console.log("Error message:", errorMessage);
        console.log("Error code:", errorCode);
        console.log("User friendly message:", userFriendlyMessage);
        console.log("Current state:", { isLoading, messagesLength: messages.length });
        console.groupEnd();
        
        const displayMessage = userFriendlyMessage || errorMessage;
        
        if (errorMessage.includes("Error running agent") && isLoading && messages.length > 0) {
          toast.error("Sorry, a new version was just released. This caused the current run to be interrupted. We're working extremely hard on this software. Sorry and thank you for your understanding!");
        } else {
          toast.error(displayMessage);
          if (selectedModel.id !== "claude-sonnet-4-20250514" && !hasProAccessFn() && isLoading) {
            setShowUpgradePrompt("error");
          }
        }
        // setIsUploading(false); // If error is related to upload
        setIsLoading(false);
        break;
      
      default:
        console.warn("Unhandled event type in handleEvent:", data.type, data);
        break;
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    // Dependencies:
    addMessage, updateLastMessage, setIsLoading, setIsCompleted, setFileContent,
    setTaskSummary, setShowUpgradePrompt, addUploadedFile, setActiveTab, setDeployedUrl,
    workspaceInfo, setWorkspaceInfo, setSessionId, handleClickAction, selectedModel, userPrompt, taskSummary,
    generateTaskSummaryFn, hasProAccessFn, clearTimeoutCheck, isLoading, messages.length // Added isLoading and messages.length for error context
  ]);

  return { handleEvent, clearTimeoutCheck };
};
