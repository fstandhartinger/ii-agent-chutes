"use client";

import { Cpu } from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useChutes, AVAILABLE_MODELS } from "@/providers/chutes-provider";

export default function ModelSelector() {
  const { selectedModel, setSelectedModel } = useChutes();

  return (
    <Select
      value={selectedModel.id}
      onValueChange={(value) => {
        const model = AVAILABLE_MODELS.find(m => m.id === value);
        if (model) {
          setSelectedModel(model);
        }
      }}
    >
      <SelectTrigger className="w-[200px] text-sm opacity-70 hover:opacity-100 transition-opacity">
        <div className="flex items-center gap-2">
          <Cpu className="h-3 w-3" />
          <SelectValue>
            {selectedModel.name}
          </SelectValue>
        </div>
      </SelectTrigger>
      <SelectContent>
        {AVAILABLE_MODELS.map((model) => (
          <SelectItem key={model.id} value={model.id}>
            <div className="flex flex-col">
              <div className="font-medium">{model.name}</div>
              <div className="text-xs text-muted-foreground">
                {model.description}
              </div>
            </div>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
} 