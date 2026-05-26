import { useEffect, useState } from "react";

/**
 * 数字滚动器 — 用 ease-out cubic 缓动,1.8s 滚到 target。
 * Phase 1 占位数据;接入 events 表 count 后可换真实流。
 */
export function StatCounter({
  target,
  label,
  delayMs = 0,
}: {
  target: number;
  label: string;
  delayMs?: number;
}) {
  const [value, setValue] = useState(0);
  const [started, setStarted] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setStarted(true), delayMs);
    return () => clearTimeout(t);
  }, [delayMs]);

  useEffect(() => {
    if (!started) return;
    const start = performance.now();
    const duration = 1800;
    let raf = 0;
    const tick = (now: number) => {
      const t = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - t, 3);
      setValue(Math.floor(eased * target));
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [started, target]);

  return (
    <span className="inline-flex items-baseline gap-2">
      <span className="tabular font-serif-cn text-2xl text-stone-900 dark:text-stone-50">
        {value.toLocaleString()}
      </span>
      <span className="text-xs text-stone-500 dark:text-stone-400">{label}</span>
    </span>
  );
}
