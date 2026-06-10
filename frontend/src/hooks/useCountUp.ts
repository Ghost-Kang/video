import { useEffect, useRef, useState } from "react";

/**
 * Animate a number from 0 → `target` (easeOutCubic) once `start` is true.
 * Gives the analysis page a "数据感" tech feel (counts up on reveal).
 *
 * Shows the final value immediately under prefers-reduced-motion, or when
 * IntersectionObserver is unavailable (jsdom/tests, old browsers) — mirrors
 * useInView so callers gated on inView render the real number in tests.
 */
function prefersInstant(): boolean {
  const reduce =
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const noRaf =
    typeof requestAnimationFrame === "undefined" ||
    typeof IntersectionObserver === "undefined";
  return reduce || noRaf;
}

export function useCountUp(
  target: number,
  { start = true, duration = 900, decimals = 0 }: { start?: boolean; duration?: number; decimals?: number } = {},
): number {
  const [value, setValue] = useState(0);
  const raf = useRef<number | null>(null);
  // reduced-motion / 无 rAF(jsdom)→ 终值在 return 处直接派生,不进 effect setState
  // (react-hooks/set-state-in-effect);动画路径才需要状态。
  const instant = prefersInstant();

  useEffect(() => {
    if (!start || instant) return;

    let t0: number | null = null;
    const tick = (t: number) => {
      if (t0 === null) t0 = t;
      const p = Math.min(1, (t - t0) / duration);
      const eased = 1 - Math.pow(1 - p, 3);
      setValue(target * eased);
      if (p < 1) raf.current = requestAnimationFrame(tick);
      else setValue(target);
    };
    raf.current = requestAnimationFrame(tick);
    return () => {
      if (raf.current !== null) cancelAnimationFrame(raf.current);
    };
  }, [target, start, duration, instant]);

  const factor = 10 ** decimals;
  const shown = instant && start ? target : value;
  return Math.round(shown * factor) / factor;
}
