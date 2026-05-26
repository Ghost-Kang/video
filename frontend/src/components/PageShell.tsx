import { type ReactNode } from "react";
import { AmbientCursor } from "./landing/AmbientCursor";
import { ScrollProgress } from "./landing/ScrollProgress";
import { DarkModeToggle } from "./landing/DarkModeToggle";

/**
 * 全站统一壳子 — 一切页面用这个 wrap,自动获得:
 * - paper / dark 主题背景 + 颜色过渡
 * - AmbientCursor 鼠标光斑 + aurora 后景
 * - 顶部 ScrollProgress 进度条
 * - 右上 DarkModeToggle
 *
 * Props:
 *   - ambient(default true): 是否启用 aurora + 鼠标光斑(高交互页面如 chat 可能想关)
 *   - showProgress(default true): 是否显示顶部 scroll 进度条
 *   - showToggle(default true): 是否显示右上角 dark mode 切换
 */
export function PageShell({
  children,
  ambient = true,
  showProgress = true,
  showToggle = true,
  className = "",
}: {
  children: ReactNode;
  ambient?: boolean;
  showProgress?: boolean;
  showToggle?: boolean;
  className?: string;
}) {
  return (
    <div
      className={`relative min-h-screen flex flex-col bg-[var(--color-paper)] dark:bg-stone-950 text-stone-900 dark:text-stone-100 transition-colors duration-500 ${className}`}
    >
      {showProgress && <ScrollProgress />}
      {showToggle && <DarkModeToggle />}
      {ambient && <AmbientCursor />}
      <div className="relative z-10 flex-1 flex flex-col">{children}</div>
    </div>
  );
}
