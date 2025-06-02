"use client";

import { Eye, FileText } from "lucide-react";
import { motion } from "framer-motion";
import { TEXT_MODELS, VISION_MODELS } from "@/providers/chutes-provider";

export default function ModelSelector() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, delay: 0.2 }}
      className="relative"
    >
      {/* Glow Effect */}
      <div className="absolute inset-0 bg-gradient-to-r from-blue-500/20 via-purple-500/20 to-emerald-500/20 rounded-2xl blur-xl opacity-50" />
      
      <div className="relative bg-glass border border-white/20 rounded-2xl p-4 shadow-lg backdrop-blur-xl">
        <div className="text-center mb-4">
          <h3 className="text-lg font-semibold text-white mb-2">Automatic Model Selection</h3>
          <p className="text-sm text-muted-foreground">
            Models are automatically chosen based on your content
          </p>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Text Models */}
          <div className="bg-black/20 rounded-xl p-3 border border-white/10">
            <div className="flex items-center gap-2 mb-2">
              <FileText className="w-4 h-4 text-blue-400" />
              <span className="text-sm font-medium text-white">Text Tasks</span>
            </div>
            <div className="space-y-2">
              {TEXT_MODELS.map((model, index) => (
                <div key={model.id} className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full ${index === 0 ? 'bg-blue-400' : 'bg-gray-500'}`} />
                  <span className={`text-xs ${index === 0 ? 'text-white font-medium' : 'text-muted-foreground'}`}>
                    {model.name} {index === 0 && '(Primary)'}
                  </span>
                </div>
              ))}
            </div>
          </div>
          
          {/* Vision Models */}
          <div className="bg-black/20 rounded-xl p-3 border border-white/10">
            <div className="flex items-center gap-2 mb-2">
              <Eye className="w-4 h-4 text-purple-400" />
              <span className="text-sm font-medium text-white">Vision Tasks</span>
            </div>
            <div className="space-y-2">
              {VISION_MODELS.map((model, index) => (
                <div key={model.id} className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full ${index === 0 ? 'bg-purple-400' : 'bg-gray-500'}`} />
                  <span className={`text-xs ${index === 0 ? 'text-white font-medium' : 'text-muted-foreground'}`}>
                    {model.name} {index === 0 && '(Primary)'}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
        
        <div className="mt-4 pt-3 border-t border-white/10">
          <p className="text-xs text-muted-foreground text-center">
            💡 Upload images or paste them to automatically switch to vision models
          </p>
        </div>
      </div>
    </motion.div>
  );
} 