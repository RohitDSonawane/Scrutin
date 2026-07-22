import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowLeft } from "lucide-react";
import { CardAgents } from "./cards/CardAgents";
import { CardSearches } from "./cards/CardSearches";
import { CardTrending } from "./cards/CardTrending";
import { CardMisinfo } from "./cards/CardMisinfo";

type Stage = "agents" | "searches" | "news" | "misinfo" | "complete";

const STAGES: { id: Stage; duration: number }[] = [
  { id: "agents", duration: 6000 },
  { id: "searches", duration: 4000 },
  { id: "news", duration: 4000 },
  { id: "misinfo", duration: 4000 },
];

const STATUS_MESSAGES = [
  "Searching government archives",
  "Found 27 sources",
  "3 contradictions detected",
  "Cross-referencing Reuters and BBC",
  "Analyzing source credibility",
  "Checking publication history"
];

export function VerificationWorkspace({ onCancel, queryText }: { onCancel: () => void; queryText: string }) {
  const [currentStageIndex, setCurrentStageIndex] = useState(0);
  const [statusMessageIndex, setStatusMessageIndex] = useState(0);

  useEffect(() => {
    if (currentStageIndex >= STAGES.length) return;
    const stage = STAGES[currentStageIndex];
    const timer = setTimeout(() => {
      setCurrentStageIndex(prev => Math.min(prev + 1, STAGES.length - 1));
    }, stage.duration);
    return () => clearTimeout(timer);
  }, [currentStageIndex]);

  useEffect(() => {
    const timer = setInterval(() => {
      setStatusMessageIndex(prev => (prev + 1) % STATUS_MESSAGES.length);
    }, 1200);
    return () => clearInterval(timer);
  }, []);

  const currentStage = STAGES[currentStageIndex].id;
  const cardNumber = Math.min(currentStageIndex + 1, 4);

  const getCardComponent = (stageId: Stage) => {
    switch (stageId) {
      case "agents": return <CardAgents />;
      case "searches": return <CardSearches />;
      case "news": return <CardTrending />;
      case "misinfo": return <CardMisinfo />;
      default: return null;
    }
  };

  const activeCardComponent = getCardComponent(currentStage);

  return (
    <div className="relative w-full h-full bg-[#FCFAF7] flex flex-col font-sans">
      {/* Top Bar */}
      <div className="absolute top-0 left-0 w-full h-16 flex items-center justify-center z-20 pointer-events-none">
        <div className="flex flex-col items-center gap-2">
          <span className="font-sans text-[13px] text-[#666666]">
            Verification in progress &middot; {cardNumber} of 4
          </span>
          <div className="flex items-center gap-2">
            {[1, 2, 3, 4].map((step) => (
              <div
                key={step}
                className={`w-1.5 h-1.5 rounded-full transition-colors duration-500 ${
                  step === cardNumber ? "bg-[#C67845]" : "border border-[#666666] bg-transparent"
                }`}
              />
            ))}
          </div>
        </div>
      </div>

      <button
        onClick={onCancel}
        className="absolute top-6 left-6 z-30 flex items-center gap-1.5 px-3 py-1.5 rounded-full hover:bg-black/[0.04] transition-colors text-[#666666] font-sans text-[13px] font-medium"
      >
        <ArrowLeft className="w-4 h-4" />
        Back
      </button>

      {/* Main Content Area */}
      <div className="flex-1 w-full flex pt-24 pb-20 overflow-hidden relative">
        {/* Left 70% Active Card Container */}
        <div className="w-[70%] h-full relative flex items-center justify-center z-10 px-12">
          <AnimatePresence mode="popLayout" custom={currentStageIndex}>
            <motion.div
              key={currentStage}
              initial={{ scale: 0.95, opacity: 0, x: 100 }}
              animate={{ scale: 1, opacity: 1, x: 0 }}
              exit={{ scale: 0.95, opacity: 0, x: -200, rotate: -3 }}
              transition={{ duration: 0.7, ease: [0.65, 0, 0.35, 1] }}
              className="w-full max-w-[800px] aspect-[4/3] bg-[#F6F3EE] rounded-[24px] shadow-[0_4px_24px_rgba(0,0,0,0.02)] overflow-hidden border border-black/[0.04]"
            >
              {activeCardComponent}
            </motion.div>
          </AnimatePresence>
        </div>

        {/* Right 30% Card Stack Peek */}
        <div className="w-[30%] h-full relative flex items-center z-0">
          <div className="relative w-full h-full max-h-[800px] flex items-center">
            <AnimatePresence>
              {[1, 2, 3].map((offset) => {
                const stackIndex = currentStageIndex + offset;
                if (stackIndex >= STAGES.length) return null;
                
                let yOffset = 0;
                let xOffset = 0;
                let scale = 1;
                
                if (offset === 1) { xOffset = 60; scale = 0.95; } // Card 2 enters from right
                if (offset === 2) { yOffset = 80; xOffset = 30; scale = 0.9; } // Card 3 from bottomish
                if (offset === 3) { yOffset = -20; xOffset = -20; scale = 0.85; } // Card 4 from leftish

                return (
                  <motion.div
                    key={stackIndex}
                    initial={false}
                    animate={{
                      x: xOffset,
                      y: yOffset,
                      scale: scale,
                      opacity: 1 - offset * 0.2
                    }}
                    transition={{ duration: 0.7, ease: [0.65, 0, 0.35, 1] }}
                    className="absolute left-0 w-[600px] aspect-[4/3] bg-[#F6F3EE] rounded-[24px] shadow-[0_4px_24px_rgba(0,0,0,0.02)] border border-black/[0.04]"
                    style={{ zIndex: -offset }}
                  />
                );
              })}
            </AnimatePresence>
          </div>
        </div>
      </div>

      {/* Bottom Agent Indicator Bar */}
      <div className="fixed bottom-0 left-0 w-full h-[52px] bg-white/90 backdrop-blur-md border-t border-black/[0.06] z-50 flex items-center justify-between px-8">
        <div className="flex items-center gap-3">
          <motion.div
            animate={{ opacity: [1, 0.3, 1] }}
            transition={{ duration: 0.8, repeat: Infinity, ease: "easeInOut" }}
            className="w-2 h-2 rounded-full bg-[#C67845]"
          />
          <span className="font-sans font-medium text-[13px] text-[#171717]">
            Evidence Agent
          </span>
        </div>
        
        <div className="flex-1 flex justify-center">
          <AnimatePresence mode="wait">
            <motion.span
              key={statusMessageIndex}
              initial={{ opacity: 0, y: 5 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -5 }}
              transition={{ duration: 0.2 }}
              className="font-sans text-[13px] text-[#666666]"
            >
              {STATUS_MESSAGES[statusMessageIndex]}
            </motion.span>
          </AnimatePresence>
        </div>

        <div className="font-sans text-[13px] text-[#666666]">
          Verification in progress
        </div>
      </div>
    </div>
  );
}
