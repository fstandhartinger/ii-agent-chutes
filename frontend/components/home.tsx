/* eslint-disable @typescript-eslint/no-unused-vars */
/* eslint-disable react-hooks/exhaustive-deps */
"use client";

import dynamic from "next/dynamic";
import { useEffect, useRef, useCallback, useState } from "react";
import { motion, AnimatePresence, LayoutGroup } from "framer-motion";
import { ArrowLeft, Share, Menu, Loader2, RefreshCw, Sparkles, Globe, Code, TerminalIcon } from "lucide-react";
import Image from "next/image";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Message } from "@/typings/agent";
// Uncomment these imports and fix them
// import { TAB, TOOL } from "@/lib/constants";
// import { parseJson, getRemoteURL } from "@/lib/utils";
// import { hasProAccess } from "@/lib/pro";

// Temporary constants until we can fix the imports
const TAB = {
  BROWSER: 'browser',
  CODE: 'code', 
  TERMINAL: 'terminal',
  WEBSITE: 'website'
};

const TOOL = {
  VISIT: 'visit',
  WEB_SEARCH: 'web_search',
  IMAGE_GENERATE: 'image_generate',
  BROWSER_SCREENSHOT: 'browser_screenshot',
  BROWSER_CLICK: 'browser_click',
  BROWSER_TYPE: 'browser_type',
  BROWSER_SCROLL: 'browser_scroll'
};

// Temporary utility functions
const parseJson = (str: string) => {
  try {
    return JSON.parse(str);
  } catch {
    return null;
  }
};

const getRemoteURL = (filename: string, workspaceInfo: any) => {
  if (!filename || !workspaceInfo) return '';
  return `${workspaceInfo.base_url || ''}/files/${filename}`;
};

const hasProAccess = () => false; // Temporary implementation

// Dynamic imports
const ChatMessage = dynamic(() => import("@/components/chat-message"), { ssr: false });
const QuestionInput = dynamic(() => import("@/components/question-input"), { ssr: false });
const Examples = dynamic(() => import("@/components/examples"), { ssr: false });
const Browser = dynamic(() => import("@/components/browser"), { ssr: false });
const SearchBrowser = dynamic(() => import("@/components/search-browser"), { ssr: false });
const ImageBrowser = dynamic(() => import("@/components/image-browser"), { ssr: false });
const CodeEditor = dynamic(() => import("@/components/code-editor"), { ssr: false });
const TerminalComponent = dynamic(() => import("@/components/terminal"), { ssr: false });
const WebsiteViewer = dynamic(() => import("@/components/website-viewer"), { ssr: false });
const ModelPicker = dynamic(() => import("@/components/model-picker"), { ssr: false });
const ProUpgradeButton = dynamic(() => import("@/components/pro-upgrade-button"), { ssr: false });
const InstallPrompt = dynamic(() => import("@/components/install-prompt"), { ssr: false });
const ConsentDialog = dynamic(() => import("@/components/consent-dialog"), { ssr: false });
const CookieBanner = dynamic(() => import("@/components/cookie-banner"), { ssr: false });

// Import the WebSocket hook
import { useWebSocketManager } from "@/components/home-parts/useWebSocketManager";

// Custom hooks - temporarily commented but we'll implement minimal versions
// import { useEventHandler } from "@/hooks/useEventHandler";
// import { useSessionManager } from "@/hooks/useSessionManager";
// import { useHomeInteractionHandlers } from "@/hooks/useHomeInteractionHandlers";
// import { useChatState } from "@/hooks/useChatState";
// import { useUIState } from "@/hooks/useUIState";
// import { useActionHandler } from "@/hooks/useActionHandler";

export default function Home() {
  const router = useRouter();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const terminalRef = useRef<any>(null);
  
  // Simplified state management (temporary until hooks are restored)
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [currentQuestion, setCurrentQuestion] = useState("");
  const [activeTab, setActiveTab] = useState(TAB.BROWSER);
  const [showReloadButton, setShowReloadButton] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isMobileDetailPaneOpen, setIsMobileDetailPaneOpen] = useState(false);
  const [showConsentDialog, setShowConsentDialog] = useState(false);
  const [deviceId, setDeviceId] = useState<string | null>(null);
  const [selectedModel, setSelectedModel] = useState({ provider: 'chutes' as const, id: 'sonnet-3.5', name: 'Claude 3.5 Sonnet' });
  const [useNativeToolCalling, setUseNativeToolCalling] = useState(false);
  
  // Convert WebSocket events to Message objects
  const convertEventToMessage = (event: any): Message | null => {
    if (event.type === "user_message") {
      return {
        id: event.id || `user_${Date.now()}`,
        role: "user",
        content: event.content?.text || "",
        timestamp: Date.now(),
      };
    } else if (event.type === "agent_response") {
      return {
        id: event.id || `assistant_${Date.now()}`,
        role: "assistant", 
        content: event.content?.text || "",
        timestamp: Date.now(),
      };
    } else if (event.type === "tool_result") {
      return {
        id: event.id || `tool_${Date.now()}`,
        role: "assistant",
        content: event.content?.result || "",
        timestamp: Date.now(),
        action: event.content ? {
          type: event.content.tool_name,
          data: event.content
        } : undefined
      };
    }
    return null;
  };
  
  // Initialize device ID
  useEffect(() => {
    const storedDeviceId = localStorage.getItem('deviceId');
    if (storedDeviceId) {
      setDeviceId(storedDeviceId);
    } else {
      const newDeviceId = `device_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      localStorage.setItem('deviceId', newDeviceId);
      setDeviceId(newDeviceId);
    }
  }, []);

  // WebSocket connection
  const {
    socket,
    isSocketConnected,
    isSocketReady,
    sendMessage,
    connect,
    disconnect
  } = useWebSocketManager({
    deviceId,
    isReplayMode: false,
    selectedModel,
    useNativeToolCalling,
    onEventReceived: (event) => {
      console.log("Event received:", event);
      
      if (event.type === "agent_thinking" || event.type === "processing") {
        setIsLoading(true);
      } else if (event.type === "stream_complete" || event.type === "error") {
        setIsLoading(false);
      }
      
      // Convert events to messages and add to chat
      const message = convertEventToMessage(event);
      if (message) {
        setMessages(prev => [...prev, message]);
      }
    },
    getProKey: () => null,
    isLoading
  });
  
  // Check if we're in chat view
  const isInChatView = messages && messages.length > 0;
  
  // Auto-reload when connection is poor
  useEffect(() => {
    let timer: NodeJS.Timeout | null = null;
    if (!isSocketReady && !isInChatView) {
      timer = setTimeout(() => {
        setShowReloadButton(true);
      }, 15000); // Show reload button after 15 seconds of poor connection
    } else {
      // Clear timer if connection is restored
      setShowReloadButton(false);
    }
    
    return () => {
      if (timer) {
        clearTimeout(timer);
      }
    };
  }, [isSocketReady, isInChatView]);
  
  // Function to scroll to bottom
  const scrollToBottom = useCallback(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, []);
  
  // Scroll to bottom when new messages arrive
  useEffect(() => {
    if (isInChatView) {
      scrollToBottom();
    }
  }, [messages, isInChatView, scrollToBottom]);
  
  // Simplified handlers (temporary)
  const handleQuestionSubmit = async (question: string) => {
    console.log("Question submitted:", question);
    if (!isSocketReady || !question.trim()) return;
    
    setIsLoading(true);
    setCurrentQuestion("");
    
    // Add user message to trigger chat view immediately
    const userMessage: Message = {
      id: `user_${Date.now()}`,
      role: "user",
      content: question,
      timestamp: Date.now()
    };
    setMessages(prev => [...prev, userMessage]);
    
    try {
      const success = await sendMessage({
        type: "user_message",
        content: {
          text: question,
          resume: false,
          files: []
        }
      });
      
      if (!success) {
        console.error("Failed to send message");
        setIsLoading(false);
      }
    } catch (error) {
      console.error("Error sending message:", error);
      setIsLoading(false);
    }
  };
  
  const handleShare = () => {
    console.log("Share clicked");
  };
  
  const handleLogoClick = () => {
    console.log("Logo clicked");
  };
  
  const handleExampleClick = (example: string, isDeepResearch: boolean = false, fileUrl?: string) => {
    console.log("Example clicked:", example, isDeepResearch, fileUrl);
    setCurrentQuestion(example);
    // Auto-submit the example
    handleQuestionSubmit(example);
  };
  
  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    console.log("Files uploaded:", e.target.files);
  };
  
  const handleStopAgent = () => {
    console.log("Stop agent");
    setIsLoading(false);
    // Send stop message to backend
    if (isSocketReady) {
      sendMessage({
        type: "cancel_processing",
        content: {}
      });
    }
  };

  const handleConsentAccept = () => {
    setShowConsentDialog(false);
  };

  const handleConsentCancel = () => {
    setShowConsentDialog(false);
  };

  const handleClickAction = (action: any, isReplay: boolean = false) => {
    console.log("Action clicked:", action, isReplay);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (currentQuestion.trim() && isSocketReady) {
        handleQuestionSubmit(currentQuestion);
      }
    }
  };

  return (
    <div className="flex flex-col h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900">
      <div className="flex flex-col h-full min-h-0">
        {/* Header */}
        <div className={`flex justify-between items-center w-full px-4 md:px-8 py-4${!isInChatView ? ' pb-0' : ''}`}>
          {!isInChatView && (
            <div className="w-full">
              {/* Home page header - minimal */}
            </div>
          )}
          <h1 className={
            isInChatView ? "text-xl md:text-2xl font-semibold flex-1 min-w-0" : "hidden"
          }>
            {/* Only show title in chat view, not on home page */}
          </h1>
          
          {isInChatView && (
            <div className="flex items-center gap-2 md:gap-4">
              <Button
                variant="outline"
                size="sm"
                onClick={handleShare}
                className="bg-glass border-white/20 hover:bg-white/10 transition-all-smooth hover-lift shadow-lg"
              >
                <Share className="w-4 h-4 mr-2" />
                Share
              </Button>
              
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
                className="md:hidden bg-glass border border-white/20 hover:bg-white/10"
              >
                <Menu className="w-5 h-5" />
              </Button>
            </div>
          )}
        </div>

        {/* Mobile menu overlay */}
        {isMobileMenuOpen && isInChatView && (
          <motion.div
            className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm md:hidden"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setIsMobileMenuOpen(false)}
          >
            <motion.div
              className="absolute right-0 top-0 h-full w-80 bg-glass-dark border-l border-white/20 p-6 shadow-2xl"
              initial={{ x: "100%" }}
              animate={{ x: 0 }}
              exit={{ x: "100%" }}
              onClick={(e) => e.stopPropagation()}
            >
              <div className="mb-6">
                <h3 className="text-lg font-semibold mb-4">Tools</h3>
                <div className="space-y-2">
                  {/* Tool buttons would go here */}
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}

        <main className="flex-1 relative z-10 flex flex-col min-h-0 overflow-hidden h-full">
          {!isInChatView && (
            <div className="flex-1 flex flex-col min-h-0 mobile-home-container">
              {/* Hero Section - Always Visible Priority */}
              <motion.div
                className="flex-shrink-0 mobile-hero-section px-4 pt-4 md:pt-8"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.8, delay: 0.2 }}
              >
                <div className="text-center">
                  <motion.div 
                    className="flex items-center justify-center mb-4 md:mb-8 cursor-pointer group"
                    onClick={handleLogoClick}
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.8, delay: 0.3 }}
                  >
                    <div className="relative">
                      <Image
                        src="/logo-only.png"
                        alt="fubea Logo"
                        width={80}
                        height={80}
                        className="rounded-2xl shadow-2xl transition-all duration-300 group-hover:shadow-blue-500/25"
                        priority
                      />
                      <div className="absolute inset-0 bg-gradient-to-r from-blue-500/20 to-purple-500/20 rounded-2xl blur-sm group-hover:blur-md transition-all duration-300" />
                    </div>
                  </motion.div>
                  
                  <motion.h1
                    className="text-4xl md:text-6xl font-bold mb-4 tracking-tight"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.8, delay: 0.4 }}
                  >
                    <span className="bg-gradient-to-r from-blue-400 via-purple-400 to-emerald-400 bg-clip-text text-transparent">
                      fubea
                    </span>
                  </motion.h1>
                  
                  <motion.h2
                    className="text-xl md:text-2xl text-white/90 mb-2 font-light"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.8, delay: 0.5 }}
                  >
                    How can I help you today?
                  </motion.h2>
                  
                  <motion.p
                    className="text-base md:text-lg text-muted-foreground mb-6 font-light"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.8, delay: 0.6 }}
                  >
                    Leading Deep Research Agent. For Free.
                  </motion.p>
                  
                  <motion.div
                    className="text-xs sm:text-sm text-muted-foreground mb-6"
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
                </div>
              </motion.div>
              
              {/* Connection Status - Separate Section */}
              {!isSocketReady && (
                <motion.div
                  className="flex-shrink-0 px-4 pb-2"
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
              
              {/* Input Section - Always Visible (Highest Priority) */}
              <div className="flex-shrink-0 mobile-input-priority">
                <motion.div
                  key="input-view"
                  className="flex items-center justify-center px-4 pb-4 mobile-input-container"
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
                    isUploading={false}
                    isUseDeepResearch={false}
                    setIsUseDeepResearch={(value) => {}}
                    isDisabled={!isSocketConnected || !isSocketReady}
                    isLoading={isLoading}
                    handleStopAgent={handleStopAgent}
                    className="w-full max-w-4xl"
                    textareaClassName={!isInChatView ? "border-0 bg-transparent" : ""}
                    showBorder={false}
                  />
                </motion.div>
              </div>
              
              {/* Flexible Content Area - For Examples */}
              <div className="flex-1 flex flex-col min-h-0 mobile-content-area">
                <motion.div
                  key="examples-view"
                  className="flex-1 flex items-start justify-center px-4 mobile-examples-section"
                  initial={{ opacity: 0, y: 30 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ 
                    duration: 0.6, 
                    delay: 0.8,
                    exit: { duration: 0.1, delay: 0 } 
                  }}
                >
                  <Examples
                    onExampleClick={handleExampleClick}
                    className="w-full max-w-4xl mobile-examples-wrapper"
                  />
                </motion.div>
              </div>
            </div>
          )}

          {/* Chat View - When conversation has started */}
          {isInChatView && (
            <motion.div
              key="chat-view"
              initial={{ opacity: 0, y: 30, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -20, scale: 0.95 }}
              transition={{
                type: "spring",
                stiffness: 300,
                damping: 30,
                mass: 1,
              }}
              className="flex-1 flex flex-col min-h-0 overflow-hidden"
            >
              <div className="flex-1 overflow-hidden px-4 md:px-8 pb-4">
                <ChatMessage
                  messages={messages}
                  isLoading={isLoading}
                  isCompleted={false}
                  workspaceInfo=""
                  handleClickAction={(action: any, isReplay: boolean = false) => handleClickAction(action, isReplay)}
                  isUploading={false}
                  isUseDeepResearch={false}
                  isReplayMode={false}
                  currentQuestion={currentQuestion}
                  messagesEndRef={messagesEndRef}
                  setCurrentQuestion={setCurrentQuestion}
                  handleKeyDown={handleKeyDown}
                  handleQuestionSubmit={handleQuestionSubmit}
                  handleFileUpload={handleFileUpload}
                  handleStopAgent={handleStopAgent}
                />
              </div>
            </motion.div>
          )}

          {false && (
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
      </div>
      
      <InstallPrompt />
      
      <ConsentDialog
        isOpen={showConsentDialog}
        onAccept={handleConsentAccept}
        onCancel={handleConsentCancel}
      />
      
      <CookieBanner />
    </div>
  );
} 