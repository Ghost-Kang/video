import { useEffect, useRef } from "react";

/**
 * 双层环境光斑:
 * - 上层 clay 渐变跟随鼠标(暖光斑)
 * - 下层 aurora 双 blob 自漂移(慢呼吸,即使不动鼠标也活)
 * - paper-grid 在上,被光斑扫过时若隐若现
 */
export function AmbientCursor() {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    let raf = 0;
    const handle = (e: MouseEvent) => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        el.style.setProperty("--mx", `${e.clientX}px`);
        el.style.setProperty("--my", `${e.clientY}px`);
      });
    };
    window.addEventListener("mousemove", handle, { passive: true });
    return () => {
      window.removeEventListener("mousemove", handle);
      cancelAnimationFrame(raf);
    };
  }, []);

  return (
    <>
      {/* 后景 aurora 双 blob 自漂移 */}
      <div className="pointer-events-none fixed inset-0 z-0 overflow-hidden">
        <div
          aria-hidden
          className="absolute top-[-20%] left-[-10%] h-[60vh] w-[60vh] rounded-full blur-3xl anim-aurora-1"
          style={{
            background:
              "radial-gradient(closest-side, rgba(124, 45, 18, 0.10), transparent)",
          }}
        />
        <div
          aria-hidden
          className="absolute bottom-[-20%] right-[-10%] h-[55vh] w-[55vh] rounded-full blur-3xl anim-aurora-2"
          style={{
            background:
              "radial-gradient(closest-side, rgba(194, 65, 12, 0.09), transparent)",
          }}
        />
      </div>

      {/* paper grid 网格 — 在 aurora 之上,被光斑扫过时浮现 */}
      <div
        aria-hidden
        className="paper-grid pointer-events-none fixed inset-0 z-[1] opacity-60"
      />

      {/* 上层鼠标光斑 — 跟随光标的暖光 */}
      <div
        ref={ref}
        aria-hidden
        className="pointer-events-none fixed inset-0 z-[2]"
        style={{
          background:
            "radial-gradient(700px circle at var(--mx, 50%) var(--my, 50%), rgba(124, 45, 18, 0.10), rgba(124, 45, 18, 0.03) 35%, transparent 65%)",
          transition: "background 0.25s cubic-bezier(0.16, 1, 0.3, 1)",
        }}
      />
    </>
  );
}
