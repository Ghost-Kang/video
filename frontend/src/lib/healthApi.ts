/**
 * Wrapper for backend GET /api/health/summary — W5D2-D。
 *
 * Shape 跟 backend `app/api/health.py` 对齐。失败时返回 null,UI 自行
 * 进 error state。
 */

import { apiFetch } from "./apiClient";

export interface HealthServer {
  cpu_percent: number;
  mem_used_mb: number;
  mem_total_mb: number;
  disk_used_gb: number;
  disk_total_gb: number;
  uptime_seconds: number;
}

export interface HealthEvents5Min {
  total: number;
  by_type: Record<string, number>;
}

export type HealthUpstreamSuccessRate = Record<string, number>;

export interface HealthRecentFailure {
  id: number;
  ts: string;
  event_name: string;
  payload: Record<string, unknown>;
}

export interface HealthSummary {
  server: HealthServer;
  events_5min: HealthEvents5Min;
  upstream_success_rate: HealthUpstreamSuccessRate;
  recent_failures: HealthRecentFailure[];
}

export async function fetchHealthSummary(): Promise<HealthSummary | null> {
  try {
    const res = await apiFetch("/api/health/summary");
    if (!res.ok) return null;
    const body = (await res.json()) as Partial<HealthSummary>;
    if (!body || !body.server) return null;
    return {
      server: body.server,
      events_5min: body.events_5min ?? { total: 0, by_type: {} },
      upstream_success_rate: body.upstream_success_rate ?? {},
      recent_failures: Array.isArray(body.recent_failures) ? body.recent_failures : [],
    } as HealthSummary;
  } catch {
    return null;
  }
}
