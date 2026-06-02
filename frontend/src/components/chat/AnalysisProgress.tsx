import { useEffect, useRef, useState } from "react";
import { useWSStore } from "../../store/wsStore";
import { COPY } from "../../lib/cardCopy";
import { trackEvent } from "../../lib/eventsApi";
import { useCanvasStore } from "../../store/canvasStore";
import { synthesizeClientTimeout } from "../../store/wsStore";

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
  /** Test override — let specs simulate "started 100s ago" without timer hacks. */
  startedAtMs?: number;
}

const TOTAL_ETA_SEC = 60;
// W5D3 — 95% pin escape:进度卡 95% 持续 90 秒 → 弹软警告,让用户主动跳出。
const PIN_ESCAPE_THRESHOLD_SEC = 90;
const PIN_ESCAPE_PERCENT = 95;
// 用户点「继续等」后,沉默 60 秒再考虑下一次弹警告。
const PIN_ESCAPE_SNOOZE_SEC = 60;
// W5D4 — last-resort auto-fail. If nothing terminal arrives by here, flip the
// run to failed so a walked-away user never stares at a frozen 95% spinner. Set
// ABOVE the backend run ceiling (RUN_TURN_TIMEOUT_S=180s) so a legitimately slow
// run that does finish — or a reconnect that resumes terminal state via
// get_session_state — always wins first.
const HARD_TIMEOUT_SEC = 210;

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

// W5D3-T1 — map backend stage string (analysis_progress.stage) to local Stage enum.
function stageFromBackend(stage: string | null): Stage | null {
  if (!stage) return null;
  if (stage === "resolve_url") return "fetch";
  if (stage === "ark_overlay") return "analyze";
  if (stage === "transcribe" || stage === "done") return "finalize";
  return null;
}

const STAGE_ORDER: Stage[] = ["fetch", "analyze", "finalize"];

const STAGE_LABEL: Record<Stage, string> = {
  fetch: COPY.side_running_stage_fetch,
  analyze: COPY.side_running_stage_analyze,
  finalize: COPY.side_running_stage_finalize,
};

export function AnalysisProgress({ thinking, startedAtMs }: Props) {
  const [elapsed, setElapsed] = useState(() =>
    startedAtMs ? Math.max(0, (Date.now() - startedAtMs) / 1000) : 0,
  );
  // snoozeEndElapsed = the `elapsed` value at which the snooze expires. By
  // comparing two elapsed-seconds values (both deterministic given the timer
  // tick), we keep render pure (no Date.now() in render body).
  const [snoozeEndElapsed, setSnoozeEndElapsed] = useState<number>(0);
  const reduced = prefersReducedMotion();

  // Live mirror of `elapsed` for use inside other effects without making them
  // depend on (and re-fire each tick of) elapsed. Synced in the timer effect.
  const elapsedRef = useRef(elapsed);

  useEffect(() => {
    // The ticker must run even under reduced-motion. Bugfix (萌宠 case): when the
    // backend is slow to emit its first real progress frame (e.g. a v.douyin.com
    // short-link resolve doing a 302-follow + SSR scrape, ~10-20s before the 15%
    // stage), the time-based ramp is the ONLY thing moving the bar. Previously
    // `if (reduced) return` killed the ticker, so a reduced-motion user saw a
    // frozen 2% bar = "没有显示拆解的进度". reduced-motion means "don't ANIMATE",
    // not "don't update" — we slow the tick (1.5s vs 0.5s) and the bar's CSS
    // transition is what reduced-motion suppresses, not the value itself.
    const start = startedAtMs ?? Date.now();
    const tickMs = reduced ? 1500 : 500;
    const id = setInterval(() => {
      const e = (Date.now() - start) / 1000;
      elapsedRef.current = e;
      setElapsed(e);
    }, tickMs);
    return () => clearInterval(id);
  }, [reduced, startedAtMs]);

  // W5D4 — auto-fail backstop (see HARD_TIMEOUT_SEC). Ref-guarded so it fires
  // once; setFailure flips ChatPanel out of `loading`, unmounting this card.
  const hardFailedRef = useRef(false);
  useEffect(() => {
    if (!hardFailedRef.current && elapsed >= HARD_TIMEOUT_SEC) {
      hardFailedRef.current = true;
      useCanvasStore.getState().setFailure(synthesizeClientTimeout());
    }
  }, [elapsed]);

  // W5D3-T1 — prefer real backend progress when available; fall back to
  // time-based ramp for older deploys / mediakit upstream / WS reconnect mid-run.
  const realPercent = useWSStore((s) => s.progressPercent);
  const realEta = useWSStore((s) => s.progressEta);
  const realStageStr = useWSStore((s) => s.progressStage);
  const realDetail = useWSStore((s) => s.progressDetail);

  // Bugfix (萌宠 case): the backend emits at stage *boundaries* (5% resolve_url →
  // 15% ark_overlay → 85% → …). Between boundaries there can be a long silence —
  // a v.douyin.com short-link resolve (302-follow + SSR scrape) sits at 5% for
  // ~10-20s, and the slow ARK vision call sits at 15% for most of the run.
  // Previously percent was pinned to the last real value the whole time, so the
  // bar FROZE between stages = "进入拆解后没显示进度". Fix: snapshot the elapsed
  // at which each real percent arrived, then creep from it toward the next
  // stage's value so the bar always inches forward during the gap.
  // Snapshot (percent, elapsed-at-arrival) each time a NEW real percent lands,
  // so the inter-stage creep below knows how long this stage has been running.
  // Stored in state (not a render-time ref mutation) to stay render-pure.
  const [lastReal, setLastReal] = useState<{ percent: number; atElapsed: number } | null>(null);
  useEffect(() => {
    if (realPercent !== null && realPercent > 0) {
      // elapsed-at-arrival read from the timer-synced ref (updated in an effect,
      // never in render — rules-of-hooks clean).
      const at = elapsedRef.current;
      setLastReal((prev) =>
        prev && prev.percent === realPercent ? prev : { percent: realPercent, atElapsed: at },
      );
    } else if (realPercent === null) {
      // New run started (setLoading reset progress to null) → drop stale snapshot
      // so we don't creep from a prior run's stage. Falls back to the time-ramp.
      setLastReal(null);
    }
  }, [realPercent, startedAtMs]);

  // Soft ceiling for the inter-stage creep: just under the next known boundary,
  // so the creep never overshoots a real stage. Boundaries: 5→15→85→92→95→100.
  const nextBoundary = (p: number): number => {
    if (p < 15) return 14;
    if (p < 85) return 84;
    if (p < 92) return 91;
    if (p < 95) return 94;
    if (p < 100) return 99;
    return 100;
  };

  let percent: number;
  if (lastReal) {
    const { percent: base, atElapsed } = lastReal;
    const ceiling = nextBoundary(base);
    // Creep ~ (ceiling-base) over ~45s since this stage started, easing out so
    // it slows as it approaches the ceiling (never reaches it — only a real
    // frame advances past). Stays put under reduced-motion handling via the
    // shared ticker (which still updates `elapsed`, just less often).
    const sinceStage = Math.max(0, elapsed - atElapsed);
    const span = ceiling - base;
    const creep = span * (1 - Math.exp(-sinceStage / 18));
    percent = base + creep;
  } else if (elapsed <= TOTAL_ETA_SEC) {
    percent = (elapsed / TOTAL_ETA_SEC) * 80;
  } else {
    const extra = elapsed - TOTAL_ETA_SEC;
    percent = 80 + Math.min(15, (extra / 60) * 15);
  }
  percent = Math.max(2, Math.min(100, percent));

  const remaining =
    realEta !== null && realEta >= 0
      ? realEta
      : Math.max(0, Math.round(TOTAL_ETA_SEC - elapsed));
  const stage = stageFromBackend(realStageStr) ?? stageFromThinking(thinking, elapsed);
  const stageIdx = STAGE_ORDER.indexOf(stage);

  // 95% pin escape — 已经走到上限 % 且总耗时超阈值,且未在 snooze 窗口内。
  const pinned =
    Math.round(percent) >= PIN_ESCAPE_PERCENT &&
    elapsed >= PIN_ESCAPE_THRESHOLD_SEC &&
    elapsed >= snoozeEndElapsed;

  // 软提示弹出记一次(去重)—— 配合下方两个 action 算「弹出后继续等 vs 换一条」分布。
  const pinShownRef = useRef(false);
  useEffect(() => {
    if (pinned && !pinShownRef.current) {
      pinShownRef.current = true;
      trackEvent("pin_escape_shown", { elapsed_sec: Math.round(elapsed) });
    }
  }, [pinned, elapsed]);

  const handleSwitch = () => {
    trackEvent("pin_escape_action", { action: "switch", elapsed_sec: Math.round(elapsed) });
    // 主动跳出 — 合成 failure(超时同义),让 ChatPanel 切到 failed 状态、给样本 chips。
    useCanvasStore
      .getState()
      .setFailure(synthesizeClientTimeout());
  };

  const handleWait = () => {
    trackEvent("pin_escape_action", { action: "wait", elapsed_sec: Math.round(elapsed) });
    setSnoozeEndElapsed(elapsed + PIN_ESCAPE_SNOOZE_SEC);
  };

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
            : `${STAGE_LABEL[stage]} · ${COPY.side_running_finishing}`}
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

      {pinned && (
        <div
          className="mt-3 rounded-lg border border-amber-300/60 dark:border-amber-700/60 bg-amber-50/80 dark:bg-amber-950/30 px-3 py-2 text-[12px] text-stone-700 dark:text-stone-200"
          data-testid="pin-escape"
          role="status"
        >
          <p className="mb-2">{COPY.pin_escape_warning}</p>
          <div className="flex gap-2">
            {/* 反转语序:「继续等」升为推荐主操作(陶土橙填充),「换一条」降为次选(灰描边)。
                慢的时候站在用户这边等,而不是把「换一条」摆显眼位置劝退。 */}
            <button
              type="button"
              onClick={handleWait}
              data-testid="pin-escape-wait"
              className="rounded-full bg-[#7c2d12] dark:bg-[#ea580c] px-3 py-1 text-[11px] text-[#faf8f3] hover:bg-[#9a3412] dark:hover:bg-[#c2410c] transition-colors font-inherit"
            >
              {COPY.pin_escape_wait}
            </button>
            <button
              type="button"
              onClick={handleSwitch}
              data-testid="pin-escape-switch"
              className="rounded-full border border-stone-300 dark:border-stone-700 px-3 py-1 text-[11px] text-stone-500 dark:text-stone-400 hover:border-stone-500 dark:hover:border-stone-500 transition-colors font-inherit"
            >
              {COPY.pin_escape_switch}
            </button>
          </div>
        </div>
      )}

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
              {active && realDetail && (
                <span className="ml-1.5 text-[11px] text-stone-500 dark:text-stone-400">
                  · {realDetail}
                </span>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
