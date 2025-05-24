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
    id: "anthropic-claude-3-5-sonnet",
    name: "Claude 3.5 Sonnet",
    provider: "anthropic",
    description: "Anthropic's most capable model"
  },
  {
    id: "deepseek-ai/DeepSeek-V3-0324",
    name: "DeepSeek V3",
    provider: "chutes",
    description: "Advanced reasoning model"
  },
  {
    id: "chutesai/Llama-4-Maverick-17B-128E-Instruct-FP8",
    name: "Llama 4 Maverick 17B",
    provider: "chutes",
    description: "Efficient instruction-following model"
  },
  {
    id: "Qwen/Qwen3-235B-A22B",
    name: "Qwen 3 235B",
    provider: "chutes", 
    description: "Large-scale reasoning model"
  },
  {
    id: "deepseek-ai/DeepSeek-R1",
    name: "DeepSeek R1",
    provider: "chutes",
    description: "Reasoning-optimized model"
  },
  {
    id: "Qwen/Qwen2.5-VL-32B-Instruct",
    name: "Qwen 2.5 VL 32B",
    provider: "chutes",
    description: "Vision-language model"
  },
  {
    id: "deepseek/deepseek-chat-v3-0324:free",
    name: "DeepSeek V3 (OpenRouter Free)",
    provider: "openrouter",
    description: "Free tier - No tool calling"
  },
  {
    id: "meta-llama/llama-4-maverick:free",
    name: "Llama 4 Maverick (OpenRouter Free)",
    provider: "openrouter",
    description: "Free tier - No tool calling"
  },
  {
    id: "qwen/qwen3-235b-a22b:free",
    name: "Qwen 3 235B (OpenRouter Free)",
    provider: "openrouter",
    description: "Free tier - No tool calling"
  },
  {
    id: "deepseek/deepseek-r1:free",
    name: "DeepSeek R1 (OpenRouter Free)",
    provider: "openrouter",
    description: "Free tier - No tool calling"
  },
  {
    id: "qwen/qwen2.5-vl-32b-instruct:free",
    name: "Qwen 2.5 VL 32B (OpenRouter Free)",
    provider: "openrouter",
    description: "Free tier - No tool calling"
  },
  {
    id: "openai/gpt-4o-mini",
    name: "GPT-4o Mini (OpenRouter)",
    provider: "openrouter",
    description: "Affordable GPT with tool calling"
  },
  {
    id: "anthropic/claude-3-haiku",
    name: "Claude 3 Haiku (OpenRouter)",
    provider: "openrouter",
    description: "Fast and affordable with tool calling"
  },
  {
    id: "google/gemini-flash-1.5",
    name: "Gemini Flash 1.5 (OpenRouter)",
    provider: "openrouter",
    description: "Google's fast model with tool calling"
  },
  {
    id: "mistralai/mistral-7b-instruct",
    name: "Mistral 7B Instruct (OpenRouter)",
    provider: "openrouter",
    description: "Affordable Mistral with tool calling"
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
      // Try to migrate from old useChutesLLM setting
      const savedChutesValue = localStorage.getItem("useChutesLLM");
      if (savedChutesValue === "true") {
        setSelectedModelState(AVAILABLE_MODELS.find(m => m.provider === "chutes") || AVAILABLE_MODELS[0]);
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
    const currentIsChutes = selectedModel.provider === "chutes";
    const newModel = currentIsChutes 
      ? AVAILABLE_MODELS.find(m => m.provider === "anthropic") || AVAILABLE_MODELS[0]
      : AVAILABLE_MODELS.find(m => m.provider === "chutes") || AVAILABLE_MODELS[1];
    
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