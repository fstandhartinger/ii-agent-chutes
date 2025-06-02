"use client";

import { createContext, useContext, useState, useEffect, ReactNode } from "react";

export interface LLMModel {
  id: string;
  name: string;
  provider: "anthropic" | "chutes" | "openrouter";
  description?: string;
  supportsVision?: boolean;
}

// Define model categories for automatic selection
export const TEXT_MODELS: LLMModel[] = [
  {
    id: "deepseek-ai/DeepSeek-R1",
    name: "DeepSeek R1",
    provider: "chutes",
    description: "Reasoning-optimized model",
    supportsVision: false
  },
  {
    id: "deepseek-ai/DeepSeek-R1-0528",
    name: "DeepSeek R1 0528",
    provider: "chutes",
    description: "DeepSeek R1 Snapshot vom 28.05.",
    supportsVision: false
  },
  {
    id: "nvidia/Llama-3_1-Nemotron-Ultra-253B-v1",
    name: "Nemotron Ultra",
    provider: "chutes",
    description: "NVIDIA's ultra-powerful model",
    supportsVision: false
  },
  {
    id: "claude-opus-4-20250514",
    name: "Claude Opus 4",
    provider: "anthropic",
    description: "Claude Opus 4 - Most capable model with vision",
    supportsVision: true
  },
  {
    id: "claude-sonnet-4-0",
    name: "Claude Sonnet 4",
    provider: "anthropic",
    description: "Claude Sonnet 4 - High-performance model with vision",
    supportsVision: true
  },
  {
    id: "Qwen/Qwen3-235B-A22B",
    name: "Qwen3 235B",
    provider: "chutes", 
    description: "Large-scale reasoning model",
    supportsVision: false
  }
];

export const VISION_MODELS: LLMModel[] = [
  {
    id: "deepseek-ai/DeepSeek-V3-0324",
    name: "DeepSeek V3 0324",
    provider: "chutes",
    description: "Advanced reasoning model with vision",
    supportsVision: true
  },
  {
    id: "chutesai/Llama-4-Maverick-17B-128E-Instruct-FP8",
    name: "Llama Maverick 4",
    provider: "chutes",
    description: "Efficient instruction-following model with vision",
    supportsVision: true
  }
];

// All available models (for display in selector)
export const AVAILABLE_MODELS: LLMModel[] = [...TEXT_MODELS, ...VISION_MODELS];

type LLMContextType = {
  selectedModel: LLMModel;
  setSelectedModel: (model: LLMModel) => void;
  getOptimalModel: (hasImages: boolean) => LLMModel;
  useChutesLLM: boolean; // Keep for backward compatibility
  toggleChutesLLM: () => void; // Keep for backward compatibility
};

const LLMContext = createContext<LLMContextType | undefined>(undefined);

export function ChutesProvider({ children }: { children: ReactNode }) {
  const [selectedModel, setSelectedModelState] = useState<LLMModel>(VISION_MODELS[0]);

  // Keep backward compatibility 
  const useChutesLLM = selectedModel.provider === "chutes";

  // Function to get optimal model based on content
  const getOptimalModel = (hasImages: boolean): LLMModel => {
    if (hasImages) {
      // Use vision models when images are present
      return VISION_MODELS[0]; // DeepSeek V3 0324 as primary
    } else {
      // Use text models when no images
      return TEXT_MODELS[0]; // DeepSeek R1 as primary
    }
  };

  // Load state from localStorage when component mounts
  useEffect(() => {
    const savedModelId = localStorage.getItem("selectedModelId");
    if (savedModelId) {
      const model = AVAILABLE_MODELS.find(m => m.id === savedModelId);
      if (model) {
        setSelectedModelState(model);
      }
    } else {
      // Try to migrate from old useChutesLLM setting or set default to DeepSeek V3
      const savedChutesValue = localStorage.getItem("useChutesLLM");
      if (savedChutesValue === "true") {
        setSelectedModelState(VISION_MODELS[0]); // DeepSeek V3 is now default
      } else {
        // Default to DeepSeek V3 for new users
        setSelectedModelState(VISION_MODELS[0]);
      }
    }
  }, []);

  const setSelectedModel = (model: LLMModel) => {
    setSelectedModelState(model);
    localStorage.setItem("selectedModelId", model.id);
    
    // Reload the page to re-establish WebSocket connection with the new setting
    setTimeout(() => {
      window.location.reload();
    }, 100);
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
      getOptimalModel,
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