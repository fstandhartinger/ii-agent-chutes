"use client";

import { motion } from "framer-motion";
import { useState, useEffect } from "react";

interface ExamplesProps {
  onExampleClick: (text: string, isDeepResearch: boolean, fileUrl?: string) => void;
  className?: string;
}

const EXAMPLES = [
  "research how chutes.ai's role as a bittensor subnet allows them to provide llm inference for free. (Deep Research)",
  "create a report about the psychological benefits of working on something you love.",
  "build a game of tic tac toe with cats for my cat loving girl friend. host it online, so that I can send it to her.",
  "find out everything there is to know about fusion reactors and how far we are from getting them into production use. (Deep Research)",
  //"design a calendar app with all the appointments of my kids. style it like attached style guide file. my kids appointments are: eva: mo-fr school until 1pm, eva: monday afternoon sports, thursday afternoon: theater, jon: mon-thu: kindergarten 8-11 am, fri 9-10: painting for kids (file: https://help.apple.com/pdf/applestyleguide/en_US/apple-style-guide.pdf)",
  "research all about siamese cats (Deep Research)",
  //"tell me where to travel in southeast asia in september, I know not all places have good weather. answer with a report and a scrollable map app that shows red/orange/green indicators.",
  "write a letter to my boss saying thank you for the dinner invitation last time.",
  "design a todo app, styled like attached style guide file. (file: https://help.apple.com/pdf/applestyleguide/en_US/apple-style-guide.pdf)",
];

const Examples = ({ onExampleClick, className }: ExamplesProps) => {
  const [selectedExamples, setSelectedExamples] = useState<string[]>([]);

  // Randomly select 3 examples on component mount
  useEffect(() => {
    const shuffled = [...EXAMPLES].sort(() => 0.5 - Math.random());
    setSelectedExamples(shuffled.slice(0, 3));
  }, []);

  const handleExampleClick = (example: string) => {
    // Check if it has (Deep Research) suffix
    const isDeepResearch = example.includes("(Deep Research)");
    
    // Check if it has (file: url) pattern
    const fileMatch = example.match(/\(file: (https?:\/\/[^\)]+)\)/);
    const fileUrl = fileMatch ? fileMatch[1] : undefined;
    
    // Clean the text by removing the suffixes
    const cleanText = example
      .replace(/\s*\(Deep Research\)$/, "")
      .replace(/\s*\(file: https?:\/\/[^\)]+\)/, "");
    
    onExampleClick(cleanText, isDeepResearch, fileUrl);
  };

  const truncateText = (text: string, maxLength: number = 80) => {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + "...";
  };

  if (selectedExamples.length === 0) return null;

  return (
    <motion.div
      className={`w-full max-w-4xl ${className}`}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, delay: 0.3 }}
    >
      <motion.h3
        className="text-lg font-medium text-muted-foreground mb-4 text-center"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.4 }}
      >
        Try one of these
      </motion.h3>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {selectedExamples.map((example, index) => {
          const cleanExample = example
            .replace(/\s*\(Deep Research\)$/, "")
            .replace(/\s*\(file: https?:\/\/[^\)]+\)/, "");
          
          return (
            <motion.button
              key={index}
              className="group relative bg-glass border border-white/20 rounded-xl p-4 text-left hover:bg-white/10 transition-all-smooth hover-lift shadow-lg backdrop-blur-sm"
              onClick={() => handleExampleClick(example)}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 + index * 0.1 }}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              {/* Gradient Border Effect */}
              <div className="absolute inset-0 bg-gradient-to-r from-blue-500/10 via-purple-500/10 to-emerald-500/10 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
              
              <div className="relative">
                <p className="text-sm text-white/90 leading-relaxed">
                  {truncateText(cleanExample)}
                </p>
                
                {/* Indicators */}
                <div className="flex items-center gap-2 mt-3">
                  {example.includes("(Deep Research)") && (
                    <span className="inline-flex items-center px-2 py-1 rounded-md bg-gradient-skyblue-lavender text-black text-xs font-medium">
                      Deep Research
                    </span>
                  )}
                  {example.includes("(file:") && (
                    <span className="inline-flex items-center px-2 py-1 rounded-md bg-emerald-500/20 text-emerald-300 text-xs font-medium border border-emerald-500/30">
                      File Attached
                    </span>
                  )}
                </div>
              </div>
            </motion.button>
          );
        })}
      </div>
    </motion.div>
  );
};

export default Examples; 