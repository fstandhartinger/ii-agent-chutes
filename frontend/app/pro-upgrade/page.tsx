"use client";

import { motion } from "framer-motion";
import { Crown, Sparkles, ArrowLeft, Zap, Brain, Rocket } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useRouter } from "next/navigation";

const STRIPE_PAYMENT_LINK = "https://buy.stripe.com/5kQ00ibzwencbx09wk1Jm00";

export default function ProUpgradePage() {
  const router = useRouter();

  const handleUpgrade = () => {
    window.open(STRIPE_PAYMENT_LINK, '_blank');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-black to-gray-900 text-white">
      {/* Background Effects */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-yellow-500/10 rounded-full blur-3xl animate-pulse" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-orange-500/10 rounded-full blur-3xl animate-pulse delay-1000" />
      </div>

      <div className="relative z-10 container mx-auto px-4 py-8">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="flex items-center gap-4 mb-8"
        >
          <Button
            variant="ghost"
            size="sm"
            onClick={() => router.back()}
            className="text-white/70 hover:text-white hover:bg-white/10"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back
          </Button>
        </motion.div>

        {/* Main Content */}
        <div className="max-w-4xl mx-auto">
          {/* Hero Section */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="text-center mb-12"
          >
            <div className="flex items-center justify-center gap-3 mb-6">
              <Crown className="w-12 h-12 text-yellow-400" />
              <h1 className="text-5xl font-bold bg-gradient-to-r from-yellow-400 to-orange-400 bg-clip-text text-transparent">
                Upgrade to Pro
              </h1>
              <Sparkles className="w-12 h-12 text-orange-400 animate-pulse" />
            </div>
            
            <p className="text-xl text-gray-300 max-w-2xl mx-auto">
              Unlock the power of Claude Sonnet 4 - the most advanced AI model for dramatically better performance and results.
            </p>
          </motion.div>

          {/* Sonnet 4 Benefits */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="bg-glass border border-white/20 rounded-2xl p-8 mb-8 backdrop-blur-xl"
          >
            <div className="text-center mb-8">
              <h2 className="text-3xl font-bold mb-4 flex items-center justify-center gap-3">
                <Brain className="w-8 h-8 text-blue-400" />
                Claude Sonnet 4
                <span className="text-yellow-400 text-lg font-medium">PREMIUM</span>
              </h2>
              <p className="text-gray-300 text-lg">
                Experience the next generation of AI with significantly enhanced capabilities
              </p>
            </div>

            <div className="grid md:grid-cols-3 gap-6">
              <div className="text-center p-6 bg-black/20 rounded-xl border border-white/10">
                <Zap className="w-12 h-12 text-yellow-400 mx-auto mb-4" />
                <h3 className="text-xl font-semibold mb-2">Lightning Fast</h3>
                <p className="text-gray-400">
                  Dramatically faster response times for complex tasks and reasoning
                </p>
              </div>

              <div className="text-center p-6 bg-black/20 rounded-xl border border-white/10">
                <Brain className="w-12 h-12 text-blue-400 mx-auto mb-4" />
                <h3 className="text-xl font-semibold mb-2">Superior Intelligence</h3>
                <p className="text-gray-400">
                  Advanced reasoning, better code generation, and more accurate analysis
                </p>
              </div>

              <div className="text-center p-6 bg-black/20 rounded-xl border border-white/10">
                <Rocket className="w-12 h-12 text-purple-400 mx-auto mb-4" />
                <h3 className="text-xl font-semibold mb-2">Enhanced Performance</h3>
                <p className="text-gray-400">
                  Better handling of complex projects and multi-step workflows
                </p>
              </div>
            </div>
          </motion.div>

          {/* Pricing */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.4 }}
            className="bg-gradient-to-r from-yellow-500/10 to-orange-500/10 border border-yellow-500/30 rounded-2xl p-8 text-center"
          >
            <div className="mb-6">
              <div className="text-4xl font-bold mb-2">
                $20<span className="text-lg text-gray-400">/month</span>
              </div>
              <p className="text-gray-300">
                Full access to Claude Sonnet 4 with premium performance
              </p>
            </div>

            <Button
              onClick={handleUpgrade}
              size="lg"
              className="bg-gradient-to-r from-yellow-500 to-orange-500 hover:from-yellow-600 hover:to-orange-600 text-black font-bold px-8 py-4 text-lg rounded-xl shadow-lg hover:shadow-xl transition-all-smooth border-0"
            >
              <Crown className="w-5 h-5 mr-2" />
              Subscribe Now - $20/month
              <Sparkles className="w-5 h-5 ml-2" />
            </Button>

            <p className="text-sm text-gray-400 mt-4">
              Secure payment powered by Stripe • Cancel anytime
            </p>
          </motion.div>

          {/* Why Upgrade */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.6 }}
            className="mt-12 text-center"
          >
            <h3 className="text-2xl font-bold mb-6">Why Upgrade?</h3>
            <div className="bg-glass border border-white/20 rounded-xl p-6 backdrop-blur-xl">
              <p className="text-gray-300 text-lg leading-relaxed">
                Claude Sonnet 4 represents a significant leap in AI capabilities. Due to the higher computational costs, 
                this premium model is only available in our Pro plan. The investment ensures you get access to the most 
                advanced AI technology available, delivering dramatically better results for your projects.
              </p>
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
} 