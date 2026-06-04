import { apiFetch } from "./apiClient";

export interface FunnelStage {
  label: string;
  event: string;
  users: number;
  /** 占第一阶段(发起)的比例 */
  pct_of_top: number | null;
  /** 相对上一阶段的转化率 */
  step_conv: number | null;
}

/** Beta 转化漏斗:每阶段去重用户数 + 转化率(后端 /api/funnel 聚合)。 */
export async function fetchFunnel(): Promise<FunnelStage[]> {
  const res = await apiFetch("/api/funnel");
  if (!res.ok) return [];
  const body = (await res.json()) as { stages?: FunnelStage[] };
  return Array.isArray(body.stages) ? body.stages : [];
}
