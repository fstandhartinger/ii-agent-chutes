"use client";

import { Terminal as XTerm } from "@xterm/xterm";
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
} from "lucide-react";
import Image from "next/image";
import { useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { cloneDeep, debounce } from "lodash";
import dynamic from "next/dynamic";
import Cookies from "js-cookie";
import { v4 as uuidv4 } from "uuid";
import { useRouter, useSearchParams } from "next/navigation";
import SidebarButton from "@/components/sidebar-button";
import { useChutes } from "@/providers/chutes-provider";
import Examples from "@/components/examples";
import ModelPicker from "@/components/model-picker";

import Browser from "@/components/browser";
import CodeEditor from "@/components/code-editor";
import QuestionInput from "@/components/question-input";
import SearchBrowser from "@/components/search-browser";
const Terminal = dynamic(() => import("@/components/terminal"), {
  ssr: false,
});
import { Button } from "@/components/ui/button";
import {
  ActionStep,
  AgentEvent,
  IEvent,
  Message,
  TAB,
  TOOL,
} from "@/typings/agent";
import ChatMessage from "./chat-message";
import ImageBrowser from "./image-browser";
import WebsiteViewer from "./website-viewer";
import InstallPrompt from "./install-prompt";
import PWAHandler from "./pwa-handler";

export default function Home() {
  const xtermRef = useRef<XTerm | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const searchParams = useSearchParams();
  const router = useRouter();

  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [isSocketConnected, setIsSocketConnected] = useState(false);
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

  const isReplayMode = useMemo(() => !!searchParams.get("id"), [searchParams]);
  const { selectedModel } = useChutes();

  // Generate task summary using LLM
  const generateTaskSummary = async (firstUserMessage: string) => {
    try {
      const response = await fetch('/api/generate-summary', {
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
  }, [searchParams]);

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
                xtermRef.current?.writeln(
                  `${data.data.tool_input?.command || ""}`
                );
              }
              // result
              if (data.data.result) {
                const lines = `${data.data.result || ""}`.split("\n");
                lines.forEach((line) => {
                  xtermRef.current?.writeln(line);
                });
                xtermRef.current?.write("$ ");
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
      // Also unlock hidden models
      localStorage.setItem("hiddenModelsUnlocked", "true");
      toast.success("Hidden features unlocked! Native Tool Calling toggle and premium models are now available.");
      // Trigger a re-render of the model picker
      window.dispatchEvent(new Event('storage'));
    }
  };

  const handleExampleClick = async (text: string, isDeepResearch: boolean, fileUrl?: string) => {
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

  const handleQuestionSubmit = async (newQuestion: string) => {
    if (!newQuestion.trim() || isLoading) return;

    setIsLoading(true);
    setCurrentQuestion("");
    setIsCompleted(false);

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

    if (!socket || !isSocketConnected || socket.readyState !== WebSocket.OPEN) {
      toast.error("WebSocket connection is not open. Please try again.");
      setIsLoading(false);
      return;
    }

    // send init agent event when first query
    if (!sessionId) {
      socket.send(
        JSON.stringify({
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
        })
      );
    }

    // Send the query using the existing socket connection
    socket.send(
      JSON.stringify({
        type: "query",
        content: {
          text: newQuestion,
          resume: messages.length > 0,
          files: uploadedFiles?.map((file) => `.${file}`),
        },
      })
    );
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
    const workspacePath = workspaceInfo || "";
    const connectionId = workspacePath.split("/").pop();

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
        toast.error(data.content.message as string);
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
    if (!sessionId) return;
    const url = `${window.location.origin}/?id=${sessionId}`;
    navigator.clipboard.writeText(url);
    toast.success("Copied to clipboard");
  };

  const connectWebSocket = () => {
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
      
      // Log model selection for debugging
      console.log(`Using model: ${modelToUse.name} (${modelToUse.id}) - Provider: ${modelToUse.provider} - Native tool calling: ${useNativeToolCalling}`);
    }

    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log("WebSocket connection established");
      setIsSocketConnected(true);
      // Request workspace info immediately after connection
      ws.send(
        JSON.stringify({
          type: "workspace_info",
          content: {},
        })
      );
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        handleEvent({ ...data, id: Date.now().toString() });
      } catch (error) {
        console.error("Error parsing WebSocket data:", error);
      }
    };

    ws.onerror = (error) => {
      console.log("WebSocket error:", error);
      toast.error("WebSocket connection error");
      setIsSocketConnected(false);
    };

    ws.onclose = () => {
      console.log("WebSocket connection closed");
      setSocket(null);
      setIsSocketConnected(false);
    };

    setSocket(ws);
  };

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
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [deviceId, isReplayMode, selectedModel, useNativeToolCalling]);

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

  return (
    <div className="flex flex-col min-h-screen bg-background relative overflow-hidden">
      {/* PWA Handler */}
      <PWAHandler />
      
      {/* Background Elements */}
      <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 via-purple-500/5 to-emerald-500/5" />
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl animate-pulse" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl animate-pulse delay-1000" />
      
      {!isInChatView && <SidebarButton />}
      
      {/* Header */}
      <motion.header 
        className="relative z-10 mobile-header-safe"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
      >
        <div className={`flex justify-between items-center w-full px-4 md:px-8 py-4 ${!isInChatView ? 'pb-0' : ''}`}>
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
                <ArrowLeft 
                  className="w-6 h-6 text-white/80 hover:text-white cursor-pointer transition-colors flex-shrink-0" 
                  onClick={resetChat}
                />
                <div className="relative flex-shrink-0">
                  <Image
                    src="/logo-only.png"
                    alt="fubea Logo"
                    width={32}
                    height={32}
                    className="rounded-lg shadow-lg"
                  />
                  <div className="absolute inset-0 bg-gradient-to-r from-blue-500/20 to-purple-500/20 rounded-lg blur-sm" />
                </div>
                <span className="bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent truncate text-base md:text-xl min-w-0 flex-1">
                  {taskSummary || userPrompt || "fubea"}
                </span>
              </>
            )}
          </motion.div>
          
          {isInChatView ? (
            <div className="flex items-center gap-2 flex-shrink-0 ml-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleShare}
                className="bg-glass border-white/20 hover:bg-white/10 transition-all-smooth hover-lift"
                title="Share Session"
              >
                <Share className="w-4 h-4" />
                <span className="ml-2 hidden sm:inline">Share</span>
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
                className="md:hidden bg-glass border-white/20"
              >
                <Menu className="w-4 h-4" />
              </Button>
            </div>
          ) : (
            <div className="flex-1 flex justify-end items-center gap-4">
              {/* Native Tool Calling Toggle - Hidden until logo is clicked 5 times */}
              {showNativeToolToggle && (
                <div className="flex items-center gap-2 bg-glass border border-white/20 rounded-lg px-3 py-2">
                  <span className="text-sm text-white/80">Native Tool Calling</span>
                  <button
                    onClick={() => setUseNativeToolCalling(!useNativeToolCalling)}
                    className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
                      useNativeToolCalling ? 'bg-blue-500' : 'bg-gray-600'
                    }`}
                    title={useNativeToolCalling ? "Using native tool calling (Squad-style)" : "Using JSON workaround (default)"}
                  >
                    <span
                      className={`inline-block h-3 w-3 transform rounded-full bg-white transition-transform ${
                        useNativeToolCalling ? 'translate-x-5' : 'translate-x-1'
                      }`}
                    />
                  </button>
                </div>
              )}
              <ModelPicker />
            </div>
          )}
        </div>
        
        {/* Mobile Menu */}
        {isMobileMenuOpen && isInChatView && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="md:hidden bg-glass-dark border-t border-white/10 px-4 py-3"
          >
            <Button
              variant="outline"
              size="sm"
              onClick={handleShare}
              className="w-full bg-glass border-white/20 hover:bg-white/10 mb-2"
            >
              <Share className="w-4 h-4 mr-2" />
              Share Session
            </Button>
          </motion.div>
        )}
      </motion.header>

      {/* Main Content */}
      <main className="flex-1 relative z-10 flex flex-col min-h-0">
        {!isInChatView && (
          <div className="flex-1 flex flex-col">
            <motion.div
              className="flex flex-col items-center justify-center flex-1 px-4"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.8, delay: 0.2 }}
            >
              {/* Hero Section */}
              <div className="text-center mb-8 md:mb-12">
                <motion.div 
                  className="flex items-center justify-center mb-8 cursor-pointer group"
                  onClick={handleLogoClick}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  <div className="relative">
                    <Image
                      src="/logo-only.png"
                      alt="fubea Logo"
                      width={200}
                      height={144}
                      className="rounded-2xl shadow-2xl transition-all-smooth group-hover:shadow-glow"
                    />
                    <div className="absolute inset-0 bg-gradient-to-r from-blue-500/20 to-purple-500/20 rounded-2xl blur-xl group-hover:blur-2xl transition-all-smooth" />
                    <Sparkles className="absolute -top-2 -right-2 w-6 h-6 text-yellow-400 animate-pulse" />
                  </div>
                </motion.div>
                
                <motion.h1
                  className="text-3xl md:text-5xl lg:text-6xl font-bold mb-4 bg-gradient-to-r from-white via-blue-100 to-purple-100 bg-clip-text text-transparent"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.8, delay: 0.4 }}
                >
                  How can I help you today?
                </motion.h1>
                
                <motion.p
                  className="text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.8, delay: 0.6 }}
                >
                  <span 
                    className="cursor-pointer hover:text-blue-400 transition-colors underline decoration-dotted underline-offset-4"
                    onClick={() => router.push('/gaia')}
                    title="Run GAIA Benchmark"
                  >
                    Leading
                  </span> Deep Research Agent. For Free.
                </motion.p>
              </div>
            </motion.div>
            
            {/* Input and Examples Container - Bottom aligned */}
            <div className="mt-auto">
              <motion.div
                key="input-view"
                className="flex items-center justify-center px-4 pb-8"
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.6 }}
              >
                <QuestionInput
                  placeholder="Give fubea a task to work on..."
                  value={currentQuestion}
                  setValue={setCurrentQuestion}
                  handleKeyDown={handleKeyDown}
                  handleSubmit={handleQuestionSubmit}
                  handleFileUpload={handleFileUpload}
                  isUploading={isUploading}
                  isUseDeepResearch={isUseDeepResearch}
                  setIsUseDeepResearch={setIsUseDeepResearch}
                  isDisabled={!isSocketConnected}
                  isLoading={isLoading}
                  handleStopAgent={handleStopAgent}
                  className="w-full max-w-4xl"
                />
              </motion.div>
              
              {/* Examples Section */}
              <motion.div
                key="examples-view"
                className="flex items-center justify-center px-4 pb-8"
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ 
                  duration: 0.6, 
                  delay: 0.2,
                  exit: { duration: 0.1, delay: 0 } // Fast exit animation
                }}
              >
                <Examples
                  onExampleClick={handleExampleClick}
                  className="w-full max-w-4xl"
                />
              </motion.div>
            </div>
          </div>
        )}

        {isLoadingSession ? (
          <motion.div 
            className="flex flex-col items-center justify-center min-h-[50vh] px-4"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            <div className="bg-glass rounded-2xl p-8 text-center">
              <Loader2 className="h-12 w-12 text-blue-400 animate-spin mb-4 mx-auto" />
              <p className="text-lg font-medium mb-2">Loading session history...</p>
              <p className="text-muted-foreground">Please wait while we restore your conversation</p>
            </div>
          </motion.div>
        ) : (
          <LayoutGroup>
            <AnimatePresence mode="wait">
              {isInChatView && (
                <motion.div
                  key="chat-view"
                  initial={{ opacity: 0, y: 30 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ duration: 0.6 }}
                  className="w-full flex-1 flex flex-col md:grid md:grid-cols-10 gap-4 px-4 pb-4 mobile-safe-area mobile-chat-view"
                >
                  {/* Chat Messages Panel */}
                  <div className={`${isMobileDetailPaneOpen ? 'hidden' : 'flex'} md:flex md:order-1 md:col-span-4 flex-col flex-1 min-h-0`}>
                    <ChatMessage
                      messages={messages}
                      isLoading={isLoading}
                      isCompleted={isCompleted}
                      workspaceInfo={workspaceInfo}
                      handleClickAction={(action, isReplay) => {
                        handleClickAction(action, isReplay);
                        // On mobile, open detail pane when action is clicked
                        if (window.innerWidth < 768) {
                          setIsMobileDetailPaneOpen(true);
                        }
                      }}
                      isUploading={isUploading}
                      isUseDeepResearch={isUseDeepResearch}
                      isReplayMode={isReplayMode}
                      currentQuestion={currentQuestion}
                      messagesEndRef={messagesEndRef}
                      setCurrentQuestion={setCurrentQuestion}
                      handleKeyDown={handleKeyDown}
                      handleQuestionSubmit={handleQuestionSubmit}
                      handleFileUpload={handleFileUpload}
                      handleStopAgent={handleStopAgent}
                    />
                  </div>

                  {/* Tools Panel */}
                  <div className={`${!isMobileDetailPaneOpen ? 'hidden' : 'flex'} md:flex md:order-2 md:col-span-6 bg-glass-dark rounded-2xl border border-white/10 overflow-hidden flex-1 min-h-0 flex-col`}>
                    {/* Tab Navigation */}
                    <div className="flex items-center justify-between p-4 pt-6 border-b border-white/10 bg-black/20">
                      <div className="flex gap-2 overflow-x-auto pb-2">
                        {/* Mobile back button */}
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => setIsMobileDetailPaneOpen(false)}
                          className="md:hidden bg-glass border-white/20 hover:bg-white/10 transition-all-smooth hover-lift mr-2"
                        >
                          <ArrowLeft className="w-4 h-4" />
                        </Button>
                        
                        <Button
                          size="sm"
                          variant={activeTab === TAB.BROWSER ? "default" : "outline"}
                          onClick={() => setActiveTab(TAB.BROWSER)}
                          className={`transition-all-smooth hover-lift ${
                            activeTab === TAB.BROWSER
                              ? "bg-gradient-skyblue-lavender text-black shadow-glow"
                              : "bg-glass border-white/20 hover:bg-white/10"
                          }`}
                        >
                          <Globe className="w-4 h-4 mr-2" />
                          Browser
                        </Button>
                        <Button
                          size="sm"
                          variant={activeTab === TAB.CODE ? "default" : "outline"}
                          onClick={() => setActiveTab(TAB.CODE)}
                          className={`transition-all-smooth hover-lift ${
                            activeTab === TAB.CODE
                              ? "bg-gradient-skyblue-lavender text-black shadow-glow"
                              : "bg-glass border-white/20 hover:bg-white/10"
                          }`}
                        >
                          <Code className="w-4 h-4 mr-2" />
                          Files
                        </Button>
                        <Button
                          size="sm"
                          variant={activeTab === TAB.TERMINAL ? "default" : "outline"}
                          onClick={() => setActiveTab(TAB.TERMINAL)}
                          className={`transition-all-smooth hover-lift ${
                            activeTab === TAB.TERMINAL
                              ? "bg-gradient-skyblue-lavender text-black shadow-glow"
                              : "bg-glass border-white/20 hover:bg-white/10"
                          }`}
                        >
                          <TerminalIcon className="w-4 h-4 mr-2" />
                          Terminal
                        </Button>
                        {deployedUrl && (
                          <Button
                            size="sm"
                            variant={activeTab === TAB.WEBSITE ? "default" : "outline"}
                            onClick={() => setActiveTab(TAB.WEBSITE)}
                            className={`transition-all-smooth hover-lift ${
                              activeTab === TAB.WEBSITE
                                ? "bg-gradient-skyblue-lavender text-black shadow-glow"
                                : "bg-glass border-white/20 hover:bg-white/10"
                            }`}
                          >
                            <Globe className="w-4 h-4 mr-2" />
                            Website
                          </Button>
                        )}
                      </div>
                    </div>

                    {/* Tab Content */}
                    <div className="flex-1 overflow-hidden">
                      <Browser
                        className={`tab-content-enter ${
                          activeTab === TAB.BROWSER &&
                          (currentActionData?.type === TOOL.VISIT || isBrowserTool)
                            ? ""
                            : "hidden"
                        }`}
                        url={currentActionData?.data?.tool_input?.url || browserUrl}
                        screenshot={
                          isBrowserTool
                            ? (currentActionData?.data.result as string)
                            : undefined
                        }
                        raw={
                          currentActionData?.type === TOOL.VISIT
                            ? (currentActionData?.data?.result as string)
                            : undefined
                        }
                      />
                      <SearchBrowser
                        className={`tab-content-enter ${
                          activeTab === TAB.BROWSER &&
                          currentActionData?.type === TOOL.WEB_SEARCH
                            ? ""
                            : "hidden"
                        }`}
                        keyword={currentActionData?.data.tool_input?.query}
                        search_results={
                          currentActionData?.type === TOOL.WEB_SEARCH &&
                          currentActionData?.data?.result
                            ? parseJson(currentActionData?.data?.result as string)
                            : undefined
                        }
                      />
                      <ImageBrowser
                        className={`tab-content-enter ${
                          activeTab === TAB.BROWSER &&
                          currentActionData?.type === TOOL.IMAGE_GENERATE
                            ? ""
                            : "hidden"
                        }`}
                        url={currentActionData?.data.tool_input?.output_filename}
                        image={getRemoteURL(
                          currentActionData?.data.tool_input?.output_filename
                        )}
                      />
                      <CodeEditor
                        currentActionData={currentActionData}
                        activeTab={activeTab}
                        className={`tab-content-enter ${activeTab === TAB.CODE ? "" : "hidden"}`}
                        workspaceInfo={workspaceInfo}
                        activeFile={activeFileCodeEditor}
                        setActiveFile={setActiveFileCodeEditor}
                        filesContent={filesContent}
                        isReplayMode={isReplayMode}
                      />
                      <Terminal
                        ref={xtermRef}
                        className={`tab-content-enter ${activeTab === TAB.TERMINAL ? "" : "hidden"}`}
                      />
                      {deployedUrl && (
                        <WebsiteViewer
                          url={deployedUrl}
                          className={`tab-content-enter ${activeTab === TAB.WEBSITE ? "" : "hidden"}`}
                        />
                      )}
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </LayoutGroup>
        )}
      </main>

      {/* Footer */}
      {!isInChatView && (
        <motion.footer
          className="relative z-10 text-center py-6 mobile-safe-area"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8, delay: 1 }}
        >
          <div className="text-sm text-muted-foreground">
            <div className="flex flex-wrap items-center justify-center gap-1 md:gap-2">
              <span>fubea is</span>
              <a 
                href="https://github.com/fstandhartinger/ii-agent-chutes/tree/main" 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-blue-400 hover:text-blue-300 transition-colors hover-lift underline"
              >
                open source
              </a>
              <span>and free</span>
              <span className="text-muted-foreground/60 mx-1 md:mx-2">•</span>
              <span>based on the amazing</span>
              <a 
                href="https://github.com/Intelligent-Internet/ii-agent" 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-blue-400 hover:text-blue-300 transition-colors hover-lift underline"
              >
                ii-agent
              </a>
              <span className="text-muted-foreground/60 mx-1 md:mx-2">•</span>
              <span>powered by</span>
              <a 
                href="https://chutes.ai" 
                target="_blank" 
                rel="noopener noreferrer"
                className="hover:text-foreground transition-colors hover-lift inline-flex items-center gap-1"
              >
                <span className="bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent font-semibold">
                  Chutes
                </span>
              </a>
            </div>
          </div>
        </motion.footer>
      )}
      
      {/* Install Prompt */}
      <InstallPrompt />
    </div>
  );
}
