"use client";

import { useChutes } from "@/providers/chutes-provider";
import { Crown } from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useState, useEffect } from "react";

// Define the available models with premium indicators
const CHUTES_MODELS = [
  { id: "deepseek-ai/DeepSeek-R1", name: "R1", isPremium: false },
  { id: "deepseek-ai/DeepSeek-V3-0324", name: "DeepSeek V3", isPremium: false },
  { id: "Qwen/Qwen3-235B-A22B", name: "Qwen3 235B", isPremium: false },
  { id: "chutesai/Llama-4-Maverick-17B-128E-Instruct-FP8", name: "Llama 4 Maverick", isPremium: false },
  { id: "nvidia/Llama-3_1-Nemotron-Ultra-253B-v1", name: "Nemotron Ultra", isPremium: false },
  // Premium models - hidden by default
  { id: "anthropic/claude-3-5-sonnet", name: "Sonnet 3.5", isPremium: true, hidden: true },
  { id: "anthropic/claude-3-opus", name: "Opus 3", isPremium: true, hidden: true },
];

export default function ModelPicker() {
  const { selectedModel, setSelectedModel } = useChutes();
  const [showHiddenModels, setShowHiddenModels] = useState(false);

  // Load hidden models state from localStorage
  useEffect(() => {
    const hiddenModelsUnlocked = localStorage.getItem("hiddenModelsUnlocked") === "true";
    setShowHiddenModels(hiddenModelsUnlocked);
  }, []);

  // Filter models based on whether hidden models are shown
  const visibleModels = CHUTES_MODELS.filter(model => !model.hidden || showHiddenModels);

  // Find the current model name or default to R1
  const currentModel = visibleModels.find(m => m.id === selectedModel.id);
  const currentModelName = currentModel?.name || "R1";
  const isCurrentModelPremium = currentModel?.isPremium || false;

  const handleModelChange = (modelId: string) => {
    const model = CHUTES_MODELS.find(m => m.id === modelId);
    if (model) {
      // Find the full model object from the provider
      const fullModel = {
        id: model.id,
        name: model.name,
        provider: "chutes" as const,
        supportsVision: model.id.includes("V3") || model.id.includes("Maverick")
      };
      setSelectedModel(fullModel);
    }
  };

  return (
    <div className="flex items-center gap-2 text-sm">
      <span className="text-muted-foreground/70 text-xs">Model:</span>
      <Select value={selectedModel.id} onValueChange={handleModelChange}>
        <SelectTrigger 
          size="sm" 
          className="h-7 min-w-0 w-auto bg-glass border-white/10 hover:bg-white/5 text-xs font-medium text-white/90 hover:text-white transition-all-smooth"
        >
          <SelectValue placeholder="R1">
            <div className="flex items-center gap-1">
              {isCurrentModelPremium && (
                <Crown className="w-3 h-3 text-yellow-400" />
              )}
              {currentModelName}
            </div>
          </SelectValue>
        </SelectTrigger>
        <SelectContent className="bg-glass-dark border-white/20 backdrop-blur-xl">
          {visibleModels.map((model) => (
            <SelectItem 
              key={model.id} 
              value={model.id}
              className="text-white/90 hover:bg-white/10 focus:bg-white/10 text-xs"
            >
              <div className="flex items-center gap-2">
                {model.isPremium && (
                  <Crown className="w-3 h-3 text-yellow-400" />
                )}
                <span>{model.name}</span>
                {model.isPremium && (
                  <span className="text-yellow-400/70 text-[10px] font-medium">PREMIUM</span>
                )}
              </div>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
} 