import { deriveStatus } from "../../hooks/useCreators";
import { CreatorStatusBadge } from "./CreatorStatusBadge";
import type { Creator } from "../../lib/creatorsApi";

function relativeTime(iso: string | null): string {
  if (!iso) return "—";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "—";
  const deltaSeconds = Math.floor((Date.now() - then) / 1000);
  if (deltaSeconds < 60) return `${deltaSeconds} 秒前`;
  if (deltaSeconds < 3600) return `${Math.floor(deltaSeconds / 60)} 分钟前`;
  if (deltaSeconds < 86400) return `${Math.floor(deltaSeconds / 3600)} 小时前`;
  if (deltaSeconds < 86400 * 30) return `${Math.floor(deltaSeconds / 86400)} 天前`;
  if (deltaSeconds < 86400 * 365) return `${Math.floor(deltaSeconds / 86400 / 30)} 月前`;
  return `${Math.floor(deltaSeconds / 86400 / 365)} 年前`;
}

function truncateId(id: string, length: number = 14): string {
  return id.length <= length ? id : `${id.slice(0, length)}…`;
}

export function CreatorRow({ creator }: { creator: Creator }) {
  const status = deriveStatus(creator);
  return (
    <tr className="border-t border-stone-200 hover:bg-stone-50/50">
      <td className="px-4 py-3 font-mono text-xs text-stone-700" title={creator.user_id}>
        {truncateId(creator.user_id)}
      </td>
      <td className="px-4 py-3 text-sm text-stone-500" title={creator.last_seen ?? ""}>
        {relativeTime(creator.last_seen)}
      </td>
      <td className="px-4 py-3 text-sm text-stone-700 tabular-nums text-right">{creator.runs_started}</td>
      <td className="px-4 py-3 text-sm text-stone-700 tabular-nums text-right">{creator.rewrites_completed}</td>
      <td className="px-4 py-3 text-sm text-stone-700 tabular-nums text-right">{creator.publish_packs_copied}</td>
      <td className="px-4 py-3 text-sm text-stone-700">
        {creator.anchors_count} 个 · 复用 {creator.anchors_total_reuse_count}
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <CreatorStatusBadge status={status} />
          {creator.interview_logged && (
            <span className="inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium bg-stone-200 text-stone-600">
              已访谈
            </span>
          )}
        </div>
      </td>
    </tr>
  );
}
