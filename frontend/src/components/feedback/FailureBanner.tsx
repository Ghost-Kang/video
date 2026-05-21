import { ACTION_LABELS, type FailurePayload, type RecoveryAction } from "../../types/cascade";
import { RECOVERY_HINTS } from "../../lib/recoveryHints";

interface Props {
  failure: FailurePayload;
  onAction?: (action: RecoveryAction) => void;
}

export function FailureBanner({ failure, onAction }: Props) {
  const actions = failure.actions.slice(0, 3);
  const hint = RECOVERY_HINTS[failure.code] || failure.hint;
  return (
    <section className="rounded-2xl bg-white shadow-sm border border-stone-200 p-5 text-center">
      <p className="text-base text-stone-800 mb-5">{hint}</p>
      <div className="flex flex-wrap justify-center gap-3 mb-5">
        {actions.map((action) => (
          <button
            type="button"
            key={action}
            className="rounded-xl border border-stone-200 px-4 py-2 text-sm font-medium text-stone-700 hover:bg-stone-50 transition-colors"
            onClick={() => onAction?.(action)}
          >
            {ACTION_LABELS[action]}
          </button>
        ))}
      </div>
      <p className="text-xs text-stone-400">
        错误代码: {failure.code} · 请求 ID: {failure.request_id}
      </p>
    </section>
  );
}
