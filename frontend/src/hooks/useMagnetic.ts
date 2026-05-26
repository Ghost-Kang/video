import { useEffect, useRef } from "react";

/**
 * 磁吸效果 — 鼠标进入 radius 范围,元素朝光标方向偏移(strength 控制力度)。
 * 不重绘 React state,直接改 element transform,GPU 加速。
 * 加 transition 让回归位时缓动,跟随时即时。
 */
export function useMagnetic<T extends HTMLElement = HTMLElement>(
  strength = 0.35,
  radius = 120,
) {
  const ref = useRef<T>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.transition = "transform 0.4s cubic-bezier(0.16, 1, 0.3, 1)";
    let raf = 0;
    let active = false;
    const handle = (e: MouseEvent) => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        const rect = el.getBoundingClientRect();
        const cx = rect.left + rect.width / 2;
        const cy = rect.top + rect.height / 2;
        const dx = e.clientX - cx;
        const dy = e.clientY - cy;
        const dist = Math.hypot(dx, dy);
        if (dist < radius) {
          const force = (1 - dist / radius) * strength;
          el.style.transform = `translate(${dx * force}px, ${dy * force}px)`;
          if (!active) {
            el.style.transition = "transform 0.15s cubic-bezier(0.16, 1, 0.3, 1)";
            active = true;
          }
        } else if (active) {
          el.style.transform = "translate(0, 0)";
          el.style.transition = "transform 0.4s cubic-bezier(0.16, 1, 0.3, 1)";
          active = false;
        }
      });
    };
    window.addEventListener("mousemove", handle, { passive: true });
    return () => {
      window.removeEventListener("mousemove", handle);
      cancelAnimationFrame(raf);
      if (el) el.style.transform = "";
    };
  }, [strength, radius]);
  return ref;
}
