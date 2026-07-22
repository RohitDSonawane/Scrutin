import { motion, useAnimation } from 'framer-motion'
import { useEffect, useState, useRef } from 'react'
import { useIsMobile } from '../hooks/useIsMobile'
import { BlurFadeWords } from '../BlurFadeWords'

const sleep = (ms: number) => new Promise<void>(r => setTimeout(r, ms))

const RING_END   = [0.54, 0.69, 0.84, 1.00]
const RING_EXIT  = [0.70, 0.90, 1.09, 1.30]

function OrbitRings({ isActive }: { isActive: boolean }) {
  const c0 = useAnimation()
  const c1 = useAnimation()
  const c2 = useAnimation()
  const c3 = useAnimation()

  useEffect(() => {
    if (!isActive) return
    let cancelled = false
    const loop = async () => {
      if (cancelled) return
      c0.set({ scale: 0.18, opacity: 0 })
      c1.set({ scale: 0.18, opacity: 0 })
      c2.set({ scale: 0.18, opacity: 0 })
      c3.set({ scale: 0.18, opacity: 0 })

      const inT = { duration: 1.0, ease: [0.22, 1, 0.36, 1] as const }
      c0.start({ scale: RING_END[0], opacity: 1, transition: inT })
      await sleep(220)
      if (cancelled) return
      c1.start({ scale: RING_END[1], opacity: 1, transition: inT })
      await sleep(220)
      if (cancelled) return
      c2.start({ scale: RING_END[2], opacity: 1, transition: inT })
      await sleep(220)
      if (cancelled) return
      await c3.start({ scale: RING_END[3], opacity: 1, transition: inT })

      await sleep(700)
      if (cancelled) return

      const outT = { duration: 1.1, ease: [0.76, 0, 0.24, 1] as const }
      await Promise.all([
        c0.start({ scale: RING_EXIT[0], opacity: 0, transition: outT }),
        c1.start({ scale: RING_EXIT[1], opacity: 0, transition: outT }),
        c2.start({ scale: RING_EXIT[2], opacity: 0, transition: outT }),
        c3.start({ scale: RING_EXIT[3], opacity: 0, transition: outT }),
      ])

      await sleep(3000)
      if (!cancelled) loop()
    }
    loop()
    return () => { cancelled = true }
  }, [c0, c1, c2, c3, isActive])

  const srcs = [
    '/assets/orbit-1.svg',
    '/assets/orbit-2.svg',
    '/assets/orbit-3.svg',
    '/assets/orbit-3.svg',
  ]
  const controls = [c0, c1, c2, c3]

  return (
    <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', pointerEvents: 'none', zIndex: 5, willChange: 'transform' }}>
      {srcs.map((src, i) => (
        <motion.img
          key={i}
          src={src}
          alt=""
          initial={{ scale: 0.18, opacity: 0 }}
          animate={controls[i]}
          style={{ position: 'absolute', width: '175%', height: '175%', objectFit: 'contain' }}
        />
      ))}
    </div>
  )
}

const NATIVE_W = 1040
const NATIVE_H = 684

export function Section4() {
  const isMobile = useIsMobile()
  const [scale, setScale] = useState(1)
  const sectionRef = useRef<HTMLElement>(null)
  const [isInView, setIsInView] = useState(false)
  useEffect(() => {
    const el = sectionRef.current
    if (!el) return
    let wasVisible = false
    const enterRatio = isMobile ? 0.3 : 0.45
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

  const card = (
    <div
      style={{
        position: 'relative',
        width: NATIVE_W,
        height: NATIVE_H,
        borderRadius: '24px',
        backgroundColor: 'transparent',
        background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.45) 0%, rgba(255, 248, 240, 0.25) 100%)',
        backdropFilter: 'blur(30px) saturate(160%)',
        border: '1.5px solid rgba(198, 120, 69, 0.22)',
        overflow: 'hidden',
        boxShadow:
          '0 30px 60px -15px rgba(80, 45, 10, 0.12), inset 0 2.5px 5px rgba(255, 255, 255, 0.85), inset 0 -2px 4px rgba(100, 70, 30, 0.05), 0 0 0 1px rgba(198, 120, 69, 0.08)',
      }}
    >
      <OrbitRings isActive={isInView} />

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
          zIndex: 50,
          filter: 'drop-shadow(0 0 50px rgba(198, 120, 69, 0.35))',
        }}
      />

      <div
        style={{
          position: 'absolute',
          top: '80px',
          left: 0, right: 0,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          zIndex: 10,
          visibility: isInView ? 'visible' : 'hidden',
        }}
      >
        <h1
          style={{
            fontFamily: 'var(--font-jakarta)',
            fontSize: '60px',
            fontWeight: 300,
            lineHeight: 1.05,
            letterSpacing: '-1.5px',
            color: '#171717',
            margin: 0,
            marginBottom: '10px',
            overflow: 'visible',
          }}
        >
          <BlurFadeWords text="Regional Alerts" baseDelay={0.3} isInView={isInView} />
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
            text="ai/Disinfo-Watch"
            baseDelay={0.6}
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
            lineHeight: 1.5,
            letterSpacing: '-0.2px',
            color: '#666666',
            margin: 0,
          }}
        >
          <BlurFadeWords text="Active hoaxes and manipulated forwards in your region." baseDelay={1.0} isInView={isInView} />
        </p>

        <div style={{ perspective: '1000px', marginTop: '40px', flexShrink: 0 }}>
          <motion.div
            initial={{ opacity: 0, rotateX: -28, y: 40, scale: 0.88 }}
            animate={isInView ? { opacity: 1, rotateX: 0, y: 0, scale: 1 } : { opacity: 0, rotateX: -28, y: 40, scale: 0.88 }}
            transition={isInView ? { delay: 2.3, duration: 1.3, ease: [0.22, 1, 0.36, 1] } : { duration: 0 }}
            style={{
              position: 'relative',
              width: '420px',
              height: '240px',
              background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.55) 0%, rgba(255, 248, 240, 0.35) 100%)',
              backdropFilter: 'blur(20px)',
              border: '1px solid rgba(255, 255, 255, 0.4)',
              transformOrigin: 'center bottom',
              borderRadius: '20px',
              boxShadow: '0 15px 30px rgba(100, 70, 30, 0.05)',
              padding: '20px',
              boxSizing: 'border-box',
            }}
          >
            <h3 style={{ fontFamily: 'var(--font-aeonik)', fontSize: '16px', fontWeight: 600, color: '#171717', margin: 0, marginBottom: '12px' }}>Local Disinfo watch</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {[
                { label: "WhatsApp forward: Bank Closure voice note", type: "FAKE" },
                { label: "Edited photo of city highway flooding", type: "MANIPULATED" },
                { label: "Unverified emergency alert post on X", type: "UNFOUNDED" }
              ].map((alert, idx) => (
                <div key={idx} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid rgba(0,0,0,0.03)' }}>
                  <span style={{ fontFamily: 'var(--font-aeonik)', fontSize: '13px', color: '#171717', maxWidth: '75%', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{alert.label}</span>
                  <span style={{
                    fontFamily: 'var(--font-aeonik)', fontSize: '10px', fontWeight: 600,
                    color: alert.type === 'FAKE' ? '#E53E3E' : alert.type === 'MANIPULATED' ? '#DD6B20' : '#805AD5',
                    padding: '2px 6px', borderRadius: '4px',
                    backgroundColor: alert.type === 'FAKE' ? 'rgba(229,62,62,0.1)' : alert.type === 'MANIPULATED' ? 'rgba(221,107,32,0.1)' : 'rgba(128,90,213,0.1)'
                  }}>{alert.type}</span>
                </div>
              ))}
            </div>
          </motion.div>
        </div>

        <motion.div
          initial={{ scale: 0 }}
          animate={isInView ? { scale: 1 } : { scale: 0 }}
          transition={isInView ? { delay: 2.5, duration: 0.5, ease: [0.34, 1.56, 0.64, 1] } : { duration: 0 }}
          style={{
            width: '180px', height: '40px',
            marginTop: '30px',
            borderRadius: '999px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
            backgroundColor: 'rgba(255, 255, 255, 0.55)',
            border: '1px solid rgba(198,120,69,0.25)',
            backdropFilter: 'blur(12px)',
          }}
        >
          <img src="/assets/s4-loader-spinner.png" alt="" style={{ width: '18px', height: '18px', flexShrink: 0, filter: 'brightness(0.2)' }} />
          <span style={{ fontFamily: 'var(--font-aeonik)', fontSize: '14px', fontWeight: 400, color: '#171717', whiteSpace: 'nowrap' }}>Open in 25 Sec...</span>
        </motion.div>
      </div>
      <div style={{ position: 'absolute', top: 0, bottom: 0, left: 0, right: 0, borderRadius: '24px', pointerEvents: 'none', overflow: 'hidden', zIndex: 60, padding: '2px', WebkitMask: 'linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0)', WebkitMaskComposite: 'xor', maskComposite: 'exclude' }}>
        <motion.div
          style={{ position: 'absolute', left: '50%', top: '50%', width: '250%', height: '250%', background: 'conic-gradient(from 0deg, transparent 0%, transparent 42%, rgba(198,120,69,0.1) 47%, #C67845 50%, rgba(198,120,69,0.1) 53%, transparent 58%, transparent 100%)', x: '-50%', y: '-50%', transformOrigin: 'center center', filter: 'drop-shadow(0 0 5px rgba(198, 120, 69, 0.5)) drop-shadow(0 0 10px rgba(198, 120, 69, 0.3))', willChange: 'transform' }}
          animate={{ rotate: 360 }}
          transition={{ repeat: Infinity, duration: 10, ease: 'linear' }}
        />
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
          top: 0, left: 0,
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
