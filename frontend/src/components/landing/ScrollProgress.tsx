import { useScrollProgress } from "../../hooks/useScrollProgress";

/**
 * 顶部 1px clay 进度条 — 随 scroll 填充。
 */
export function ScrollProgress() {
  const p = useScrollProgress();
  return (
    <div
      aria-hidden
      className="fixed top-0 left-0 right-0 z-[100] h-[2px] bg-stone-200/20 dark:bg-stone-800/40"
    >
      <div
        className="h-full bg-[#7c2d12] dark:bg-[#ea580c] transition-[width] duration-150 ease-out"
        style={{ width: `${(p * 100).toFixed(2)}%` }}
      />
    </div>
  );
}
