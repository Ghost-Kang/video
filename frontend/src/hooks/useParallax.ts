import { useEffect, useRef } from "react";

/**
 * Hero 视差 — 元素随鼠标在视口里的位置做小幅平移,
 * intensity 控制最大偏移 px。深度感来自:多个元素用不同 intensity 错开。
 */
export function useParallax<T extends HTMLElement = HTMLElement>(intensity = 6) {
  const ref = useRef<T>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.transition = "transform 0.6s cubic-bezier(0.16, 1, 0.3, 1)";
    el.style.willChange = "transform";
    let raf = 0;
    const handle = (e: MouseEvent) => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        const x = (e.clientX / window.innerWidth - 0.5) * intensity;
        const y = (e.clientY / window.innerHeight - 0.5) * intensity;
        el.style.transform = `translate3d(${x}px, ${y}px, 0)`;
      });
    };
    window.addEventListener("mousemove", handle, { passive: true });
    return () => {
      window.removeEventListener("mousemove", handle);
      cancelAnimationFrame(raf);
    };
  }, [intensity]);
  return ref;
}
