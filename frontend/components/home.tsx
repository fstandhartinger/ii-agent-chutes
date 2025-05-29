/* eslint-disable @typescript-eslint/no-unused-vars */
/* eslint-disable react-hooks/exhaustive-deps */
"use client";

import dynamic from "next/dynamic";
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
import { hasProAccess, getProKey } from "@/utils/pro-utils";

// Dynamic imports
const Browser = dynamic(() => import("@/components/browser"), { ssr: false });
const WebsiteViewer = dynamic(() => import("./website-viewer"), { ssr: false });
const TerminalComponent = dynamic(() => import("./terminal"), { ssr: false });
const CodeEditor = dynamic(() => import("@/components/code-editor"), { ssr: false });
const ChatMessage = dynamic(() => import("./chat-message"), { ssr: false });
const ImageBrowser = dynamic(() => import("./image-browser"), { ssr: false });

import type { TerminalRef } from "./terminal";
import Examples from "@/components/examples";
import ModelPicker from "@/components/model-picker";
import ProUpgradeButton from "@/components/pro-upgrade-button";
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
  WebSocketMessage,
} from "@/typings/agent";

import InstallPrompt from "./install-prompt";
import ConsentDialog, { hasUserConsented, setUserConsent } from "./consent-dialog";
import CookieBanner from "./cookie-banner";

// Import hooks
import { useUIState } from "@/components/home-parts/useUIState";
import { useChatState } from "@/components/home-parts/useChatState";
import { useWebSocketManager } from "@/components/home-parts/useWebSocketManager";
import { useEventHandler } from "@/components/home-parts/useEventHandler";
import { useSessionManager } from "@/components/home-parts/useSessionManager";
import { useHomeInteractionHandlers } from "@/components/home-parts/useHomeInteractionHandlers";
import { useActionHandler } from "@/components/home-parts/useActionHandler";

export default function Home() {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const searchParams = useSearchParams();
  const router = useRouter();
  const terminalRef = useRef<TerminalRef>(null);

  // UI State Management
  const uiState = useUIState();
  const {
    activeTab,
    currentActionData,
    activeFileCodeEditor,
    browserUrl,
    isMobileMenuOpen,
    isMobileDetailPaneOpen,
    deployedUrl,
    logoClickCount,
    showNativeToolToggle,
    showConsentDialog,
    shouldShakeConnectionIndicator,
    showReloadButton,
    setActiveTab,
    setCurrentActionData,
    setActiveFileCodeEditor,
    setBrowserUrl,
    setIsMobileMenuOpen,
    setIsMobileDetailPaneOpen,
    setDeployedUrl,
    incrementLogoClickCount,
    setShowNativeToolToggle,
    setShowConsentDialog,
    triggerShakeConnectionIndicator,
    setShowReloadButton,
    resetUIState,
  } = uiState;

  // Chat State Management
  const chatState = useChatState();
  const {
    messages,
    isLoading,
    isCompleted,
    currentQuestion,
    uploadedFiles,
    isUploading,
    filesContent,
    taskSummary,
    userPrompt,
    showUpgradePrompt,
    pendingQuestion,
    isUseDeepResearch,
    setMessages,
    addMessage,
    updateLastMessage,
    setIsLoading,
    setIsCompleted,
    setCurrentQuestion,
    setUploadedFiles,
    addUploadedFile,
    setIsUploading,
    setFilesContent,
    setFileContent,
    setTaskSummary,
    setUserPrompt,
    setShowUpgradePrompt,
    setPendingQuestion,
    setIsUseDeepResearch,
    resetChatState,
  } = chatState;

  // Additional state
  const [deviceId, setDeviceId] = useState<string>("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isLoadingSession, setIsLoadingSession] = useState(false);
  const [workspaceInfo, setWorkspaceInfo] = useState("");
  const [useNativeToolCalling, setUseNativeToolCalling] = useState(false);
  const [timeoutCheckInterval, setTimeoutCheckInterval] = useState<NodeJS.Timeout | null>(null);
  const [returnedFromChat, setReturnedFromChat] = useState(false);

  const isReplayMode = useMemo(() => !!searchParams.get("id"), [searchParams]);
  const { selectedModel, setSelectedModel } = useChutes();

  // Initialize device ID on page load
  useEffect(() => {
    let existingDeviceId = Cookies.get("device_id");

    if (!existingDeviceId) {
      existingDeviceId = uuidv4();
      Cookies.set("device_id", existingDeviceId, {
        expires: 365,
        sameSite: "strict",
        secure: window.location.protocol === "https:",
      });
      console.log("Generated new device ID:", existingDeviceId);
    } else {
      console.log("Using existing device ID:", existingDeviceId);
    }

    setDeviceId(existingDeviceId);
  }, []);

  // Auto-switch Pro users to Sonnet 4
  useEffect(() => {
    const proAccess = hasProAccess();
    const manualSwitch = localStorage.getItem("userManuallySwitchedModel");
    
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

  // Utility functions
  const parseJson = (jsonString: string) => {
    try {
      return JSON.parse(jsonString);
    } catch {
      return null;
    }
  };

  // Action Handler
  const { handleClickAction } = useActionHandler({
    setActiveTab,
    setCurrentActionData,
    setActiveFileCodeEditor,
    workspaceInfo,
    terminalRef
  });

  // Generate task summary function
  const generateTaskSummary = useCallback(async (firstUserMessage: string) => {
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
  }, [selectedModel.id, setTaskSummary]);

  // Event Handler
  const { handleEvent } = useEventHandler({
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
    setUserPrompt,
    addUploadedFile,
    setActiveTab,
    setDeployedUrl,
    workspaceInfo,
    setWorkspaceInfo,
    setSessionId,
    handleClickAction,
    selectedModel,
    generateTaskSummaryFn: generateTaskSummary,
    hasProAccessFn: hasProAccess,
    terminalRef
  });

  // Session Manager  
  const {
    fetchSessionEvents
  } = useSessionManager({
    deviceId,
    sessionId,
    isLoadingSession: false,
    workspaceInfo,
    returnedFromChat,
    useNativeToolCalling
  });

  // Session-ID beim Mount aus URL initialisieren
  useEffect(() => {
    const id = searchParams.get('id');
    if (id) setSessionId(id);
  }, [searchParams]);

  // Fetch session events when session ID is available
  useEffect(() => {
    const id = searchParams.get("id");
    if (id) {
      fetchSessionEvents(
        id,
        (eventPayload, eventId) => handleEvent({ ...eventPayload, id: eventId, type: eventPayload.type as string, content: eventPayload.content as Record<string, unknown> }),
        (path) => setWorkspaceInfo(path),
        () => setIsLoadingSession(false)
      );
    }
  }, [searchParams, fetchSessionEvents, handleEvent, setWorkspaceInfo, setIsLoadingSession]);

  // WebSocket Manager
  const {
    socket,
    isSocketConnected,
    isSocketReady,
    sendMessage,
  } = useWebSocketManager({
    deviceId,
    isReplayMode,
    selectedModel,
    useNativeToolCalling,
    onEventReceived: handleEvent,
    getProKey,
    isLoading
  });

  // Interaction Handlers
  const {
    handleQuestionSubmit,
    handleShare,
    handleLogoClick,
    handleExampleClick,
    handleFileUpload,
    handleStopAgent,
    handleConsentAccept,
    handleConsentCancel
  } = useHomeInteractionHandlers({
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
    parseJsonFn: parseJson
  });

  // Additional handlers not in the interaction handlers hook
  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleQuestionSubmit((e.target as HTMLTextAreaElement).value);
    }
  }, [handleQuestionSubmit]);

  const resetChat = useCallback(() => {
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
    resetChatState();
    resetUIState();
    setReturnedFromChat(true);
  }, [socket, timeoutCheckInterval, setTimeoutCheckInterval, setSessionId, router, resetChatState, resetUIState, setReturnedFromChat]);

  const isInChatView = useMemo(
    () => !!sessionId && !isLoadingSession,
    [isLoadingSession, sessionId]
  );

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

  const getRemoteURL = (path: string | undefined) => {
    const workspaceId = workspaceInfo.split("/").pop();
    return `${process.env.NEXT_PUBLIC_API_URL}/workspace/${workspaceId}/${path}`;
  };

  // Show reload button if connection is not ready after returning from chat
  useEffect(() => {
    let timer: NodeJS.Timeout | null = null;
    
    if (returnedFromChat && !isSocketReady && !isInChatView) {
      timer = setTimeout(() => {
        if (!isSocketReady && !isInChatView) {
          setShowReloadButton(true);
        }
      }, 5000);
    }
    
    if (isSocketReady) {
      setShowReloadButton(false);
      if (returnedFromChat) {
        setReturnedFromChat(false);
      }
    }
    
    return () => {
      if (timer) {
        clearTimeout(timer);
      }
    };
  }, [returnedFromChat, isSocketReady, isInChatView, setShowReloadButton]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages?.length]);

  return (
    <main className={`relative flex flex-col flex-1 w-full min-h-screen bg-gradient-to-b from-[#181d2a] via-[#181d2a] to-[#1a1a1f] overflow-x-hidden`}>
      <div className="absolute inset-0 z-0 pointer-events-none select-none" aria-hidden="true">
        <div className="w-full h-full bg-gradient-to-b from-[#23263b] via-transparent to-[#181d2a] opacity-50" />
      </div>
      <div className={`relative z-10 flex flex-col flex-1 min-h-screen`}>
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
                {!hasProAccess() && <ProUpgradeButton />}
                
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
      <main className="flex-1 relative z-10 flex flex-col min-h-0 overflow-hidden h-full">
        {!isInChatView && (
          <div className="flex-1 flex flex-col min-h-0">
            <motion.div
              className="flex flex-col items-center justify-center flex-1 px-4 min-h-0"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.8, delay: 0.2 }}
            >
              {/* Hero Section */}
              <div className={`text-center mb-8 md:mb-12`}>
                <motion.div 
                  className="flex items-center justify-center mb-6 md:mb-8 cursor-pointer group"
                  onClick={handleLogoClick}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  <div className="relative">
                    <Image
                      src="/logo-only.png"
                      alt="fubea Logo"
                      width={150}
                      height={108}
                      className="w-[150px] h-[108px] md:w-[200px] md:h-[144px] rounded-2xl shadow-2xl transition-all-smooth group-hover:shadow-glow"
                    />
                    <div className="absolute inset-0 bg-gradient-to-r from-blue-500/20 to-purple-500/20 rounded-2xl blur-xl group-hover:blur-2xl transition-all-smooth" />
                    <Sparkles className="absolute -top-2 -right-2 w-5 h-5 text-yellow-400 animate-pulse" />
                  </div>
                </motion.div>
                
                <motion.h1
                  className="text-2xl sm:text-3xl md:text-5xl lg:text-6xl font-bold mb-3 md:mb-4 bg-gradient-to-r from-white via-blue-100 to-purple-100 bg-clip-text text-transparent"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.8, delay: 0.4 }}
                >
                  How can I help you today?
                </motion.h1>
                
                <motion.p
                  className="text-base sm:text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto"
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
                
                {/* Powered by Chutes */}
                <motion.div
                  className="mt-4 text-sm text-muted-foreground"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.8, delay: 0.7 }}
                >
                  <span>powered by</span>
                  <a 
                    href="https://chutes.ai" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="hover:text-foreground transition-colors hover-lift inline-flex items-center gap-1 ml-1"
                  >
                    <span className="bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent font-semibold">
                      Chutes
                    </span>
                  </a>
                </motion.div>
                
                {/* Connection Status Indicator */}
                {!isSocketReady && (
                  <motion.div
                    className={`mt-4 ${
                      shouldShakeConnectionIndicator ? 'animate-shake' : ''
                    }`}
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
                      <motion.div
                        className="mt-3 flex flex-col items-center gap-2"
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.3 }}
                      >
                        <Button
                          onClick={() => window.location.reload()}
                          variant="outline"
                          size="sm"
                          className="bg-glass border-white/20 hover:bg-white/10 transition-all-smooth hover-lift"
                        >
                          <RefreshCw className="w-3 h-3 mr-2" />
                          Reload Page
                        </Button>
                        <p className="text-xs text-muted-foreground text-center max-w-xs">
                          Connection is taking longer than expected. This might be due to high server load.
                        </p>
                      </motion.div>
                    )}
                  </motion.div>
                )}
              </div>
            </motion.div>
            
            {/* Input and Examples Container */}
            <div className="mt-auto flex-shrink-0">
              <motion.div
                key="input-view"
                className="flex items-center justify-center px-4 pb-4"
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.6 }}
              >
                <QuestionInput
                  placeholder={!isSocketConnected ? "Connecting to server..." : "Give fubea a task to work on..."}
                  value={currentQuestion}
                  setValue={setCurrentQuestion}
                  handleKeyDown={handleKeyDown}
                  handleSubmit={handleQuestionSubmit}
                  handleFileUpload={handleFileUpload}
                  isUploading={isUploading}
                  isUseDeepResearch={isUseDeepResearch}
                  setIsUseDeepResearch={setIsUseDeepResearch}
                  isDisabled={!isSocketConnected || !isSocketReady}
                  isLoading={isLoading || (!isSocketConnected || !isSocketReady)}
                  handleStopAgent={handleStopAgent}
                  className="w-full max-w-4xl"
                />
              </motion.div>
              
              {/* Examples Section */}
              <motion.div
                key="examples-view"
                className="flex items-center justify-center px-4 pb-4"
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ 
                  duration: 0.6, 
                  delay: 0.2,
                  exit: { duration: 0.1, delay: 0 }
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
                  className="w-full h-full chat-grid-layout px-0 pb-0 md:px-4 md:pb-4"
                >
                  {/* Chat Messages Panel */}
                  <div className={`
                    ${isMobileDetailPaneOpen ? 'hidden md:flex' : 'flex'} 
                    chat-panel-container px-4 pb-4 md:px-0 md:pb-0
                    ${isMobileDetailPaneOpen ? 'mobile-slide-left' : 'mobile-slide-in-from-left'}
                  `}>
                    <ChatMessage
                      messages={messages}
                      isLoading={isLoading}
                      isCompleted={isCompleted}
                      workspaceInfo={workspaceInfo}
                      handleClickAction={(action, isReplay) => {
                        handleClickAction(action, isReplay);
                        if (typeof window !== 'undefined' && window.innerWidth < 768) {
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
                      showUpgradePrompt={showUpgradePrompt}
                    />
                  </div>

                  {/* Tools Panel */}
                  <div className={`
                    ${isMobileDetailPaneOpen ? 'flex' : 'hidden'} 
                    md:flex detail-panel-container bg-glass-dark rounded-2xl border border-white/10 overflow-hidden
                    ${isMobileDetailPaneOpen ? 'mobile-slide-in-from-right' : 'mobile-slide-right'}
                  `}>
                    {/* Tab Navigation */}
                    <div className="flex items-center justify-between p-4 pt-6 border-b border-white/10 bg-black/20 flex-shrink-0">
                      <div className="flex gap-2 overflow-x-auto pb-2">
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
                    <div className="tab-content-container">
                      {activeTab === TAB.BROWSER && (
                        <>
                          {(currentActionData?.type === TOOL.VISIT || isBrowserTool) && (
                            <Browser
                              className="tab-content-enter"
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
                          )}
                          {currentActionData?.type === TOOL.WEB_SEARCH && (
                            <SearchBrowser
                              className="tab-content-enter"
                              keyword={currentActionData?.data.tool_input?.query}
                              search_results={
                                currentActionData?.type === TOOL.WEB_SEARCH &&
                                currentActionData?.data?.result
                                  ? parseJson(currentActionData?.data?.result as string)
                                  : undefined
                              }
                            />
                          )}
                          {currentActionData?.type === TOOL.IMAGE_GENERATE && (
                            <ImageBrowser
                              className="tab-content-enter"
                              url={currentActionData?.data.tool_input?.output_filename}
                              image={getRemoteURL(
                                currentActionData?.data.tool_input?.output_filename
                              )}
                            />
                          )}
                        </>
                      )}
                      {activeTab === TAB.CODE && (
                        <CodeEditor
                          currentActionData={currentActionData}
                          activeTab={activeTab}
                          className="tab-content-enter"
                          workspaceInfo={workspaceInfo}
                          activeFile={activeFileCodeEditor}
                          setActiveFile={setActiveFileCodeEditor}
                          filesContent={filesContent}
                          isReplayMode={isReplayMode}
                        />
                      )}
                      {activeTab === TAB.TERMINAL && (
                        <TerminalComponent
                          ref={terminalRef}
                          className="tab-content-enter"
                          onCommand={(command) => {
                            console.log(`[TERMINAL_DEBUG] Handling terminal command: ${command}`);
                            if (socket && isSocketConnected) {
                              try {
                                socket.send(JSON.stringify({
                                  type: "terminal_command",
                                  content: {
                                    command: command
                                  }
                                }));
                              } catch (error) {
                                console.error(`[TERMINAL_DEBUG] Error sending terminal command:`, error);
                                if (terminalRef.current) {
                                  terminalRef.current.writeOutput(`\r\nError: Failed to send command to server\r\n`);
                                }
                              }
                            } else {
                              console.error(`[TERMINAL_DEBUG] WebSocket not connected`);
                              if (terminalRef.current) {
                                terminalRef.current.writeOutput(`\r\nError: WebSocket not connected, cannot execute command\r\n`);
                              }
                            }
                          }}
                        />
                      )}
                      {activeTab === TAB.WEBSITE && deployedUrl && (
                        <WebsiteViewer
                          url={deployedUrl}
                          className="tab-content-enter"
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
          className="relative z-10 text-center py-2 px-4 mobile-safe-area flex-shrink-0"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8, delay: 1 }}
        >
          <div className="text-xs sm:text-sm text-muted-foreground">
            <div className="flex flex-col sm:flex-row flex-wrap items-center justify-center gap-1 sm:gap-2">
              <div className="flex items-center gap-1">
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
              </div>
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
        </motion.footer>
      )}
      
      <InstallPrompt />
      <ConsentDialog
        isOpen={showConsentDialog}
        onAccept={handleConsentAccept}
        onCancel={handleConsentCancel}
      />
      <CookieBanner />
    </div>
    </main>
  );
} 