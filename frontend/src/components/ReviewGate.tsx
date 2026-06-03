import { useReviewStore } from "../store/reviewStore";
import type { ReviewDecisionMsg } from "../types/ws";

interface Props {
  /** 当前 thread。仅当待审核卡属于该 thread 时才渲染(跨线程兜底)。 */
  threadId: string;
  sendCommand: (cmd: ReviewDecisionMsg) => void;
}

/**
 * P2 审核闸门 UI — Director **自主**调生成工具时,LangGraph interrupt 暂停了 graph,
 * 后端推 `review_required`。这里弹一张审核卡,用户「确认生成」或「先不生成」,前端
 * 发 `review_decision`(decisions 与 reviews 同序同数),后端 Command(resume) 续跑。
 *
 * 显式点「生成」(CardStack 按钮)**不会**走到这里 —— 后端自动批准。这张卡只在
 * Director 自己想烧钱时出现,是「不跑过头」护栏的可见形态。
 *
 * Hooks 全部在任何 early-return 之前调用(rules-of-hooks:jsdom 抓不到「hook 在
 * early-return 之后」,prod 会被错误边界吞成白屏)。
 */
export function ReviewGate({ threadId, sendCommand }: Props) {
  const pending = useReviewStore((s) => s.pending);
  const clear = useReviewStore((s) => s.clear);

  // 仅当有卡、且属于当前 thread 时显示。所有 hook 已在上面调用完。
  if (!pending || pending.threadId !== threadId) return null;

  const decide = (type: "approve" | "reject") => {
    // 一次性对全部被拦工具做同一决策(slice-1:approve/reject all)。decisions 必须
    // 与 reviews 同序同数 —— 后端 HumanInTheLoopMiddleware 硬校验数量匹配。
    const decisions = pending.reviews.map(() => ({ type }));
    sendCommand({
      type: "review_decision",
      thread_id: pending.threadId,
      decisions,
      interrupt_id: pending.interruptId,
    });
    clear();
  };

  return (
    <div
      className="absolute inset-0 z-[60] flex items-end justify-center px-4 pb-28 sm:items-center sm:pb-4 bg-stone-900/20 dark:bg-black/40 backdrop-blur-[2px]"
      data-testid="review-gate-scrim"
    >
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="review-gate-title"
        data-testid="review-gate"
        className="w-full max-w-md rounded-2xl border border-[#7c2d12]/25 dark:border-[#ea580c]/35 bg-[#fef7f0] dark:bg-stone-900 p-5 shadow-[0_16px_48px_-12px_rgba(28,25,23,0.35)] dark:shadow-[0_16px_48px_-12px_rgba(0,0,0,0.6)]"
      >
        <div className="flex items-start gap-3">
          <span aria-hidden className="mt-0.5 text-xl">🛡️</span>
          <div className="min-w-0 flex-1">
            <h2
              id="review-gate-title"
              className="font-serif-cn text-base font-medium text-stone-900 dark:text-stone-50 tracking-[-0.01em]"
            >
              {pending.summary || "待你确认是否生成"}
            </h2>
            <p className="mt-1 text-xs text-stone-500 dark:text-stone-400">
              导演想自动生成下面的内容,确认后才会执行(会消耗额度)。
            </p>
          </div>
        </div>

        <ul className="mt-4 space-y-2" data-testid="review-gate-list">
          {pending.reviews.map((r, i) => (
            <li
              key={`${r.tool}-${i}`}
              className="flex items-center gap-2 rounded-xl border border-stone-200 dark:border-stone-700 bg-white dark:bg-stone-800 px-3 py-2 text-sm text-stone-800 dark:text-stone-100"
            >
              <span aria-hidden className="text-[#7c2d12] dark:text-[#ea580c]">✦</span>
              <span className="truncate">{r.label}</span>
            </li>
          ))}
        </ul>

        <div className="mt-5 flex gap-3">
          <button
            type="button"
            data-testid="review-gate-approve"
            onClick={() => decide("approve")}
            className="flex-1 rounded-full bg-[#7c2d12] dark:bg-[#ea580c] px-4 py-2.5 text-sm font-medium text-[#faf8f3] hover:brightness-110 active:scale-[0.98] transition-all"
          >
            确认生成
          </button>
          <button
            type="button"
            data-testid="review-gate-reject"
            onClick={() => decide("reject")}
            className="rounded-full border border-stone-300 dark:border-stone-600 bg-white dark:bg-stone-900 px-4 py-2.5 text-sm font-medium text-stone-700 dark:text-stone-200 hover:bg-stone-50 dark:hover:bg-stone-800 active:scale-[0.98] transition-all"
          >
            先不生成
          </button>
        </div>
      </section>
    </div>
  );
}
