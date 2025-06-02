"use client";

import { motion } from "framer-motion";
import { Crown, Sparkles, Zap, AlertCircle, Clock } from "lucide-react";
import Link from "next/link";

interface UpgradePromptProps {
  type: "success" | "error" | "timeout";
  className?: string;
}

export default function UpgradePrompt({ type, className = "" }: UpgradePromptProps) {
  const getContent = () => {
    switch (type) {
      case "success":
        return {
          icon: <Sparkles className="w-5 h-5 text-yellow-400" />,
          title: "Great job!",
          message: "Your task completed successfully. For even better results with",
          highlight: "Claude Sonnet 4",
          suffix: ", try",
          linkText: "PRO Mode",
          bgGradient: "from-emerald-500/10 to-green-500/10",
          borderColor: "border-emerald-500/20",
        };
      case "error":
        return {
          icon: <AlertCircle className="w-5 h-5 text-orange-400" />,
          title: "Task encountered an issue",
          message: "This didn't work as expected. It might work better with",
          highlight: "Claude Sonnet 4",
          suffix: " in",
          linkText: "PRO Mode",
          bgGradient: "from-orange-500/10 to-red-500/10",
          borderColor: "border-orange-500/20",
        };
      case "timeout":
        return {
          icon: <Clock className="w-5 h-5 text-blue-400" />,
          title: "Taking longer than expected",
          message: "Complex tasks run faster and more reliably with",
          highlight: "Claude Sonnet 4",
          suffix: " in",
          linkText: "PRO Mode",
          bgGradient: "from-blue-500/10 to-purple-500/10",
          borderColor: "border-blue-500/20",
        };
    }
  };

  const content = getContent();

  return (
    <motion.div
      className={`relative ${className}`}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.5, duration: 0.3 }}
    >
      <div className={`relative bg-gradient-to-r ${content.bgGradient} border ${content.borderColor} rounded-xl p-4 backdrop-blur-sm`}>
        <div className="flex items-start gap-3">
          <div className="flex-shrink-0 mt-0.5">
            {content.icon}
          </div>
          <div className="flex-1 min-w-0">
            <h4 className="text-sm font-semibold text-white mb-1">
              {content.title}
            </h4>
            <p className="text-sm text-white/80">
              {content.message}{" "}
              <span className="font-semibold text-white">{content.highlight}</span>
              {content.suffix}{" "}
              <Link
                href="/pro-upgrade"
                className="inline-flex items-center gap-1 text-yellow-400 hover:text-yellow-300 font-semibold transition-colors group"
              >
                <Crown className="w-3.5 h-3.5" />
                <span className="underline decoration-dotted underline-offset-2">
                  {content.linkText}
                </span>
                <Zap className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity" />
              </Link>
            </p>
          </div>
        </div>
      </div>
    </motion.div>
  );
} 