"use client";

import { createContext, useContext, useState, useEffect, ReactNode } from "react";

type ChutesContextType = {
  useChutesLLM: boolean;
  toggleChutesLLM: () => void;
};

const ChutesContext = createContext<ChutesContextType | undefined>(undefined);

export function ChutesProvider({ children }: { children: ReactNode }) {
  const [useChutesLLM, setUseChutesLLM] = useState<boolean>(false);

  // Load state from localStorage when component mounts
  useEffect(() => {
    const savedValue = localStorage.getItem("useChutesLLM");
    if (savedValue !== null) {
      setUseChutesLLM(JSON.parse(savedValue));
    }
  }, []);

  const toggleChutesLLM = () => {
    const newValue = !useChutesLLM;
    setUseChutesLLM(newValue);
    localStorage.setItem("useChutesLLM", JSON.stringify(newValue));
    
    // Show alert notification
    alert(newValue ? "Chutes LLM provider activated!" : "Anthropic LLM provider activated!");
  };

  return (
    <ChutesContext.Provider value={{ useChutesLLM, toggleChutesLLM }}>
      {children}
    </ChutesContext.Provider>
  );
}

export const useChutes = (): ChutesContextType => {
  const context = useContext(ChutesContext);
  if (context === undefined) {
    throw new Error("useChutes must be used within a ChutesProvider");
  }
  return context;
}; 