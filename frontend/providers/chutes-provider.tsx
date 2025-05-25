"use client";

import { createContext, useContext, useState, useEffect, ReactNode } from "react";

export interface LLMModel {
  id: string;
  name: string;
  provider: "anthropic" | "chutes" | "openrouter";
  description?: string;
}

export const AVAILABLE_MODELS: LLMModel[] = [
  {
    id: "deepseek-ai/DeepSeek-R1",
    name: "DeepSeek R1",
    provider: "chutes",
    description: "Reasoning-optimized model"
  },
  {
    id: "deepseek-ai/DeepSeek-V3-0324",
    name: "DeepSeek V3 0324",
    provider: "chutes",
    description: "Advanced reasoning model"
  },
  {
    id: "Qwen/Qwen3-235B-A22B",
    name: "Qwen3 235B",
    provider: "chutes", 
    description: "Large-scale reasoning model"
  },
  {
    id: "chutesai/Llama-4-Maverick-17B-128E-Instruct-FP8",
    name: "Llama Maverick",
    provider: "chutes",
    description: "Efficient instruction-following model"
  }
];

type LLMContextType = {
  selectedModel: LLMModel;
  setSelectedModel: (model: LLMModel) => void;
  useChutesLLM: boolean; // Keep for backward compatibility
  toggleChutesLLM: () => void; // Keep for backward compatibility
};

const LLMContext = createContext<LLMContextType | undefined>(undefined);

export function ChutesProvider({ children }: { children: ReactNode }) {
  const [selectedModel, setSelectedModelState] = useState<LLMModel>(AVAILABLE_MODELS[0]);

  // Keep backward compatibility 
  const useChutesLLM = selectedModel.provider === "chutes";

  // Load state from localStorage when component mounts
  useEffect(() => {
    const savedModelId = localStorage.getItem("selectedModelId");
    if (savedModelId) {
      const model = AVAILABLE_MODELS.find(m => m.id === savedModelId);
      if (model) {
        setSelectedModelState(model);
      }
    } else {
      // Try to migrate from old useChutesLLM setting or set default to DeepSeek R1
      const savedChutesValue = localStorage.getItem("useChutesLLM");
      if (savedChutesValue === "true") {
        setSelectedModelState(AVAILABLE_MODELS[0]); // DeepSeek R1 is now first
      } else {
        // Default to DeepSeek R1 for new users
        setSelectedModelState(AVAILABLE_MODELS[0]);
      }
    }
  }, []);

  const setSelectedModel = (model: LLMModel) => {
    setSelectedModelState(model);
    localStorage.setItem("selectedModelId", model.id);
    
    // Show notification
    alert(`Switched to ${model.name}! Page will reload to apply changes.`);
    
    // Reload the page to re-establish WebSocket connection with the new setting
    setTimeout(() => {
      window.location.reload();
    }, 500);
  };

  // Keep backward compatibility for the toggle function
  const toggleChutesLLM = () => {
    // Since we only have Chutes models now, just cycle through them
    const currentIndex = AVAILABLE_MODELS.findIndex(m => m.id === selectedModel.id);
    const nextIndex = (currentIndex + 1) % AVAILABLE_MODELS.length;
    const newModel = AVAILABLE_MODELS[nextIndex];
    
    setSelectedModel(newModel);
  };

  return (
    <LLMContext.Provider value={{ 
      selectedModel, 
      setSelectedModel, 
      useChutesLLM, 
      toggleChutesLLM 
    }}>
      {children}
    </LLMContext.Provider>
  );
}

export const useChutes = (): LLMContextType => {
  const context = useContext(LLMContext);
  if (context === undefined) {
    throw new Error("useChutes must be used within a ChutesProvider");
  }
  return context;
}; 