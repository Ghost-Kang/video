import { useCallback, useEffect, useMemo, useState } from "react";
import { listAnchors, reuseAnchor, type Anchor, type AnchorKind } from "../lib/anchorApi";

export type AnchorSort = "reuse" | "recency";

export function useAnchors(kind?: AnchorKind, sortBy: AnchorSort = "reuse") {
  const [anchors, setAnchors] = useState<Anchor[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    setAnchors(await listAnchors(kind));
    setIsLoading(false);
  }, [kind]);

  useEffect(() => {
    queueMicrotask(() => void refresh());
  }, [refresh]);

  // Backend returns `reuse_count DESC, created_at DESC`. For "recency"
  // we re-sort client-side. Kept here (not in listAnchors) so the
  // hook can switch sort without re-fetching.
  const sorted = useMemo(() => {
    if (sortBy === "recency") {
      return [...anchors].sort((a, b) => b.created_at.localeCompare(a.created_at));
    }
    return anchors;
  }, [anchors, sortBy]);

  return { anchors: sorted, isLoading, refresh };
}

export function useReuseAnchor() {
  return { reuseAnchor };
}
