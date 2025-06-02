"use client";

import { Crown } from "lucide-react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { useRouter } from "next/navigation";

export default function ProUpgradeButton() {
  const router = useRouter();

  const handleUpgradeClick = () => {
    router.push("/pro-upgrade");
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3 }}
    >
      <Button
        onClick={handleUpgradeClick}
        className="relative bg-gradient-to-r from-yellow-500 to-orange-500 hover:from-yellow-600 hover:to-orange-600 text-black font-semibold px-3 py-1.5 rounded-lg shadow-lg hover:shadow-xl transition-all-smooth border-0"
      >
        {/* Glow effect */}
        <div className="absolute inset-0 bg-gradient-to-r from-yellow-400/50 to-orange-400/50 rounded-lg blur-lg opacity-75" />
        
        <div className="relative flex items-center gap-2">
          <Crown className="w-4 h-4" />
          <span className="text-sm font-bold">Upgrade</span>
        </div>
      </Button>
    </motion.div>
  );
} 