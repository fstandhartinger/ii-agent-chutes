"use client";

import { Button } from "@/components/ui/button";
import { ArrowLeft, ExternalLink, Trophy, Star } from "lucide-react";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import Image from "next/image";

// Commented out for potential future reactivation
/*
interface GaiaResult {
  agent_name: string;
  question: string;
  prediction: string;
  task: string;
  task_id: string;
  true_answer: string;
  start_time: string;
  end_time: string;
  iteration_limit_exceeded: boolean;
  agent_error: string | null;
}

interface GaiaSummary {
  total_tasks: number;
  completed_tasks: number;
  completion_rate: number;
  run_name: string;
  set_to_run: string;
}

interface GaiaResponse {
  status: string;
  results: GaiaResult[];
  summary: GaiaSummary;
  message?: string;
}
*/

export default function GaiaPage() {
  // Commented out for potential future reactivation
  /*
  const [isRunning, setIsRunning] = useState(false);
  const [results, setResults] = useState<GaiaResponse | null>(null);
  const [maxTasks, setMaxTasks] = useState(5);
  const [setToRun, setSetToRun] = useState<"validation" | "test">("validation");
  const { selectedModel } = useChutes();
  */
  const router = useRouter();

  // Commented out for potential future reactivation
  /*
  const runGaiaBenchmark = async () => {
    setIsRunning(true);
    setResults(null);
    
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/gaia/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          set_to_run: setToRun,
          run_name: `gaia-run-${Date.now()}`,
          max_tasks: maxTasks,
          model_id: selectedModel.id,
          model_provider: selectedModel.provider
        })
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data: GaiaResponse = await response.json();
      
      if (data.status === "success") {
        setResults(data);
        toast.success("GAIA benchmark completed successfully!");
      } else {
        toast.error(`Benchmark failed: ${data.message}`);
        setResults(data);
      }
    } catch (error) {
      console.error("GAIA benchmark failed:", error);
      toast.error("Failed to run GAIA benchmark");
    } finally {
      setIsRunning(false);
    }
  };
  */

  return (
    <div className="min-h-screen bg-background relative overflow-hidden">
      {/* Background Elements */}
      <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 via-purple-500/5 to-emerald-500/5" />
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl animate-pulse" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl animate-pulse delay-1000" />
      
      <div className="relative z-10 container mx-auto p-4 md:p-8 max-w-6xl">
        {/* Header */}
        <motion.div
          className="flex items-center gap-4 mb-8"
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <Button
            variant="outline"
            size="sm"
            onClick={() => router.push("/")}
            className="bg-glass border-white/20 hover:bg-white/10 transition-all-smooth hover-lift"
          >
            <ArrowLeft className="w-4 h-4" />
          </Button>
          <div className="flex items-center gap-3">
            <Trophy className="w-8 h-8 text-yellow-400" />
            <h1 className="text-3xl md:text-4xl font-bold bg-gradient-to-r from-yellow-400 via-orange-400 to-red-400 bg-clip-text text-transparent">
              GAIA Benchmark Leader
            </h1>
          </div>
        </motion.div>

        {/* Record Achievement Banner */}
        <motion.div
          className="bg-gradient-to-r from-yellow-500/20 via-orange-500/20 to-red-500/20 rounded-2xl border border-yellow-400/30 p-6 mb-8"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}
        >
          <div className="flex items-center gap-3 mb-4">
            <Star className="w-6 h-6 text-yellow-400" />
            <h2 className="text-2xl font-bold text-yellow-400">Record-Breaking Performance</h2>
          </div>
          <p className="text-lg text-white/90 mb-4">
            <strong>fubea</strong>, our AI agent powered by <strong>ii-agent</strong>, holds the current record on the GAIA benchmark - 
            the most important benchmark for Deep Research AI capabilities.
          </p>
          <div className="flex flex-wrap gap-4 text-sm text-white/80">
            <span>🏆 Leading performance: 75.57%</span>
            <span>🔬 Deep Research Excellence</span>
            <span>🚀 Powered by ii-agent technology</span>
          </div>
        </motion.div>

        {/* About GAIA Benchmark */}
        <motion.div
          className="bg-glass-dark rounded-2xl border border-white/10 p-6 mb-8"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
        >
          <h2 className="text-xl font-semibold mb-4">About the GAIA Benchmark</h2>
          <p className="text-muted-foreground mb-4">
            GAIA (General AI Assistant) is the most important benchmark for evaluating AI agents on real-world tasks 
            requiring advanced reasoning, research capabilities, and tool usage. It represents the gold standard for 
            measuring Deep Research AI performance.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-muted-foreground">
            <div className="space-y-2">
              <span className="block">• Complex multi-step reasoning tasks</span>
              <span className="block">• Real-world research challenges</span>
              <span className="block">• Advanced tool usage requirements</span>
            </div>
            <div className="space-y-2">
              <span className="block">• Document analysis and comprehension</span>
              <span className="block">• Web research and fact verification</span>
              <span className="block">• Problem-solving automation</span>
            </div>
          </div>
        </motion.div>

        {/* Benchmark Results Image */}
        <motion.div
          className="bg-glass-dark rounded-2xl border border-white/10 p-6 mb-8"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.3 }}
        >
          <h2 className="text-xl font-semibold mb-6 text-center">GAIA Benchmark Results</h2>
          <div className="flex justify-center">
            <div className="relative max-w-4xl w-full">
              <Image
                src="/benchmark_scores.png"
                alt="GAIA Benchmark Results showing fubea's leading performance of 75.57%"
                width={1335}
                height={1107}
                className="rounded-lg border border-white/20 shadow-2xl"
                priority
              />
            </div>
          </div>
          <p className="text-center text-muted-foreground mt-4 text-sm">
            fubea achieves 75.57% on the GAIA benchmark, outperforming other leading AI systems
          </p>
        </motion.div>

        {/* Technology Behind fubea */}
        <motion.div
          className="bg-glass-dark rounded-2xl border border-white/10 p-6 mb-8"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.4 }}
        >
          <h2 className="text-xl font-semibold mb-4">Powered by ii-agent</h2>
          <p className="text-muted-foreground mb-4">
            fubea is built on top of <strong>ii-agent</strong>, our advanced AI agent framework that enables 
            sophisticated reasoning, research, and problem-solving capabilities. This technology stack allows 
            fubea to excel at complex, multi-step tasks that require deep understanding and autonomous execution.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-glass rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-blue-400 mb-2">Advanced</div>
              <div className="text-sm text-muted-foreground">Reasoning Engine</div>
            </div>
            <div className="bg-glass rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-green-400 mb-2">Autonomous</div>
              <div className="text-sm text-muted-foreground">Research Capabilities</div>
            </div>
            <div className="bg-glass rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-purple-400 mb-2">Integrated</div>
              <div className="text-sm text-muted-foreground">Tool Ecosystem</div>
            </div>
          </div>
        </motion.div>

        {/* Call to Action */}
        <motion.div
          className="bg-glass-dark rounded-2xl border border-white/10 p-6 text-center"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.5 }}
        >
          <h2 className="text-xl font-semibold mb-4">Experience Record-Breaking AI</h2>
          <p className="text-muted-foreground mb-6">
            Try fubea today and experience the same AI technology that achieved the leading score on the GAIA benchmark.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Button
              onClick={() => router.push("/")}
              className="bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600 text-white"
              size="lg"
            >
              Try fubea Now
            </Button>
            <Button
              onClick={() => window.open("https://x.com/ii_posts/status/1924818953756373145/photo/1", "_blank")}
              variant="outline"
              className="bg-glass border-white/20 hover:bg-white/10 flex items-center gap-2"
              size="lg"
            >
              <ExternalLink className="w-4 h-4" />
              View Announcement
            </Button>
          </div>
        </motion.div>

        {/* Commented out benchmark execution functionality for potential future reactivation */}
        {/*
        {!isRunning && !results && (
          <motion.div
            className="bg-glass-dark rounded-2xl border border-white/10 p-6 mb-8"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
          >
            <h2 className="text-xl font-semibold mb-4">Configuration</h2>
            <div className="mb-4 p-3 bg-blue-500/10 border border-blue-500/20 rounded-lg">
              <p className="text-sm text-blue-400">
                <strong>Selected Model:</strong> {selectedModel.name} ({selectedModel.provider})
              </p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
              <div>
                <label className="block text-sm font-medium mb-2">Dataset</label>
                <select
                  value={setToRun}
                  onChange={(e) => setSetToRun(e.target.value as "validation" | "test")}
                  className="w-full p-3 bg-black/50 border border-white/20 rounded-lg text-white [&>option]:bg-black [&>option]:text-white"
                >
                  <option value="validation" className="bg-black text-white">Validation Set</option>
                  <option value="test" className="bg-black text-white">Test Set</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Max Tasks (Demo)</label>
                <input
                  type="number"
                  min="1"
                  max="20"
                  value={maxTasks}
                  onChange={(e) => setMaxTasks(parseInt(e.target.value) || 5)}
                  className="w-full p-3 bg-black/50 border border-white/20 rounded-lg text-white placeholder-white/50"
                />
              </div>
            </div>
            
            <Button 
              onClick={runGaiaBenchmark} 
              className="flex items-center gap-2 bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600 text-white"
              size="lg"
            >
              <Play className="w-5 h-5" />
              Run GAIA Benchmark
            </Button>
          </motion.div>
        )}

        {isRunning && (
          <motion.div
            className="bg-glass-dark rounded-2xl border border-white/10 p-8 text-center"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.6 }}
          >
            <Loader2 className="w-12 h-12 text-blue-400 animate-spin mb-4 mx-auto" />
            <h2 className="text-2xl font-semibold mb-2">Running GAIA Benchmark</h2>
            <p className="text-muted-foreground mb-4">
              Evaluating fubea with {selectedModel.name} on {maxTasks} tasks from the {setToRun} set...
            </p>
            <div className="text-sm text-muted-foreground">
              This may take several minutes depending on task complexity.
            </div>
          </motion.div>
        )}

        {results && (
          <motion.div
            className="space-y-6"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <div className="bg-glass-dark rounded-2xl border border-white/10 p-6">
              <div className="flex items-center gap-3 mb-4">
                {results.status === "success" ? (
                  <CheckCircle className="w-6 h-6 text-green-400" />
                ) : (
                  <AlertCircle className="w-6 h-6 text-red-400" />
                )}
                <h2 className="text-2xl font-semibold">
                  {results.status === "success" ? "Benchmark Complete" : "Benchmark Failed"}
                </h2>
              </div>
              
              {results.summary && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                  <div className="bg-glass rounded-lg p-4 text-center">
                    <div className="text-2xl font-bold text-blue-400">{results.summary.total_tasks}</div>
                    <div className="text-sm text-muted-foreground">Total Tasks</div>
                  </div>
                  <div className="bg-glass rounded-lg p-4 text-center">
                    <div className="text-2xl font-bold text-green-400">{results.summary.completed_tasks}</div>
                    <div className="text-sm text-muted-foreground">Completed</div>
                  </div>
                  <div className="bg-glass rounded-lg p-4 text-center">
                    <div className="text-2xl font-bold text-purple-400">
                      {(results.summary.completion_rate * 100).toFixed(1)}%
                    </div>
                    <div className="text-sm text-muted-foreground">Success Rate</div>
                  </div>
                  <div className="bg-glass rounded-lg p-4 text-center">
                    <div className="text-2xl font-bold text-orange-400">{results.summary.set_to_run}</div>
                    <div className="text-sm text-muted-foreground">Dataset</div>
                  </div>
                </div>
              )}

              {results.message && (
                <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4 mb-4">
                  <p className="text-red-400 whitespace-pre-wrap">{results.message}</p>
                  {results.message.includes("GAIA dependencies not installed") && (
                    <div className="mt-3 p-3 bg-yellow-500/10 border border-yellow-500/20 rounded-lg">
                      <p className="text-yellow-400 text-sm">
                        <strong>Note:</strong> The GAIA benchmark requires additional Python dependencies. 
                        Please contact the administrator to install the required packages.
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>

            {results.results && results.results.length > 0 && (
              <div className="bg-glass-dark rounded-2xl border border-white/10 p-6">
                <h3 className="text-xl font-semibold mb-4">Detailed Results</h3>
                <div className="space-y-4 max-h-96 overflow-y-auto">
                  {results.results.map((result, index) => (
                    <div key={index} className="bg-glass rounded-lg p-4 border border-white/10">
                      <div className="flex items-start justify-between mb-2">
                        <h4 className="font-medium text-sm">Task {index + 1} - {result.task}</h4>
                        <span className={`px-2 py-1 rounded text-xs ${
                          result.prediction ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
                        }`}>
                          {result.prediction ? 'Completed' : 'Failed'}
                        </span>
                      </div>
                      <p className="text-sm text-muted-foreground mb-2 line-clamp-2">
                        {result.question}
                      </p>
                      {result.agent_error && (
                        <p className="text-xs text-red-400 bg-red-500/10 rounded p-2">
                          Error: {result.agent_error}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="flex gap-4">
              <Button
                onClick={() => {
                  setResults(null);
                  setIsRunning(false);
                }}
                variant="outline"
                className="bg-glass border-white/20 hover:bg-white/10"
              >
                Run Another Test
              </Button>
              <Button
                onClick={() => router.push("/")}
                variant="outline"
                className="bg-glass border-white/20 hover:bg-white/10"
              >
                Back to Home
              </Button>
            </div>
          </motion.div>
        )}
        */}
      </div>
    </div>
  );
} 