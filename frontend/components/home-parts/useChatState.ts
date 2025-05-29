import { useState, useCallback } from 'react';
import type { Message } from '@/typings/agent';

export interface ChatState {
  messages: Message[];
  isLoading: boolean;
  isCompleted: boolean;
  currentQuestion: string;
  uploadedFiles: string[];
  isUploading: boolean;
  filesContent: { [key: string]: string };
  taskSummary: string;
  userPrompt: string;
  showUpgradePrompt: "success" | "error" | "timeout" | null;
  pendingQuestion: string;
  isUseDeepResearch: boolean;
}

export interface ChatStateActions {
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
  addMessage: (message: Message) => void;
  updateLastMessage: (updater: (lastMessage: Message) => Message) => void;
  setIsLoading: React.Dispatch<React.SetStateAction<boolean>>;
  setIsCompleted: React.Dispatch<React.SetStateAction<boolean>>;
  setCurrentQuestion: React.Dispatch<React.SetStateAction<string>>;
  setUploadedFiles: React.Dispatch<React.SetStateAction<string[]>>;
  addUploadedFile: (filePath: string) => void;
  setIsUploading: React.Dispatch<React.SetStateAction<boolean>>;
  setFilesContent: React.Dispatch<React.SetStateAction<{ [key: string]: string }>>;
  setFileContent: (filePath: string, content: string) => void;
  setTaskSummary: React.Dispatch<React.SetStateAction<string>>;
  setUserPrompt: React.Dispatch<React.SetStateAction<string>>;
  setShowUpgradePrompt: React.Dispatch<React.SetStateAction<"success" | "error" | "timeout" | null>>;
  setPendingQuestion: React.Dispatch<React.SetStateAction<string>>;
  setIsUseDeepResearch: React.Dispatch<React.SetStateAction<boolean>>;
  resetChatState: (initialMessages?: Message[]) => void;
}

export type UseChatStateReturn = ChatState & ChatStateActions;

const initialChatState: ChatState = {
  messages: [],
  isLoading: false,
  isCompleted: false,
  currentQuestion: "",
  uploadedFiles: [],
  isUploading: false,
  filesContent: {},
  taskSummary: "",
  userPrompt: "",
  showUpgradePrompt: null,
  pendingQuestion: "",
  isUseDeepResearch: false,
};

export const useChatState = (initialState?: Partial<ChatState>): UseChatStateReturn => {
  const [messages, setMessages] = useState<Message[]>(initialState?.messages || initialChatState.messages);
  const [isLoading, setIsLoading] = useState<boolean>(initialState?.isLoading || initialChatState.isLoading);
  const [isCompleted, setIsCompleted] = useState<boolean>(initialState?.isCompleted || initialChatState.isCompleted);
  const [currentQuestion, setCurrentQuestion] = useState<string>(initialState?.currentQuestion || initialChatState.currentQuestion);
  const [uploadedFiles, setUploadedFiles] = useState<string[]>(initialState?.uploadedFiles || initialChatState.uploadedFiles);
  const [isUploading, setIsUploading] = useState<boolean>(initialState?.isUploading || initialChatState.isUploading);
  const [filesContent, setFilesContent] = useState<{ [key: string]: string }>(initialState?.filesContent || initialChatState.filesContent);
  const [taskSummary, setTaskSummary] = useState<string>(initialState?.taskSummary || initialChatState.taskSummary);
  const [userPrompt, setUserPrompt] = useState<string>(initialState?.userPrompt || initialChatState.userPrompt);
  const [showUpgradePrompt, setShowUpgradePrompt] = useState<"success" | "error" | "timeout" | null>(initialState?.showUpgradePrompt || initialChatState.showUpgradePrompt);
  const [pendingQuestion, setPendingQuestion] = useState<string>(initialState?.pendingQuestion || initialChatState.pendingQuestion);
  const [isUseDeepResearch, setIsUseDeepResearch] = useState<boolean>(initialState?.isUseDeepResearch || initialChatState.isUseDeepResearch);

  const addMessage = useCallback((message: Message) => {
    setMessages(prev => [...prev, message]);
  }, []);

  const updateLastMessage = useCallback((updater: (lastMessage: Message) => Message) => {
    setMessages(prev => {
      if (prev.length === 0) return prev;
      const newMessages = [...prev];
      newMessages[newMessages.length - 1] = updater(newMessages[newMessages.length - 1]);
      return newMessages;
    });
  }, []);

  const addUploadedFile = useCallback((filePath: string) => {
    setUploadedFiles(prev => [...prev, filePath]);
  }, []);

  const setFileContent = useCallback((filePath: string, content: string) => {
    setFilesContent(prev => ({ ...prev, [filePath]: content }));
  }, []);

  const resetChatState = useCallback((initialMessages: Message[] = []) => {
    setMessages(initialMessages);
    setIsLoading(false);
    setIsCompleted(false);
    setCurrentQuestion("");
    setUploadedFiles([]);
    setIsUploading(false);
    setFilesContent({});
    setTaskSummary("");
    setUserPrompt("");
    setShowUpgradePrompt(null);
    setPendingQuestion("");
    // isUseDeepResearch is often a user preference, might not reset it here or make it optional
  }, []);

  return {
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
  };
};
