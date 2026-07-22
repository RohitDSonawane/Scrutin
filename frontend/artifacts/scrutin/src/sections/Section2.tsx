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

const MAGIC_BORDER_PURPLE = 'conic-gradient(from 0deg, transparent 0%, transparent 35%, rgba(198,120,69,0.15) 42%, #C67845 50%, rgba(198,120,69,0.15) 58%, transparent 65%, transparent 100%)'

const NATIVE_W = 1040
const NATIVE_H = 684

export function Section2() {
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
          <BlurFadeWords text="Related Searches" baseDelay={0.5} isInView={isInView} />
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
            text="ai/PeopleSearching"
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
          <BlurFadeWords text="Discover what queries others are submitting" baseDelay={1.1} isInView={isInView} />
          <br />
          <BlurFadeWords text="and reverse-searching in real-time." baseDelay={1.45} isInView={isInView} />
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
          src="/assets/asterisk-icon.svg"
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
          src="/assets/slack-icon.svg"
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

      <div style={{ perspective: '1200px', position: 'absolute', top: '60px', right: '65px', width: '400px', height: '564px' }}>
        <motion.div
          initial={{ opacity: 0, x: 140, rotateY: -22, scale: 0.88 }}
          animate={isInView ? { opacity: 1, x: 0, rotateY: 0, scale: 1 } : { opacity: 0, x: 140, rotateY: -22, scale: 0.88 }}
          transition={isInView ? { delay: 0.4, duration: 1.2, ease: [0.22, 1, 0.36, 1] } : { duration: 0 }}
          style={{ position: 'relative', width: '100%', height: '100%', transformOrigin: 'right center' }}
        >
          <div
            style={{
              position: 'absolute', inset: 0,
              background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.55) 0%, rgba(255, 248, 240, 0.35) 100%)',
              backdropFilter: 'blur(20px)',
              border: '1.5px solid rgba(198, 120, 69, 0.22)',
              borderRadius: '24px',
              boxShadow: 'inset 0 1.5px 0 rgba(255, 255, 255, 0.65), inset 0 -1.5px 3px rgba(100, 70, 30, 0.08), 0 15px 30px rgba(100, 70, 30, 0.05)',
              padding: '24px',
              boxSizing: 'border-box',
            }}
          >
            <h3 style={{ fontFamily: 'var(--font-aeonik)', fontSize: '18px', fontWeight: 500, color: '#171717', margin: 0, marginBottom: '16px', letterSpacing: '-0.2px' }}>Related Questions Live</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {[
                { q: "Is the viral speech audio clip synthetic?", surge: "+340%" },
                { q: "Where was the background photo taken?", surge: "+180%" },
                { q: "Did the minister announce a curfew?", surge: "Active" },
                { q: "WhatsApp forward fact check on taxation", surge: "Hot" }
              ].map((item, idx) => (
                <div key={idx} style={{ padding: '12px 14px', borderRadius: '12px', border: '1px solid rgba(198,120,69,0.15)', backgroundColor: 'rgba(255,255,255,0.4)', cursor: 'pointer' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                    <span style={{ fontFamily: 'var(--font-aeonik)', fontSize: '14px', fontWeight: 400, color: '#171717' }}>{item.q}</span>
                    <span style={{ fontFamily: 'var(--font-aeonik)', fontSize: '11px', fontWeight: 600, color: '#C67845', padding: '2px 6px', borderRadius: '4px', backgroundColor: 'rgba(198,120,69,0.1)' }}>{item.surge}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div style={{ position: 'absolute', top: 0, bottom: 0, left: 0, right: 0, borderRadius: '24px', pointerEvents: 'none', overflow: 'hidden', zIndex: 60, padding: '2px', WebkitMask: 'linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0)', WebkitMaskComposite: 'xor', maskComposite: 'exclude' }}>
            <motion.div
              style={{ position: 'absolute', left: '50%', top: '50%', width: '250%', height: '250%', background: MAGIC_BORDER_PURPLE, x: '-50%', y: '-50%', transformOrigin: 'center center', filter: 'drop-shadow(0 0 5px rgba(144, 106, 255, 0.5)) drop-shadow(0 0 10px rgba(144, 106, 255, 0.3))', willChange: 'transform' }}
              animate={isInView ? { rotate: [270, 630] } : false}
              transition={{ repeat: Infinity, duration: 10, ease: 'linear' }}
            />
          </div>
        </motion.div>
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
