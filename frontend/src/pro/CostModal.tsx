/**
 * Run 前成本确认弹窗(护城河接线,plan §4.4)。点 Run → 先 POST /api/pro/estimate → 弹此 →
 * 确认才 pro_run_submit。复用暖色科技 tokens。
 */

import { useProCanvasStore } from "../store/proCanvasStore";

interface CostModalProps {
  onConfirm: () => void;
}

export function CostModal({ onConfirm }: CostModalProps) {
  const open = useProCanvasStore((s) => s.costModalOpen);
  const estimate = useProCanvasStore((s) => s.estimate);
  const close = useProCanvasStore((s) => s.closeCostModal);

  if (!open || !estimate) return null;

  const cost = estimate.cost_cny.toFixed(2);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
      onClick={close}
      role="dialog"
      aria-modal="true"
      aria-label="确认运行成本"
    >
      <div
        className="w-[min(92vw,420px)] rounded-2xl border border-[var(--color-clay)]/20 bg-[var(--color-paper)] p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-lg font-semibold text-[var(--color-ink)]">确认运行这张图</h2>
        <p className="mt-1 text-sm text-[var(--color-ink-soft)]">
          执行在境内 ComfyUI 后端,扣费前请确认成本。
        </p>

        <div className="mt-4 rounded-xl bg-[var(--color-paper-deeper)] p-4">
          <div className="flex items-baseline justify-between">
            <span className="text-sm text-[var(--color-ink-soft)]">预计成本</span>
            <span className="text-2xl font-bold text-[var(--color-clay)]">¥{cost}</span>
          </div>
          <div className="mt-2 flex justify-between text-xs text-[var(--color-ink-soft)]">
            <span>计费节点 {estimate.billable_node_count} 个</span>
            {estimate.cached_skipped > 0 && <span>已缓存跳过 {estimate.cached_skipped} 个</span>}
          </div>
        </div>

        <div className="mt-6 flex gap-3">
          <button
            type="button"
            onClick={close}
            className="flex-1 rounded-xl border border-[var(--color-ink)]/15 px-4 py-2.5 text-sm font-medium text-[var(--color-ink-soft)] transition hover:bg-[var(--color-paper-deeper)]"
          >
            取消
          </button>
          <button
            type="button"
            onClick={() => {
              close();
              onConfirm();
            }}
            className="flex-1 rounded-xl bg-[var(--color-clay)] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-[var(--color-clay-soft)]"
          >
            确认运行 ¥{cost}
          </button>
        </div>
      </div>
    </div>
  );
}
