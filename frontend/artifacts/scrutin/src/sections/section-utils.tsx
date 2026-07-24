import { motion } from 'framer-motion';
import { useState, useEffect, RefObject } from 'react';

export const MAGIC_BORDER_GRADIENT =
  'conic-gradient(from 0deg, transparent 0%, transparent 35%, rgba(198,120,69,0.15) 42%, #C67845 50%, rgba(198,120,69,0.15) 58%, transparent 65%, transparent 100%)';

export const NATIVE_W = 1040;
export const NATIVE_H = 684;

export function AnimatedWords({
  text,
  baseDelay = 0,
  isInView,
}: {
  text: string;
  baseDelay?: number;
  isInView: boolean;
}) {
  const words = text.split(' ');
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
          {word}
          {i < words.length - 1 ? ' ' : ''}
        </motion.span>
      ))}
    </>
  );
}

export function useSectionScale() {
  const [scale, setScale] = useState(1);

  useEffect(() => {
    const update = () => {
      const w = window.innerWidth;
      const h = window.innerHeight;
      setScale(
        w > 1024 ? Math.min(1, (w * 0.6) / NATIVE_W, h / 900) * 0.78 : Math.max(0.28, (w - 24) / NATIVE_W)
      );
    };
    update();
    window.addEventListener('resize', update);
    return () => window.removeEventListener('resize', update);
  }, []);

  return scale;
}

export function useSectionIntersection(
  ref: RefObject<HTMLElement | null>,
  isMobile: boolean
) {
  const [isInView, setIsInView] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    let wasVisible = false;
    const enterRatio = isMobile ? 0.2 : 0.45;
    const exitRatio = isMobile ? 0.05 : 0.1;

    const obs = new IntersectionObserver(
      ([entry]) => {
        const ratio = entry.intersectionRatio;
        if (entry.isIntersecting && ratio >= enterRatio && !wasVisible) {
          wasVisible = true;
          setIsInView(true);
        } else if (!entry.isIntersecting || ratio < exitRatio) {
          wasVisible = false;
          setIsInView(false);
        }
      },
      { threshold: [exitRatio, enterRatio] }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, [ref, isMobile]);

  return isInView;
}
