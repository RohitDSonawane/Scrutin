import { motion } from 'framer-motion'
import { useRef } from 'react'
import { AnimatedNetworkLines } from './AnimatedNetworkLines'
import { useIsMobile } from '../hooks/useIsMobile'
import { BlurFadeWords } from '../BlurFadeWords'
import {
  useSectionScale,
  useSectionIntersection,
  MAGIC_BORDER_GRADIENT as MAGIC_BORDER_PURPLE,
  NATIVE_W,
  NATIVE_H,
} from './section-utils'

export interface Section2Props {
  sseData?: {
    findings?: Array<{ agent: string; claim_id: string; stance: string; confidence: number; rationale?: string }>;
    claims?: Array<{ claim_id: string; claim_text: string }>;
    planTasks?: Array<{ task_id: string; agent: string; claim_id: string; parallel_group?: string | null }>;
    provisionalVerdict?: string | null;
  };
}

function StanceBadge({ stance }: { stance: string }) {
  const map: Record<string, { color: string; bg: string; label: string }> = {
    supports:   { color: '#22c55e', bg: 'rgba(34,197,94,0.12)',   label: 'Supports' },
    refutes:    { color: '#ef4444', bg: 'rgba(239,68,68,0.12)',   label: 'Refutes'  },
    mixed:      { color: '#f59e0b', bg: 'rgba(245,158,11,0.12)',  label: 'Mixed'    },
    insufficient: { color: '#6b7280', bg: 'rgba(107,114,128,0.12)', label: 'Insufficient' },
  }
  const info = map[stance?.toLowerCase()] ?? { color: '#6b7280', bg: 'rgba(107,114,128,0.12)', label: stance ?? '?' }
  return (
    <span style={{
      fontFamily: 'var(--font-aeonik)',
      fontSize: '10px', fontWeight: 700, textTransform: 'uppercase' as const,
      letterSpacing: '0.5px', padding: '2px 7px', borderRadius: '6px',
      color: info.color, backgroundColor: info.bg,
      border: `1px solid ${info.color}33`,
    }}>
      {info.label}
    </span>
  )
}

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100)
  const color = pct >= 70 ? '#22c55e' : pct >= 40 ? '#f59e0b' : '#ef4444'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
      <div style={{ flex: 1, height: '3px', borderRadius: '2px', backgroundColor: 'rgba(0,0,0,0.06)' }}>
        <div style={{ width: `${pct}%`, height: '100%', borderRadius: '2px', backgroundColor: color, transition: 'width 0.6s ease' }} />
      </div>
      <span style={{ fontFamily: 'monospace', fontSize: '10px', color: '#999', minWidth: '28px' }}>{pct}%</span>
    </div>
  )
}

// Friendly agent display names
const AGENT_LABELS: Record<string, string> = {
  decomposition: 'Decomposition',
  evidence:      'Evidence',
  credibility:   'Credibility',
  forensics:     'Forensics',
  adversarial:   'Adversarial',
}

export function Section2({ sseData }: Section2Props) {
  const sectionRef = useRef<HTMLElement>(null)
  const isMobile = useIsMobile()
  const isInView = useSectionIntersection(sectionRef, isMobile)
  const scale = useSectionScale()

  const findings  = sseData?.findings  ?? []
  const claims    = sseData?.claims    ?? []
  const planTasks = sseData?.planTasks ?? []
  const provisional = sseData?.provisionalVerdict

  // Use real claims if available, else show pending plan tasks as skeleton
  const claimItems = claims.length > 0 ? claims : planTasks.slice(0, 5).map(t => ({
    claim_id: t.claim_id,
    claim_text: `Analyzing ${AGENT_LABELS[t.agent] ?? t.agent} perspective...`,
  }))

  const cardStyle = {
    width: '100%', height: '100%', borderRadius: '24px',
    background: 'linear-gradient(135deg, rgba(255,255,255,0.55) 0%, rgba(255,248,240,0.35) 100%)',
    backdropFilter: 'blur(20px)',
    border: '1.5px solid rgba(198,120,69,0.22)',
    overflow: 'hidden', position: 'relative' as const, transformOrigin: 'center center',
    boxShadow: 'inset 0 1.5px 0 rgba(255,255,255,0.65), inset 0 -1.5px 3px rgba(100,70,30,0.08), 0 15px 30px rgba(100,70,30,0.05)',
  }

  const card = (
    <div
      style={{
        position: 'relative',
        width: NATIVE_W,
        height: NATIVE_H,
        borderRadius: '24px',
        background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.45) 0%, rgba(255, 248, 240, 0.25) 100%)',
        backdropFilter: 'blur(30px) saturate(160%)',
        border: '1.5px solid rgba(198, 120, 69, 0.22)',
        overflow: 'hidden',
        boxShadow:
          '0 30px 60px -15px rgba(80, 45, 10, 0.12), inset 0 2.5px 5px rgba(255, 255, 255, 0.85), inset 0 -2px 4px rgba(100, 70, 30, 0.05), 0 0 0 1px rgba(198, 120, 69, 0.08)',
      }}
    >
      <img
        src="/assets/card-light-overlay.png"
        alt=""
        style={{
          position: 'absolute',
          top: 0, left: 0,
          width: '100%', height: '100%',
          objectFit: 'cover',
          objectPosition: 'center',
          pointerEvents: 'none',
          zIndex: 999,
          filter: 'drop-shadow(0 0 50px rgba(198, 120, 69, 0.35))',
        }}
      />

      {/* Left: heading + network decoration */}
      <div
        style={{
          position: 'absolute',
          top: '20px',
          left: '65px',
          width: '480px',
          display: 'flex',
          flexDirection: 'column',
          zIndex: 10,
          visibility: isInView ? 'visible' : 'hidden',
        }}
      >
        <motion.div
          initial={{ opacity: 0, x: 48 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.5, duration: 0.85, ease: [0.22, 1, 0.36, 1] }}
          style={{ position: 'relative', width: '320px', height: '80px', marginBottom: '25px', marginLeft: '-30px', marginTop: '10px' }}
        >
          <img
            src="/assets/step-indicator-s2.svg"
            alt="02/03"
            style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'center center', display: 'block', filter: 'grayscale(1) sepia(1) hue-rotate(345deg) saturate(1.8)' }}
          />
          <div style={{
            position: 'absolute', width: '155px', height: '155px',
            top: '50%', left: '44px', transform: 'translate(-50%, -50%)',
            background: 'radial-gradient(circle, rgba(198,120,69,0.12) 0%, rgba(198,120,69,0) 70%)',
            pointerEvents: 'none', borderRadius: '50%',
          }} />
        </motion.div>

        <h1
          style={{
            fontFamily: 'var(--font-jakarta)',
            fontSize: '60px',
            fontWeight: 300,
            lineHeight: 1.05,
            letterSpacing: '-1.5px',
            color: '#171717',
            margin: 0,
            marginBottom: '6px',
            overflow: 'visible',
          }}
        >
          <BlurFadeWords text="Claims & Findings" baseDelay={0.5} isInView={isInView} />
        </h1>

        <p
          style={{
            fontFamily: 'var(--font-jakarta)',
            fontSize: '36px',
            fontWeight: 300,
            lineHeight: 1.18,
            letterSpacing: '-0.6px',
            margin: 0,
            marginBottom: '18px',
            overflow: 'visible',
          }}
        >
          <BlurFadeWords
            text="ai/AgentFindings"
            baseDelay={0.8}
            isInView={isInView}
            wordStyle={{
              background: 'linear-gradient(180deg, #D48E5F 0%, #C67845 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
            }}
          />
        </p>

        <p
          style={{
            fontFamily: 'var(--font-jakarta)',
            fontSize: '19px',
            fontWeight: 300,
            lineHeight: 1.3,
            letterSpacing: '-0.2px',
            color: '#666666',
            margin: 0,
            maxWidth: '400px',
            overflow: 'visible',
          }}
        >
          <BlurFadeWords text="Sub-claims decomposed by the planner agent," baseDelay={1.1} isInView={isInView} />
          <br />
          <BlurFadeWords text="each inspected by a dedicated specialist." baseDelay={1.45} isInView={isInView} />
        </p>
      </div>

      {/* Left bottom: network animation */}
      <div
        style={{
          position: 'absolute',
          left: '35px',
          bottom: '-25px',
          width: '570px',
          height: '358px',
          zIndex: 10,
        }}
      >
        <AnimatedNetworkLines isInView={isInView} color="#C67845" />
      </div>

      {/* Right panel: two sub-cards stacked */}
      <div
        style={{
          position: 'absolute',
          top: '60px',
          bottom: '60px',
          right: '65px',
          width: '400px',
          display: 'flex',
          flexDirection: 'column',
          gap: '16px',
          boxSizing: 'border-box',
          perspective: '1200px',
          zIndex: 60,
        }}
      >

        {/* Top sub-card: Decomposed Claims */}
        <div style={{ flex: 1.1, overflow: 'hidden' }}>
          <motion.div
            initial={{ opacity: 0, x: -200, rotateY: -90, scale: 0.8 }}
            animate={isInView ? { opacity: 1, x: 0, rotateY: 0, scale: 1 } : { opacity: 0, x: -200, rotateY: -90, scale: 0.8 }}
            transition={isInView ? { type: 'spring', stiffness: 32, damping: 22, mass: 1.2 } : { duration: 0 }}
            style={cardStyle}
          >
            <div style={{ padding: '18px 20px', height: '100%', overflow: 'hidden', boxSizing: 'border-box' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
                <span style={{ fontFamily: 'var(--font-aeonik)', fontSize: '12px', textTransform: 'uppercase', letterSpacing: '1px', color: '#C67845', fontWeight: 600 }}>
                  Decomposed Sub-Claims
                </span>
                <span style={{ fontFamily: 'monospace', fontSize: '11px', color: '#999' }}>
                  {claims.length > 0 ? `${claims.length} claims` : `${planTasks.length} tasks`}
                </span>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '7px', maxHeight: '140px', overflowY: 'auto' }}>
                {claimItems.length > 0 ? (
                  claimItems.map((c, i) => (
                    <div key={c.claim_id ?? i} style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', padding: '6px 8px', borderRadius: '8px', backgroundColor: 'rgba(198,120,69,0.04)', border: '1px solid rgba(198,120,69,0.09)' }}>
                      <span style={{ fontFamily: 'monospace', fontSize: '10px', color: '#C67845', fontWeight: 700, marginTop: '1px', flexShrink: 0 }}>
                        {c.claim_id}
                      </span>
                      <span style={{ fontFamily: 'var(--font-aeonik)', fontSize: '12px', color: '#3A2E24', lineHeight: 1.4 }}>
                        {c.claim_text}
                      </span>
                    </div>
                  ))
                ) : (
                  <div style={{ fontFamily: 'var(--font-aeonik)', fontSize: '12px', color: '#999' }}>
                    Awaiting claim decomposition…
                  </div>
                )}
              </div>
            </div>

            {/* Magic border */}
            <div style={{ position: 'absolute', top: 0, bottom: 0, left: 0, right: 0, borderRadius: '24px', pointerEvents: 'none', overflow: 'hidden', zIndex: 60, padding: '2px', WebkitMask: 'linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0)', WebkitMaskComposite: 'xor', maskComposite: 'exclude' }}>
              <motion.div
                style={{ position: 'absolute', left: '50%', top: '50%', width: '250%', height: '250%', background: MAGIC_BORDER_PURPLE, x: '-50%', y: '-50%', transformOrigin: 'center center', willChange: 'transform' }}
                animate={isInView ? { rotate: [0, 360] } : false}
                transition={{ repeat: Infinity, duration: 4, ease: 'linear' }}
              />
            </div>
          </motion.div>
        </div>

        {/* Bottom sub-card: Per-agent findings */}
        <div style={{ flex: 0.9, overflow: 'hidden' }}>
          <motion.div
            initial={{ opacity: 0, x: 200, rotateY: 90, scale: 0.8 }}
            animate={isInView ? { opacity: 1, x: 0, rotateY: 0, scale: 1 } : { opacity: 0, x: 200, rotateY: 90, scale: 0.8 }}
            transition={isInView ? { type: 'spring', stiffness: 32, damping: 22, mass: 1.2, delay: 0.15 } : { duration: 0 }}
            style={cardStyle}
          >
            <div style={{ padding: '16px 20px', height: '100%', overflow: 'hidden', boxSizing: 'border-box' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
                <span style={{ fontFamily: 'var(--font-aeonik)', fontSize: '12px', textTransform: 'uppercase', letterSpacing: '1px', color: '#C67845', fontWeight: 600 }}>
                  Agent Findings
                </span>
                {provisional && (
                  <span style={{ fontFamily: 'var(--font-aeonik)', fontSize: '10px', fontWeight: 700, padding: '2px 8px', borderRadius: '10px', backgroundColor: 'rgba(198,120,69,0.15)', color: '#C67845', textTransform: 'uppercase' }}>
                    {provisional}
                  </span>
                )}
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '110px', overflowY: 'auto' }}>
                {findings.length > 0 ? (
                  findings.slice(-6).map((f, i) => (
                    <div key={i} style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '6px' }}>
                        <span style={{ fontFamily: 'var(--font-aeonik)', fontSize: '12px', color: '#171717', fontWeight: 500 }}>
                          {AGENT_LABELS[f.agent] ?? f.agent}
                          <span style={{ color: '#999', fontWeight: 400 }}> · {f.claim_id}</span>
                        </span>
                        <StanceBadge stance={f.stance} />
                      </div>
                      <ConfidenceBar value={f.confidence} />
                    </div>
                  ))
                ) : (
                  <div style={{ fontFamily: 'var(--font-aeonik)', fontSize: '12px', color: '#999' }}>
                    Awaiting agent findings…
                  </div>
                )}
              </div>
            </div>

            {/* Magic border */}
            <div style={{ position: 'absolute', top: 0, bottom: 0, left: 0, right: 0, borderRadius: '24px', pointerEvents: 'none', overflow: 'hidden', zIndex: 60, padding: '2px', WebkitMask: 'linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0)', WebkitMaskComposite: 'xor', maskComposite: 'exclude' }}>
              <motion.div
                style={{ position: 'absolute', left: '50%', top: '50%', width: '250%', height: '250%', background: MAGIC_BORDER_PURPLE, x: '-50%', y: '-50%', transformOrigin: 'center center', willChange: 'transform' }}
                animate={isInView ? { rotate: [180, 540] } : false}
                transition={{ repeat: Infinity, duration: 4, ease: 'linear' }}
              />
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  )

  return (
    <section
      ref={sectionRef}
      style={{
        width: '100%',
        height: isMobile ? 'auto' : '100vh',
        ...(isMobile ? { minHeight: '100svh', backgroundColor: '#060b0d', overflow: 'hidden' } : {}),
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        contain: 'layout style paint',
      }}
    >
      <div style={{
        position: 'relative',
        flexShrink: 0,
        width: NATIVE_W * scale,
        height: NATIVE_H * scale,
      }}>
        <div style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: NATIVE_W,
          height: NATIVE_H,
          transform: `scale(${scale})`,
          transformOrigin: 'top left',
        }}>
          {card}
        </div>
      </div>
    </section>
  )
}
