"use client";

import { motion } from "framer-motion";
import { Check, Copy, Download } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import jsPDF from 'jspdf';

import Action from "@/components/action";
import Markdown from "@/components/markdown";
import QuestionInput from "@/components/question-input";
import { ActionStep, Message } from "@/typings/agent";
import { getFileIconAndColor } from "@/utils/file-utils";
import { Button } from "@/components/ui/button";

interface ChatMessageProps {
  messages: Message[];
  isLoading: boolean;
  isCompleted: boolean;
  workspaceInfo: string;
  isUploading: boolean;
  isUseDeepResearch: boolean;
  isReplayMode: boolean;
  currentQuestion: string;
  messagesEndRef: React.RefObject<HTMLDivElement | null>;
  handleClickAction: (
    action: ActionStep | undefined,
    isReplay?: boolean
  ) => void;
  setCurrentQuestion: (question: string) => void;
  handleKeyDown: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void;
  handleQuestionSubmit: (question: string) => void;
  handleFileUpload: (e: React.ChangeEvent<HTMLInputElement>) => void;
  handleStopAgent?: () => void;
}

const ChatMessage = ({
  messages,
  isLoading,
  isCompleted,
  workspaceInfo,
  isUploading,
  isUseDeepResearch,
  currentQuestion,
  messagesEndRef,
  handleClickAction,
  setCurrentQuestion,
  handleKeyDown,
  handleQuestionSubmit,
  handleFileUpload,
  handleStopAgent,
}: ChatMessageProps) => {
  const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null);

  const copyToClipboard = async (text: string, messageId: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedMessageId(messageId);
      toast.success("Copied to clipboard");
      setTimeout(() => setCopiedMessageId(null), 2000);
    } catch {
      toast.error("Failed to copy to clipboard");
    }
  };

  const downloadMessageAsPDF = (content: string, messageId: string) => {
    try {
      const pdf = new jsPDF();
      
      // Set font and add title
      pdf.setFontSize(16);
      pdf.text('Chat Message', 20, 20);
      
      // Add timestamp
      pdf.setFontSize(10);
      pdf.text(`Generated: ${new Date().toLocaleString()}`, 20, 30);
      
      // Add content with text wrapping
      pdf.setFontSize(12);
      const splitText = pdf.splitTextToSize(content, 170);
      pdf.text(splitText, 20, 45);
      
      // Save the PDF
      pdf.save(`message-${messageId}.pdf`);
      toast.success("PDF downloaded successfully");
    } catch (error) {
      console.error("Error generating PDF:", error);
      toast.error("Failed to generate PDF");
    }
  };

  return (
    <div className="flex flex-col h-full bg-glass-dark rounded-2xl border border-white/10 overflow-hidden mobile-chat-panel">
      {/* Messages Container */}
      <motion.div
        className="flex-1 p-4 md:p-6 overflow-y-auto space-y-4 md:space-y-6 mobile-chat-messages chat-messages-container mobile-messages-container"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2, duration: 0.3 }}
      >
        {messages.map((message, index) => (
          <motion.div
            key={message.id}
            className="flex flex-col gap-3"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.05 * index, duration: 0.4 }}
          >
            {/* Message Content */}
            <div className="flex-1 min-w-0 relative group">
              {/* File Attachments */}
              {message.files && message.files.length > 0 && (
                <div className="flex flex-wrap gap-2 mb-3">
                  {message.files.map((fileName, fileIndex) => {
                    const isImage = fileName.match(/\.(jpeg|jpg|gif|png|webp|svg|heic|bmp)$/i) !== null;

                    if (isImage && message.fileContents && message.fileContents[fileName]) {
                      return (
                        <motion.div
                          key={`${message.id}-file-${fileIndex}`}
                          className="relative group"
                          initial={{ opacity: 0, scale: 0.8 }}
                          animate={{ opacity: 1, scale: 1 }}
                          transition={{ delay: 0.1 * fileIndex }}
                        >
                          <div className="w-32 h-32 md:w-40 md:h-40 rounded-xl overflow-hidden bg-glass border border-white/20 shadow-lg">
                            <img
                              src={message.fileContents[fileName]}
                              alt={fileName}
                              className="w-full h-full object-cover"
                            />
                          </div>
                          <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-all-smooth rounded-xl" />
                          {/* Copy button for image */}
                          <Button
                            variant="ghost"
                            size="sm"
                            className={`absolute top-1 right-1 z-10 bg-black/50 hover:bg-black/70 border border-white/20 p-1 h-6 w-6 rounded-md transition-all-smooth hover-lift ${
                              index === messages.length - 1 
                                ? 'opacity-70 hover:opacity-100' 
                                : 'opacity-0 group-hover:opacity-70 hover:!opacity-100'
                            }`}
                            onClick={() => copyToClipboard(fileName, `${message.id}-file-${fileIndex}`)}
                            title="Copy filename"
                          >
                            {copiedMessageId === `${message.id}-file-${fileIndex}` ? (
                              <Check className="w-3 h-3 text-green-400" />
                            ) : (
                              <Copy className="w-3 h-3 text-white/80" />
                            )}
                          </Button>
                        </motion.div>
                      );
                    }

                    const { IconComponent, bgColor, label } = getFileIconAndColor(fileName);

                    return (
                      <motion.div
                        key={`${message.id}-file-${fileIndex}`}
                        className="relative flex items-center gap-3 bg-glass border border-white/20 rounded-xl px-3 py-2 shadow-lg backdrop-blur-sm max-w-xs"
                        initial={{ opacity: 0, scale: 0.8 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ delay: 0.1 * fileIndex }}
                      >
                        <div className={`flex items-center justify-center w-8 h-8 ${bgColor} rounded-lg shadow-sm`}>
                          <IconComponent className="w-4 h-4 text-white" />
                        </div>
                        <div className="flex flex-col min-w-0 pr-6">
                          <span className="text-sm font-medium text-white truncate">
                            {fileName}
                          </span>
                          <span className="text-xs text-muted-foreground">{label}</span>
                        </div>
                        {/* Copy button for file */}
                        <Button
                          variant="ghost"
                          size="sm"
                          className={`absolute top-1 right-1 z-10 bg-black/30 hover:bg-black/50 border border-white/20 p-1 h-6 w-6 rounded-md transition-all-smooth hover-lift ${
                            index === messages.length - 1 
                              ? 'opacity-70 hover:opacity-100' 
                              : 'opacity-0 group-hover:opacity-70 hover:!opacity-100'
                          }`}
                          onClick={() => copyToClipboard(fileName, `${message.id}-file-${fileIndex}`)}
                          title="Copy filename"
                        >
                          {copiedMessageId === `${message.id}-file-${fileIndex}` ? (
                            <Check className="w-3 h-3 text-green-400" />
                          ) : (
                            <Copy className="w-3 h-3 text-white/80" />
                          )}
                        </Button>
                      </motion.div>
                    );
                  })}
                </div>
              )}

              {/* Text Content */}
              {message.content && (
                <motion.div
                  className={`relative ${
                    message.role === "user"
                      ? "flex justify-end"
                      : "flex justify-start"
                  }`}
                  initial={{ scale: 0.95, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  transition={{
                    type: "spring",
                    stiffness: 400,
                    damping: 25,
                    delay: 0.1
                  }}
                >
                  <div
                    className={`relative max-w-full md:max-w-[85%] ${
                      message.role === "user"
                        ? "bg-gradient-to-br from-blue-500/20 to-purple-500/20 backdrop-blur-sm border border-blue-500/30 rounded-2xl p-3 md:p-4 text-white shadow-lg"
                        : "text-white"
                    }`}
                  >
                    {/* Button container - positioned absolutely to overlay content */}
                    <div className={`absolute top-1 right-1 z-10 flex gap-1 ${
                      index === messages.length - 1 
                        ? 'opacity-100' 
                        : 'opacity-0 group-hover:opacity-100'
                    } transition-opacity duration-200`}>
                      {/* PDF Download Button - Only for long messages */}
                      {message.content && message.content.length > 500 && (
                        <Button
                          variant="ghost"
                          size="sm"
                          className="bg-black/50 hover:bg-black/70 border border-white/20 p-1 h-6 w-6 rounded-md transition-all-smooth hover-lift"
                          onClick={() => downloadMessageAsPDF(message.content || "", message.id)}
                          title="Download as PDF"
                        >
                          <Download className="w-3 h-3 text-white/80" />
                        </Button>
                      )}
                      
                      {/* Copy Button */}
                      <Button
                        variant="ghost"
                        size="sm"
                        className="bg-black/50 hover:bg-black/70 border border-white/20 p-1 h-6 w-6 rounded-md transition-all-smooth hover-lift"
                        onClick={() => copyToClipboard(message.content || "", message.id)}
                        title="Copy message"
                      >
                        {copiedMessageId === message.id ? (
                          <Check className="w-3 h-3 text-green-400" />
                        ) : (
                          <Copy className="w-3 h-3 text-white/80" />
                        )}
                      </Button>
                    </div>

                    {message.role === "user" ? (
                      <div className="text-sm md:text-base leading-relaxed">
                        {message.content}
                      </div>
                    ) : (
                      <div className="prose prose-invert prose-sm md:prose-base max-w-none">
                        <Markdown>{message.content}</Markdown>
                      </div>
                    )}
                  </div>
                </motion.div>
              )}

              {/* Action Component */}
              {message.action && (
                <motion.div
                  className="mt-3"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2, duration: 0.3 }}
                >
                  <Action
                    workspaceInfo={workspaceInfo}
                    type={message.action.type}
                    value={message.action.data}
                    onClick={() => handleClickAction(message.action, true)}
                  />
                </motion.div>
              )}
            </div>
          </motion.div>
        ))}

        {/* Loading Indicator */}
        {isLoading && (
          <motion.div
            className="flex gap-3 md:gap-4"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{
              type: "spring",
              stiffness: 300,
              damping: 30,
            }}
          >
            <motion.div
              className="flex-1 bg-glass border border-white/20 rounded-2xl p-3 md:p-4 backdrop-blur-sm shadow-lg"
              initial={{ scale: 0.95 }}
              animate={{ scale: 1 }}
              transition={{
                type: "spring",
                stiffness: 400,
                damping: 25,
              }}
            >
              <div className="flex items-center gap-3">
                <div className="flex space-x-2">
                  <div className="w-2 h-2 bg-blue-400 rounded-full animate-[dot-bounce_1.2s_ease-in-out_infinite_0ms]" />
                  <div className="w-2 h-2 bg-purple-400 rounded-full animate-[dot-bounce_1.2s_ease-in-out_infinite_200ms]" />
                  <div className="w-2 h-2 bg-emerald-400 rounded-full animate-[dot-bounce_1.2s_ease-in-out_infinite_400ms]" />
                </div>
                <span className="text-sm text-muted-foreground">fubea is thinking...</span>
              </div>
            </motion.div>
          </motion.div>
        )}

        {/* Completion Indicator */}
        {isCompleted && (
          <motion.div
            className="flex items-center gap-3 bg-gradient-to-r from-emerald-500/20 to-green-500/20 border border-emerald-500/30 rounded-2xl p-3 md:p-4 backdrop-blur-sm shadow-lg"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.3 }}
          >
            <div className="w-8 h-8 bg-emerald-500 rounded-full flex items-center justify-center shadow-lg">
              <Check className="w-4 h-4 text-white" />
            </div>
            <span className="text-emerald-400 font-medium text-sm md:text-base">
              fubea has completed the current task.
            </span>
          </motion.div>
        )}

        <div ref={messagesEndRef} />
      </motion.div>

      {/* Input Section */}
      <motion.div
        className="border-t border-white/10 bg-black/20 backdrop-blur-sm mobile-input-section"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4, duration: 0.3 }}
      >
        <QuestionInput
          className="p-3 md:p-4 w-full max-w-none"
          textareaClassName="text-sm md:text-base"
          placeholder="Ask me anything..."
          value={currentQuestion}
          setValue={setCurrentQuestion}
          handleKeyDown={handleKeyDown}
          handleSubmit={handleQuestionSubmit}
          handleFileUpload={handleFileUpload}
          isUploading={isUploading}
          isUseDeepResearch={isUseDeepResearch}
          isLoading={isLoading}
          handleStopAgent={handleStopAgent}
        />
      </motion.div>
    </div>
  );
};

export default ChatMessage;