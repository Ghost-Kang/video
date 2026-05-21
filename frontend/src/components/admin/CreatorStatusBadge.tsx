import type { CreatorStatus } from "../../hooks/useCreators";

const STATUS_META: Record<CreatorStatus, { label: string; tone: string }> = {
  invited: { label: "已邀请", tone: "bg-stone-100 text-stone-600" },
  registered: { label: "已注册", tone: "bg-blue-50 text-blue-700" },
  rewritten: { label: "已改写", tone: "bg-amber-50 text-amber-700" },
  published: { label: "已发布", tone: "bg-emerald-50 text-emerald-700" },
  looping: { label: "循环复用", tone: "bg-emerald-600 text-white" },
};

export function CreatorStatusBadge({ status }: { status: CreatorStatus }) {
  const meta = STATUS_META[status];
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${meta.tone}`}
      aria-label={`creator status: ${status}`}
    >
      {meta.label}
    </span>
  );
}
