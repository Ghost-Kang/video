import { useEffect, useRef, useState } from "react";
import type { SampleCase } from "../../lib/sampleCases";
import { CaseShowcase } from "./CaseShowcase";

interface Props {
  cases: SampleCase[];
  onPick: (c: SampleCase) => void;
  /** Max cards visible at once on desktop. Mobile always shows 1. */
  perPageDesktop?: number;
}

const PAGE_ADVANCE_MS = 9000;

// 落地页「能拆出什么」案例区 —— 把所有真实作品做成逐幕视频卡,左右并排(桌面 2 列,
// 手机 1 列)。作品多到一屏装不下时,按「页」自动轮转,把全部作品都轮播展示到。
//
// 为什么按页轮转而不是横向滚动条:每张卡内部已有逐幕 clip 自动轮播 + hover 暂停,
// 横向滚动条与卡内轮播的手势/视觉会打架;按页淡入淡出更干净,且无障碍可达(下方圆点)。
export function CaseShowcaseRow({ cases, onPick, perPageDesktop = 2 }: Props) {
  // 一页放几张:桌面 perPageDesktop,手机 1。用 matchMedia 判断,SSR/无 matchMedia 时
  // 取桌面值(渲染不依赖它做 hooks 分支,避免 rules-of-hooks 问题)。
  const [perPage, setPerPage] = useState(perPageDesktop);
  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") return;
    const mq = window.matchMedia("(max-width: 767px)");
    const apply = () => setPerPage(mq.matches ? 1 : perPageDesktop);
    apply();
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, [perPageDesktop]);

  const pageCount = Math.max(1, Math.ceil(cases.length / perPage));
  const [page, setPage] = useState(0);
  const [paused, setPaused] = useState(false);

  // page 可能因 perPage 变化(转屏)而越界 → 渲染时收敛回合法范围(纯计算,不在
  // effect 里 setState)。下面所有用 page 处一律用 safePage。
  const safePage = Math.min(page, pageCount - 1);

  const reduce =
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // 多于一页时按页自动轮转(reduced-motion / hover 暂停)。
  const timer = useRef<number | null>(null);
  useEffect(() => {
    if (reduce || paused || pageCount <= 1) return;
    timer.current = window.setTimeout(
      () => setPage((p) => (Math.min(p, pageCount - 1) + 1) % pageCount),
      PAGE_ADVANCE_MS,
    );
    return () => {
      if (timer.current !== null) window.clearTimeout(timer.current);
    };
  }, [safePage, paused, reduce, pageCount]);

  if (cases.length === 0) return null;

  const start = safePage * perPage;
  const visible = cases.slice(start, start + perPage);

  return (
    <div
      data-testid="case-showcase-row"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
    >
      {/* 左右并排:手机 1 列,桌面按 perPage 列。每张卡仍是带逐幕视频的 CaseShowcase。 */}
      <div
        className={`grid justify-center gap-4 ${
          perPage >= 2 ? "grid-cols-1 md:grid-cols-2" : "grid-cols-1"
        }`}
      >
        {visible.map((c) => (
          <CaseShowcase key={c.id} sample={c} onPick={onPick} />
        ))}
      </div>

      {/* 页圆点 —— 仅当作品多到不止一页时显示;点了可手动翻页。 */}
      {pageCount > 1 && (
        <div className="mt-4 flex justify-center gap-1.5" role="tablist" aria-label="案例分页">
          {Array.from({ length: pageCount }).map((_, i) => (
            <button
              key={i}
              type="button"
              role="tab"
              aria-selected={i === safePage}
              aria-label={`第 ${i + 1} 页案例`}
              onClick={() => setPage(i)}
              className={`h-1.5 rounded-full transition-all ${
                i === safePage
                  ? "w-5 bg-[#7c2d12] dark:bg-[#ea580c]"
                  : "w-1.5 bg-stone-300 hover:bg-stone-400 dark:bg-stone-700 dark:hover:bg-stone-500"
              }`}
            />
          ))}
        </div>
      )}
    </div>
  );
}
