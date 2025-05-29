import { useCallback } from 'react';
import { debounce } from 'lodash';
import { TAB, TOOL, ActionStep } from '@/typings/agent';
import type { TerminalRef } from "@/components/terminal"; // Assuming TerminalRef is exported from terminal component

export interface UseActionHandlerProps {
  setActiveTab: (tab: TAB) => void;
  setCurrentActionData: (data: ActionStep | undefined) => void;
  setActiveFileCodeEditor: (path: string) => void;
  workspaceInfo: string;
  terminalRef: React.RefObject<TerminalRef | null>;
}

export const useActionHandler = ({
  setActiveTab,
  setCurrentActionData,
  setActiveFileCodeEditor,
  workspaceInfo,
  terminalRef,
}: UseActionHandlerProps) => {

  const handleClickAction = useCallback(debounce(
    (data: ActionStep | undefined, showTabOnly = false) => {
      if (!data) return;

      setCurrentActionData(data); // Set current action data immediately for other components to react

      switch (data.type) {
        case TOOL.WEB_SEARCH:
          setActiveTab(TAB.BROWSER);
          break;

        case TOOL.IMAGE_GENERATE:
        case TOOL.BROWSER_USE: // This case might need specific handling if it's just a result display
        case TOOL.VISIT:
          setActiveTab(TAB.BROWSER);
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
          break;

        case TOOL.BASH:
          setActiveTab(TAB.TERMINAL);
          if (!showTabOnly && terminalRef.current) {
            // Ensure terminalRef.current exists before trying to use it
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
            }, 500); // Delay to allow tab switch and terminal rendering
          }
          break;

        case TOOL.STR_REPLACE_EDITOR:
          setActiveTab(TAB.CODE);
          const path = data.data.tool_input?.path || data.data.tool_input?.file;
          if (path && workspaceInfo) { // Ensure workspaceInfo is available
            setActiveFileCodeEditor(
              path.startsWith(workspaceInfo) ? path : `${workspaceInfo}/${path}`
            );
          } else if (path) {
            // Fallback if workspaceInfo is not yet set (should be rare)
            setActiveFileCodeEditor(path);
          }
          break;

        default:
          // Optionally, set a default tab or handle unknown tools
          // console.warn("Unhandled tool type in handleClickAction:", data.type);
          break;
      }
    },
    50 // Debounce time
  ), [setActiveTab, setCurrentActionData, setActiveFileCodeEditor, workspaceInfo, terminalRef]);

  return { handleClickAction };
};
