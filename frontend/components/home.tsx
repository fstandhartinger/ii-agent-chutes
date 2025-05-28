"use client";

// Import ohne Namenskollision
const Browser = dynamic(() => import("@/components/browser"), { ssr: false });
const WebsiteViewer = dynamic(() => import("./website-viewer"), { ssr: false });
const TerminalComponent = dynamic(() => import("./terminal"), { ssr: false });
import type { TerminalRef } from "./terminal";
import { AnimatePresence, LayoutGroup, motion } from "framer-motion";
import {
  Code,
  Globe,
  Terminal as TerminalIcon,
  Loader2,
  Share,
  Menu,
  Sparkles,
  ArrowLeft,
  RefreshCw,
} from "lucide-react";
import Image from "next/image";
import { useEffect, useMemo, useRef, useState, useCallback } from "react";
import { toast } from "sonner";
import { cloneDeep, debounce } from "lodash";
import Cookies from "js-cookie";
import { v4 as uuidv4 } from "uuid";
import { useRouter, useSearchParams } from "next/navigation";
import { useChutes } from "@/providers/chutes-provider";
import Examples from "@/components/examples";
import ModelPicker from "@/components/model-picker";
import ProUpgradeButton from "@/components/pro-upgrade-button";
import { hasProAccess, getProKey } from "@/utils/pro-utils";

import dynamic from "next/dynamic";
const CodeEditor = dynamic(() => import("@/components/code-editor"), { ssr: false });

// Message type for WebSocket communication
interface WebSocketMessage {
  type: string;
  content?: unknown;
  text?: string;
  resume?: boolean;
  files?: { name: string; content: string }[]; // More specific type for files if known
  // Add other potential properties of your WebSocket messages here
}
import QuestionInput from "@/components/question-input";
import SearchBrowser from "@/components/search-browser";
import { Button } from "@/components/ui/button";
import {
  ActionStep,
  AgentEvent,
  IEvent,
  Message,
  TAB,
  TOOL,
} from "@/typings/agent";
const ChatMessage = dynamic(() => import("./chat-message"), { ssr: false });
const ImageBrowser = dynamic(() => import("./image-browser"), { ssr: false });

import InstallPrompt from "./install-prompt";
import ConsentDialog, { hasUserConsented, setUserConsent } from "./consent-dialog";
import CookieBanner from "./cookie-banner";

export default function Home() {
  // entferne die doppelte Deklaration, behalte nur die unten
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const searchParams = useSearchParams();
  const router = useRouter();

  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [isSocketConnected, setIsSocketConnected] = useState(false);
  const [isSocketReady, setIsSocketReady] = useState(false); // NEW: Server confirmed ready
  const [messageQueue, setMessageQueue] = useState<WebSocketMessage[]>([]); // NEW: Queue for messages
  const [retryAttempt, setRetryAttempt] = useState(0); // NEW: Track retry attempts
  const [activeTab, setActiveTab] = useState(TAB.BROWSER);
  const [currentActionData, setCurrentActionData] = useState<ActionStep>();
  const [activeFileCodeEditor, setActiveFileCodeEditor] = useState("");
  const [currentQuestion, setCurrentQuestion] = useState("");
  const [isCompleted, setIsCompleted] = useState(false);
  const [workspaceInfo, setWorkspaceInfo] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<string[]>([]);
  const [isUseDeepResearch, setIsUseDeepResearch] = useState(false);
  const [deviceId, setDeviceId] = useState<string>("");
  const [sessionId, setSessionId] = useState<string | null>(null);

  // Session-ID beim Mount aus URL initialisieren
  useEffect(() => {
    const id = searchParams.get('id');
    if (id) setSessionId(id);
  }, [searchParams]);
  const [isLoadingSession, setIsLoadingSession] = useState(false);
  const [filesContent, setFilesContent] = useState<{ [key: string]: string }>(
    {}
  );
  const [browserUrl, setBrowserUrl] = useState("");
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isMobileDetailPaneOpen, setIsMobileDetailPaneOpen] = useState(false);
  const [deployedUrl, setDeployedUrl] = useState<string>("");
  const [taskSummary, setTaskSummary] = useState<string>("");
  const [userPrompt, setUserPrompt] = useState<string>("");
  const [useNativeToolCalling, setUseNativeToolCalling] = useState(false);
  const [logoClickCount, setLogoClickCount] = useState(0);
  const [showNativeToolToggle, setShowNativeToolToggle] = useState(false);
  const [showConsentDialog, setShowConsentDialog] = useState(false);
  const [pendingQuestion, setPendingQuestion] = useState<string>("");
  const [showUpgradePrompt, setShowUpgradePrompt] = useState<
    "success" | "error" | "timeout" | null
  >(null);
  const [timeoutCheckInterval, setTimeoutCheckInterval] = useState<
    NodeJS.Timeout | null
  >(null);
  const [shouldShakeConnectionIndicator, setShouldShakeConnectionIndicator] = useState(false);
  const [showReloadButton, setShowReloadButton] = useState(false);
  const [returnedFromChat, setReturnedFromChat] = useState(false);
  // Referenz für die Terminal-Komponente mit korrektem Typ
  const terminalRef = useRef<TerminalRef>(null);

  const isReplayMode = useMemo(() => !!searchParams.get("id"), [searchParams]);
  const { selectedModel, setSelectedModel } = useChutes();

  // Generate task summary using LLM
  const generateTaskSummary = async (firstUserMessage: string) => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/generate-summary`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: firstUserMessage,
          modelId: selectedModel.id,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setTaskSummary(data.summary || "Task in progress");
      } else {
        console.error("Error generating task summary:", response.statusText);
        setTaskSummary("Task in progress");
      }
    } catch (error) {
      console.error("Error generating task summary:", error);
      setTaskSummary("Task in progress");
    }
  };

  // Get session ID from URL params
  useEffect(() => {
    const id = searchParams.get("id");
    setSessionId(id);
  }, [searchParams]);

  // Fetch session events when session ID is available
  useEffect(() => {
    const fetchSessionEvents = async () => {
      const id = searchParams.get("id");
      if (!id) return;

      setIsLoadingSession(true);
      try {
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/api/sessions/${id}/events`
        );

        if (!response.ok) {
          throw new Error(
            `Error fetching session events: ${response.statusText}`
          );
        }

        const data = await response.json();
        setWorkspaceInfo(data.events?.[0]?.workspace_dir);

        if (data.events && Array.isArray(data.events)) {
          // Process events to reconstruct the conversation
          const reconstructedMessages: Message[] = [];

          // Function to process events with delay
          const processEventsWithDelay = async () => {
            setIsLoading(true);
            for (let i = 0; i < data.events.length; i++) {
              const event = data.events[i];
              // Process each event with a 2-second delay
              await new Promise((resolve) => setTimeout(resolve, 50));
              handleEvent({ ...event.event_payload, id: event.id });
            }
            setIsLoading(false);
          };

          // Start processing events with delay
          processEventsWithDelay();

          // Set the reconstructed messages
          if (reconstructedMessages.length > 0) {
            setMessages(reconstructedMessages);
            setIsCompleted(true);
          }

          // Extract workspace info if available
          const workspaceEvent = data.events.find(
            (e: IEvent) => e.event_type === AgentEvent.WORKSPACE_INFO
          );
          if (workspaceEvent && workspaceEvent.event_payload.path) {
            setWorkspaceInfo(workspaceEvent.event_payload.path);
          }
        }
      } catch (error) {
        console.error("Failed to fetch session events:", error);
        toast.error("Failed to load session history");
      } finally {
        setIsLoadingSession(false);
      }
    };

    fetchSessionEvents();
  }, [searchParams]); // eslint-disable-line react-hooks/exhaustive-deps

  // Initialize device ID on page load
  useEffect(() => {
    // Check if device ID exists in cookies
    let existingDeviceId = Cookies.get("device_id");

    // If no device ID exists, generate a new one and save it
    if (!existingDeviceId) {
      existingDeviceId = uuidv4();

      // Set cookie with a long expiration (1 year)
      Cookies.set("device_id", existingDeviceId, {
        expires: 365,
        sameSite: "strict",
        secure: window.location.protocol === "https:",
      });

      console.log("Generated new device ID:", existingDeviceId);
    } else {
      console.log("Using existing device ID:", existingDeviceId);
    }

    // Set the device ID in state
    setDeviceId(existingDeviceId);
  }, []);

  // Auto-switch Pro users to Sonnet 4 (backup logic in case ModelPicker doesn't handle it)
  useEffect(() => {
    const proAccess = hasProAccess();
    const manualSwitch = localStorage.getItem("userManuallySwitchedModel");
    
    // Only auto-switch if user has Pro access, hasn't manually switched, and current model isn't Sonnet 4
    if (proAccess && manualSwitch !== "true" && selectedModel.id !== "claude-sonnet-4-20250514") {
      console.log("Home: Auto-switching Pro user to Claude Sonnet 4");
      
      const sonnet4Model = {
        id: "claude-sonnet-4-20250514",
        name: "Claude Sonnet 4",
        provider: "anthropic" as const,
        supportsVision: true
      };
      
      setSelectedModel(sonnet4Model);
    }
  }, [selectedModel, setSelectedModel]);

  const handleClickAction = debounce(
    (data: ActionStep | undefined, showTabOnly = false) => {
      if (!data) return;

      switch (data.type) {
        case TOOL.WEB_SEARCH:
          setActiveTab(TAB.BROWSER);
          setCurrentActionData(data);
          break;

        case TOOL.IMAGE_GENERATE:
        case TOOL.BROWSER_USE:
        case TOOL.VISIT:
          setActiveTab(TAB.BROWSER);
          setCurrentActionData(data);
          break;

        case TOOL.BROWSER_CLICK:
        case TOOL.BROWSER_ENTER_TEXT:
        case TOOL.BROWSER_PRESS_KEY:
        case TOOL.BROWSER_GET_SELECT_OPTIONS:
        case TOOL.BROWSER_SELECT_DROPDOWN_OPTION:
        case TOOL.BROWSER_SWITCH_TAB:
        case TOOL.BROWSER_OPEN_NEW_TAB:
        case TOOL.BROWSER_VIEW:
        case TOOL.BROWSER_NAVIGATION:
        case TOOL.BROWSER_RESTART:
        case TOOL.BROWSER_WAIT:
        case TOOL.BROWSER_SCROLL_DOWN:
        case TOOL.BROWSER_SCROLL_UP:
          setActiveTab(TAB.BROWSER);
          setCurrentActionData(data);
          break;

        case TOOL.BASH:
          setActiveTab(TAB.TERMINAL);
          if (!showTabOnly) {
            setTimeout(() => {
              if (!data.data?.isResult) {
                // query
                terminalRef.current?.writeOutput(
                  `${data.data.tool_input?.command || ""}`
                );
              }
              // result
              if (data.data.result) {
                const lines = `${data.data.result || ""}`.split("\n");
                lines.forEach((line) => {
                  terminalRef.current?.writeOutput(line);
                });
                terminalRef.current?.writeOutput("$ ");
              }
            }, 500);
          }
          break;

        case TOOL.STR_REPLACE_EDITOR:
          setActiveTab(TAB.CODE);
          setCurrentActionData(data);
          const path = data.data.tool_input?.path || data.data.tool_input?.file;
          if (path) {
            setActiveFileCodeEditor(
              path.startsWith(workspaceInfo) ? path : `${workspaceInfo}/${path}`
            );
          }
          break;

        default:
          break;
      }
    },
    50
  );

  const handleLogoClick = () => {
    const newCount = logoClickCount + 1;
    setLogoClickCount(newCount);
    
    if (newCount >= 5) {
      setShowNativeToolToggle(true);
      toast.success("Hidden features unlocked! Native Tool Calling toggle is now available.");
    }
  };

  const handleExampleClick = async (text: string, isDeepResearch: boolean, fileUrl?: string) => {
    // Check if connection is ready
    if (!isSocketConnected || !isSocketReady) {
      // Trigger shake animation
      setShouldShakeConnectionIndicator(true);
      setTimeout(() => setShouldShakeConnectionIndicator(false), 1000); // Stop shaking after 1 second
      
      // Show a toast message
      toast.info("Please wait while we establish a connection to the server...");
      return;
    }
    
    // Set the question text
    setCurrentQuestion(text);
    
    // Set deep research if needed
    if (isDeepResearch) {
      setIsUseDeepResearch(true);
    }
    
    // Handle file download and upload if fileUrl is provided
    if (fileUrl) {
      try {
        setIsUploading(true);
        
        // Download the file
        const response = await fetch(fileUrl);
        if (!response.ok) {
          throw new Error(`Failed to download file: ${response.statusText}`);
        }
        
        const blob = await response.blob();
        const fileName = fileUrl.split('/').pop() || 'downloaded_file.pdf';
        
        // Create a File object
        const file = new File([blob], fileName, { type: blob.type });
        
        // Create a fake file input event
        const dataTransfer = new DataTransfer();
        dataTransfer.items.add(file);
        
        const fakeEvent = {
          target: {
            files: dataTransfer.files,
            value: ""
          }
        } as unknown as React.ChangeEvent<HTMLInputElement>;
        
        // Upload the file
        await handleFileUpload(fakeEvent);
        
        setIsUploading(false);
      } catch (error) {
        console.error("Error downloading/uploading file:", error);
        toast.error("Failed to download and attach file");
        setIsUploading(false);
      }
    }
    
    // Submit the question
    setTimeout(() => {
      handleQuestionSubmit(text);
    }, fileUrl ? 1000 : 0); // Wait a bit if we're uploading a file
  };

  // Enhanced error handling function
  const handleWebSocketError = useCallback((error: Event | Error | unknown, context: string) => {
    console.error(`WEBSOCKET_DEBUG: WebSocket ${context}:`, error);
    
    // Log detailed information for debugging
    console.group(`🔍 WEBSOCKET_DEBUG Error Details - ${context}`);
    console.log('WEBSOCKET_DEBUG Error object:', error);
    console.log('WEBSOCKET_DEBUG Socket state:', socket?.readyState);
    console.log('WEBSOCKET_DEBUG Is connected:', isSocketConnected);
    console.log('WEBSOCKET_DEBUG Is ready:', isSocketReady);
    console.log('WEBSOCKET_DEBUG Retry attempt:', retryAttempt);
    console.log('WEBSOCKET_DEBUG Message queue length:', messageQueue.length);
    console.log('WEBSOCKET_DEBUG Active connections on server:', 'unknown'); // Will be provided by server
    console.log('WEBSOCKET_DEBUG Current model:', selectedModel);
    console.log('WEBSOCKET_DEBUG Device ID:', deviceId);
    console.log('WEBSOCKET_DEBUG Is loading:', isLoading);
    console.log('WEBSOCKET_DEBUG Messages count:', messages.length);
    console.groupEnd();
    
    // Determine user-friendly message based on context
    let userMessage = "";
    let shouldReload = false;
    
    if (context === "connection_error") {
      userMessage = "Connection failed. This might be due to high server load with many users. Please refresh the page and try again.";
      shouldReload = true;
    } else if (context === "connection_closed") {
      if (isLoading && messages.length > 0) {
        userMessage = "Sorry, a new version was just released. This caused the current run to be interrupted. We're working extremely hard on this software. Sorry and thank you for your understanding!";
      } else {
        userMessage = "Connection lost. This might be due to high server load. Please refresh the page and try again.";
        shouldReload = true;
        // Auto-reload after 2 seconds when returning from chat
        if (sessionId && !isLoadingSession) {
          setTimeout(() => {
            window.location.reload();
          }, 2000);
        }
      }
    } else {
      userMessage = "Connection issue detected. Please refresh the page and try again.";
      shouldReload = true;
    }
    
    // Show user-friendly toast
    toast.error(userMessage);
    
    // Optionally suggest reload
    if (shouldReload && !isLoading) {
      setTimeout(() => {
        toast.info("💡 Tip: Refreshing the page often helps with connection issues", {
          duration: 5000,
        });
      }, 2000);
    }
  }, [socket, isSocketConnected, isSocketReady, retryAttempt, messageQueue, selectedModel, deviceId, isLoading, messages, sessionId, isLoadingSession]);

  // NEW: Function to process message queue
  const processMessageQueue = useCallback(() => {
    console.log(`WEBSOCKET_DEBUG: Processing ${messageQueue.length} queued messages`);
    if (socket && isSocketConnected && isSocketReady && messageQueue.length > 0) {
      messageQueue.forEach((message, index) => {
        console.log(`WEBSOCKET_DEBUG: Sending queued message ${index + 1}:`, message);
        socket.send(JSON.stringify(message));
      });
      setMessageQueue([]);
    }
  }, [socket, isSocketConnected, isSocketReady, messageQueue]);

  // NEW: Function to send message with retry logic
  const sendMessageWithRetry = useCallback(async (message: WebSocketMessage, maxRetries: number = 3): Promise<boolean> => {
    console.log(`WEBSOCKET_DEBUG: Attempting to send message (attempt ${retryAttempt + 1}/${maxRetries + 1}):`, message);
    
    // Check if socket is ready for connection
    if (!socket || !isSocketConnected || socket.readyState !== WebSocket.OPEN) {
      console.warn(`WEBSOCKET_DEBUG: Socket not ready, queuing message`);
      setMessageQueue(prev => [...prev, message]);
      return false;
    }

    // If not server-ready, wait and retry with exponential backoff
    if (!isSocketReady) {
      console.log(`WEBSOCKET_DEBUG: Server not ready, waiting before retry (attempt ${retryAttempt + 1}/${maxRetries + 1})`);
      if (retryAttempt < maxRetries) {
        setRetryAttempt(prev => prev + 1);
        // Exponential backoff: 500ms, 1s, 2s
        const delay = Math.min(500 * Math.pow(2, retryAttempt), 2000);
        await new Promise(resolve => setTimeout(resolve, delay));
        return sendMessageWithRetry(message, maxRetries);
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
        // Exponential backoff for send errors: 1s, 2s, 4s
        const delay = Math.min(1000 * Math.pow(2, retryAttempt), 4000);
        await new Promise(resolve => setTimeout(resolve, delay));
        return sendMessageWithRetry(message, maxRetries);
      } else {
        console.error(`WEBSOCKET_DEBUG: Max retries reached for sending, message failed`);
        setRetryAttempt(0);
        return false;
      }
    }
  }, [socket, isSocketConnected, isSocketReady, retryAttempt]); // Removed messageQueue from dependencies

  const handleQuestionSubmit = async (newQuestion: string) => {
    if (!newQuestion.trim() || isLoading) return;

    // Check for user consent before proceeding
    if (!hasUserConsented()) {
      setPendingQuestion(newQuestion);
      setShowConsentDialog(true);
      return;
    }

    setIsLoading(true);
    setCurrentQuestion("");
    setIsCompleted(false);
    setShowUpgradePrompt(null); // Reset upgrade prompt

    if (!sessionId) {
      const id = `${workspaceInfo}`.split("/").pop();
      if (id) {
        setSessionId(id);
      }
    }

    const newUserMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: newQuestion,
      timestamp: Date.now(),
    };

    setMessages((prev) => [...prev, newUserMessage]);

    // Store the user prompt for the first message
    if (messages.length === 0) {
      setUserPrompt(newQuestion);
      // Don't generate task summary immediately - wait for first LLM response
    }

    // Enhanced WebSocket connection check with detailed error handling
    if (!socket || !isSocketConnected || !isSocketReady || socket.readyState !== WebSocket.OPEN) {
      console.error("🚫 WebSocket not ready for sending message");
      console.group("🔍 WebSocket State Details");
      console.log("Socket exists:", !!socket);
      console.log("Is connected flag:", isSocketConnected);
      console.log("Is server ready flag:", isSocketReady);
      console.log("Socket ready state:", socket?.readyState);
      console.log("WebSocket.OPEN constant:", WebSocket.OPEN);
      console.log("Ready state meanings:", {
        0: "CONNECTING",
        1: "OPEN", 
        2: "CLOSING",
        3: "CLOSED"
      });
      console.groupEnd();
      
      // More specific error messages based on the state
      let errorMessage = "Connection not ready. ";
      if (!socket) {
        errorMessage += "WebSocket not initialized. ";
      } else if (!isSocketConnected) {
        errorMessage += "WebSocket not connected. ";
      } else if (!isSocketReady) {
        errorMessage += "Server not ready yet. ";
      } else if (socket.readyState !== WebSocket.OPEN) {
        errorMessage += `WebSocket in ${socket.readyState === 0 ? 'CONNECTING' : socket.readyState === 2 ? 'CLOSING' : 'CLOSED'} state. `;
      }
      errorMessage += "Please wait a moment and try again.";
      
      toast.error(errorMessage);
      
      // Additional helpful tip for specific states
      if (!isSocketReady && isSocketConnected) {
        setTimeout(() => {
          toast.info("💡 The connection is established but the server is still initializing. This usually takes just a few seconds.", {
            duration: 4000,
          });
        }, 1000);
      } else {
        setTimeout(() => {
          toast.info("💡 If the problem persists, try refreshing the page.", {
            duration: 6000,
          });
        }, 2000);
      }
      
      setIsLoading(false);
      return;
    }

    try {
      // Always send init agent event for new queries (even in loaded sessions)
      // This ensures the agent is properly initialized for the current connection
      await sendMessageWithRetry({
        type: "init_agent",
        content: {
          tool_args: {
            deep_research: isUseDeepResearch,
            pdf: true,
            media_generation: true,
            audio_generation: true,
            browser: true,
          },
        },
      });

      // Send the query using the existing socket connection
      await sendMessageWithRetry({
        type: "query",
        content: {
          text: newQuestion,
          resume: messages.length > 0,
          files: uploadedFiles?.map((file) => file.startsWith('/') ? file.substring(1) : file),
        },
      });
    } catch (error) {
      console.error("Error sending message:", error);
      toast.error("Failed to send message. Please refresh the page and try again.");
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleQuestionSubmit((e.target as HTMLTextAreaElement).value);
    }
  };

  const resetChat = () => {
    if (socket) {
      socket.close();
    }
    
    // Clear timeout check if active
    if (timeoutCheckInterval) {
      clearInterval(timeoutCheckInterval);
      setTimeoutCheckInterval(null);
    }
    
    setSessionId(null);
    router.push("/");
    setMessages([]);
    setIsLoading(false);
    setIsCompleted(false);
    setCurrentQuestion(""); // Reset the current question
    setUploadedFiles([]); // Reset uploaded files
    setFilesContent({}); // Reset files content
    setActiveTab(TAB.BROWSER); // Reset active tab
    setCurrentActionData(undefined); // Reset current action data
    setTaskSummary(""); // Reset task summary
    setUserPrompt(""); // Reset user prompt
    setShowUpgradePrompt(null); // Reset upgrade prompt
    setReturnedFromChat(true); // Mark that we returned from chat
  };

  const parseJson = (jsonString: string) => {
    try {
      return JSON.parse(jsonString);
    } catch {
      return null;
    }
  };

  const handleFileUpload = async (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    if (!event.target.files || event.target.files.length === 0) return;

    const files = Array.from(event.target.files);

    // Create a map to track upload status for each file
    const fileStatusMap: { [filename: string]: boolean } = {};
    files.forEach((file) => {
      fileStatusMap[file.name] = false; // false = not uploaded yet
    });

    setIsUploading(true);

    // Create a map of filename to content for message history
    const fileContentMap: { [filename: string]: string } = {};

    // Get the connection ID from the workspace path
    const workspaceId = workspaceInfo.split("/").pop();
    const connectionId = workspaceId;

    // Add files to message history (initially without content)
    const newUserMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      files: files.map((file) => file.name),
      fileContents: fileContentMap,
      timestamp: Date.now(),
    };

    setMessages((prev) => [...prev, newUserMessage]);

    // Process each file in parallel
    const uploadPromises = files.map(async (file) => {
      return new Promise<{ name: string; success: boolean }>(
        async (resolve) => {
          try {
            const reader = new FileReader();

            reader.onload = async (e) => {
              const content = e.target?.result as string;
              fileContentMap[file.name] = content;

              // Upload the file
              const response = await fetch(
                `${process.env.NEXT_PUBLIC_API_URL}/api/upload`,
                {
                  method: "POST",
                  headers: {
                    "Content-Type": "application/json",
                  },
                  body: JSON.stringify({
                    session_id: connectionId,
                    file: {
                      path: file.name,
                      content,
                    },
                  }),
                }
              );

              const result = await response.json();

              if (response.ok) {
                // Update uploaded files state
                setUploadedFiles((prev) => [...prev, result.file.path]);
                resolve({ name: file.name, success: true });
              } else {
                console.error(`Error uploading ${file.name}:`, result.error);
                resolve({ name: file.name, success: false });
              }
            };

            reader.onerror = () => {
              resolve({ name: file.name, success: false });
            };

            // Read as data URL
            reader.readAsDataURL(file);
          } catch (error) {
            console.error(`Error processing ${file.name}:`, error);
            resolve({ name: file.name, success: false });
          }
        }
      );
    });

    try {
      // Wait for all uploads to complete
      const results = await Promise.all(uploadPromises);

      // Check if any uploads failed
      const failedUploads = results.filter((r) => !r.success);
      if (failedUploads.length > 0) {
        toast.error(`Failed to upload ${failedUploads.length} file(s)`);
      }

      // Update message with final content
      setMessages((prev) => {
        const updatedMessages = [...prev];
        const messageIndex = updatedMessages.findIndex(
          (m) => m.id === newUserMessage.id
        );
        if (messageIndex >= 0) {
          updatedMessages[messageIndex] = {
            ...updatedMessages[messageIndex],
            fileContents: fileContentMap,
          };
        }
        return updatedMessages;
      });
    } catch (error) {
      console.error("Error uploading files:", error);
      toast.error("Error uploading files");
    } finally {
      setIsUploading(false);
      // Clear the input
      event.target.value = "";
    }
  };

  const getRemoteURL = (path: string | undefined) => {
    const workspaceId = workspaceInfo.split("/").pop();
    return `${process.env.NEXT_PUBLIC_API_URL}/workspace/${workspaceId}/${path}`;
  };

  const handleEvent = (data: {
    id: string;
    type: AgentEvent;
    content: Record<string, unknown>;
  }) => {
    switch (data.type) {
      case AgentEvent.CONNECTION_ESTABLISHED:
        console.log("Connection established:", data.content.message);
        break;

      case AgentEvent.USER_MESSAGE:
        setMessages((prev) => [
          ...prev,
          {
            id: data.id,
            role: "user",
            content: data.content.text as string,
            timestamp: Date.now(),
          },
        ]);

        break;
      case AgentEvent.PROCESSING:
        setIsLoading(true);
        setIsCompleted(false);
        
        // Start tracking agent run time for timeout detection
        const startTime = Date.now();
        
        // Start checking for timeout (> 1 minute)
        const interval = setInterval(() => {
          if (Date.now() - startTime > 60000) {
            // Check if using free model (not Sonnet 4)
            if (selectedModel.id !== "claude-sonnet-4-20250514" && !hasProAccess()) {
              setShowUpgradePrompt("timeout");
            }
            clearInterval(interval);
          }
        }, 5000); // Check every 5 seconds
        
        setTimeoutCheckInterval(interval);
        break;
      case AgentEvent.WORKSPACE_INFO:
        setWorkspaceInfo(data.content.path as string);
        break;
      case AgentEvent.AGENT_THINKING:
        setMessages((prev) => [
          ...prev,
          {
            id: data.id,
            role: "assistant",
            content: data.content.text as string,
            timestamp: Date.now(),
          },
        ]);
        break;

      case AgentEvent.TOOL_CALL:
        if (data.content.tool_name === TOOL.SEQUENTIAL_THINKING) {
          setMessages((prev) => [
            ...prev,
            {
              id: data.id,
              role: "assistant",
              content: (data.content.tool_input as { thought: string })
                .thought as string,
              timestamp: Date.now(),
            },
          ]);
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
          const url = (data.content.tool_input as { url: string })
            ?.url as string;
          if (url) {
            setBrowserUrl(url);
          }
          setMessages((prev) => [...prev, message]);
          handleClickAction(message.action);
        }
        break;

      case AgentEvent.FILE_EDIT:
        setMessages((prev) => {
          const lastMessage = cloneDeep(prev[prev.length - 1]);
          if (
            lastMessage.action &&
            lastMessage.action.type === TOOL.STR_REPLACE_EDITOR
          ) {
            lastMessage.action.data.content = data.content.content as string;
            lastMessage.action.data.path = data.content.path as string;
            const filePath = (data.content.path as string)?.includes(
              workspaceInfo
            )
              ? (data.content.path as string)
              : `${workspaceInfo}/${data.content.path}`;

            setFilesContent((prev) => {
              return {
                ...prev,
                [filePath]: data.content.content as string,
              };
            });
          }
          setTimeout(() => {
            handleClickAction(lastMessage.action);
          }, 500);
          return [...prev.slice(0, -1), lastMessage];
        });
        break;

      case AgentEvent.BROWSER_USE:
        // const message: Message = {
        //   id: data.id,
        //   role: "assistant",
        //   action: {
        //     type: data.type as unknown as TOOL,
        //     data: {
        //       result: data.content.screenshot as string,
        //       tool_input: {
        //         url: data.content.url as string,
        //       },
        //     },
        //   },
        //   timestamp: Date.now(),
        // };
        // setMessages((prev) => [...prev, message]);
        // handleClickAction(message.action);
        break;

      case AgentEvent.TOOL_RESULT:
        if (data.content.tool_name === TOOL.BROWSER_USE) {
          setMessages((prev) => [
            ...prev,
            {
              id: data.id,
              role: "assistant",
              content: data.content.result as string,
              timestamp: Date.now(),
            },
          ]);
        } else {
          if (
            data.content.tool_name !== TOOL.SEQUENTIAL_THINKING &&
            data.content.tool_name !== TOOL.PRESENTATION
          ) {
            // Handle static deploy result to extract URL
            if (data.content.tool_name === TOOL.STATIC_DEPLOY) {
              const result = data.content.result as string;
              if (result && result.startsWith('http')) {
                setDeployedUrl(result);
                setActiveTab(TAB.WEBSITE);
              }
            }
            
            // TODO: Implement helper function to handle tool results
            setMessages((prev) => {
              const lastMessage = cloneDeep(prev[prev.length - 1]);
              if (
                lastMessage?.action &&
                lastMessage.action?.type === data.content.tool_name
              ) {
                lastMessage.action.data.result = `${data.content.result}`;
                if (
                  [
                    TOOL.BROWSER_VIEW,
                    TOOL.BROWSER_CLICK,
                    TOOL.BROWSER_ENTER_TEXT,
                    TOOL.BROWSER_PRESS_KEY,
                    TOOL.BROWSER_GET_SELECT_OPTIONS,
                    TOOL.BROWSER_SELECT_DROPDOWN_OPTION,
                    TOOL.BROWSER_SWITCH_TAB,
                    TOOL.BROWSER_OPEN_NEW_TAB,
                    TOOL.BROWSER_WAIT,
                    TOOL.BROWSER_SCROLL_DOWN,
                    TOOL.BROWSER_SCROLL_UP,
                    TOOL.BROWSER_NAVIGATION,
                    TOOL.BROWSER_RESTART,
                  ].includes(data.content.tool_name as TOOL)
                ) {
                  lastMessage.action.data.result =
                    data.content.result && Array.isArray(data.content.result)
                      ? data.content.result.find(
                          (item) => item.type === "image"
                        )?.source?.data
                      : undefined;
                }
                lastMessage.action.data.isResult = true;
                setTimeout(() => {
                  handleClickAction(lastMessage.action);
                }, 500);
                return [...prev.slice(0, -1), lastMessage];
              } else {
                return [
                  ...prev,
                  { ...lastMessage, action: data.content as ActionStep },
                ];
              }
            });
          }
        }

        break;

      case AgentEvent.AGENT_RESPONSE:
        setMessages((prev) => [
          ...prev,
          {
            id: Date.now().toString(),
            role: "assistant",
            content: data.content.text as string,
            timestamp: Date.now(),
          },
        ]);
        setIsCompleted(true);
        setIsLoading(false);
        
        // Clear timeout check
        if (timeoutCheckInterval) {
          clearInterval(timeoutCheckInterval);
          setTimeoutCheckInterval(null);
        }
        
        // Check if we should show upgrade prompt for successful completion
        if (selectedModel.id !== "claude-sonnet-4-20250514" && !hasProAccess()) {
          setShowUpgradePrompt("success");
        }
        
        // Generate task summary when LLM responds for the first time
        if (userPrompt && !taskSummary) {
          generateTaskSummary(userPrompt);
        }
        break;

      case AgentEvent.UPLOAD_SUCCESS:
        setIsUploading(false);

        // Update the uploaded files state
        const newFiles = data.content.files as {
          path: string;
          saved_path: string;
        }[];
        const paths = newFiles.map((f) => f.path);
        setUploadedFiles((prev) => [...prev, ...paths]);

        break;

      case "error":
        const errorMessage = data.content.message as string;
        const errorCode = data.content.error_code as string;
        const userFriendlyMessage = data.content.user_friendly as string;
        
        // Clear timeout check
        if (timeoutCheckInterval) {
          clearInterval(timeoutCheckInterval);
          setTimeoutCheckInterval(null);
        }
        
        // Log detailed error information for debugging
        console.group("🚨 Server Error Details");
        console.log("Error message:", errorMessage);
        console.log("Error code:", errorCode);
        console.log("User friendly message:", userFriendlyMessage);
        console.log("Current state:", { isLoading, messagesLength: messages.length });
        console.groupEnd();
        
        // Use user-friendly message if available, otherwise fall back to technical message
        const displayMessage = userFriendlyMessage || errorMessage;
        
        // Check if this might be a deployment-related error
        if (errorMessage.includes("Error running agent") && isLoading && messages.length > 0) {
          toast.error("Sorry, a new version was just released. This caused the current run to be interrupted. We're working extremely hard on this software. Sorry and thank you for your understanding!");
        } else {
          toast.error(displayMessage);
          
          // Show upgrade prompt for errors if using free model
          if (selectedModel.id !== "claude-sonnet-4-20250514" && !hasProAccess() && isLoading) {
            setShowUpgradePrompt("error");
          }
        }
        
        setIsUploading(false);
        setIsLoading(false);
        break;
    }
  };

  const isInChatView = useMemo(
    () => !!sessionId && !isLoadingSession,
    [isLoadingSession, sessionId]
  );

  const handleShare = () => {
    console.log("SHARE_DEBUG: handleShare invoked");
    // Try all possible sources for sessionId
    let idSource = "";
    let idToUse: string | null = null;

    // 1. Try state
    if (sessionId) {
      idToUse = sessionId;
      idSource = "state";
    }
    // 2. Try URL param
    if (!idToUse) {
      const urlId = searchParams.get('id');
      if (urlId) {
        idToUse = urlId;
        idSource = "url_param";
      }
    }
    // 3. Try workspaceInfo (last segment after /)
    if (!idToUse && workspaceInfo) {
      const wsId = workspaceInfo.split("/").pop();
      if (wsId) {
        idToUse = wsId;
        idSource = "workspaceInfo";
      }
    }
    // Log all sources and which was used
    console.log("SHARE_DEBUG: sessionId state:", sessionId);
    console.log("SHARE_DEBUG: URL param id:", searchParams.get('id'));
    console.log("SHARE_DEBUG: workspaceInfo:", workspaceInfo);
    console.log("SHARE_DEBUG: Using id '", idToUse, "' from ", idSource);

    if (!idToUse) {
      toast.error("Keine Session aktiv – bitte erst eine Session starten!");
      console.error("SHARE_DEBUG: No sessionId found in any source");
      return;
    }
    const url = `${window.location.origin}/?id=${idToUse}`;
    console.log("SHARE_DEBUG: Copying URL to clipboard:", url);
    navigator.clipboard.writeText(url)
      .then(() => {
        console.log("SHARE_DEBUG: URL copied to clipboard successfully");
        toast.success("Link zur Session kopiert!");
      })
      .catch((err) => {
        console.error("SHARE_DEBUG: Failed to copy URL to clipboard", err);
        toast.error("Fehler beim Kopieren des Links");
      });
  };




  const connectWebSocket = () => {
    console.log("WEBSOCKET_DEBUG: Starting WebSocket connection process");
    
    // Connect to WebSocket when the component mounts
    let wsUrl = `${process.env.NEXT_PUBLIC_API_URL}/ws`.replace("http://", "ws://").replace("https://", "wss://");

    // Append device ID if available
    if (deviceId) {
      wsUrl += `?device_id=${deviceId}`;

      // Use the selected model from ModelPicker
      const modelToUse = selectedModel;
      
      // Determine which provider to use based on the model
      if (modelToUse.provider === 'anthropic') {
        // For Anthropic models, don't send use_chutes parameter (defaults to anthropic-direct)
        wsUrl += `&model_id=${encodeURIComponent(modelToUse.id)}`;
      } else if (modelToUse.provider === 'openrouter') {
        wsUrl += `&use_openrouter=true&model_id=${encodeURIComponent(modelToUse.id)}`;
      } else {
        // Default to Chutes
        wsUrl += `&use_chutes=true&model_id=${encodeURIComponent(modelToUse.id)}`;
      }
      
      // Add native tool calling parameter if enabled
      if (useNativeToolCalling) {
        wsUrl += `&use_native_tool_calling=true`;
      }
      
      // Add Pro key parameter if available (from URL or local storage)
      const proKey = getProKey();
      if (proKey) {
        wsUrl += `&pro_user_key=${encodeURIComponent(proKey)}`;
      }
      
      // Log model selection for debugging
      console.log(`WEBSOCKET_DEBUG: Using model: ${modelToUse.name} (${modelToUse.id}) - Provider: ${modelToUse.provider} - Native tool calling: ${useNativeToolCalling} - Pro key: ${proKey ? 'Yes' : 'No'}`);
    }

    console.log(`WEBSOCKET_DEBUG: Connecting to: ${wsUrl}`);
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log("WEBSOCKET_DEBUG: ✅ WebSocket connection established - waiting for server ready signal");
      setIsSocketConnected(true);
      setIsSocketReady(false); // Wait for server confirmation
      
      // Request workspace info immediately after connection
      console.log("WEBSOCKET_DEBUG: Sending workspace_info request");
      try {
        ws.send(
          JSON.stringify({
            type: "workspace_info",
            content: {},
          })
        );
      } catch (error) {
        console.error("WEBSOCKET_DEBUG: Error sending workspace_info:", error);
      }
    };

    ws.onmessage = (event) => {
      console.log("WEBSOCKET_DEBUG: Received message:", event.data);
      try {
        const data = JSON.parse(event.data);
        
        // Check for server ready signals
        if (data.type === "connection_established" || data.type === "workspace_info") {
          console.log("WEBSOCKET_DEBUG: Server ready signal received, setting isSocketReady=true");
          setIsSocketReady(true);
          
          // Process any queued messages
          setTimeout(() => {
            processMessageQueue();
          }, 100); // Small delay to ensure state is updated
        }
        
        handleEvent({ ...data, id: Date.now().toString() });
      } catch (error) {
        console.error("WEBSOCKET_DEBUG: Error parsing WebSocket data:", error);
        handleWebSocketError(error, "message_parsing");
      }
    };

    ws.onerror = (error) => {
      console.error("WEBSOCKET_DEBUG: ❌ WebSocket error event:", error);
      handleWebSocketError(error, "connection_error");
      setIsSocketConnected(false);
      setIsSocketReady(false);
    };

    ws.onclose = (event) => {
      console.log("WEBSOCKET_DEBUG: 🔌 WebSocket connection closed", event);
      console.group("🔍 WEBSOCKET_DEBUG Close Event Details");
      console.log("WEBSOCKET_DEBUG Close code:", event.code);
      console.log("WEBSOCKET_DEBUG Close reason:", event.reason);
      console.log("WEBSOCKET_DEBUG Was clean:", event.wasClean);
      console.log("WEBSOCKET_DEBUG Close code meanings:", {
        1000: "Normal closure",
        1001: "Going away",
        1006: "Abnormal closure",
        1013: "Service overloaded"
      });
      console.groupEnd();
      
      handleWebSocketError(event, "connection_closed");
      setSocket(null);
      setIsSocketConnected(false);
      setIsSocketReady(false);
      setMessageQueue([]); // Clear message queue on disconnect
    };

    setSocket(ws);
  };

  // Show reload button if connection is not ready after returning from chat
  useEffect(() => {
    let timer: NodeJS.Timeout | null = null;
    
    if (returnedFromChat && !isSocketReady && !isInChatView) {
      // Start a timer to show the reload button after 5 seconds
      timer = setTimeout(() => {
        if (!isSocketReady && !isInChatView) {
          setShowReloadButton(true);
        }
      }, 5000);
    }
    
    // Hide reload button when connection is established
    if (isSocketReady) {
      setShowReloadButton(false);
      if (returnedFromChat) {
        setReturnedFromChat(false);
      }
    }
    
    // Cleanup timer
    return () => {
      if (timer) {
        clearTimeout(timer);
      }
    };
  }, [returnedFromChat, isSocketReady, isInChatView]);

  // Only connect if we have a device ID AND we're not viewing a session history
  useEffect(() => {
    if (deviceId && !isReplayMode) {
      connectWebSocket();
    }

    // Clean up the WebSocket connection when the component unmounts
    return () => {
      if (socket) {
        socket.close();
      }
      
      // Clear timeout check if active
      if (timeoutCheckInterval) {
        clearInterval(timeoutCheckInterval);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [deviceId, isReplayMode, selectedModel, useNativeToolCalling]);

  useEffect(() => {
    if (socket && isSocketConnected) {
      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === AgentEvent.CONNECTION_ESTABLISHED) {
            setIsSocketReady(true);
            processMessageQueue();
          } else {
            handleEvent({ ...data, id: Date.now().toString() });
          }
        } catch (error) {
          console.error("Error parsing WebSocket data:", error);
          handleWebSocketError(error, "message_parsing");
        }
      };
    }
  }, [socket, isSocketConnected, handleWebSocketError, processMessageQueue]); // eslint-disable-line react-hooks/exhaustive-deps

  const isBrowserTool = useMemo(
    () =>
      [
        TOOL.BROWSER_VIEW,
        TOOL.BROWSER_CLICK,
        TOOL.BROWSER_ENTER_TEXT,
        TOOL.BROWSER_PRESS_KEY,
        TOOL.BROWSER_GET_SELECT_OPTIONS,
        TOOL.BROWSER_SELECT_DROPDOWN_OPTION,
        TOOL.BROWSER_SWITCH_TAB,
        TOOL.BROWSER_OPEN_NEW_TAB,
        TOOL.BROWSER_WAIT,
        TOOL.BROWSER_SCROLL_DOWN,
        TOOL.BROWSER_SCROLL_UP,
        TOOL.BROWSER_NAVIGATION,
        TOOL.BROWSER_RESTART,
      ].includes(currentActionData?.type as TOOL),
    [currentActionData]
  );

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages?.length]);

  // Function to stop the current agent run
  const handleStopAgent = () => {
    if (!socket || !isSocketConnected || socket.readyState !== WebSocket.OPEN) {
      toast.error("WebSocket connection is not available.");
      return;
    }

    if (!isLoading) {
      toast.error("No active agent run to stop.");
      return;
    }

    // Send cancel message to backend
    socket.send(
      JSON.stringify({
        type: "cancel",
        content: {},
      })
    );

    // Update UI state immediately
  
  if (returnedFromChat && !isSocketReady && !isInChatView) {
    // Start a timer to show the reload button after 5 seconds
    timer = setTimeout(() => {
      if (!isSocketReady && !isInChatView) {
        setShowReloadButton(true);
      }
    }, 5000);
  }
  
  // Hide reload button when connection is established
  if (isSocketReady) {
    setShowReloadButton(false);
    if (returnedFromChat) {
      setReturnedFromChat(false);
    }
  }
  
  // Cleanup timer
  return () => {
    if (timer) {
      clearTimeout(timer);
    }
  };
}, [returnedFromChat, isSocketReady, isInChatView]);

// Only connect if we have a device ID AND we're not viewing a session history
useEffect(() => {
  if (deviceId && !isReplayMode) {
    connectWebSocket();
  }

  // Clean up the WebSocket connection when the component unmounts
  return () => {
    if (socket) {
      socket.close();
    }
    
    // Clear timeout check if active
    if (timeoutCheckInterval) {
      clearInterval(timeoutCheckInterval);
    }
  };
  // eslint-disable-next-line react-hooks/exhaustive-deps
}, [deviceId, isReplayMode, selectedModel, useNativeToolCalling]);

useEffect(() => {
  if (socket && isSocketConnected) {
    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === AgentEvent.CONNECTION_ESTABLISHED) {
          setIsSocketReady(true);
          processMessageQueue();
        } else {
          handleEvent({ ...data, id: Date.now().toString() });
        }
      } catch (error) {
        console.error("Error parsing WebSocket data:", error);
        handleWebSocketError(error, "message_parsing");
      }
    };
  }
}, [socket, isSocketConnected, handleWebSocketError, processMessageQueue]); // eslint-disable-line react-hooks/exhaustive-deps

const isBrowserTool = useMemo(
  () =>
    [
      TOOL.BROWSER_VIEW,
      TOOL.BROWSER_CLICK,
      TOOL.BROWSER_ENTER_TEXT,
      TOOL.BROWSER_PRESS_KEY,
      TOOL.BROWSER_GET_SELECT_OPTIONS,
      TOOL.BROWSER_SELECT_DROPDOWN_OPTION,
      TOOL.BROWSER_SWITCH_TAB,
      TOOL.BROWSER_OPEN_NEW_TAB,
      TOOL.BROWSER_WAIT,
      TOOL.BROWSER_SCROLL_DOWN,
      TOOL.BROWSER_SCROLL_UP,
      TOOL.BROWSER_NAVIGATION,
      TOOL.BROWSER_RESTART,
    ].includes(currentActionData?.type as TOOL),
  [currentActionData]
);

useEffect(() => {
  messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
}, [messages?.length]);

// Function to stop the current agent run
const handleStopAgent = () => {
  if (!socket || !isSocketConnected || socket.readyState !== WebSocket.OPEN) {
    toast.error("WebSocket connection is not available.");
    return;
  }

  if (!isLoading) {
    toast.error("No active agent run to stop.");
    return;
  }

  // Send cancel message to backend
  socket.send(
    JSON.stringify({
      type: "cancel",
      content: {},
    })
  );

  // Update UI state immediately
  setIsLoading(false);
  toast.success("Agent run stopped");
};

const handleConsentAccept = () => {
  try {
    setUserConsent();
    setShowConsentDialog(false);
    // Proceed with the pending question
    if (pendingQuestion) {
      handleQuestionSubmit(pendingQuestion);
    }
  } catch (error) {
    console.error("Error in handleConsentAccept:", error);
  }
};

const handleConsentCancel = () => {
  setShowConsentDialog(false);
  setPendingQuestion("");
};

return (
  <>
    {/* Loading and reload overlays */}
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
    >
      <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="w-4 h-4 animate-spin" />
        <span>
          {!isSocketConnected ? "Connecting to server..." : "Initializing server..."}
        </span>
      </div>
      {showReloadButton && (
        <div className="mt-3 flex flex-col items-center gap-2">
          <Button
            onClick={() => window.location.reload()}
            variant="outline"
            size="sm"
            className="bg-glass border-white/20 hover:bg-white/10 transition-all-smooth hover-lift"
          >
            <RefreshCw className="w-3 h-3 mr-2" />
            Reload
          </Button>
          <p className="text-xs text-muted-foreground text-center max-w-xs">
            Connection is taking longer than expected. This might be due to high server load.
          </p>
        </div>
      )}
    </motion.div>
    <main className={"relative flex flex-col flex-1 w-full min-h-screen bg-gradient-to-b from-[#181d2a] via-[#181d2a] to-[#1a1a1f] overflow-x-hidden"}>
      {/* Header bar, model picker, etc. */}
      <motion.header 
        className="relative z-10 mobile-header-safe flex-shrink-0"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
      >
        <div className={`flex justify-between items-center w-full px-4 md:px-8 py-4${!isInChatView ? ' pb-0' : ''}`}>
          {!isInChatView && (
            <div className="flex-1" />
          )}
          <motion.div
            className={`flex items-center gap-3 ${
              isInChatView ? "text-xl md:text-2xl font-semibold flex-1 min-w-0" : "hidden"
            }`}
            layout
            layoutId="page-title"
          >
            {isInChatView && (
              <>
                <div className="flex flex-col sm:flex-row flex-wrap items-center justify-center gap-1 sm:gap-2">
                  <span>
                    fubea is{' '}
                    <a
                      href="https://github.com/fstandhartinger/ii-agent-chutes/tree/main"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-400 hover:text-blue-300 transition-colors hover-lift underline"
                    >
                      open source
                    </a>{' '}
                    and free
                  </span>
                  <span className="hidden sm:inline text-muted-foreground/60 mx-1">•</span>
                  <div className="flex items-center gap-1">
                    <span>based on the amazing</span>
                    <a 
                      href="https://github.com/Intelligent-Internet/ii-agent" 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="text-blue-400 hover:text-blue-300 transition-colors hover-lift underline"
                    >
                      ii-agent
                    </a>
                  </div>
                </div>
              </>
            )}
          </motion.div>
        </div>
      </motion.header>
      <footer className="w-full py-6 px-2 md:px-0 flex flex-col items-center">
        <div className="text-xs sm:text-sm text-muted-foreground">
          <div className="flex flex-col sm:flex-row flex-wrap items-center justify-center gap-1 sm:gap-2">
            <span>
              fubea is{' '}
              <a
                href="https://github.com/fstandhartinger/ii-agent-chutes/tree/main"
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-400 hover:text-blue-300 transition-colors hover-lift underline"
              >
                open source
              </a>{' '}
              and free
            </span>
            <span className="hidden sm:inline text-muted-foreground/60 mx-1">•</span>
            <div className="flex items-center gap-1">
              <span>based on the amazing</span>
              <a 
                href="https://github.com/Intelligent-Internet/ii-agent" 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-blue-400 hover:text-blue-300 transition-colors hover-lift underline"
              >
                ii-agent
              </a>
            </div>
          </div>
          {/* Legal Links */}
          <div className="flex items-center justify-center gap-2 mt-2 text-xs text-muted-foreground/80">
            <a 
              href="/privacy-policy" 
              className="hover:text-muted-foreground transition-colors underline"
            >
              Privacy Policy
            </a>
            <span>•</span>
            <a 
              href="/terms" 
              className="hover:text-muted-foreground transition-colors underline"
            >
              Terms of Service
            </a>
            <span>•</span>
            <a 
              href="/imprint" 
              className="hover:text-muted-foreground transition-colors underline"
            >
              Imprint
            </a>
          </div>
        </div>
      </footer>
    </main>
  </>
);
