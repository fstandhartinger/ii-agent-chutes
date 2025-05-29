/* eslint-disable @typescript-eslint/no-unused-vars */
/* eslint-disable react-hooks/exhaustive-deps */
"use client";

// @ts-nocheck

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
import { useEffect, useMemo, useRef, useCallback } from "react"; // Removed useState
// import { toast } from "sonner"; // toast is used by hooks
// import { cloneDeep, debounce } from "lodash"; // Moved to hooks
// import Cookies from "js-cookie"; // Moved to useSessionManager
// import { v4 as uuidv4 } from "uuid"; // Moved to hooks if needed there
import { useRouter, useSearchParams } from "next/navigation"; // Keep useRouter for /gaia, useSearchParams for isReplayMode
import { useChutes } from "@/providers/chutes-provider";
import Examples from "@/components/examples";
import ModelPicker from "@/components/model-picker";
import ProUpgradeButton from "@/components/pro-upgrade-button";
import { hasProAccess, getProKey } from "@/utils/pro-utils"; // Keep for Pro logic

import dynamic from "next/dynamic";
const CodeEditor = dynamic(() => import("@/components/code-editor"), { ssr: false });

// Removed inline WebSocketMessage interface

import QuestionInput from "@/components/question-input";
import SearchBrowser from "@/components/search-browser";
import { Button } from "@/components/ui/button";
import {
  ActionStep,
  // AgentEvent, // Moved to hooks
  // IEvent, // Moved to hooks
  Message,
  TAB,
  TOOL,
  WebSocketMessage, // Now imported from typings
} from "@/typings/agent";
const ChatMessage = dynamic(() => import("./chat-message"), { ssr: false });
const ImageBrowser = dynamic(() => import("./image-browser"), { ssr: false });

import InstallPrompt from "./install-prompt";
import ConsentDialog /*, { hasUserConsented, setUserConsent } // Moved to useHomeInteractionHandlers */ from "./consent-dialog";
import CookieBanner from "./cookie-banner";

// Import new hooks
import { useChatState } from "./home-parts/useChatState";
import { useUIState } from "./home-parts/useUIState";
import { useSessionManager } from "./home-parts/useSessionManager";
import { useWebSocketManager } from "./home-parts/useWebSocketManager";
import { useActionHandler } from "./home-parts/useActionHandler";
import { useEventHandler } from "./home-parts/useEventHandler";
import { useHomeInteractionHandlers } from "./home-parts/useHomeInteractionHandlers";


export default function Home() {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const terminalRef = useRef<TerminalRef>(null);
  const searchParams = useSearchParams(); // For isReplayMode
  const router = useRouter(); // For /gaia navigation

  // Initialize Chutes context
  const { selectedModel, setSelectedModel } = useChutes();

  // Local utility functions (must be defined before useEventHandler if passed to it)
  const parseJson = useCallback((jsonString: string) => {
    try { return JSON.parse(jsonString); } catch { return null; }
  }, []);

  const getRemoteURL = useCallback((path: string | undefined, currentWorkspaceInfo: string) => {
    if (!currentWorkspaceInfo && !path) return ""; 
    if (!currentWorkspaceInfo && path) return `${process.env.NEXT_PUBLIC_API_URL}/workspace/unknown/${path}`; // Fallback if needed
    const workspaceId = currentWorkspaceInfo.split("/").pop();
    return `${process.env.NEXT_PUBLIC_API_URL}/workspace/${workspaceId}/${path}`;
  }, []);

  // Initialize custom hooks
  const sessionManager = useSessionManager();
  const chatState = useChatState();
  const uiState = useUIState();

  const { handleClickAction } = useActionHandler({
    setActiveTab: uiState.setActiveTab,
    setCurrentActionData: uiState.setCurrentActionData,
    setActiveFileCodeEditor: uiState.setActiveFileCodeEditor,
    workspaceInfo: sessionManager.workspaceInfo,
    terminalRef,
  });

  // Define generateTaskSummary locally in Home.tsx
  const localGenerateTaskSummary = useCallback(async (firstUserMessage: string) => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/generate-summary`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: firstUserMessage, modelId: selectedModel.id }),
      });
      if (response.ok) {
        const data = await response.json();
        chatState.setTaskSummary(data.summary || "Task in progress");
      } else {
        console.error("Error generating task summary:", response.statusText);
        chatState.setTaskSummary("Task in progress");
      }
    } catch (error) {
      console.error("Error generating task summary:", error);
      chatState.setTaskSummary("Task in progress");
    }
  }, [selectedModel, chatState.setTaskSummary]);

  const eventHandlerObject = useEventHandler({ // Renamed to avoid conflict with eventHandler variable name
    messages: chatState.messages,
    userPrompt: chatState.userPrompt,
    taskSummary: chatState.taskSummary,
    isLoading: chatState.isLoading,
    addMessage: chatState.addMessage,
    updateLastMessage: chatState.updateLastMessage,
    setIsLoading: chatState.setIsLoading,
    setIsCompleted: chatState.setIsCompleted,
    setFileContent: chatState.setFileContent,
    setTaskSummary: chatState.setTaskSummary,
    setShowUpgradePrompt: chatState.setShowUpgradePrompt,
    setUserPrompt: chatState.setUserPrompt,
    addUploadedFile: chatState.addUploadedFile,
    setActiveTab: uiState.setActiveTab,
    setDeployedUrl: uiState.setDeployedUrl,
    workspaceInfo: sessionManager.workspaceInfo,
    setWorkspaceInfo: sessionManager.setWorkspaceInfo,
    setSessionId: sessionManager.setSessionId, // Added this line
    handleClickAction: handleClickAction, 
    selectedModel,
    generateTaskSummaryFn: localGenerateTaskSummary, 
    hasProAccessFn: hasProAccess,
  });
  
  const webSocketManager = useWebSocketManager({
    deviceId: sessionManager.deviceId,
    isReplayMode: useMemo(() => !!searchParams.get("id"), [searchParams]), 
    selectedModel,
    useNativeToolCalling: sessionManager.useNativeToolCalling,
    onEventReceived: eventHandlerObject.handleEvent as (event: { id: string; type: string; content: Record<string, unknown> }) => void,
    getProKey: getProKey,
    isLoading: chatState.isLoading,
    currentMessages: chatState.messages,
  });

  const interactionHandlers = useHomeInteractionHandlers({
    isLoading: chatState.isLoading,
    messages: chatState.messages,
    uploadedFiles: chatState.uploadedFiles,
    userPrompt: chatState.userPrompt,
    pendingQuestion: chatState.pendingQuestion,
    isUseDeepResearch: chatState.isUseDeepResearch, 
    setIsLoading: chatState.setIsLoading,
    setCurrentQuestion: chatState.setCurrentQuestion,
    setIsCompleted: chatState.setIsCompleted,
    addMessage: chatState.addMessage,
    setUserPrompt: chatState.setUserPrompt,
    setIsUploading: chatState.setIsUploading,
    addUploadedFile: chatState.addUploadedFile,
    setPendingQuestion: chatState.setPendingQuestion,
    setShowUpgradePrompt: chatState.setShowUpgradePrompt,
    setMessages: chatState.setMessages,
    logoClickCount: uiState.logoClickCount,
    setShowConsentDialog: uiState.setShowConsentDialog,
    triggerShakeConnectionIndicator: uiState.triggerShakeConnectionIndicator,
    incrementLogoClickCount: uiState.incrementLogoClickCount,
    setShowNativeToolToggle: uiState.setShowNativeToolToggle,
    setActiveTab: uiState.setActiveTab,
    sessionId: sessionManager.sessionId,
    workspaceInfo: sessionManager.workspaceInfo,
    hasProAccess: hasProAccess,
    isSocketConnected: webSocketManager.isSocketConnected,
    isSocketReady: webSocketManager.isSocketReady,
    sendMessage: webSocketManager.sendMessage,
    socket: webSocketManager.socket,
    selectedModel,
    parseJsonFn: parseJson,
  });
  
  const isReplayMode = useMemo(() => !!searchParams.get("id"), [searchParams]);
  const isInChatView = useMemo(
    () => !!sessionManager.sessionId && !sessionManager.isLoadingSession,
    [sessionManager.sessionId, sessionManager.isLoadingSession]
  );
  const isBrowserTool = useMemo(
    () =>
      [
        TOOL.BROWSER_VIEW, TOOL.BROWSER_CLICK, TOOL.BROWSER_ENTER_TEXT,
        TOOL.BROWSER_PRESS_KEY, TOOL.BROWSER_GET_SELECT_OPTIONS,
        TOOL.BROWSER_SELECT_DROPDOWN_OPTION, TOOL.BROWSER_SWITCH_TAB,
        TOOL.BROWSER_OPEN_NEW_TAB, TOOL.BROWSER_WAIT, TOOL.BROWSER_SCROLL_DOWN,
        TOOL.BROWSER_SCROLL_UP, TOOL.BROWSER_NAVIGATION, TOOL.BROWSER_RESTART,
      ].includes(uiState.currentActionData?.type as TOOL),
    [uiState.currentActionData]
  );

  useEffect(() => {
    if (sessionManager.sessionId && isReplayMode) { 
      sessionManager.fetchSessionEvents(
        sessionManager.sessionId,
        (eventPayload, eventId) => eventHandlerObject.handleEvent({ ...eventPayload, id: eventId } as any), 
        (path) => sessionManager.setWorkspaceInfo(path), 
        () => chatState.setIsLoading(false) 
      );
    }
  }, [sessionManager.sessionId, isReplayMode, sessionManager.fetchSessionEvents, eventHandlerObject.handleEvent, sessionManager.setWorkspaceInfo, chatState.setIsLoading]);

  useEffect(() => {
    const proAccess = hasProAccess();
    const manualSwitch = localStorage.getItem("userManuallySwitchedModel");
    if (proAccess && manualSwitch !== "true" && selectedModel.id !== "claude-sonnet-4-20250514") {
      console.log("Home: Auto-switching Pro user to Claude Sonnet 4");
      const sonnet4Model = {
        id: "claude-sonnet-4-20250514", name: "Claude Sonnet 4",
        provider: "anthropic" as const, supportsVision: true
      };
      setSelectedModel(sonnet4Model); 
    }
  }, [selectedModel, setSelectedModel]); 

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatState.messages?.length]);

  useEffect(() => {
    let timer: NodeJS.Timeout | null = null;
    if (sessionManager.returnedFromChat && !webSocketManager.isSocketReady && !isInChatView) {
      timer = setTimeout(() => {
        if (!webSocketManager.isSocketReady && !isInChatView) {
          uiState.setShowReloadButton(true);
        }
      }, 5000);
    }
    if (webSocketManager.isSocketReady) {
      uiState.setShowReloadButton(false);
      if (sessionManager.returnedFromChat) {
        sessionManager.setReturnedFromChat(false);
      }
    }
    return () => { if (timer) clearTimeout(timer); };
  }, [sessionManager.returnedFromChat, webSocketManager.isSocketReady, isInChatView, uiState.setShowReloadButton, sessionManager.setReturnedFromChat]);

  const combinedResetChat = useCallback(() => {
    webSocketManager.disconnect();
    
    // Add a slight delay to ensure disconnect processes, then explicitly connect
    setTimeout(() => {
      // webSocketManager.connect() already checks for deviceId and !isReplayMode internally
      // We need isReplayMode here just for the console log or if we wanted to gate it here too.
      // const currentIsReplayMode = !!searchParams.get("id"); // Recalculate or pass if needed
      console.log("HOME_DEBUG: Explicitly calling connect() after combinedResetChat disconnect.");
      webSocketManager.connect();
    }, 100); // 100ms delay

    eventHandlerObject.clearTimeoutCheck();
    sessionManager.resetSessionForNewChat(); 
    chatState.resetChatState();
    uiState.resetUIState();
  }, [webSocketManager, eventHandlerObject, sessionManager, chatState, uiState]); // searchParams could be added if used directly for currentIsReplayMode

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      interactionHandlers.handleQuestionSubmit((e.target as HTMLTextAreaElement).value);
    }
  };

  return (
    <main className={`relative flex flex-col flex-1 w-full min-h-screen bg-gradient-to-b from-[#181d2a] via-[#181d2a] to-[#1a1a1f] overflow-x-hidden`}>
      <div className="absolute inset-0 z-0 pointer-events-none select-none" aria-hidden="true">
        <div className="w-full h-full bg-gradient-to-b from-[#23263b] via-transparent to-[#181d2a] opacity-50" />
      </div>
      <div className={`relative z-10 flex flex-col flex-1 min-h-screen`}>
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
                    onClick={combinedResetChat}
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
                    {chatState.taskSummary || chatState.userPrompt || "fubea"}
                  </span>
                </>
              )}
            </motion.div>
            
            {isInChatView ? (
              <div className="flex items-center gap-2 flex-shrink-0 ml-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={interactionHandlers.handleShare}
                  className="bg-glass border-white/20 hover:bg-white/10 transition-all-smooth hover-lift"
                  title="Share Session"
                >
                  <Share className="w-4 h-4" />
                  <span className="ml-2 hidden sm:inline">Share</span>
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => uiState.setIsMobileMenuOpen(!uiState.isMobileMenuOpen)}
                  className="md:hidden bg-glass border-white/20"
                >
                  <Menu className="w-4 h-4" />
                </Button>
              </div>
            ) : (
              <div className="flex-1 flex justify-end items-center gap-4">
                {!hasProAccess() && <ProUpgradeButton />}
                {uiState.showNativeToolToggle && (
                  <div className="flex items-center gap-2 bg-glass border border-white/20 rounded-lg px-3 py-2">
                    <span className="text-sm text-white/80">Native Tool Calling</span>
                    <button
                      onClick={() => sessionManager.setUseNativeToolCalling(!sessionManager.useNativeToolCalling)}
                      className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
                        sessionManager.useNativeToolCalling ? 'bg-blue-500' : 'bg-gray-600'
                      }`}
                      title={sessionManager.useNativeToolCalling ? "Using native tool calling (Squad-style)" : "Using JSON workaround (default)"}
                    >
                      <span
                        className={`inline-block h-3 w-3 transform rounded-full bg-white transition-transform ${
                          sessionManager.useNativeToolCalling ? 'translate-x-5' : 'translate-x-1'
                        }`}
                      />
                    </button>
                  </div>
                )}
                <ModelPicker />
              </div>
            )}
        </div>
        
        {uiState.isMobileMenuOpen && isInChatView && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="md:hidden bg-glass-dark border-t border-white/10 px-4 py-3"
          >
            <Button
              variant="outline"
              size="sm"
              onClick={interactionHandlers.handleShare}
              className="w-full bg-glass border-white/20 hover:bg-white/10 mb-2"
            >
              <Share className="w-4 h-4 mr-2" />
              Share Session
            </Button>
          </motion.div>
        )}
      </motion.header>

      <main className="flex-1 relative z-10 flex flex-col min-h-0 overflow-hidden h-full">
        {!isInChatView && (
          <div className="flex-1 flex flex-col min-h-0">
            <motion.div
              className="flex flex-col items-center justify-center flex-1 px-4 min-h-0"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.8, delay: 0.2 }}
            >
              <div className={`text-center mb-8 md:mb-12`}>
                <motion.div 
                  className="flex items-center justify-center mb-6 md:mb-8 cursor-pointer group"
                  onClick={interactionHandlers.handleLogoClick}
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
                
                {!webSocketManager.isSocketReady && (
                  <motion.div
                    className={`mt-4 ${
                      uiState.shouldShakeConnectionIndicator ? 'animate-shake' : ''
                    }`}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ duration: 0.3 }}
                  >
                    <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>
                        {!webSocketManager.isSocketConnected ? "Connecting to server..." : "Initializing server..."}
                      </span>
                    </div>
                    
                    {uiState.showReloadButton && (
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
                  placeholder={!webSocketManager.isSocketConnected ? "Connecting to server..." : "Give fubea a task to work on..."}
                  value={chatState.currentQuestion}
                  setValue={chatState.setCurrentQuestion}
                  handleKeyDown={handleKeyDown}
                  handleSubmit={interactionHandlers.handleQuestionSubmit}
                  handleFileUpload={interactionHandlers.handleFileUpload}
                  isUploading={chatState.isUploading}
                  isUseDeepResearch={chatState.isUseDeepResearch}
                  setIsUseDeepResearch={chatState.setIsUseDeepResearch}
                  isDisabled={!webSocketManager.isSocketConnected || !webSocketManager.isSocketReady}
                  isLoading={chatState.isLoading || (!webSocketManager.isSocketConnected || !webSocketManager.isSocketReady)}
                  handleStopAgent={interactionHandlers.handleStopAgent}
                  className="w-full max-w-4xl"
                />
              </motion.div>
              
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
                  onExampleClick={interactionHandlers.handleExampleClick}
                  className="w-full max-w-4xl"
                />
              </motion.div>
            </div>
          </div>
        )}

        {sessionManager.isLoadingSession ? (
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
                  <div className={`
                    ${uiState.isMobileDetailPaneOpen ? 'hidden md:flex' : 'flex'} 
                    chat-panel-container px-4 pb-4 md:px-0 md:pb-0
                    ${uiState.isMobileDetailPaneOpen ? 'mobile-slide-left' : 'mobile-slide-in-from-left'}
                  `}>
                    <ChatMessage
                      messages={chatState.messages}
                      isLoading={chatState.isLoading}
                      isCompleted={chatState.isCompleted}
                      workspaceInfo={sessionManager.workspaceInfo}
                      handleClickAction={(action, isReplay) => {
                        handleClickAction(action, isReplay);
                        if (typeof window !== 'undefined' && window.innerWidth < 768) {
                          uiState.setIsMobileDetailPaneOpen(true);
                        }
                      }}
                      isUploading={chatState.isUploading}
                      isUseDeepResearch={chatState.isUseDeepResearch}
                      isReplayMode={isReplayMode}
                      currentQuestion={chatState.currentQuestion}
                      messagesEndRef={messagesEndRef}
                      setCurrentQuestion={chatState.setCurrentQuestion}
                      handleKeyDown={handleKeyDown}
                      handleQuestionSubmit={interactionHandlers.handleQuestionSubmit}
                      handleFileUpload={interactionHandlers.handleFileUpload}
                      handleStopAgent={interactionHandlers.handleStopAgent}
                      showUpgradePrompt={chatState.showUpgradePrompt}
                    />
                  </div>

                  <div className={`
                    ${uiState.isMobileDetailPaneOpen ? 'flex' : 'hidden'} 
                    md:flex detail-panel-container bg-glass-dark rounded-2xl border border-white/10 overflow-hidden
                    ${uiState.isMobileDetailPaneOpen ? 'mobile-slide-in-from-right' : 'mobile-slide-right'}
                  `}>
                    <div className="flex items-center justify-between p-4 pt-6 border-b border-white/10 bg-black/20 flex-shrink-0">
                      <div className="flex gap-2 overflow-x-auto pb-2">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => uiState.setIsMobileDetailPaneOpen(false)}
                          className="md:hidden bg-glass border-white/20 hover:bg-white/10 transition-all-smooth hover-lift mr-2"
                        >
                          <ArrowLeft className="w-4 h-4" />
                        </Button>
                        
                        <Button
                          size="sm"
                          variant={uiState.activeTab === TAB.BROWSER ? "default" : "outline"}
                          onClick={() => uiState.setActiveTab(TAB.BROWSER)}
                          className={`transition-all-smooth hover-lift ${
                            uiState.activeTab === TAB.BROWSER
                              ? "bg-gradient-skyblue-lavender text-black shadow-glow"
                              : "bg-glass border-white/20 hover:bg-white/10"
                          }`}
                        >
                          <Globe className="w-4 h-4 mr-2" />
                          Browser
                        </Button>
                        <Button
                          size="sm"
                          variant={uiState.activeTab === TAB.CODE ? "default" : "outline"}
                          onClick={() => uiState.setActiveTab(TAB.CODE)}
                          className={`transition-all-smooth hover-lift ${
                            uiState.activeTab === TAB.CODE
                              ? "bg-gradient-skyblue-lavender text-black shadow-glow"
                              : "bg-glass border-white/20 hover:bg-white/10"
                          }`}
                        >
                          <Code className="w-4 h-4 mr-2" />
                          Files
                        </Button>
                        <Button
                          size="sm"
                          variant={uiState.activeTab === TAB.TERMINAL ? "default" : "outline"}
                          onClick={() => uiState.setActiveTab(TAB.TERMINAL)}
                          className={`transition-all-smooth hover-lift ${
                            uiState.activeTab === TAB.TERMINAL
                              ? "bg-gradient-skyblue-lavender text-black shadow-glow"
                              : "bg-glass border-white/20 hover:bg-white/10"
                          }`}
                        >
                          <TerminalIcon className="w-4 h-4 mr-2" />
                          Terminal
                        </Button>
                        {uiState.deployedUrl && (
                          <Button
                            size="sm"
                            variant={uiState.activeTab === TAB.WEBSITE ? "default" : "outline"}
                            onClick={() => uiState.setActiveTab(TAB.WEBSITE)}
                            className={`transition-all-smooth hover-lift ${
                              uiState.activeTab === TAB.WEBSITE
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

                    <div className="tab-content-container">
                      {uiState.activeTab === TAB.BROWSER && (
                        <>
                          {(uiState.currentActionData?.type === TOOL.VISIT || isBrowserTool) && (
                            <Browser
                              className="tab-content-enter"
                              url={uiState.currentActionData?.data?.tool_input?.url || uiState.browserUrl}
                              screenshot={
                                isBrowserTool
                                  ? (uiState.currentActionData?.data.result as string)
                                  : undefined
                              }
                              raw={
                                uiState.currentActionData?.type === TOOL.VISIT
                                  ? (uiState.currentActionData?.data?.result as string)
                                  : undefined
                              }
                            />
                          )}
                          {uiState.currentActionData?.type === TOOL.WEB_SEARCH && (
                            <SearchBrowser
                              className="tab-content-enter"
                              keyword={uiState.currentActionData?.data.tool_input?.query}
                              search_results={
                                uiState.currentActionData?.type === TOOL.WEB_SEARCH &&
                                uiState.currentActionData?.data?.result
                                  ? parseJson(uiState.currentActionData?.data?.result as string)
                                  : undefined
                              }
                            />
                          )}
                          {uiState.currentActionData?.type === TOOL.IMAGE_GENERATE && (
                            <ImageBrowser
                              className="tab-content-enter"
                              url={uiState.currentActionData?.data.tool_input?.output_filename}
                              image={getRemoteURL(
                                uiState.currentActionData?.data.tool_input?.output_filename,
                                sessionManager.workspaceInfo
                              )}
                            />
                          )}
                        </>
                      )}
                      {uiState.activeTab === TAB.CODE && (
                        <CodeEditor
                          currentActionData={uiState.currentActionData}
                          activeTab={uiState.activeTab}
                          className="tab-content-enter"
                          workspaceInfo={sessionManager.workspaceInfo}
                          activeFile={uiState.activeFileCodeEditor}
                          setActiveFile={uiState.setActiveFileCodeEditor}
                          filesContent={chatState.filesContent}
                          isReplayMode={isReplayMode}
                        />
                      )}
                      {uiState.activeTab === TAB.TERMINAL && (
                        <TerminalComponent
                          ref={terminalRef}
                          className="tab-content-enter"
                          onCommand={(command) => {
                            console.log(`[TERMINAL_DEBUG] Handling terminal command: ${command}`);
                            if (webSocketManager.socket && webSocketManager.isSocketConnected) {
                              try {
                                webSocketManager.socket.send(JSON.stringify({
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
                      {uiState.activeTab === TAB.WEBSITE && uiState.deployedUrl && (
                        <WebsiteViewer
                          url={uiState.deployedUrl}
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
        isOpen={uiState.showConsentDialog}
        onAccept={interactionHandlers.handleConsentAccept}
        onCancel={interactionHandlers.handleConsentCancel}
      />
      
      <CookieBanner />
    </div>
    </main>
  );
}
