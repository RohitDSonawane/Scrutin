import { motion } from 'framer-motion';
import { ArrowLeft, ShieldAlert, ShieldCheck, AlertTriangle, ShieldQuestion } from 'lucide-react';
import type { VerificationReport } from "@workspace/api-client-react";

const highlightText = (text: string) => {
  if (!text) return null;
  // Match text in single quotes, double quotes, or parentheses
  const regex = /(['"(][^'"()]+['")])/g;
  const parts = text.split(regex);
  return parts.map((part, i) => {
    if (regex.test(part)) {
      return <span key={i} style={{ color: '#9c4c1c', fontWeight: 500, backgroundColor: 'rgba(198, 120, 69, 0.08)', padding: '0 4px', borderRadius: '4px' }}>{part}</span>;
    }
    return part;
  });
};

export function VerificationResult({ result, onReset }: { result: VerificationReport, onReset: () => void }) {
  const getVerdictInfo = (verdict: string) => {
    switch(verdict) {
      case 'true': return { color: '#22c55e', bg: 'rgba(34, 197, 94, 0.1)', icon: ShieldCheck, label: 'True' };
      case 'false': return { color: '#ef4444', bg: 'rgba(239, 68, 68, 0.1)', icon: ShieldAlert, label: 'False' };
      case 'misleading': return { color: '#f59e0b', bg: 'rgba(245, 158, 11, 0.1)', icon: AlertTriangle, label: 'Misleading' };
      default: return { color: '#666666', bg: 'rgba(102, 102, 102, 0.1)', icon: ShieldQuestion, label: 'Inconclusive' };
    }
  };

  const vInfo = getVerdictInfo(String(result.overall_verdict));
  const Icon = vInfo.icon;

  return (
    <div className="w-full max-w-[1040px] flex flex-col relative px-4 md:px-0">
      
      {/* Top Action Bar */}
      <div className="w-full flex items-center justify-start mb-8 z-50">
        <button 
          onClick={onReset}
          className="flex items-center gap-2 px-5 py-2.5 rounded-full transition-all cursor-pointer hover:scale-105 active:scale-95"
          style={{
            background: 'rgba(230, 226, 215, 0.85)',
            backdropFilter: 'blur(12px)',
            border: '1px solid rgba(255, 255, 255, 0.3)',
            boxShadow: '0 4px 12px rgba(0,0,0,0.03), inset 0 1px 0 rgba(255,255,255,0.6)',
            color: '#2B231D',
            fontFamily: 'var(--font-jakarta)',
            fontSize: '15px',
            fontWeight: 400
          }}
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Search</span>
        </button>
      </div>

      {/* Main Glass Card matching Section1Productivity */}
      <motion.div 
        initial={{ opacity: 0, y: 40 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.85, ease: [0.22, 1, 0.36, 1] }}
        className="w-full rounded-[24px] overflow-hidden p-6 md:p-10 lg:px-[65px] lg:py-[50px]"
        style={{
          background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.45) 0%, rgba(255, 248, 240, 0.25) 100%)',
          backdropFilter: 'blur(30px) saturate(160%)',
          border: '1.5px solid rgba(198, 120, 69, 0.22)',
          boxShadow: '0 30px 60px -15px rgba(80, 45, 10, 0.12), inset 0 2.5px 5px rgba(255, 255, 255, 0.85), inset 0 -2px 4px rgba(100, 70, 30, 0.05), 0 0 0 1px rgba(198, 120, 69, 0.08)',
        }}
      >
        {/* Header section with Claim and Verdict */}
        <div className="flex flex-col md:flex-row justify-between items-start mb-8 md:mb-10 gap-6 md:gap-10">
          <div className="flex-1">
            <motion.h2 
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.2, duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
              style={{ fontFamily: 'var(--font-aeonik)', fontSize: '13px', textTransform: 'uppercase', letterSpacing: '1px', color: '#C67845', fontWeight: 600, marginBottom: '16px' }}
            >
              Claim Analyzed
            </motion.h2>
            <motion.p 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.4, duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
              style={{ fontFamily: 'var(--font-jakarta)', fontSize: 'clamp(24px, 4vw, 32px)', fontWeight: 300, lineHeight: 1.2, letterSpacing: '-0.6px', color: '#171717', margin: 0 }}
            >
              "{result.raw_input}"
            </motion.p>
          </div>

          <motion.div 
            initial={{ opacity: 0, scale: 0.8, rotate: -5 }}
            animate={{ opacity: 1, scale: 1, rotate: 0 }}
            transition={{ delay: 0.5, duration: 0.8, ease: [0.22, 1, 0.36, 1], type: 'spring', bounce: 0.4 }}
            className="flex flex-col items-center justify-center py-6 px-8 rounded-[24px] min-w-full md:min-w-[200px]"
            style={{ 
              backgroundColor: vInfo.bg, color: vInfo.color,
              border: `1.5px solid ${vInfo.color}33`,
            }}
          >
            <Icon style={{ width: '40px', height: '40px', marginBottom: '12px' }} />
            <span style={{ fontFamily: 'var(--font-aeonik)', fontSize: '18px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '1px' }}>
              {vInfo.label}
            </span>
          </motion.div>
        </div>

        {/* Inner detail cards */}
        <div className="flex flex-col md:flex-row gap-6 mb-6">
          
          {/* Credibility Score Card */}
          <motion.div 
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3, duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
            className="flex-[0.4] rounded-[24px] p-6 md:p-8"
            style={{
              background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.55) 0%, rgba(255, 248, 240, 0.35) 100%)',
              backdropFilter: 'blur(20px)',
              border: '1.5px solid rgba(198, 120, 69, 0.22)',
              boxShadow: 'inset 0 1.5px 0 rgba(255, 255, 255, 0.65), inset 0 -1.5px 3px rgba(100, 70, 30, 0.08), 0 15px 30px rgba(100, 70, 30, 0.05)',
            }}
          >
            <h3 style={{ fontFamily: 'var(--font-aeonik)', fontSize: '13px', textTransform: 'uppercase', letterSpacing: '1px', color: '#C67845', fontWeight: 600, marginBottom: '20px' }}>
              Credibility Score
            </h3>
            <div style={{ display: 'flex', alignItems: 'flex-end', gap: '4px', marginBottom: '16px' }}>
              <span style={{ fontFamily: 'var(--font-jakarta)', fontSize: 'clamp(48px, 6vw, 64px)', fontWeight: 300, lineHeight: 1, letterSpacing: '-2px', color: '#171717' }}>
                {Math.round(result.credibility_score)}
              </span>
              <span style={{ fontFamily: 'var(--font-jakarta)', fontSize: '20px', fontWeight: 300, color: '#999999', paddingBottom: '6px' }}>
                /100
              </span>
            </div>
            <div style={{ 
              display: 'inline-flex', padding: '6px 12px', borderRadius: '12px', 
              background: 'rgba(198, 120, 69, 0.1)', border: '1px solid rgba(198, 120, 69, 0.2)',
              fontFamily: 'var(--font-aeonik)', fontSize: '12px', color: '#C67845', fontWeight: 500
            }}>
              AI Confidence: {Math.round(result.confidence * 100)}%
            </div>
          </motion.div>

          {/* Source Analysis Card */}
          <motion.div 
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4, duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
            className="flex-[0.6] rounded-[24px] p-6 md:p-8"
            style={{
              background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.55) 0%, rgba(255, 248, 240, 0.35) 100%)',
              backdropFilter: 'blur(20px)',
              border: '1.5px solid rgba(198, 120, 69, 0.22)',
              boxShadow: 'inset 0 1.5px 0 rgba(255, 255, 255, 0.65), inset 0 -1.5px 3px rgba(100, 70, 30, 0.08), 0 15px 30px rgba(100, 70, 30, 0.05)',
            }}
          >
            <h3 style={{ fontFamily: 'var(--font-aeonik)', fontSize: '13px', textTransform: 'uppercase', letterSpacing: '1px', color: '#C67845', fontWeight: 600, marginBottom: '16px' }}>
              Source Trust & Analysis
            </h3>
            <p style={{ fontFamily: 'var(--font-jakarta)', fontSize: '15.5px', fontWeight: 400, lineHeight: 1.6, color: '#3A2E24', margin: 0 }}>
              {highlightText(result.source_credibility_notes)}
            </p>
          </motion.div>
          
        </div>

        {/* Adversarial Analysis full width card */}
        <motion.div 
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5, duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
          className="w-full rounded-[24px] p-6 md:p-8"
          style={{
            background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.55) 0%, rgba(255, 248, 240, 0.35) 100%)',
            backdropFilter: 'blur(20px)',
            border: '1.5px solid rgba(198, 120, 69, 0.22)',
            boxShadow: 'inset 0 1.5px 0 rgba(255, 255, 255, 0.65), inset 0 -1.5px 3px rgba(100, 70, 30, 0.08), 0 15px 30px rgba(100, 70, 30, 0.05)',
          }}
        >
          <h3 style={{ fontFamily: 'var(--font-aeonik)', fontSize: '13px', textTransform: 'uppercase', letterSpacing: '1px', color: '#C67845', fontWeight: 600, marginBottom: '16px' }}>
            Adversarial Check
          </h3>
          <p style={{ fontFamily: 'var(--font-jakarta)', fontSize: '15.5px', fontWeight: 400, lineHeight: 1.6, color: '#3A2E24', margin: 0 }}>
            {highlightText(result.adversarial_summary)}
          </p>
        </motion.div>
        
      </motion.div>
    </div>
  );
}
