import { useEffect, useRef, useState } from "react";

/**
 * Reveal-on-scroll helper. Returns a `ref` to attach + an `inView` flag that
 * flips true once (and stays true) when the element first enters the viewport.
 *
 * Respects `prefers-reduced-motion`: under it, `inView` starts true so callers
 * render the terminal (visible) state immediately — no entrance motion. This
 * mirrors the CSS reduced-motion killswitch in index.css.
 *
 * Usage:
 *   const { ref, inView } = useInView<HTMLDivElement>();
 *   <div ref={ref} className={inView ? "anim-fade-up" : "opacity-0"}>…</div>
 */
export function useInView<T extends HTMLElement = HTMLElement>(
  opts?: IntersectionObserverInit,
) {
  const ref = useRef<T>(null);
  const [inView, setInView] = useState(false);

  useEffect(() => {
    if (inView) return; // once — stop observing after first reveal
    const el = ref.current;
    if (!el) return;

    // Reduced motion / no IntersectionObserver → show terminal state now.
    const reduce =
      typeof window !== "undefined" &&
      typeof window.matchMedia === "function" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce || typeof IntersectionObserver === "undefined") {
      setInView(true);
      return;
    }

    const io = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) {
          setInView(true);
          io.disconnect();
        }
      },
      { threshold: 0.2, rootMargin: "0px 0px -10% 0px", ...opts },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [inView, opts]);

  return { ref, inView };
}
