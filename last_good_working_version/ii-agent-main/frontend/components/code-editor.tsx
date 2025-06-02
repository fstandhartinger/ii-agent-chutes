"use client";

import type { editor } from "monaco-editor";
import { Editor, Monaco } from "@monaco-editor/react";
import {
  ChevronDown,
  ChevronRight,
  File,
  Folder,
  ChevronRight as ChevronRightIcon,
  Download,
} from "lucide-react";
import { useRef, useState, useEffect } from "react";
import { ActionStep, TAB } from "@/typings/agent";
import { Button } from "./ui/button";

const ROOT_NAME = "fubea";

// Map file extensions to Monaco editor language IDs
const languageMap: { [key: string]: string } = {
  ts: "typescript",
  tsx: "typescript",
  js: "javascript",
  jsx: "javascript",
  json: "json",
  md: "markdown",
  css: "css",
  scss: "scss",
  less: "less",
  html: "html",
  xml: "xml",
  yaml: "yaml",
  yml: "yaml",
  py: "python",
  rb: "ruby",
  php: "php",
  java: "java",
  cpp: "cpp",
  c: "c",
  cs: "csharp",
  go: "go",
  rs: "rust",
  swift: "swift",
  kt: "kotlin",
  sql: "sql",
  sh: "shell",
  bash: "shell",
  dockerfile: "dockerfile",
  vue: "vue",
  svelte: "svelte",
  graphql: "graphql",
  env: "plaintext",
};

interface FileStructure {
  name: string;
  type: "file" | "folder";
  children?: FileStructure[];
  language?: string;
  value?: string;
  path: string;
}

interface CodeEditorProps {
  className?: string;
  currentActionData?: ActionStep;
  workspaceInfo?: string;
  activeFile?: string;
  setActiveFile?: (file: string) => void;
  filesContent?: { [filename: string]: string };
  isReplayMode?: boolean;
  activeTab?: TAB;
}

const CodeEditor = ({
  className,
  currentActionData,
  workspaceInfo,
  activeFile,
  setActiveFile,
  filesContent,
  isReplayMode,
  activeTab,
}: CodeEditorProps) => {
  const [activeLanguage, setActiveLanguage] = useState<string>("plaintext");
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(
    new Set()
  );
  const [fileStructure, setFileStructure] = useState<FileStructure[]>([]);
  const editorRef = useRef<editor.IStandaloneCodeEditor | null>(null);
  const monacoRef = useRef<Monaco | null>(null);
  const [fileContent, setFileContent] = useState<string>("");

  const getFileLanguage = (fileName: string): string => {
    const extension = fileName.split(".").pop()?.toLowerCase() || "";
    // Handle special case for files like "Dockerfile"
    if (fileName.toLowerCase() === "dockerfile") {
      return languageMap["dockerfile"];
    }
    return languageMap[extension] || "plaintext";
  };

  const loadDirectory = async (path: string) => {
    try {
      console.log(`[FILE_BROWSER] Loading directory from path: ${path}`);
      const response = await fetch("/api/files", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ path }),
      });

      if (!response.ok) {
        console.error(`[FILE_BROWSER] Failed to load directory, status: ${response.status} ${response.statusText}`);
        throw new Error(`Failed to load directory: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      console.log(`[FILE_BROWSER] Directory loaded with ${data.files?.length || 0} items`);
      setFileStructure(data.files);
      setExpandedFolders(new Set([path]));
    } catch (error) {
      console.error("[FILE_BROWSER] Error loading directory:", error);
    }
  };

  const loadFileContent = async (filePath: string) => {
    try {
      console.log(`[FILE_BROWSER] Loading file content from path: ${filePath}`);
      const response = await fetch("/api/files/content", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ path: filePath }),
      });

      if (!response.ok) {
        console.error(`[FILE_BROWSER] Failed to load file content, status: ${response.status} ${response.statusText}`);
        throw new Error(`Failed to load file content: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      console.log(`[FILE_BROWSER] File content loaded successfully, length: ${data.content?.length || 0} characters`);
      return data.content;
    } catch (error) {
      console.error("[FILE_BROWSER] Error loading file:", error);
      return "";
    }
  };

  useEffect(() => {
    if (workspaceInfo && activeTab === TAB.CODE) {
      console.log(`[FILE_BROWSER] Workspace info detected, loading directory: ${workspaceInfo}`);
      loadDirectory(workspaceInfo);
    } else {
      console.log(`[FILE_BROWSER] Not loading directory - workspaceInfo: ${Boolean(workspaceInfo)}, activeTab: ${activeTab}, TAB.CODE: ${TAB.CODE}`);
    }
  }, [currentActionData, workspaceInfo, activeTab]);

  const toggleFolder = (folderPath: string) => {
    setExpandedFolders((prev) => {
      const next = new Set(prev);
      if (next.has(folderPath)) {
        next.delete(folderPath);
      } else {
        next.add(folderPath);
      }
      return next;
    });
  };

  const renderBreadcrumb = () => {
    if (!activeFile || !workspaceInfo) return null;

    const relativePath = activeFile.replace(workspaceInfo, "");
    const parts = relativePath.split("/").filter(Boolean);
    const fileName = parts[parts.length - 1];
    const folderName = ROOT_NAME;

    return (
      <div className="flex items-center gap-2 px-2 py-1 text-sm text-neutral-400 border-b border-neutral-700">
        <span className="text-neutral-400">{folderName}</span>
        <ChevronRightIcon className="h-4 w-4" />
        <span className="text-white">{fileName}</span>
      </div>
    );
  };

  useEffect(() => {
    (async () => {
      if (activeFile && workspaceInfo) {
        const filePath = activeFile.startsWith(workspaceInfo)
          ? activeFile
          : `${workspaceInfo}/${activeFile}`;
        // If we are in replay mode, use the file content from the filesContent prop
        if (isReplayMode) {
          const content = filesContent?.[filePath] || "";
          setActiveLanguage(getFileLanguage(filePath));
          setFileContent(content);
          return;
        }

        setActiveLanguage(getFileLanguage(filePath));
        const content = await loadFileContent(filePath);
        setFileContent(content);
      }
    })();
  }, [
    activeFile,
    workspaceInfo,
    filesContent,
    currentActionData,
    isReplayMode,
  ]);

  const downloadFile = async (filePath: string) => {
    try {
      const response = await fetch("/api/files/download", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ path: filePath }),
      });

      if (!response.ok) {
        throw new Error("Failed to download file");
      }

      // Create a blob from the response
      const blob = await response.blob();
      
      // Get filename from the path
      const filename = filePath.split('/').pop() || 'download';
      
      // Create download link
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error("Error downloading file:", error);
    }
  };

  const downloadFolderAsZip = async (folderPath: string) => {
    try {
      const response = await fetch("/api/files/download-zip", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ path: folderPath }),
      });

      if (!response.ok) {
        throw new Error("Failed to download folder as zip");
      }

      // Create a blob from the response
      const blob = await response.blob();
      
      // Get folder name from the path
      const folderName = folderPath.split('/').pop() || 'download';
      const filename = `${folderName}.zip`;
      
      // Create download link
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error("Error downloading folder as zip:", error);
    }
  };

  const renderFileTree = (items: FileStructure[]) => {
    // Sort items: folders first, then files, both in alphabetical order
    const sortedItems = [...items].sort((a, b) => {
      if (a.type === b.type) {
        // If both are folders or both are files, sort alphabetically
        return a.name.toLowerCase().localeCompare(b.name.toLowerCase());
      }
      // Folders come before files
      return a.type === "folder" ? -1 : 1;
    });

    return sortedItems.map((item) => {
      const fullPath = item.path;

      if (item.type === "folder") {
        const isExpanded = expandedFolders.has(fullPath);
        return (
          <div key={fullPath}>
            <div className="flex items-center justify-between group hover:bg-neutral-700">
              <button
                className="flex items-center gap-2 flex-1 px-2 py-1 text-left text-sm"
                onClick={() => toggleFolder(fullPath)}
              >
                {isExpanded ? (
                  <ChevronDown className="h-4 w-4" />
                ) : (
                  <ChevronRight className="h-4 w-4" />
                )}
                <Folder className="h-4 w-4" />
                {item.name}
              </button>
              <Button
                variant="ghost"
                size="sm"
                className="opacity-0 group-hover:opacity-100 transition-opacity p-1 h-6 w-6 mr-1"
                onClick={(e) => {
                  e.stopPropagation();
                  downloadFolderAsZip(fullPath);
                }}
                title="Download as ZIP"
              >
                <Download className="h-3 w-3" />
              </Button>
            </div>
            {isExpanded && item.children && (
              <div className="ml-4">{renderFileTree(item.children)}</div>
            )}
          </div>
        );
      }

      return (
        <div key={fullPath} className="flex items-center justify-between group hover:bg-neutral-700">
          <button
            className={`flex items-center gap-2 flex-1 px-2 py-1 text-left text-sm ${
              activeFile === fullPath
                ? "bg-neutral-700 text-white"
                : "text-neutral-400"
            }`}
            onClick={() => {
              setActiveFile?.(fullPath);
            }}
          >
            <File className="h-4 w-4" />
            {item.name}
          </button>
          <Button
            variant="ghost"
            size="sm"
            className="opacity-0 group-hover:opacity-100 transition-opacity p-1 h-6 w-6 mr-1"
            onClick={(e) => {
              e.stopPropagation();
              downloadFile(fullPath);
            }}
            title="Download file"
          >
            <Download className="h-3 w-3" />
          </Button>
        </div>
      );
    });
  };

  return (
    <div
      className={`browser-container rounded-xl border border-[#3A3B3F] shadow-sm overflow-hidden ${className || ''}`}
    >
      <div className="flex flex-1 h-full">
        {/* File Explorer */}
        <div className="w-64 bg-neutral-900 border-r border-neutral-700 flex flex-col">
          <div className="px-3 py-1 text-sm font-medium text-neutral-400 border-b border-neutral-700">
            {ROOT_NAME}
          </div>
          <div className="overflow-y-auto flex-1">
            {renderFileTree(fileStructure)}
          </div>
        </div>

        {/* Editor Section */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {renderBreadcrumb()}
          <div className="flex-1 overflow-hidden">
            <Editor
              theme="vs-dark"
              language={activeLanguage}
              height="100%"
              value={fileContent}
              options={{
                minimap: { enabled: false },
                scrollBeyondLastLine: false,
                automaticLayout: true,
                readOnly: false,
              }}
              beforeMount={(monaco) => {
                monacoRef.current = monaco;
              }}
              onMount={(editor) => {
                editorRef.current = editor;
              }}
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export default CodeEditor;
