import { apiFetch } from "./apiClient";

export interface Creator {
  user_id: string;
  first_seen: string | null;
  last_seen: string | null;
  runs_started: number;
  rewrites_completed: number;
  publish_packs_copied: number;
  anchors_count: number;
  anchors_total_reuse_count: number;
  interview_logged: boolean;
}

const MOCK_CREATORS: Creator[] = [
  {
    user_id: "u_demo_alice",
    first_seen: "2026-05-19T08:00:00Z",
    last_seen: "2026-05-21T11:42:00Z",
    runs_started: 4,
    rewrites_completed: 3,
    publish_packs_copied: 1,
    anchors_count: 2,
    anchors_total_reuse_count: 5,
    interview_logged: true,
  },
  {
    user_id: "u_demo_betty",
    first_seen: "2026-05-20T10:00:00Z",
    last_seen: "2026-05-21T09:15:00Z",
    runs_started: 1,
    rewrites_completed: 1,
    publish_packs_copied: 0,
    anchors_count: 1,
    anchors_total_reuse_count: 0,
    interview_logged: false,
  },
  {
    user_id: "u_demo_carol",
    first_seen: "2026-05-21T07:30:00Z",
    last_seen: "2026-05-21T07:30:00Z",
    runs_started: 0,
    rewrites_completed: 0,
    publish_packs_copied: 0,
    anchors_count: 0,
    anchors_total_reuse_count: 0,
    interview_logged: false,
  },
];

export async function listCreators(): Promise<Creator[]> {
  try {
    const res = await apiFetch("/api/creators");
    if (res.ok) {
      const body = (await res.json()) as { creators?: Creator[] };
      if (body && Array.isArray(body.creators)) return body.creators;
    }
  } catch {
    // dev fallback below
  }
  return MOCK_CREATORS;
}
