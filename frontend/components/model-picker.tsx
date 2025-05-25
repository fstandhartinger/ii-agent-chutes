"use client";

import { useChutes } from "@/providers/chutes-provider";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

// Define the available models as requested
const CHUTES_MODELS = [
  { id: "deepseek-ai/DeepSeek-R1", name: "R1" },
  { id: "deepseek-ai/DeepSeek-V3-0324", name: "DeepSeek V3" },
  { id: "Qwen/Qwen3-235B-A22B", name: "Qwen3 235B" },
  { id: "chutesai/Llama-4-Maverick-17B-128E-Instruct-FP8", name: "Llama 4 Maverick" },
];

export default function ModelPicker() {
  const { selectedModel, setSelectedModel } = useChutes();

  // Find the current model name or default to R1
  const currentModelName = CHUTES_MODELS.find(m => m.id === selectedModel.id)?.name || "R1";

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
            {currentModelName}
          </SelectValue>
        </SelectTrigger>
        <SelectContent className="bg-glass-dark border-white/20 backdrop-blur-xl">
          {CHUTES_MODELS.map((model) => (
            <SelectItem 
              key={model.id} 
              value={model.id}
              className="text-white/90 hover:bg-white/10 focus:bg-white/10 text-xs"
            >
              {model.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
} 