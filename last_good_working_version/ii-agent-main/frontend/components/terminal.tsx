"use client";

import { Terminal as XTerm } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
// import { WebLinksAddon } from "@xterm/addon-web-links";
// import { SearchAddon } from "@xterm/addon-search";
import React, { forwardRef, useEffect, useRef, useImperativeHandle, useCallback } from 'react';
import "@xterm/xterm/css/xterm.css";
import clsx from "clsx";

interface TerminalProps {
  className?: string;
  onCommand?: (command: string) => void;
}

// Definiere die öffentliche Schnittstelle der Terminal-Komponente
export interface TerminalRef {
  writeOutput: (output: string) => void;
}

// Spezielle Typdefinition für forwardRef mit explizitem Rückgabetyp
type TerminalComponentType = React.ForwardRefExoticComponent<
  TerminalProps & React.RefAttributes<TerminalRef>
>;

// Der Typ TerminalRef wird bereits verwendet und ist ausreichend

const TerminalComponent = (
  { className, onCommand }: TerminalProps,
  xtermRef: React.Ref<TerminalRef>
) => {
  // Ref für das DOM-Element
  const terminalRef = useRef<HTMLDivElement>(null);
  // Ref für die XTerm-Instanz
  const xtermInstanceRef = useRef<XTerm | null>(null);
  const commandHistoryRef = useRef<string[]>([]);
  const currentCommandRef = useRef<string>("");
  const historyIndexRef = useRef<number>(-1);

  // Terminal-Hilfsfunktionen deklarieren (memoisiert)
  const prompt = useCallback((term: XTerm) => {
    term.write("\r\n$ ");
  }, []);

  const clearCurrentLine = useCallback((term: XTerm) => {
    const len = currentCommandRef.current.length;
    term.write("\r$ " + " ".repeat(len));
    term.write("\r$ ");
  }, []); // currentCommandRef ist eine Ref, ändert sich nicht für useCallback

  const executeCommand = useCallback(async (term: XTerm, command: string) => {
    console.log(`[TERMINAL_DEBUG] Executing command: ${command}`);
    term.writeln(`\r\nExecuting: ${command}`);
    
    if (onCommand) {
      console.log(`[TERMINAL_DEBUG] Sending command to parent component`);
      onCommand(command);
    } else {
      console.log(`[TERMINAL_DEBUG] No onCommand handler provided`);
      term.writeln("\r\nERROR: Terminal not connected to backend");
      prompt(term); // prompt ist jetzt memoisiert
    }
  }, [onCommand, prompt]); // prompt als Abhängigkeit, da es innerhalb verwendet wird
  
  // Terminal initialisieren
  useEffect(() => {
    const container = terminalRef.current;
    if (!container) return;

    const term = new XTerm({
      cursorBlink: true,
      fontFamily: "Menlo, Monaco, 'Courier New', monospace",
      fontSize: 14,
      theme: {
        background: "#0a0c10",
        foreground: "#ffffff",
        cursor: "#ffffff",
        selectionBackground: "rgba(255, 255, 255, 0.3)",
      },
    });

    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);
    // term.loadAddon(new WebLinksAddon());
    // term.loadAddon(new SearchAddon());

    term.open(container);
    fitAddon.fit();

    // Speichere die XTerm-Instanz in der Ref
    xtermInstanceRef.current = term;

    console.log("[TERMINAL_DEBUG] Terminal initialized");
    term.writeln("Welcome to fubea!");
    term.writeln("Type a command and press Enter to execute.");
    prompt(term); // prompt ist memoisiert

    term.onKey(({ key, domEvent }) => {
      const printable =
        !domEvent.altKey && !domEvent.ctrlKey && !domEvent.metaKey;

      if (domEvent.key === "Enter") {
        const command = currentCommandRef.current;
        if (command.trim()) {
          commandHistoryRef.current.push(command);
          historyIndexRef.current = commandHistoryRef.current.length;
          executeCommand(term, command); // executeCommand ist memoisiert
        } else {
          prompt(term); // prompt ist memoisiert
        }
        currentCommandRef.current = "";
      } else if (domEvent.key === "Backspace") {
        if (currentCommandRef.current.length > 0) {
          currentCommandRef.current = currentCommandRef.current.slice(
            0,
            -1
          );
          term.write("\b \b");
        }
      } else if (domEvent.key === "ArrowUp") {
        if (historyIndexRef.current > 0) {
          historyIndexRef.current--;
          const command =
            commandHistoryRef.current[historyIndexRef.current];
          clearCurrentLine(term); // clearCurrentLine ist memoisiert
          term.write(command);
          currentCommandRef.current = command;
        }
      } else if (domEvent.key === "ArrowDown") {
        if (
          historyIndexRef.current <
          commandHistoryRef.current.length - 1
        ) {
          historyIndexRef.current++;
          const command =
            commandHistoryRef.current[historyIndexRef.current];
          clearCurrentLine(term); // clearCurrentLine ist memoisiert
          term.write(command);
          currentCommandRef.current = command;
        } else {
          historyIndexRef.current = commandHistoryRef.current.length;
          clearCurrentLine(term); // clearCurrentLine ist memoisiert
          currentCommandRef.current = "";
        }
      } else if (printable) {
        term.write(key);
        currentCommandRef.current += key;
      }
    });

    const handleResize = () => {
      fitAddon.fit();
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      term.dispose();
    };
  }, [prompt, executeCommand, clearCurrentLine]); // Korrekte Abhängigkeiten
  
  // Expose writeOutput method to parent component
  useImperativeHandle<TerminalRef, TerminalRef>(
    xtermRef, 
    () => ({
      writeOutput: (output: string) => {
        console.log(`[TERMINAL_DEBUG] Writing output to terminal: ${output.length} chars`);
        // Verwende die gespeicherte XTerm-Instanz
        const term = xtermInstanceRef.current;
        if (term) {
          console.log(`[TERMINAL_DEBUG] Found terminal instance, writing output`);
          term.writeln(output);
          prompt(term);
        } else {
          console.error("[TERMINAL_DEBUG] Terminal reference not available");
        }
      }
    })
    // Entferne die unnötige Abhängigkeit, da sie nicht für Re-Rendering benötigt wird
  );

  return (
    <div
      className={clsx(
        "browser-container bg-black/80 border border-[#3A3B3F] shadow-sm rounded-xl overflow-hidden",
        className || ''
      )}
    >
      <div
        ref={terminalRef}
        className="h-full w-full p-4"
        style={{ width: "100%", height: "100%" }}
      />
    </div>
  );
};

// Typensicheres forwarding der Referenz
const ForwardedTerminal: TerminalComponentType = forwardRef(TerminalComponent);
export default ForwardedTerminal;
