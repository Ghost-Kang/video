import { ImageIcon } from "lucide-react";
import type { Anchor } from "../../lib/anchorApi";

interface AnchorBarChartProps {
  anchors: Anchor[];
  maxItems?: number;
}

export function AnchorBarChart({ anchors, maxItems = 5 }: AnchorBarChartProps) {
  const sorted = [...anchors]
    .sort((a, b) => (b.reuse_count || 0) - (a.reuse_count || 0))
    .slice(0, maxItems);
  const max = sorted.reduce((acc, a) => Math.max(acc, a.reuse_count || 0), 0);

  if (sorted.length === 0) {
    return (
      <div className="rounded-2xl bg-white border border-stone-200 p-6 text-center text-sm text-stone-500">
        还没有素材可以统计 — 在画布里创建几个角色或场景后回来看
      </div>
    );
  }

  return (
    <ul className="space-y-3" aria-label="reuse_count bar chart">
      {sorted.map((anchor) => {
        const count = anchor.reuse_count || 0;
        const widthPct = max > 0 ? Math.max(4, (count / max) * 100) : 4;
        return (
          <li key={anchor.id} className="flex items-center gap-3">
            <div className="h-12 w-12 shrink-0 rounded-lg bg-stone-100 flex items-center justify-center overflow-hidden">
              {anchor.image_url ? (
                <img src={anchor.image_url} alt="" className="h-full w-full object-cover" />
              ) : (
                <ImageIcon className="h-5 w-5 text-stone-300" aria-hidden />
              )}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-2">
                <span className="truncate text-sm text-stone-800">{anchor.label}</span>
                <span className="text-sm text-stone-500 tabular-nums shrink-0">已用 {count}</span>
              </div>
              <div className="mt-1 h-2 rounded-full bg-stone-100 overflow-hidden">
                <div
                  className={count > 0 ? "h-full bg-stone-700" : "h-full bg-stone-300"}
                  style={{ width: `${widthPct}%` }}
                  role="presentation"
                />
              </div>
            </div>
          </li>
        );
      })}
    </ul>
  );
}
