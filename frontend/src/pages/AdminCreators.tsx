import { useState } from "react";
import { useCreators, STATUS_ORDER, type CreatorStatus } from "../hooks/useCreators";
import { CreatorRow } from "../components/admin/CreatorRow";

const STATUS_LABELS: Record<CreatorStatus | "all", string> = {
  all: "全部",
  invited: "已邀请",
  registered: "已注册",
  rewritten: "已改写",
  published: "已发布",
  looping: "循环复用",
};

const PILL_BASE = "rounded-full px-3 py-1 text-xs transition-colors";
const PILL_ACTIVE = "bg-stone-900 text-white";
const PILL_INACTIVE = "bg-stone-100 text-stone-600 hover:bg-stone-200";

export function AdminCreators() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<CreatorStatus | "all">("all");
  const { creators, total, counts, isLoading, refresh } = useCreators({ search, statusFilter });

  return (
    <main className="min-h-screen bg-stone-50 py-10 px-6">
      <div className="max-w-6xl mx-auto space-y-6">
        <header className="flex items-baseline justify-between">
          <div>
            <h1 className="text-2xl font-medium text-stone-900">Creator 看板</h1>
            <p className="mt-1 text-sm text-stone-500">共 {total} 人 · concierge onboarding 全景</p>
          </div>
          <button
            type="button"
            onClick={() => void refresh()}
            className="text-xs text-stone-500 hover:text-stone-900 underline"
          >
            刷新
          </button>
        </header>

        <div className="rounded-2xl bg-white border border-stone-200 p-5 space-y-4">
          <div className="flex flex-col sm:flex-row gap-3 sm:items-center sm:justify-between">
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="按 user_id 搜索"
              className="w-full sm:w-64 rounded-lg border border-stone-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-stone-300"
              aria-label="搜索 creator"
            />
            <div className="flex gap-1 flex-wrap" role="radiogroup" aria-label="status filter">
              {(["all", ...STATUS_ORDER] as const).map((s) => (
                <button
                  key={s}
                  type="button"
                  role="radio"
                  aria-checked={statusFilter === s}
                  onClick={() => setStatusFilter(s)}
                  className={`${PILL_BASE} ${statusFilter === s ? PILL_ACTIVE : PILL_INACTIVE}`}
                >
                  {STATUS_LABELS[s]}
                  {s !== "all" && (
                    <span className="ml-1 text-[10px] tabular-nums opacity-70">{counts[s as CreatorStatus]}</span>
                  )}
                </button>
              ))}
            </div>
          </div>

          {total === 0 && !isLoading ? (
            <div className="rounded-xl bg-stone-50 p-10 text-center text-sm text-stone-500">
              还没有 creator 数据 — 让首批 creator 体验后再回来。
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead className="text-xs uppercase tracking-wider text-stone-500">
                  <tr>
                    <th className="px-4 py-2 font-medium">user_id</th>
                    <th className="px-4 py-2 font-medium">最近活动</th>
                    <th className="px-4 py-2 font-medium text-right">已运行</th>
                    <th className="px-4 py-2 font-medium text-right">已改写</th>
                    <th className="px-4 py-2 font-medium text-right">已发布</th>
                    <th className="px-4 py-2 font-medium">素材 / 复用</th>
                    <th className="px-4 py-2 font-medium">状态</th>
                  </tr>
                </thead>
                <tbody>
                  {creators.map((c) => (
                    <CreatorRow key={c.user_id} creator={c} />
                  ))}
                </tbody>
              </table>
              {creators.length === 0 && (
                <p className="py-6 text-center text-sm text-stone-500">没有匹配的 creator(调整一下筛选)</p>
              )}
            </div>
          )}
        </div>

        <p className="text-xs text-stone-400">
          状态梯度: 已邀请 → 已注册 → 已改写 → 已发布 → 循环复用。"循环复用"是 H8 moat 跑通的标志,founder 看到这个 badge 第一次出现就是产品 thesis 的第一个证据。
        </p>
      </div>
    </main>
  );
}
