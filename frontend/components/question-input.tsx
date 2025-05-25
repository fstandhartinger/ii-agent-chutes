import { motion } from "framer-motion";
import { ArrowUp, Loader2, Paperclip } from "lucide-react";
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
  const [textareaHeight, setTextareaHeight] = useState<number>(50);
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
      
      // Set minimum height to 50px and maximum to 200px
      const minHeight = 50;
      const maxHeight = 200;
      const newHeight = Math.min(Math.max(scrollHeight, minHeight), maxHeight);
      
      setTextareaHeight(newHeight);
      textarea.style.height = `${newHeight}px`;
      
      // Enable/disable scrolling based on whether we've hit the max height
      if (scrollHeight > maxHeight) {
        textarea.style.overflowY = 'auto';
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
      className={`w-full max-w-2xl z-50 ${className}`}
    >
      <motion.div
        className="relative rounded-xl"
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.1 }}
      >
        {files.length > 0 && (
          <div className="absolute top-4 left-4 right-2 flex items-center overflow-auto gap-2 z-10">
            {files.map((file) => {
              if (file.isImage && file.preview) {
                return (
                  <div key={file.name} className="relative">
                    <div className="w-20 h-20 rounded-xl overflow-hidden">
                      <img
                        src={file.preview}
                        alt={file.name}
                        className="w-full h-full object-cover"
                      />
                    </div>
                    {file.loading && (
                      <div className="absolute inset-0 flex items-center justify-center bg-black/30 rounded-xl">
                        <Loader2 className="size-5 text-white animate-spin" />
                      </div>
                    )}
                  </div>
                );
              }

              const { IconComponent, bgColor, label } = getFileIconAndColor(
                file.name
              );

              return (
                <div
                  key={file.name}
                  className="flex items-center gap-2 bg-neutral-900 text-white rounded-full px-3 py-2 border border-gray-700 shadow-sm"
                >
                  <div
                    className={`flex items-center justify-center w-10 h-10 ${bgColor} rounded-full`}
                  >
                    {isUploading ? (
                      <Loader2 className="size-5 text-white animate-spin" />
                    ) : (
                      <IconComponent className="size-5 text-white" />
                    )}
                  </div>
                  <div className="flex flex-col">
                    <span className="text-sm font-medium truncate max-w-[200px]">
                      {file.name}
                    </span>
                    <span className="text-xs text-gray-500">{label}</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
        <Textarea
          ref={textareaRef}
          className={`w-full p-4 pb-[72px] rounded-xl !text-lg focus:ring-0 resize-none !placeholder-gray-400 !bg-[#27282b] border-[#3a3b3f] shadow-lg ${
            files.length > 0 ? "pt-24" : ""
          } ${textareaClassName}`}
          style={{ 
            height: `${textareaHeight}px`,
            minHeight: '50px',
            maxHeight: '200px'
          }}
          placeholder={
            placeholder ||
            "What can I help you with today?"
          }
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          onPaste={handlePaste}
        />
        <div className="flex justify-between items-center absolute bottom-0 py-4 m-px w-[calc(100%-4px)] rounded-b-xl bg-[#27282b] px-4">
          <div className="flex items-center gap-x-3">
            {handleFileUpload && (
              <label htmlFor="file-upload" className="cursor-pointer">
                <Button
                  variant="ghost"
                  size="icon"
                  className="hover:bg-gray-700/50 size-10 rounded-full cursor-pointer border border-[#3a3b3f] shadow-sm"
                  onClick={() =>
                    document.getElementById("file-upload")?.click()
                  }
                  disabled={isUploading}
                >
                  {isUploading ? (
                    <Loader2 className="size-5 text-gray-400 animate-spin" />
                  ) : (
                    <Paperclip className="size-5 text-gray-400" />
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
                className={`h-10 cursor-pointer shadow-sm ${
                  isUseDeepResearch
                    ? "bg-gradient-skyblue-lavender !text-black"
                    : "border !border-[#3a3b3f] bg-transparent"
                }`}
                onClick={() => setIsUseDeepResearch?.(!isUseDeepResearch)}
              >
                Deep Research
              </Button>
            )}
          </div>

          <Button
            disabled={!isButtonEnabled}
            onClick={() => handleSubmit(value)}
            className={`border-none p-4 size-10 font-bold rounded-full transition-transform shadow-lg ${
              !isButtonEnabled 
                ? "cursor-not-allowed opacity-50 bg-gray-500" 
                : "cursor-pointer bg-gradient-skyblue-lavender hover:scale-105 active:scale-95"
            }`}
          >
            <ArrowUp className="size-5" />
          </Button>
        </div>
      </motion.div>
    </motion.div>
  );
};

export default QuestionInput;
