import { type ReactNode } from "react";

/**
 * 关键短语高亮 — 用于副标题里的"为什么火" / "你自己的版本"
 * Hover 视觉(全部 0.3s 一起 trigger):
 *  - 文字色:墨黑 → clay 红土
 *  - 字距:normal → wider(扩 ~0.05em)
 *  - text-shadow:无 → clay 暖光晕(0 0 12px)
 *  - 整短语 scale 1.04 微放大
 *  - 背景 clay 10% tint swipe 显出
 *  - 下划线 3px → 5px,颜色 35% → 60%
 *  - ✦ sparkle 双角:左上 + 右下飞入,自转闪烁
 */
export function HighlightPhrase({
  children,
  delay = 1000,
}: {
  children: ReactNode;
  delay?: number;
}) {
  return (
    <span className="relative inline-block group cursor-default px-1 transition-transform duration-300 hover:scale-[1.04]">
      {/* sparkle 左上角 */}
      <span
        aria-hidden
        className="absolute -left-3 -top-3 text-sm text-[#7c2d12] dark:text-[#ea580c] opacity-0 -translate-y-0 group-hover:opacity-100 group-hover:-translate-y-1 group-hover:anim-sparkle-twinkle transition-all duration-300 pointer-events-none"
      >
        ✦
      </span>

      {/* sparkle 右下角(略小,延迟,反向旋转)*/}
      <span
        aria-hidden
        className="absolute -right-3 -bottom-3 text-[11px] text-[#7c2d12] dark:text-[#ea580c] opacity-0 translate-y-0 group-hover:opacity-100 group-hover:translate-y-1 group-hover:anim-sparkle-twinkle transition-all duration-300 pointer-events-none"
        style={{ animationDelay: "200ms" }}
      >
        ✦
      </span>

      {/* 背景 swipe(hover 时显出 clay 10% tint)*/}
      <span
        aria-hidden
        className="absolute inset-0 -z-10 rounded-md bg-[#7c2d12]/0 group-hover:bg-[#7c2d12]/10 dark:group-hover:bg-[#ea580c]/15 transition-colors duration-300"
      />

      {/* 文字 — 字距变化 + drop-shadow 描边光晕 */}
      <span className="relative z-10 inline-block font-semibold text-stone-900 dark:text-stone-50 tracking-normal group-hover:tracking-[0.05em] group-hover:text-[#7c2d12] dark:group-hover:text-[#ea580c] group-hover:[text-shadow:0_0_14px_rgba(124,45,18,0.35),0_1px_0_rgba(124,45,18,0.2)] dark:group-hover:[text-shadow:0_0_14px_rgba(234,88,12,0.40),0_1px_0_rgba(234,88,12,0.25)] transition-all duration-300">
        {children}
      </span>

      {/* 下划线 — 入场绘入 + hover 加粗加亮 */}
      <span
        aria-hidden
        className="anim-draw-line absolute left-1 right-1 -bottom-0.5 h-[3px] bg-[#7c2d12]/35 dark:bg-[#ea580c]/45 group-hover:h-[5px] group-hover:bg-[#7c2d12]/60 dark:group-hover:bg-[#ea580c]/75 transition-all duration-300"
        style={{ animationDelay: `${delay}ms` }}
      />
    </span>
  );
}
