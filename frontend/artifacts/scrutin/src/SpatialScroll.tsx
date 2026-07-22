import { useCallback, useEffect, useRef } from 'react'
import { motion, useMotionValue, animate } from 'framer-motion'
import { Section1Productivity } from './sections/Section1Productivity'
import { Section2 } from './sections/Section2'
import { Section3 } from './sections/Section3'
import { Section4 } from './sections/Section4'
import { useIsMobile } from './hooks/useIsMobile'

const SECTION_POSITIONS = [
  { x: 0, y: 0 },
  { x: -1, y: 0 },
  { x: -1, y: -1 },
  { x: 0, y: -1 },
]

export function SpatialScroll() {
  const isMobile = useIsMobile()
  const isPhone = useIsMobile(600)
  const x = useMotionValue(0)
  const y = useMotionValue(0)
  const sectionRef = useRef(0)
  const isAnimating = useRef(false)
  const hasLooped = useRef(false)
  const touchStart = useRef<{ x: number; y: number } | null>(null)
  const scrollContainerRef = useRef<HTMLDivElement>(null)

  const posFor = useCallback((idx: number) => {
    const pos = SECTION_POSITIONS[idx]
    const baseW = isMobile ? window.innerWidth : window.innerWidth * 0.6
    const baseH = window.innerHeight
    return {
      tx: pos.x * baseW,
      ty: pos.y * baseH,
    }
  }, [isMobile])

  const goTo = useCallback((idx: number) => {
    if (isAnimating.current) return
    isAnimating.current = true
    if (sectionRef.current === 3 && idx === 0) hasLooped.current = true
    const { tx, ty } = posFor(idx)
    animate(x, tx, { duration: 0.85, ease: [0.76, 0, 0.24, 1] })
    animate(y, ty, { duration: 0.85, ease: [0.76, 0, 0.24, 1] })
    sectionRef.current = idx
    setTimeout(() => { isAnimating.current = false }, 950)
  }, [x, y, posFor])

  // Continuous loop timer - transitions automatically every 7 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      goTo((sectionRef.current + 1) % 4)
    }, 7000)
    return () => clearInterval(interval)
  }, [goTo])

  useEffect(() => {
    if (isMobile) return
    const handleWheel = (e: WheelEvent) => {
      e.preventDefault()
      if (isAnimating.current) return
      if (Math.abs(e.deltaY) < 5) return
      const dir = e.deltaY > 0 ? 1 : -1
      if (!hasLooped.current && sectionRef.current === 0 && dir === -1) return
      goTo((sectionRef.current + dir + 4) % 4)
    }
    window.addEventListener('wheel', handleWheel, { passive: false })
    return () => window.removeEventListener('wheel', handleWheel)
  }, [goTo, isMobile])

  useEffect(() => {
    if (isMobile) return
    let timer: ReturnType<typeof setTimeout>
    const handleResize = () => {
      clearTimeout(timer)
      timer = setTimeout(() => {
        const { tx, ty } = posFor(sectionRef.current)
        x.set(tx)
        y.set(ty)
      }, 100)
    }
    window.addEventListener('resize', handleResize)
    return () => { window.removeEventListener('resize', handleResize); clearTimeout(timer) }
  }, [x, y, posFor, isMobile])

  useEffect(() => {
    if (isMobile) return
    const onTouchStart = (e: TouchEvent) => {
      const t = e.touches[0]
      touchStart.current = { x: t.clientX, y: t.clientY }
    }
    const onTouchEnd = (e: TouchEvent) => {
      if (!touchStart.current) return
      const t = e.changedTouches[0]
      const dx = touchStart.current.x - t.clientX
      const dy = touchStart.current.y - t.clientY
      touchStart.current = null
      const absDx = Math.abs(dx)
      const absDy = Math.abs(dy)
      if (absDx < 50 && absDy < 50) return
      const dir = absDx >= absDy ? (dx > 0 ? 1 : -1) : (dy > 0 ? 1 : -1)
      if (!hasLooped.current && sectionRef.current === 0 && dir === -1) return
      goTo((sectionRef.current + dir + 4) % 4)
    }
    window.addEventListener('touchstart', onTouchStart, { passive: true })
    window.addEventListener('touchend', onTouchEnd, { passive: true })
    return () => { window.removeEventListener('touchstart', onTouchStart); window.removeEventListener('touchend', onTouchEnd) }
  }, [isMobile, goTo])

  if (isMobile) {
    const isPhone = useIsMobile(600)
    const isTablet = !isPhone
    const snapSlot: React.CSSProperties = {
      height: '100vh',
      scrollSnapAlign: 'start',
      scrollSnapStop: 'always',
      overflow: 'hidden',
      paddingBottom: isTablet ? '36px' : 0,
    }
    return (
      <div ref={scrollContainerRef} style={{ width: '100vw', height: '100vh', overflowY: 'scroll', scrollSnapType: 'y mandatory', backgroundColor: 'transparent', WebkitOverflowScrolling: 'touch', position: 'relative' } as React.CSSProperties}>
        <div style={{ ...snapSlot, position: 'relative', zIndex: 1 }}><Section1Productivity /></div>
        <div style={{ ...snapSlot, position: 'relative', zIndex: 1 }}><Section2 /></div>
        <div style={{ ...snapSlot, position: 'relative', zIndex: 1 }}><Section3 /></div>
        <div style={{ ...snapSlot, position: 'relative', zIndex: 1 }}><Section4 /></div>
      </div>
    )
  }

  const baseW = window.innerWidth * 0.6
  const col2Left = `${baseW}px`
  const row2Top = `${window.innerHeight}px`

  return (
    <div style={{ width: '60vw', height: '100vh', overflow: 'hidden', backgroundColor: 'transparent', position: 'relative' }}>
      <motion.div style={{ x, y, position: 'relative', width: '120vw', height: '200vh', willChange: 'transform', zIndex: 1 }}>
        <div style={{ position: 'absolute', top: '0', left: '0', width: '60vw', height: '100vh' }}><Section1Productivity /></div>
        <div style={{ position: 'absolute', top: '0', left: col2Left, width: '60vw', height: '100vh' }}><Section2 /></div>
        <div style={{ position: 'absolute', top: row2Top, left: col2Left, width: '60vw', height: '100vh' }}><Section3 /></div>
        <div style={{ position: 'absolute', top: row2Top, left: '0', width: '60vw', height: '100vh' }}><Section4 /></div>
      </motion.div>
    </div>
  )
}
