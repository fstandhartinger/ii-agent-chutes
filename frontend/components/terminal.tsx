"use client";

import { Terminal as XTerm } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
// import { WebLinksAddon } from "@xterm/addon-web-links";
// import { SearchAddon } from "@xterm/addon-search";
import { forwardRef, Ref, useEffect, useRef, useImperativeHandle } from "react";
import "@xterm/xterm/css/xterm.css";
import clsx from "clsx";

export interface TerminalRef {
  writeOutput: (output: string) => void;
}

interface TerminalProps {
  className?: string;
  onCommand?: (command: string) => void;
}

const Terminal = (
  { className, onCommand }: TerminalProps,
  ref: Ref<TerminalRef>
) => {
  const xtermRef = useRef<XTerm | null>(null);
  const terminalRef = useRef<HTMLDivElement>(null);
  const commandHistoryRef = useRef<string[]>([]);
  const currentCommandRef = useRef<string>("");
  const historyIndexRef = useRef<number>(-1);

  useImperativeHandle(ref, () => ({
    writeOutput: (output: string) => {
      if (xtermRef.current) {
        xtermRef.current.writeln(output);
        prompt(xtermRef.current);
      }
    },
  }));

  useEffect(() => {
    const interval = setInterval(() => {
      const container = terminalRef.current;
      if (
        container &&
        container.clientWidth > 0 &&
        container.clientHeight > 0 &&
        !xtermRef.current
      ) {
        clearInterval(interval);

        const term = new XTerm({
          cursorBlink: true,
          fontSize: 14,
          fontFamily: "monospace",
          theme: {
            background: "rgba(0,0,0,0.8)",
            foreground: "#ffffff",
            cursor: "#ffffff",
            cursorAccent: "#1a1b26",
            selectionBackground: "rgba(255, 255, 255, 0.3)",
            selectionForeground: undefined,
          },
          allowTransparency: true,
        });

        const fitAddon = new FitAddon();
        term.loadAddon(fitAddon);
        // term.loadAddon(new WebLinksAddon());
        // term.loadAddon(new SearchAddon());

        term.open(container);
        fitAddon.fit();
        xtermRef.current = term;

        term.writeln("Welcome to II-Agent!");
        prompt(term);

        term.onKey(({ key, domEvent }) => {
          const printable =
            !domEvent.altKey && !domEvent.ctrlKey && !domEvent.metaKey;

          if (domEvent.key === "Enter") {
            const command = currentCommandRef.current;
            if (command.trim()) {
              commandHistoryRef.current.push(command);
              historyIndexRef.current = commandHistoryRef.current.length;
              executeCommand(term, command);
            } else {
              prompt(term);
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
              clearCurrentLine(term);
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
              clearCurrentLine(term);
              term.write(command);
              currentCommandRef.current = command;
            } else {
              historyIndexRef.current = commandHistoryRef.current.length;
              clearCurrentLine(term);
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
          xtermRef.current = null;
        };
      }
    }, 100);

    return () => clearInterval(interval);
  }, []);

  const prompt = (term: XTerm) => {
    term.write("\r\n$ ");
  };

  const clearCurrentLine = (term: XTerm) => {
    const len = currentCommandRef.current.length;
    term.write("\r$ " + " ".repeat(len));
    term.write("\r$ ");
  };

  const executeCommand = async (term: XTerm, command: string) => {
    term.writeln(`\r\nExecuting: ${command}`);
    if (onCommand) {
      onCommand(command);
    } else {
      prompt(term);
    }
  };

  return (
    <div
      className={clsx(
        "bg-black/80 border border-[#3A3B3F] shadow-sm p-4 h-[calc(100vh-178px)] rounded-xl overflow-auto",
        className
      )}
    >
      <div
        ref={terminalRef}
        className="h-full w-full"
        style={{ width: "100%", height: "100%" }}
      />
    </div>
  );
};

export default forwardRef(Terminal); 