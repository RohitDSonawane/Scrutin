import { motion, AnimatePresence } from "framer-motion";
import { useEffect, useState } from "react";
import { CheckCircle, Circle, MapPin, Search } from "lucide-react";

const AGENTS = [
  { id: "evidence", label: "Evidence Agent", icon: Search },
  { id: "claim", label: "Claim Agent", icon: CheckCircle },
  { id: "source", label: "Source Agent", icon: MapPin },
  { id: "forensics", label: "Forensics", icon: Search },
  { id: "redteam", label: "Red Team", icon: CheckCircle },
  { id: "reasoning", label: "Reasoning Core", icon: MapPin },
];

const TIMELINE_STEPS = [
  { id: "parsing", label: "Parsing Claim", status: "done" },
  { id: "extracting", label: "Extracting Claims", status: "done" },
  { id: "searching", label: "Searching Sources", status: "done" },
  { id: "scanning", label: "Scanning Government Databases", status: "active" },
  { id: "accessing", label: "Accessing Academic Archives", status: "waiting" },
  { id: "crossref", label: "Cross-referencing", status: "waiting" },
];

export function CardAgents() {
  const [activeAgentIndex, setActiveAgentIndex] = useState(0);
  const [timeLeft, setTimeLeft] = useState(18);

  useEffect(() => {
    const agentTimer = setInterval(() => {
      setActiveAgentIndex((prev) => (prev + 1) % 4); // Only cycle first 4 for demo
    }, 1500);
    return () => clearInterval(agentTimer);
  }, []);

  useEffect(() => {
    const countdown = setInterval(() => {
      setTimeLeft((prev) => Math.max(0, prev - 1));
    }, 1000);
    return () => clearInterval(countdown);
  }, []);

  return (
    <div className="w-full h-full flex flex-col p-10 relative bg-[#F6F3EE]">
      <h2 className="font-serif text-[26px] text-[#171717] mb-8 z-10">
        Where is your agent right now?
      </h2>

      <div className="flex-1 flex gap-10 min-h-0">
        {/* Left Side: Radial Map */}
        <div className="flex-1 relative flex items-center justify-center min-w-0">
          <div className="relative w-64 h-64">
            {/* Center Node */}
            <motion.div
              animate={{ scale: [1, 1.05, 1] }}
              transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
              className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-16 h-16 rounded-full bg-[#C67845]/10 flex items-center justify-center z-10 shadow-[0_0_20px_rgba(198,120,69,0.15)] border border-[#C67845]/20"
            >
              <div className="w-8 h-8 rounded-full border border-[#C67845]/30 flex items-center justify-center">
                 <div className="w-1.5 h-1.5 rounded-full bg-[#C67845]/50" />
              </div>
            </motion.div>

            {/* Agent Nodes */}
            {AGENTS.map((agent, i) => {
              const angle = (i * Math.PI * 2) / AGENTS.length - Math.PI / 2;
              const radius = 100;
              const x = Math.cos(angle) * radius;
              const y = Math.sin(angle) * radius;
              
              let state = "waiting";
              if (i < activeAgentIndex) state = "done";
              else if (i === activeAgentIndex) state = "active";

              return (
                <div
                  key={agent.id}
                  className="absolute top-1/2 left-1/2 flex flex-col items-center gap-2"
                  style={{ transform: `translate(calc(-50% + ${x}px), calc(-50% + ${y}px))` }}
                >
                  {/* Connection Line (SVG) */}
                  <svg className="absolute w-[200px] h-[200px] pointer-events-none" style={{ left: -100, top: -100 }}>
                     <line x1="100" y1="100" x2={100 - x} y2={100 - y} stroke="rgba(0,0,0,0.06)" strokeWidth="1" />
                  </svg>

                  <div className="relative z-10">
                    <AnimatePresence>
                      {state === "active" && (
                        <motion.div
                          initial={{ scale: 0.8, opacity: 1 }}
                          animate={{ scale: 1.5, opacity: 0 }}
                          transition={{ duration: 1.5, repeat: Infinity }}
                          className="absolute inset-0 rounded-full border border-[#C67845] bg-[#C67845]/10"
                        />
                      )}
                    </AnimatePresence>

                    <div className={`w-7 h-7 rounded-full flex items-center justify-center transition-colors duration-500 border ${
                      state === "done" ? "bg-[#3BAA65] border-[#3BAA65] text-white" :
                      state === "active" ? "bg-[#C67845] border-[#C67845] text-white" :
                      "bg-white border-black/[0.08] text-[#666666]"
                    }`}>
                      {state === "done" ? <CheckCircle className="w-4 h-4" /> : <agent.icon className="w-3.5 h-3.5" />}
                    </div>
                  </div>
                  
                  <span className={`font-sans text-[11px] whitespace-nowrap transition-colors duration-300 ${
                    state === "active" ? "text-[#C67845] font-medium" :
                    state === "done" ? "text-[#171717]" :
                    "text-[#666666]"
                  }`}>
                    {agent.label}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Side: Timeline */}
        <div className="w-[280px] flex flex-col justify-center">
          <div className="flex flex-col relative pl-4 border-l border-black/[0.04]">
            {TIMELINE_STEPS.map((step, i) => (
              <motion.div
                key={step.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.5, delay: i * 0.15 }}
                className="relative py-2.5 flex items-center gap-3 group"
              >
                {/* Active Indicator Line */}
                {step.status === "active" && (
                  <motion.div 
                    layoutId="activeTimelineStep"
                    className="absolute left-[-17px] w-0.5 h-full bg-[#C67845] rounded-full" 
                  />
                )}
                
                {/* Icon */}
                <div className="flex-shrink-0 z-10 w-4 flex items-center justify-center absolute left-[-25px] bg-[#F6F3EE] py-1">
                  {step.status === "done" && (
                    <motion.div className="text-[#3BAA65]">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                        <motion.polyline 
                          initial={{ pathLength: 0 }}
                          animate={{ pathLength: 1 }}
                          transition={{ duration: 0.5, delay: 0.2 }}
                          points="20 6 9 17 4 12" 
                        />
                      </svg>
                    </motion.div>
                  )}
                  {step.status === "active" && (
                    <motion.div 
                      animate={{ opacity: [1, 0.4, 1] }} 
                      transition={{ duration: 1.5, repeat: Infinity }}
                      className="w-2.5 h-2.5 rounded-full bg-[#C67845]" 
                    />
                  )}
                  {step.status === "waiting" && (
                    <div className="w-2 h-2 rounded-full bg-black/10" />
                  )}
                </div>

                <span className={`font-sans text-[13px] transition-colors ${
                  step.status === "active" ? "text-[#171717] font-medium" :
                  step.status === "done" ? "text-[#171717]" :
                  "text-[#999999]"
                }`}>
                  {step.label}
                </span>
              </motion.div>
            ))}
          </div>
        </div>
      </div>

      {/* Bottom info */}
      <div className="mt-auto pt-6 flex justify-between items-end border-t border-black/[0.04]">
        <div className="font-sans text-[13px] text-[#666666] tabular-nums">
          Estimated remaining: {timeLeft}s
        </div>
        <div className="font-sans text-[13px] text-[#666666]">
          Evidence Agent &middot; Searching &middot; 27 sources &middot; 3 contradictions found
        </div>
      </div>
    </div>
  );
}
