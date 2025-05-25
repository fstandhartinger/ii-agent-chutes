import { motion } from "framer-motion";
import { ArrowUp, Loader2, Paperclip, Sparkles } from "lucide-react";
import { Button } from "./ui/button";
import { Textarea } from "./ui/textarea";
import { useState, useEffect, useRef } from "react";
import { getFileIconAndColor } from "@/utils/file-utils";

interface FileUploadStatus {
  name: string;
  loading: boolean;
  error?: string;
  preview?: string; // Add preview URL for images
  isImage: boolean; // Flag to identify image files
}

interface QuestionInputProps {
  className?: string;
  textareaClassName?: string;
  placeholder?: string;
  value: string;
  setValue: (value: string) => void;
  handleKeyDown: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void;
  handleSubmit: (question: string) => void;
  handleFileUpload?: (e: React.ChangeEvent<HTMLInputElement>) => void;
  isUploading?: boolean;
  isUseDeepResearch?: boolean;
  setIsUseDeepResearch?: (value: boolean) => void;
  isDisabled?: boolean;
}

const QuestionInput = ({
  className,
  textareaClassName,
  placeholder,
  value,
  setValue,
  handleKeyDown,
  handleSubmit,
  handleFileUpload,
  isUploading = false,
  isUseDeepResearch = false,
  setIsUseDeepResearch,
  isDisabled,
}: QuestionInputProps) => {
  const [files, setFiles] = useState<FileUploadStatus[]>([]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [textareaHeight, setTextareaHeight] = useState<number>(60);
  const [isButtonEnabled, setIsButtonEnabled] = useState<boolean>(false);

  // Clean up object URLs when component unmounts
  useEffect(() => {
    return () => {
      files.forEach((file) => {
        if (file.preview) URL.revokeObjectURL(file.preview);
      });
    };
  }, [files]);

  // Auto-resize textarea based on content and update button state
  useEffect(() => {
    if (textareaRef.current) {
      const textarea = textareaRef.current;
      // Reset height to auto to get the correct scrollHeight
      textarea.style.height = 'auto';
      const scrollHeight = textarea.scrollHeight;
      
      // Set minimum height to 60px and maximum to 200px
      const minHeight = 60;
      const maxHeight = 200;
      const newHeight = Math.min(Math.max(scrollHeight, minHeight), maxHeight);
      
      setTextareaHeight(newHeight);
      textarea.style.height = `${newHeight}px`;
      
      // Enable/disable scrolling based on whether we've hit the max height
      if (scrollHeight > maxHeight) {
        textarea.style.overflowY = 'auto';
        // Ensure cursor is visible when scrolling is enabled
        setTimeout(() => {
          textarea.scrollTop = textarea.scrollHeight;
        }, 0);
      } else {
        textarea.style.overflowY = 'hidden';
      }
    }
    
    // Update button enabled state
    setIsButtonEnabled(!!value.trim() && !isDisabled);
  }, [value, isDisabled]);

  const isImageFile = (fileName: string): boolean => {
    const ext = fileName.split(".").pop()?.toLowerCase() || "";
    return ["jpg", "jpeg", "png", "gif", "webp", "bmp", "heic", "svg"].includes(
      ext
    );
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || !handleFileUpload) return;

    // Create file status objects
    const newFiles = Array.from(e.target.files).map((file) => {
      const isImage = isImageFile(file.name);
      const preview = isImage ? URL.createObjectURL(file) : undefined;

      return {
        name: file.name,
        loading: true,
        isImage,
        preview,
      };
    });

    setFiles((prev) => [...prev, ...newFiles]);

    // Call the parent handler
    handleFileUpload(e);

    // After a delay, mark files as not loading (this would ideally be handled by the parent)
    setTimeout(() => {
      setFiles((prev) => prev.map((file) => ({ ...file, loading: false })));
    }, 5000);
  };

  // Handle clipboard paste events (CTRL+V)
  const handlePaste = async (e: React.ClipboardEvent) => {
    if (!handleFileUpload || isUploading) return;
    
    const clipboardItems = e.clipboardData.items;
    const imageItems = Array.from(clipboardItems).filter(item => 
      item.type.indexOf('image') !== -1
    );
    
    if (imageItems.length === 0) return; // No images in clipboard
    
    e.preventDefault(); // Prevent the default paste behavior for images
    
    // Process pasted images
    const files: File[] = [];
    
    for (const item of imageItems) {
      const blob = item.getAsFile();
      if (!blob) continue;
      
      // Create a file with a meaningful name from the blob
      const timestamp = new Date().toISOString().replace(/[-:.]/g, '');
      const extension = blob.type.split('/')[1] || 'png';
      const fileName = `pasted_image_${timestamp}.${extension}`;
      
      // Create a new file with the generated name
      const file = new File([blob], fileName, { type: blob.type });
      files.push(file);
      
      // Create preview
      const preview = URL.createObjectURL(blob);
      
      // Add to files state immediately for visual feedback
      setFiles(prev => [...prev, {
        name: fileName,
        loading: true,
        isImage: true,
        preview
      }]);
    }
    
    if (files.length > 0) {
      // Create a fake event to reuse the existing file upload handler
      const dataTransfer = new DataTransfer();
      files.forEach(file => dataTransfer.items.add(file));
      
      const fakeEvent = {
        target: {
          files: dataTransfer.files
        }
      } as unknown as React.ChangeEvent<HTMLInputElement>;
      
      // Call the parent handler
      handleFileUpload(fakeEvent);
      
      // After a delay, mark files as not loading
      setTimeout(() => {
        setFiles((prev) => prev.map((file) => ({ ...file, loading: false })));
      }, 5000);
    }
  };

  return (
    <motion.div
      key="input-view"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.95, y: -10 }}
      transition={{
        type: "spring",
        stiffness: 300,
        damping: 30,
        mass: 1,
      }}
      className={`w-full max-w-4xl z-50 ${className}`}
    >
      <motion.div
        className="relative"
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.1 }}
      >
        {/* File Previews */}
        {files.length > 0 && (
          <motion.div 
            className="mb-4 flex flex-wrap gap-3"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            transition={{ duration: 0.3 }}
          >
            {files.map((file, index) => {
              if (file.isImage && file.preview) {
                return (
                  <motion.div 
                    key={file.name}
                    className="relative group"
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: index * 0.1 }}
                  >
                    <div className="w-20 h-20 rounded-xl overflow-hidden bg-glass border border-white/20 shadow-lg">
                      <img
                        src={file.preview}
                        alt={file.name}
                        className="w-full h-full object-cover"
                      />
                    </div>
                    {file.loading && (
                      <div className="absolute inset-0 flex items-center justify-center bg-black/50 rounded-xl backdrop-blur-sm">
                        <Loader2 className="w-5 h-5 text-white animate-spin" />
                      </div>
                    )}
                    <div className="absolute -top-2 -right-2 w-6 h-6 bg-blue-500 rounded-full flex items-center justify-center">
                      <Sparkles className="w-3 h-3 text-white" />
                    </div>
                  </motion.div>
                );
              }

              const { IconComponent, bgColor, label } = getFileIconAndColor(
                file.name
              );

              return (
                <motion.div
                  key={file.name}
                  className="flex items-center gap-3 bg-glass border border-white/20 rounded-xl px-4 py-3 shadow-lg backdrop-blur-sm"
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: index * 0.1 }}
                >
                  <div
                    className={`flex items-center justify-center w-10 h-10 ${bgColor} rounded-lg shadow-sm`}
                  >
                    {isUploading ? (
                      <Loader2 className="w-5 h-5 text-white animate-spin" />
                    ) : (
                      <IconComponent className="w-5 h-5 text-white" />
                    )}
                  </div>
                  <div className="flex flex-col min-w-0">
                    <span className="text-sm font-medium text-white truncate max-w-[150px]">
                      {file.name}
                    </span>
                    <span className="text-xs text-muted-foreground">{label}</span>
                  </div>
                </motion.div>
              );
            })}
          </motion.div>
        )}

        {/* Input Container */}
        <div className="relative bg-glass border border-white/20 rounded-2xl shadow-2xl backdrop-blur-xl overflow-hidden">
          {/* Gradient Border Effect */}
          <div className="absolute inset-0 bg-gradient-to-r from-blue-500/20 via-purple-500/20 to-emerald-500/20 rounded-2xl blur-sm opacity-50" />
          
          <div className="relative bg-black/20 rounded-2xl">
            <Textarea
              ref={textareaRef}
              className={`w-full p-6 pb-20 bg-transparent border-0 text-lg placeholder:text-muted-foreground/70 focus:ring-0 resize-none text-white ${textareaClassName}`}
              style={{ 
                height: `${textareaHeight}px`,
                minHeight: '60px',
                maxHeight: '200px'
              }}
              placeholder={placeholder || "What can I help you with today?"}
              value={value}
              onChange={(e) => setValue(e.target.value)}
              onKeyDown={handleKeyDown}
              onPaste={handlePaste}
            />
            
            {/* Bottom Controls */}
            <div className="absolute bottom-0 left-0 right-0 flex justify-between items-center p-4 bg-transparent">
              <div className="flex items-center gap-3">
                {handleFileUpload && (
                  <label htmlFor="file-upload" className="cursor-pointer">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="bg-glass border border-white/20 hover:bg-white/10 w-11 h-11 rounded-xl transition-all-smooth hover-lift shadow-lg"
                      onClick={() =>
                        document.getElementById("file-upload")?.click()
                      }
                      disabled={isUploading}
                    >
                      {isUploading ? (
                        <Loader2 className="w-5 h-5 text-muted-foreground animate-spin" />
                      ) : (
                        <Paperclip className="w-5 h-5 text-muted-foreground" />
                      )}
                    </Button>
                    <input
                      id="file-upload"
                      type="file"
                      multiple
                      className="hidden"
                      onChange={handleFileChange}
                      disabled={isUploading}
                    />
                  </label>
                )}
                
                {setIsUseDeepResearch && (
                  <Button
                    variant="outline"
                    size="sm"
                    className={`transition-all-smooth hover-lift shadow-lg ${
                      isUseDeepResearch
                        ? "bg-gradient-skyblue-lavender text-black border-0 shadow-glow"
                        : "bg-glass border-white/20 hover:bg-white/10 text-white"
                    }`}
                    onClick={() => setIsUseDeepResearch?.(!isUseDeepResearch)}
                  >
                    <Sparkles className="w-4 h-4 mr-2" />
                    Deep Research
                  </Button>
                )}
              </div>

              <Button
                disabled={!isButtonEnabled}
                onClick={() => handleSubmit(value)}
                className={`border-0 p-3 w-12 h-12 font-bold rounded-xl transition-all-smooth shadow-lg ${
                  !isButtonEnabled 
                    ? "cursor-not-allowed opacity-50 bg-muted" 
                    : "cursor-pointer bg-gradient-skyblue-lavender hover:scale-105 active:scale-95 shadow-glow hover-lift text-black"
                }`}
              >
                <ArrowUp className="w-5 h-5" />
              </Button>
            </div>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
};

export default QuestionInput;
