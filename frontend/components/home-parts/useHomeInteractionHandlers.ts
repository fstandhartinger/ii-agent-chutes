/* eslint-disable @typescript-eslint/no-unused-vars */
/* eslint-disable @typescript-eslint/no-explicit-any */
/* eslint-disable react-hooks/exhaustive-deps */
import { useCallback } from 'react';
import { useRouter } from 'next/navigation'; // For handleShare
import { toast } from 'sonner';
import { v4 as uuidv4 } from 'uuid'; // For message IDs if needed
import type { Message } from '@/typings/agent';
import type { LLMModel } from '@/providers/chutes-provider';
import { hasUserConsented, setUserConsent } from "@/components/consent-dialog"; // Assuming these can be imported
import { TAB } from '@/typings/agent';

// Props for the hook - these will come from other hooks or Home component props
export interface UseHomeInteractionHandlersProps {
  // From useChatState
  isLoading: boolean;
  messages: any[];
  uploadedFiles: string[];
  userPrompt: string;
  pendingQuestion: string;
  isUseDeepResearch: boolean;
  setIsLoading: (loading: boolean) => void;
  setCurrentQuestion: (question: string) => void;
  setIsCompleted: (completed: boolean) => void;
  addMessage: (message: any) => void;
  setUserPrompt: (prompt: string) => void;
  setIsUploading: (uploading: boolean) => void;
  addUploadedFile: (filePath: string) => void;
  setPendingQuestion: (question: string) => void;
  setShowUpgradePrompt: (prompt: "success" | "error" | "timeout" | null) => void;
  setMessages: (messages: any[]) => void;

  // From useUIState
  logoClickCount: number;
  setShowConsentDialog: (show: boolean) => void;
  triggerShakeConnectionIndicator: () => void;
  incrementLogoClickCount: () => void;
  setShowNativeToolToggle: (show: boolean) => void;
  setActiveTab: (tab: TAB) => void;

  // From useSessionManager
  sessionId: string | null;
  workspaceInfo: string; // For file uploads
  hasProAccess: () => boolean;

  // From useWebSocketManager
  isSocketConnected: boolean;
  isSocketReady: boolean;
  sendMessage: (message: any) => void;
  socket: WebSocket | null; // For handleStopAgent

  // From useChutes (via Home props)
  selectedModel: LLMModel;
  // generateTaskSummary prop is no longer needed here if it's passed from Home to eventHandler directly

  // Utility functions (passed via Home props)
  parseJsonFn: (jsonString: string) => any;
}

export const useHomeInteractionHandlers = ({
  isLoading,
  messages,
  uploadedFiles,
  userPrompt,
  pendingQuestion,
  isUseDeepResearch,
  setIsLoading,
  setCurrentQuestion,
  setIsCompleted,
  addMessage,
  setUserPrompt,
  setIsUploading,
  addUploadedFile,
  setPendingQuestion,
  setShowUpgradePrompt,
  setMessages,
  logoClickCount,
  setShowConsentDialog,
  triggerShakeConnectionIndicator,
  incrementLogoClickCount,
  setShowNativeToolToggle,
  setActiveTab,
  sessionId,
  workspaceInfo,
  hasProAccess,
  isSocketConnected,
  isSocketReady,
  sendMessage,
  socket,
  selectedModel,
  parseJsonFn,
}: UseHomeInteractionHandlersProps) => {
  const router = useRouter();

  // generateTaskSummary is now defined in Home.tsx and passed to useEventHandler.
  // This hook doesn't need to define it if it doesn't call it directly.
  // If any handler here *did* call it, it would need to be passed in as a prop.

  const handleQuestionSubmit = useCallback(async (newQuestion: string) => {
    if (!newQuestion.trim() || isLoading) return;

    if (!hasUserConsented()) {
      setPendingQuestion(newQuestion);
      setShowConsentDialog(true);
      return;
    }

    setIsLoading(true);
    setCurrentQuestion(""); // Clear input
    setIsCompleted(false);
    setShowUpgradePrompt(null);

    const newUserMessage: Message = {
      id: uuidv4(), // Generate unique ID
      role: "user",
      content: newQuestion,
      timestamp: Date.now(),
    };
    addMessage(newUserMessage);

    if (messages.length === 0) { // First message from user
      setUserPrompt(newQuestion);
      // Task summary generation is now handled by useEventHandler after first LLM response
    }

    if (!isSocketConnected || !isSocketReady || !socket || socket.readyState !== WebSocket.OPEN) {
      console.error("🚫 WebSocket not ready for sending message (handleQuestionSubmit)");
      let errorToastMessage = "Connection not ready. ";
      if (!socket) errorToastMessage += "WebSocket not initialized. ";
      else if (!isSocketConnected) errorToastMessage += "WebSocket not connected. ";
      else if (!isSocketReady) errorToastMessage += "Server not ready yet. ";
      else if (socket.readyState !== WebSocket.OPEN) errorToastMessage += `WebSocket in ${socket.readyState} state. `;
      errorToastMessage += "Please wait or refresh.";
      toast.error(errorToastMessage);
      setIsLoading(false);
      return;
    }

    try {
      await sendMessage({
        type: "init_agent",
        content: {
          tool_args: {
            deep_research: isUseDeepResearch,
            pdf: true, media_generation: true, audio_generation: true, browser: true,
          },
        },
      });
      await sendMessage({
        type: "query",
        content: {
          text: newQuestion,
          resume: messages.length > 0, // resume is true if there are previous messages
          files: uploadedFiles?.map((file) => file.startsWith('/') ? file.substring(1) : file),
        },
      });
    } catch (error) {
      console.error("Error sending message (handleQuestionSubmit):", error);
      toast.error("Failed to send message. Please refresh and try again.");
      setIsLoading(false);
    }
  }, [
    isLoading, hasUserConsented, setPendingQuestion, setShowConsentDialog, setIsLoading, setCurrentQuestion,
    setIsCompleted, setShowUpgradePrompt, addMessage, messages.length, setUserPrompt, isSocketConnected,
    isSocketReady, socket, sendMessage, isUseDeepResearch, uploadedFiles
  ]);

  const handleFileUpload = useCallback(async (event: React.ChangeEvent<HTMLInputElement>) => {
    if (!event.target.files || event.target.files.length === 0) return;
    const files = Array.from(event.target.files);
    setIsUploading(true);

    const fileContentMap: { [filename: string]: string } = {};
    const connectionId = workspaceInfo.split("/").pop(); // Used as session_id for upload

    const newUserMessage: Message = {
      id: uuidv4(),
      role: "user",
      files: files.map((file) => file.name),
      fileContents: {}, // Initially empty, will be populated after reading
      timestamp: Date.now(),
    };
    addMessage(newUserMessage);

    const uploadPromises = files.map(file => {
      return new Promise<{ name: string; success: boolean; path?: string }>(async (resolve) => {
        try {
          const reader = new FileReader();
          reader.onload = async (e) => {
            const content = e.target?.result as string; // Base64 content
            fileContentMap[file.name] = content; // Store for potential display in chat

            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/upload`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ session_id: connectionId, file: { path: file.name, content } }),
            });
            const result = await response.json();
            if (response.ok && result.file?.path) {
              addUploadedFile(result.file.path); // Add to list of successfully uploaded files
              resolve({ name: file.name, success: true, path: result.file.path });
            } else {
              console.error(`Error uploading ${file.name}:`, result.error);
              resolve({ name: file.name, success: false });
            }
          };
          reader.onerror = () => resolve({ name: file.name, success: false });
          reader.readAsDataURL(file);
        } catch (err) {
          console.error(`Error processing ${file.name}:`, err);
          resolve({ name: file.name, success: false });
        }
      });
    });

    try {
      const results = await Promise.all(uploadPromises);
      const failedUploads = results.filter(r => !r.success);
      if (failedUploads.length > 0) {
        toast.error(`Failed to upload ${failedUploads.length} file(s): ${failedUploads.map(f => f.name).join(', ')}`);
      }
      // Update the message with file contents (if needed for display, though original didn't seem to use it this way)
      // The `uploadedFiles` state in `useChatState` is the primary list of files for the agent.
    } catch (error) {
      console.error("Error uploading files:", error);
      toast.error("Error during file upload process.");
    } finally {
      setIsUploading(false);
      if (event.target) event.target.value = ""; // Clear file input
    }
  }, [setIsUploading, workspaceInfo, addMessage, addUploadedFile]);

  const handleExampleClick = useCallback(async (text: string, deepResearch: boolean, fileUrl?: string) => {
    if (!isSocketConnected || !isSocketReady) {
      triggerShakeConnectionIndicator();
      toast.info("Please wait for server connection...");
      return;
    }
    setCurrentQuestion(text);
    // setIsUseDeepResearch(deepResearch); // This should be handled by QuestionInput's own state or passed to it

    if (fileUrl) {
      try {
        setIsUploading(true);
        const response = await fetch(fileUrl);
        if (!response.ok) throw new Error(`Failed to download: ${response.statusText}`);
        const blob = await response.blob();
        const fileName = fileUrl.split('/').pop() || 'downloaded_file';
        const file = new File([blob], fileName, { type: blob.type });
        
        const dataTransfer = new DataTransfer();
        dataTransfer.items.add(file);
        const fakeEvent = { target: { files: dataTransfer.files, value: "" } } as unknown as React.ChangeEvent<HTMLInputElement>;
        await handleFileUpload(fakeEvent); // Reuse handleFileUpload
        // handleFileUpload sets isUploading to false
      } catch (error) {
        console.error("Error in handleExampleClick file handling:", error);
        toast.error("Failed to download/attach example file.");
        setIsUploading(false);
      }
    }
    // Submit question after a delay if a file was processed
    setTimeout(() => {
      handleQuestionSubmit(text); // isUseDeepResearch is read from state in handleQuestionSubmit
    }, fileUrl ? 500 : 0);
  }, [isSocketConnected, isSocketReady, triggerShakeConnectionIndicator, setCurrentQuestion, setIsUploading, handleFileUpload, handleQuestionSubmit]);

  const handleShare = useCallback(() => {
    if (!sessionId) {
      toast.error("No active session to share.");
      return;
    }
    const url = `${window.location.origin}/?id=${sessionId}`;
    navigator.clipboard.writeText(url)
      .then(() => toast.success("Session link copied to clipboard!"))
      .catch(() => toast.error("Failed to copy link."));
  }, [sessionId]);

  const handleStopAgent = useCallback(() => {
    if (!socket || !isSocketConnected || socket.readyState !== WebSocket.OPEN) {
      toast.error("WebSocket not available to stop agent.");
      return;
    }
    if (!isLoading) {
      toast.info("No active agent run to stop.");
      return;
    }
    sendMessage({ type: "cancel", content: {} });
    setIsLoading(false); // Optimistically update UI
    toast.success("Agent run stop request sent.");
  }, [socket, isSocketConnected, isLoading, sendMessage, setIsLoading]);

  const handleLogoClick = useCallback(() => {
    incrementLogoClickCount();
    if (logoClickCount + 1 >= 5) { // Check against new count
      setShowNativeToolToggle(true);
      toast.success("Native Tool Calling toggle unlocked!");
    }
  }, [logoClickCount, incrementLogoClickCount, setShowNativeToolToggle]);

  const handleConsentAccept = useCallback(() => {
    setUserConsent();
    setShowConsentDialog(false);
    if (pendingQuestion) {
      handleQuestionSubmit(pendingQuestion);
      setPendingQuestion("");
    }
  }, [pendingQuestion, handleQuestionSubmit, setPendingQuestion, setShowConsentDialog]);

  const handleConsentCancel = useCallback(() => {
    setShowConsentDialog(false);
    setPendingQuestion("");
  }, [setShowConsentDialog, setPendingQuestion]);


  return {
    // generateTaskSummary, // Removed if not defined here
    handleQuestionSubmit,
    handleFileUpload,
    handleExampleClick,
    handleShare,
    handleStopAgent,
    handleLogoClick,
    handleConsentAccept,
    handleConsentCancel,
  };
};
