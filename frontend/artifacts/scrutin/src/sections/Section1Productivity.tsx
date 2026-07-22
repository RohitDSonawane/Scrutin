import { motion } from 'framer-motion'
import { useState, useEffect, useRef } from 'react'
import { AnimatedNetworkLines } from './AnimatedNetworkLines'
import { useIsMobile } from '../hooks/useIsMobile'
import { BlurFadeWords } from '../BlurFadeWords'

function AnimatedWords({ text, baseDelay = 0, isInView }: {
  text: string
  baseDelay?: number
  isInView: boolean
}) {
  const words = text.split(' ')
  return (
    <>
      {words.map((word, i) => (
        <motion.span
          key={i}
          initial={{ opacity: 0 }}
          animate={{ opacity: isInView ? 1 : 0 }}
          transition={{ delay: baseDelay + i * 0.1, duration: 0.4, ease: 'easeOut' }}
          style={{ display: 'inline' }}
        >
          {word}{i < words.length - 1 ? ' ' : ''}
        </motion.span>
      ))}
    </>
  )
}

const MAGIC_BORDER_GREEN = 'conic-gradient(from 0deg, transparent 0%, transparent 35%, rgba(198,120,69,0.15) 42%, #C67845 50%, rgba(198,120,69,0.15) 58%, transparent 65%, transparent 100%)'

function MagicBorder({ color, radius = '24px', reverse = false, duration = 4, initialAngle = 0, isInView = true }: { color: string; radius?: string; reverse?: boolean; duration?: number; initialAngle?: number; isInView?: boolean }) {
  const fromAngle = reverse ? -initialAngle : initialAngle
  const toAngle = fromAngle + (reverse ? -360 : 360)
  return (
    <div style={{ position: 'absolute', top: 0, bottom: 0, left: 0, right: 0, borderRadius: radius, pointerEvents: 'none', overflow: 'hidden', zIndex: 60, padding: '2px', WebkitMask: 'linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0)', WebkitMaskComposite: 'xor', maskComposite: 'exclude' }}>
      <motion.div
        style={{ position: 'absolute', left: '50%', top: '50%', width: '250%', height: '250%', background: color, x: '-50%', y: '-50%', transformOrigin: 'center center', filter: 'drop-shadow(0 0 5px rgba(198, 120, 69, 0.5)) drop-shadow(0 0 10px rgba(198, 120, 69, 0.3))', willChange: 'transform' }}
        animate={isInView ? { rotate: [fromAngle, toAngle] } : false}
        transition={{ repeat: Infinity, duration, ease: 'linear' }}
      />
    </div>
  )
}

const NATIVE_W = 1040
const NATIVE_H = 684

export function Section1Productivity() {
  const sectionRef = useRef<HTMLElement>(null)
  const [isInView, setIsInView] = useState(false)
  const isMobile = useIsMobile()
  const [scale, setScale] = useState(1)
  useEffect(() => {
    const update = () => {
      const w = window.innerWidth
      const h = window.innerHeight
      setScale(w > 1024 ? Math.min(1, (w * 0.6) / 1040, h / 900) * 0.78 : Math.max(0.28, (w - 24) / NATIVE_W))
    }
    update()
    window.addEventListener('resize', update)
    return () => window.removeEventListener('resize', update)
  }, [])

  useEffect(() => {
    const el = sectionRef.current
    if (!el) return
    let wasVisible = false
    const enterRatio = isMobile ? 0.2 : 0.45
    const exitRatio = isMobile ? 0.05 : 0.1
    const obs = new IntersectionObserver(
      ([entry]) => {
        const ratio = entry.intersectionRatio
        if (entry.isIntersecting && ratio >= enterRatio && !wasVisible) {
          wasVisible = true
          setIsInView(true)
          } else if (!entry.isIntersecting || ratio < exitRatio) {
          wasVisible = false
          setIsInView(false)
        }
      },
      { threshold: [exitRatio, enterRatio] }
    )
    obs.observe(el)
    return () => obs.disconnect()
  }, [isMobile])

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

      <div
        style={{
          position: 'absolute',
          top: '40px',
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
          style={{ position: 'relative', width: '320px', height: '80px', marginBottom: '25px', marginLeft: '-30px' }}
        >
          <img
            src="/assets/s1-notification-badge.svg"
            alt="01/03"
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
          <BlurFadeWords text="Verification Agent" baseDelay={0.5} isInView={isInView} />
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
            text="ai/LiveFactCheck"
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
          <BlurFadeWords text="Tracking agent nodes as they inspect metadata," baseDelay={1.1} isInView={isInView} />
          <br />
          <BlurFadeWords text="geo-data, and cross-source verification live." baseDelay={1.45} isInView={isInView} />
        </p>
      </div>

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

        <motion.img
          src="/assets/asterisk-button.svg"
          alt=""
          initial={{ rotate: 0, opacity: 0 }}
          animate={isInView ? { rotate: [0, 14, 0], opacity: 1 } : { rotate: 0, opacity: 0 }}
          transition={{
            rotate: { delay: 0.1, duration: 1.1, ease: [0.45, 0, 0.55, 1] },
            opacity: { delay: 0.1, duration: 0.7, ease: 'easeOut' },
          }}
          style={{
            position: 'absolute',
            width: '85px', height: '85px',
            left: '48px', top: '134px',
            objectFit: 'contain',
            objectPosition: 'center calc(60% + 2px)',
            backdropFilter: 'blur(12px)',
            backgroundColor: 'rgba(255,255,255,0.55)',
            border: '1px solid rgba(198,120,69,0.15)',
            borderRadius: '20px',
            padding: '1px',
            boxSizing: 'border-box',
          }}
        />

        <motion.img
          src="/assets/discord-button.svg"
          alt=""
          initial={{ scale: 0, rotate: -180, y: -20 }}
          animate={isInView ? { scale: 1, rotate: 0, y: 0 } : { scale: 0, rotate: -180, y: -20 }}
          transition={isInView ? { delay: 2.0, duration: 0.8, ease: [0.22, 1, 0.36, 1] } : { duration: 0 }}
          style={{
            position: 'absolute',
            width: '85px', height: '85px',
            left: '375px', top: '64px',
            objectFit: 'contain',
            objectPosition: 'center calc(50% + 2px)',
            backdropFilter: 'blur(12px)',
            backgroundColor: 'rgba(255,255,255,0.55)',
            border: '1px solid rgba(198,120,69,0.15)',
            borderRadius: '20px',
            padding: '1px',
            boxSizing: 'border-box',
          }}
        />

        <motion.img
          src="/assets/slack-button.svg"
          alt=""
          initial={{ scale: 0, rotate: -180, y: -20 }}
          animate={isInView ? { scale: 1, rotate: 0, y: 0 } : { scale: 0, rotate: -180, y: -20 }}
          transition={isInView ? { delay: 2.35, duration: 0.8, ease: [0.22, 1, 0.36, 1] } : { duration: 0 }}
          style={{
            position: 'absolute',
            width: '85px', height: '85px',
            left: '380px', top: '193px',
            objectFit: 'contain',
            objectPosition: 'center calc(50% + 2px)',
            backdropFilter: 'blur(12px)',
            backgroundColor: 'rgba(255,255,255,0.55)',
            border: '1px solid rgba(198,120,69,0.15)',
            borderRadius: '20px',
            padding: '1px',
            boxSizing: 'border-box',
          }}
        />
      </div>

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
        <div style={{ flex: 1.15, position: 'relative', overflow: 'hidden' }}>
          <motion.div
            initial={{ opacity: 0, x: -200, rotateY: -90, scale: 0.8 }}
            animate={isInView ? { opacity: 1, x: 0, rotateY: 0, scale: 1 } : { opacity: 0, x: -200, rotateY: -90, scale: 0.8 }}
            transition={isInView ? { type: 'spring', stiffness: 32, damping: 22, mass: 1.2 } : { duration: 0 }}
            style={{
              width: '100%',
              height: '100%',
              borderRadius: '24px',
              background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.55) 0%, rgba(255, 248, 240, 0.35) 100%)',
              backdropFilter: 'blur(20px)',
              border: '1.5px solid rgba(198, 120, 69, 0.22)',
              overflow: 'hidden',
              position: 'relative',
              transformOrigin: 'center center',
              boxShadow: 'inset 0 1.5px 0 rgba(255, 255, 255, 0.65), inset 0 -1.5px 3px rgba(100, 70, 30, 0.08), 0 15px 30px rgba(100, 70, 30, 0.05)',
            }}
          >
            <div style={{ padding: '20px 24px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
                <span style={{ fontFamily: 'var(--font-aeonik)', fontSize: '13px', textTransform: 'uppercase', letterSpacing: '1px', color: '#C67845', fontWeight: 600 }}>Active Factcheck Node</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#C67845', display: 'inline-block' }} className="animate-ping" />
                  <span style={{ fontFamily: 'var(--font-aeonik)', fontSize: '12px', color: '#666666' }}>Running...</span>
                </div>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {[
                  { text: 'Extracting source metadata', status: 'done' },
                  { text: 'Reverse lookup & geo-verification', status: 'done' },
                  { text: 'Cross-referencing database nodes', status: 'active' },
                  { text: 'Synthesizing factcheck score', status: 'pending' }
                ].map((item, idx) => (
                  <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '6px 0', borderBottom: '1px solid rgba(0,0,0,0.03)' }}>
                    <div style={{
                      width: '16px', height: '16px', borderRadius: '50%',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      backgroundColor: item.status === 'done' ? 'rgba(198,120,69,0.15)' : item.status === 'active' ? 'rgba(198,120,69,0.1)' : 'transparent',
                      border: `1.5px solid ${item.status === 'pending' ? 'rgba(0,0,0,0.15)' : '#C67845'}`
                    }}>
                      {item.status === 'done' && <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#C67845' }} />}
                      {item.status === 'active' && <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#C67845' }} className="animate-pulse" />}
                    </div>
                    <span style={{ fontFamily: 'var(--font-aeonik)', fontSize: '14px', color: item.status === 'pending' ? '#999999' : '#171717', fontWeight: item.status === 'active' ? 500 : 300 }}>
                      {item.text}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <MagicBorder color={MAGIC_BORDER_GREEN} radius="24px" isInView={isInView} />
          </motion.div>
        </div>

        <div style={{ flex: 0.85, overflow: 'hidden' }}>
          <motion.div
            initial={{ opacity: 0, x: 200, rotateY: 90, scale: 0.8 }}
            animate={isInView ? { opacity: 1, x: 0, rotateY: 0, scale: 1 } : { opacity: 0, x: 200, rotateY: 90, scale: 0.8 }}
            transition={isInView ? { type: 'spring', stiffness: 32, damping: 22, mass: 1.2, delay: 0.15 } : { duration: 0 }}
            style={{
              width: '100%',
              height: '100%',
              borderRadius: '24px',
              background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.55) 0%, rgba(255, 248, 240, 0.35) 100%)',
              backdropFilter: 'blur(20px)',
              border: '1.5px solid rgba(198, 120, 69, 0.22)',
              overflow: 'hidden',
              position: 'relative',
              transformOrigin: 'center center',
              boxShadow: 'inset 0 1.5px 0 rgba(255, 255, 255, 0.65), inset 0 -1.5px 3px rgba(100, 70, 30, 0.08), 0 15px 30px rgba(100, 70, 30, 0.05)',
            }}
          >
            <div style={{ padding: '20px 24px' }}>
              <h3 style={{ fontFamily: 'var(--font-aeonik)', fontSize: '18px', fontWeight: 500, color: '#171717', margin: 0, marginBottom: '10px', letterSpacing: '-0.2px' }}>Query Extraction</h3>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                {['Reverse Search', 'Meta Extraction', 'Electoral database', 'Viral forward', 'Fake news verification'].map((kw) => (
                  <span key={kw} style={{ padding: '4px 10px', borderRadius: '6px', border: '1px solid rgba(198,120,69,0.18)', backgroundColor: 'rgba(255,255,255,0.4)', fontFamily: 'var(--font-aeonik)', fontSize: '12px', color: '#C67845' }}>
                    #{kw}
                  </span>
                ))}
              </div>
            </div>

            <MagicBorder color={MAGIC_BORDER_GREEN} radius="24px" reverse isInView={isInView} />
          </motion.div>
        </div>
      </div>
      <MagicBorder color={MAGIC_BORDER_GREEN} radius="24px" duration={10} initialAngle={180} isInView={isInView} />
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
