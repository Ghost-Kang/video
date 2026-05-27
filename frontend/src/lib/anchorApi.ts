export type AnchorKind = "character" | "scene";

export interface Anchor {
  id: string;
  kind: AnchorKind;
  label: string;
  image_url: string;
  reuse_count: number;
  created_at: string;
}

const MOCK_ANCHORS: Anchor[] = [
  { id: "anc_mom", kind: "character", label: "小张妈妈", image_url: "", reuse_count: 4, created_at: "2026-05-19T00:00:00Z" },
  { id: "anc_baby", kind: "character", label: "乖宝", image_url: "", reuse_count: 2, created_at: "2026-05-20T00:00:00Z" },
  { id: "anc_kitchen", kind: "scene", label: "厨房", image_url: "", reuse_count: 5, created_at: "2026-05-18T00:00:00Z" },
];

function parseAnchorList(payload: unknown): Anchor[] | null {
  if (Array.isArray(payload)) return payload as Anchor[];
  if (
    payload &&
    typeof payload === "object" &&
    "anchors" in payload &&
    Array.isArray((payload as { anchors?: unknown }).anchors)
  ) {
    return (payload as { anchors: Anchor[] }).anchors;
  }
  return null;
}

export async function listAnchors(kind?: AnchorKind): Promise<Anchor[]> {
  try {
    const suffix = kind ? `?kind=${kind}` : "";
    const res = await fetch(`/api/anchors${suffix}`);
    if (res.ok) {
      const anchors = parseAnchorList(await res.json());
      if (anchors) return anchors;
    }
  } catch {
    // dev fallback below
  }
  return MOCK_ANCHORS.filter((anchor) => !kind || anchor.kind === kind).sort(
    (a, b) => b.reuse_count - a.reuse_count || b.created_at.localeCompare(a.created_at)
  );
}

export async function createAnchor(anchor: Omit<Anchor, "id" | "reuse_count" | "created_at">) {
  const res = await fetch("/api/anchors", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(anchor),
  });
  return res.ok ? ((await res.json()) as Anchor) : null;
}

export async function reuseAnchor(anchorId: string, payload: { user_id: string; reused_in_run_id: string; reused_in_shot_index: number }) {
  await fetch(`/api/anchors/${anchorId}/reuse`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  }).catch(() => undefined);
}
