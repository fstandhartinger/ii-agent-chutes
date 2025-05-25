"use client";

import { Cpu, ChevronDown, Sparkles } from "lucide-react";
import { motion } from "framer-motion";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
} from "@/components/ui/select";
import { useChutes, AVAILABLE_MODELS } from "@/providers/chutes-provider";

export default function ModelSelector() {
  const { selectedModel, setSelectedModel } = useChutes();

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, delay: 0.2 }}
      className="relative"
    >
      {/* Glow Effect */}
      <div className="absolute inset-0 bg-gradient-to-r from-blue-500/20 via-purple-500/20 to-emerald-500/20 rounded-2xl blur-xl opacity-50" />
      
      <Select
        value={selectedModel.id}
        onValueChange={(value) => {
          const model = AVAILABLE_MODELS.find(m => m.id === value);
          if (model) {
            setSelectedModel(model);
          }
        }}
      >
        <SelectTrigger className="relative w-[280px] md:w-[320px] bg-glass border-white/20 hover:bg-white/10 transition-all-smooth hover-lift rounded-2xl p-4 shadow-lg backdrop-blur-xl">
          <div className="flex items-center gap-3 w-full">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-500 rounded-xl flex items-center justify-center shadow-lg">
              <Cpu className="w-5 h-5 text-white" />
            </div>
            <div className="flex flex-col items-start flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-white text-sm md:text-base">
                  {selectedModel.name}
                </span>
                <Sparkles className="w-4 h-4 text-yellow-400" />
              </div>
              <span className="text-xs md:text-sm text-muted-foreground truncate max-w-full">
                {selectedModel.description}
              </span>
            </div>
            <ChevronDown className="w-4 h-4 text-muted-foreground flex-shrink-0" />
          </div>
        </SelectTrigger>
        
        <SelectContent className="bg-glass-dark border-white/20 backdrop-blur-xl rounded-2xl shadow-2xl min-w-[280px] md:min-w-[320px]">
          {AVAILABLE_MODELS.map((model, index) => (
            <SelectItem 
              key={model.id} 
              value={model.id}
              className="hover:bg-white/10 focus:bg-white/10 rounded-xl m-1 transition-all-smooth"
            >
              <motion.div 
                className="flex items-center gap-3 w-full py-2"
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.05 }}
              >
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center shadow-sm ${
                  model.id === selectedModel.id 
                    ? "bg-gradient-to-br from-blue-500 to-purple-500" 
                    : "bg-gradient-to-br from-gray-600 to-gray-700"
                }`}>
                  <Cpu className="w-4 h-4 text-white" />
                </div>
                <div className="flex flex-col flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-white text-sm">
                      {model.name}
                    </span>
                    {model.id === selectedModel.id && (
                      <Sparkles className="w-3 h-3 text-yellow-400" />
                    )}
                  </div>
                  <span className="text-xs text-muted-foreground truncate">
                    {model.description}
                  </span>
                </div>
              </motion.div>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </motion.div>
  );
} 