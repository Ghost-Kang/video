import { useCallback, useEffect, useState } from "react";
import { listAnchors, reuseAnchor, type Anchor, type AnchorKind } from "../lib/anchorApi";

export function useAnchors(kind?: AnchorKind) {
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

  return { anchors, isLoading, refresh };
}

export function useReuseAnchor() {
  return { reuseAnchor };
}
