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
import { useState, useEffect, useCallback, useMemo } from "react";
import { hasProAccess } from "@/utils/pro-utils";
import { useRouter } from "next/navigation";

// Define the available models with premium indicators
const CHUTES_MODELS = [
  // Free models (first)
  { id: "deepseek-ai/DeepSeek-R1", name: "R1", isPremium: false },
  { id: "deepseek-ai/DeepSeek-V3-0324", name: "DeepSeek V3", isPremium: false },
  { id: "Qwen/Qwen3-235B-A22B", name: "Qwen3 235B", isPremium: false },
  { id: "chutesai/Llama-4-Maverick-17B-128E-Instruct-FP8", name: "Llama 4 Maverick", isPremium: false },
  { id: "nvidia/Llama-3_1-Nemotron-Ultra-253B-v1", name: "Nemotron Ultra", isPremium: false },
  
  // Premium models (second) - Pro plan exclusive
  { id: "google/gemini-2.5-pro-preview", name: "Gemini 2.5 Pro", isPremium: true, isOpenRouter: true },
  { id: "openai/gpt-4.1", name: "GPT-4.1", isPremium: true, isOpenRouter: true },
  { id: "openai/o3", name: "OpenAI o3", isPremium: true, isOpenRouter: true },
  { id: "google/gemini-2.5-flash-preview-05-20:thinking", name: "Gemini 2.5 Flash Thinking", isPremium: true, isOpenRouter: true },
  { id: "qwen/qwen3-32b:fast", name: "Qwen3 32B Fast", isPremium: true, isOpenRouter: true },
  { id: "meta-llama/llama-4-maverick:fast", name: "Llama 4 Maverick Fast", isPremium: true, isOpenRouter: true },
  { id: "deepseek/deepseek-r1-distill-llama-70b:fast", name: "R1 Distill Llama 70B Fast", isPremium: true, isOpenRouter: true },
  { id: "claude-sonnet-4-0", name: "Claude Sonnet 4", isPremium: true, hidden: false },
  { id: "claude-opus-4-0", name: "Claude Opus 4", isPremium: true, hidden: false },
  // OpenRouter models - Free for Pro users



];

export default function ModelPicker() {
  const { selectedModel, setSelectedModel } = useChutes();
  const [userHasProAccess, setUserHasProAccess] = useState(false);
  const [hasAutoSwitched, setHasAutoSwitched] = useState(false);
  const router = useRouter();

  // Check Pro access on component mount and handle auto-switching
  useEffect(() => {
    console.log("[MODEL_PICKER_DEBUG] Checking Pro access and handling auto-switching");
    
    const proAccess = hasProAccess();
    console.log("[MODEL_PICKER_DEBUG] Pro access:", proAccess);
    setUserHasProAccess(proAccess);

    // Check if user has manually switched models before
    const manualSwitch = localStorage.getItem("userManuallySwitchedModel");
    console.log("[MODEL_PICKER_DEBUG] Manual switch flag:", manualSwitch);
    console.log("[MODEL_PICKER_DEBUG] Has auto switched:", hasAutoSwitched);
    console.log("[MODEL_PICKER_DEBUG] Current selected model:", selectedModel);

    // Auto-switch to Sonnet 4 for Pro users if they haven't manually switched
    if (proAccess && !hasAutoSwitched && manualSwitch !== "true") {
      // Only auto-switch if current model is not already Sonnet 4
      if (selectedModel.id !== "claude-sonnet-4-0") {
        console.log("[MODEL_PICKER_DEBUG] Auto-switching Pro user to Claude Sonnet 4");
        
        const sonnet4Model = {
          id: "claude-sonnet-4-0",
          name: "Claude Sonnet 4",
          provider: "anthropic" as const,
          supportsVision: true
        };
        
        setSelectedModel(sonnet4Model);
        setHasAutoSwitched(true);
        
        // Mark that we've auto-switched, but don't mark as manual switch
        localStorage.setItem("hasAutoSwitchedToSonnet4", "true");
        console.log("[MODEL_PICKER_DEBUG] Set hasAutoSwitchedToSonnet4 flag");
      } else {
        console.log("[MODEL_PICKER_DEBUG] Already on Sonnet 4, no auto-switch needed");
      }
    } else {
      console.log("[MODEL_PICKER_DEBUG] No auto-switch needed:", { proAccess, hasAutoSwitched, manualSwitch, currentModelId: selectedModel.id });
    }
  }, [selectedModel.id, setSelectedModel, hasAutoSwitched]);

  // Sort models to show non-premium first, then premium
  const sortedModels = useMemo(() => {
    return [...CHUTES_MODELS].sort((a, b) => {
      // If a is premium and b is not, b should come first
      if (a.isPremium && !b.isPremium) {
        return 1;
      }
      // If b is premium and a is not, a should come first
      if (!a.isPremium && b.isPremium) {
        return -1;
      }
      // Otherwise, maintain original order
      return 0;
    });
  }, []);

  // Filter models - show all models including Sonnet 4
  const visibleModels = sortedModels;
  console.log("[MODEL_PICKER_DEBUG] Visible models:", visibleModels.map(m => ({ id: m.id, name: m.name, isPremium: m.isPremium })));

  // Find the current model name or default to R1
  const currentModel = visibleModels.find(m => m.id === selectedModel.id);
  console.log("[MODEL_PICKER_DEBUG] Current model in picker:", currentModel);
  const currentModelName = currentModel?.name || "R1";
  const isCurrentModelPremium = currentModel?.isPremium || false;
  console.log("[MODEL_PICKER_DEBUG] Current model name:", currentModelName, "isPremium:", isCurrentModelPremium);

  const handleModelChange = useCallback((modelId: string) => {
    console.log("[MODEL_PICKER_DEBUG] handleModelChange called with modelId:", modelId);
    
    const model = CHUTES_MODELS.find(m => m.id === modelId);
    console.log("[MODEL_PICKER_DEBUG] Found model in CHUTES_MODELS:", model);
    
    if (model) {
      // Check if user is trying to select a premium model without Pro access
      if (model.isPremium && !userHasProAccess) {
        console.log("[MODEL_PICKER_DEBUG] Premium model selected without Pro access, redirecting to upgrade");
        router.push("/pro-upgrade");
        return;
      }

      // Mark that user has manually switched models
      localStorage.setItem("userManuallySwitchedModel", "true");
      console.log("[MODEL_PICKER_DEBUG] Set userManuallySwitchedModel flag to true");

      // Determine the provider based on the model ID
      let provider: "anthropic" | "chutes" | "openrouter" = "chutes";
      if (modelId.startsWith("claude-")) {
        provider = "anthropic";
      } else if (model.isOpenRouter) {
        provider = "openrouter";
      }
      console.log("[MODEL_PICKER_DEBUG] Determined provider:", provider);
      
      // Determine vision support
      let supportsVision = model.id.includes("V3") || model.id.includes("Maverick");
      // Claude 4 models support vision
      if (modelId === "claude-sonnet-4-0" || modelId === "claude-opus-4-0") {
        supportsVision = true;
      }
      // OpenRouter models support vision
      if (model.isOpenRouter) {
        supportsVision = true;
      }
      console.log("[MODEL_PICKER_DEBUG] Determined vision support:", supportsVision);
      
      // Find the full model object from the provider
      const fullModel = {
        id: model.id,
        name: model.name,
        provider: provider,
        supportsVision: supportsVision
      };
      console.log("[MODEL_PICKER_DEBUG] Setting full model:", fullModel);
      setSelectedModel(fullModel);
    } else {
      console.error("[MODEL_PICKER_DEBUG] Model not found in CHUTES_MODELS for ID:", modelId);
    }
  }, [userHasProAccess, router, setSelectedModel]);

  return (
    <div className="flex items-center gap-2 text-sm">
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