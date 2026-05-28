import { useEffect, useState } from "react";
import { COPY } from "../../lib/cardCopy";

/**
 * W5D3 — 进度可视化。后端没给真实百分比(那需要新 WS 事件,本轮 out of scope),
 * 所以这里做的是 *估算式* 平滑进度:0 → 80% 用 60 秒线性爬,80 → 95% 慢爬,
 * 永远不让它自己到 100% — 等 `loading` 翻 false 才 snap。这样的好处是用户
 * 不会盯着 "99%" 干等(那是最伤心智的反模式)。
 *
 * 阶段映射:用 `thinking[]` 最后一个 label 优先(它是 Director 真实 tool_call
 * label),没有就 fallback 到时间。reduced-motion 下整个动画停下,只剩文字。
 */
interface Props {
  thinking: string[];
}

const TOTAL_ETA_SEC = 60;

function prefersReducedMotion(): boolean {
  if (typeof window === "undefined" || !window.matchMedia) return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

type Stage = "fetch" | "analyze" | "finalize";

function stageFromThinking(thinking: string[], elapsed: number): Stage {
  const last = thinking[thinking.length - 1] ?? "";
  // 「在拆解视频」「analyze_source」label 都在这里命中(中文/key 任一)。
  if (last.includes("拆解视频") || last.includes("analyze")) return "analyze";
  if (last.includes("整理") || last.includes("改写") || last.includes("分镜"))
    return "finalize";
  if (last.includes("解析") || last.includes("链接")) return "fetch";
  // fallback 按时间推:5s 前都算 fetch,55s 前算 analyze,之后 finalize。
  if (elapsed < 5) return "fetch";
  if (elapsed < 55) return "analyze";
  return "finalize";
}

const STAGE_ORDER: Stage[] = ["fetch", "analyze", "finalize"];

const STAGE_LABEL: Record<Stage, string> = {
  fetch: COPY.side_running_stage_fetch,
  analyze: COPY.side_running_stage_analyze,
  finalize: COPY.side_running_stage_finalize,
};

export function AnalysisProgress({ thinking }: Props) {
  const [elapsed, setElapsed] = useState(0);
  const reduced = prefersReducedMotion();

  useEffect(() => {
    if (reduced) return; // reduced-motion: 不跑计时器,直接显示静态文字
    const start = Date.now();
    const id = setInterval(() => {
      setElapsed((Date.now() - start) / 1000);
    }, 500);
    return () => clearInterval(id);
  }, [reduced]);

  // 0..80% over TOTAL_ETA_SEC, then 80..95% asymptotic over next 60s.
  let percent: number;
  if (elapsed <= TOTAL_ETA_SEC) {
    percent = (elapsed / TOTAL_ETA_SEC) * 80;
  } else {
    const extra = elapsed - TOTAL_ETA_SEC;
    percent = 80 + Math.min(15, (extra / 60) * 15);
  }
  percent = Math.max(2, Math.min(95, percent));

  const remaining = Math.max(0, Math.round(TOTAL_ETA_SEC - elapsed));
  const stage = stageFromThinking(thinking, elapsed);
  const stageIdx = STAGE_ORDER.indexOf(stage);

  return (
    <div
      className="rounded-2xl border border-stone-200 dark:border-stone-800 bg-white/70 dark:bg-stone-900/70 p-4 shadow-soft"
      role="status"
      aria-live="polite"
      data-testid="analysis-progress"
    >
      <div className="mb-3 flex items-baseline justify-between">
        <span
          className="font-serif-cn text-[15px] text-stone-900 dark:text-stone-50 tabular"
          data-testid="analysis-progress-eta"
        >
          {remaining > 0
            ? `${COPY.side_running_eta_prefix}${remaining}${COPY.side_running_eta_suffix}`
            : COPY.side_running_finishing}
        </span>
        <span className="text-[11px] text-stone-500 dark:text-stone-400 tabular">
          {Math.round(percent)}%
        </span>
      </div>

      <div
        className="h-1 w-full overflow-hidden rounded-full bg-stone-200 dark:bg-stone-800"
        role="progressbar"
        aria-valuenow={Math.round(percent)}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className="h-full rounded-full bg-[#7c2d12] dark:bg-[#ea580c] transition-[width] duration-500 ease-out"
          style={{ width: `${percent}%` }}
        />
      </div>

      <ul className="mt-3 space-y-1.5 text-[12px] text-stone-700 dark:text-stone-300">
        {STAGE_ORDER.map((s, i) => {
          const done = i < stageIdx;
          const active = i === stageIdx;
          return (
            <li
              key={s}
              className={
                done
                  ? "text-stone-500 dark:text-stone-400"
                  : active
                  ? "text-[#7c2d12] dark:text-[#ea580c] font-medium"
                  : "text-stone-400 dark:text-stone-600"
              }
              data-testid={`analysis-stage-${s}`}
            >
              <span
                className="mr-1.5 inline-block w-3 tabular"
                aria-hidden
              >
                {done ? COPY.side_running_done_mark : COPY.side_running_pending_mark}
              </span>
              {STAGE_LABEL[s]}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
