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
  // Basic text models
  {
    id: "deepseek-ai/DeepSeek-R1",
    name: "DeepSeek R1",
    provider: "chutes",
    description: "Reasoning-optimized model",
    supportsVision: false
  },
  {
    id: "deepseek-ai/DeepSeek-V3-0324",
    name: "DeepSeek V3",
    provider: "chutes",
    description: "Advanced reasoning model",
    supportsVision: false
  },
  {
    id: "claude-sonnet-4-0",
    name: "Claude Sonnet 4",
    provider: "anthropic",
    description: "Claude Sonnet 4 - High-performance model",
    supportsVision: false
  },
];

export const VISION_MODELS: LLMModel[] = [
  // Vision-capable models (no duplicates from TEXT_MODELS)
  {
    id: "google/gemini-2.5-pro-preview",
    name: "Gemini 2.5 Pro",
    provider: "openrouter",
    description: "Google Gemini 2.5 Pro with vision",
    supportsVision: true
  },
  {
    id: "google/gemini-2.5-flash-preview-05-20:thinking",
    name: "Gemini 2.5 Flash Thinking",
    provider: "openrouter",
    description: "Google Gemini 2.5 Flash (Thinking) with vision",
    supportsVision: true
  },
  {
    id: "qwen/qwen3-32b:fast",
    name: "Qwen3 32B Fast",
    provider: "openrouter",
    description: "Fast Qwen3 model via OpenRouter",
    supportsVision: true
  },
  {
    id: "meta-llama/llama-4-maverick:fast", 
    name: "Llama 4 Maverick Fast",
    provider: "openrouter",
    description: "Fast Llama 4 Maverick via OpenRouter",
    supportsVision: true
  },
  {
    id: "deepseek/deepseek-r1-distill-llama-70b:fast",
    name: "R1 Distill Llama 70B Fast", 
    provider: "openrouter",
    description: "Fast R1 Distilled model via OpenRouter",
    supportsVision: true
  },
  {
    id: "claude-opus-4-0",
    name: "Claude Opus 4",
    provider: "anthropic",
    description: "Claude Opus 4 - Most capable model with vision",
    supportsVision: true
  },
  {
    id: "openai/o3",
    name: "O3",
    provider: "openrouter",
    description: "OpenAI O3 multimodal model via OpenRouter",
    supportsVision: true
  },
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
    console.log("[CHUTES_PROVIDER_DEBUG] Loading saved model state from localStorage");
    
    const savedModelId = localStorage.getItem("selectedModelId");
    console.log("[CHUTES_PROVIDER_DEBUG] Saved model ID from localStorage:", savedModelId);
    
    if (savedModelId) {
      const model = AVAILABLE_MODELS.find(m => m.id === savedModelId);
      console.log("[CHUTES_PROVIDER_DEBUG] Found model in AVAILABLE_MODELS:", model);
      
      if (model) {
        console.log("[CHUTES_PROVIDER_DEBUG] Setting saved model:", model);
        setSelectedModelState(model);
      } else {
        console.warn("[CHUTES_PROVIDER_DEBUG] Saved model ID not found in AVAILABLE_MODELS, falling back to default");
        console.log("[CHUTES_PROVIDER_DEBUG] Available model IDs:", AVAILABLE_MODELS.map(m => m.id));
        // Ensure VISION_MODELS is not empty before accessing VISION_MODELS[0]
// Default to Gemini 2.5 Pro if available, otherwise first available vision model, or first text model.
const defaultModel = VISION_MODELS.find(m => m.id === "google/gemini-2.5-pro-preview") || VISION_MODELS[0] || TEXT_MODELS[0];
if (defaultModel) {
  setSelectedModelState(defaultModel);
} else {
  // Fallback if all lists are empty (should not happen with new models)
  console.error("[CHUTES_PROVIDER_DEBUG] No default model available!");
  // setSelectedModelState(SOME_ABSOLUTE_FALLBACK_MODEL_IF_NEEDED); 
}
      }
    } else {
      // Try to migrate from old useChutesLLM setting or set default to DeepSeek V3
      const savedChutesValue = localStorage.getItem("useChutesLLM");
      console.log("[CHUTES_PROVIDER_DEBUG] No saved model ID, checking old useChutesLLM value:", savedChutesValue);
      
      if (savedChutesValue === "true") {
        console.log("[CHUTES_PROVIDER_DEBUG] Setting default to DeepSeek V3 (migration from useChutesLLM)");
        // Ensure VISION_MODELS is not empty before accessing VISION_MODELS[0]
// Default to Gemini 2.5 Pro if available, otherwise first available vision model, or first text model.
const defaultModel = VISION_MODELS.find(m => m.id === "google/gemini-2.5-pro-preview") || VISION_MODELS[0] || TEXT_MODELS[0];
if (defaultModel) {
  setSelectedModelState(defaultModel);
} else {
  // Fallback if all lists are empty (should not happen with new models)
  console.error("[CHUTES_PROVIDER_DEBUG] No default model available!");
  // setSelectedModelState(SOME_ABSOLUTE_FALLBACK_MODEL_IF_NEEDED); 
} // DeepSeek V3 is now default
      } else {
        // Default to DeepSeek V3 for new users
        console.log("[CHUTES_PROVIDER_DEBUG] Setting default to DeepSeek V3 (new user)");
        // Ensure VISION_MODELS is not empty before accessing VISION_MODELS[0]
// Default to Gemini 2.5 Pro if available, otherwise first available vision model, or first text model.
const defaultModel = VISION_MODELS.find(m => m.id === "google/gemini-2.5-pro-preview") || VISION_MODELS[0] || TEXT_MODELS[0];
if (defaultModel) {
  setSelectedModelState(defaultModel);
} else {
  // Fallback if all lists are empty (should not happen with new models)
  console.error("[CHUTES_PROVIDER_DEBUG] No default model available!");
  // setSelectedModelState(SOME_ABSOLUTE_FALLBACK_MODEL_IF_NEEDED); 
}
      }
    }
  }, []);

  const setSelectedModel = (model: LLMModel) => {
    console.log("[CHUTES_PROVIDER_DEBUG] setSelectedModel called with:", model);
    console.log("[CHUTES_PROVIDER_DEBUG] Current selected model:", selectedModel);
    
    // Check if the model is in AVAILABLE_MODELS
    const isModelAvailable = AVAILABLE_MODELS.find(m => m.id === model.id);
    if (!isModelAvailable) {
      console.error("[CHUTES_PROVIDER_DEBUG] Model not found in AVAILABLE_MODELS:", model.id);
      console.log("[CHUTES_PROVIDER_DEBUG] Available model IDs:", AVAILABLE_MODELS.map(m => m.id));
      return;
    }
    
    setSelectedModelState(model);
    localStorage.setItem("selectedModelId", model.id);
    console.log("[CHUTES_PROVIDER_DEBUG] Model set and saved to localStorage:", model.id);
    
    // Reload the page to re-establish WebSocket connection with the new setting
    console.log("[CHUTES_PROVIDER_DEBUG] Reloading page in 100ms to apply new model");
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