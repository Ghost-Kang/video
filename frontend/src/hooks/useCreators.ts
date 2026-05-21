import { useCallback, useEffect, useMemo, useState } from "react";
import { listCreators, type Creator } from "../lib/creatorsApi";

export type CreatorStatus =
  | "invited"
  | "registered"
  | "rewritten"
  | "published"
  | "looping";

export function deriveStatus(c: Creator): CreatorStatus {
  if (c.anchors_total_reuse_count >= 1) return "looping";
  if (c.publish_packs_copied >= 1) return "published";
  if (c.rewrites_completed >= 1) return "rewritten";
  if (c.runs_started >= 1) return "registered";
  return "invited";
}

export const STATUS_ORDER: CreatorStatus[] = [
  "invited",
  "registered",
  "rewritten",
  "published",
  "looping",
];

export interface UseCreatorsOptions {
  search?: string;
  statusFilter?: CreatorStatus | "all";
}

export function useCreators(options: UseCreatorsOptions = {}) {
  const { search = "", statusFilter = "all" } = options;
  const [creators, setCreators] = useState<Creator[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    setCreators(await listCreators());
    setIsLoading(false);
  }, []);

  useEffect(() => {
    queueMicrotask(() => void refresh());
  }, [refresh]);

  const filtered = useMemo(() => {
    return creators.filter((c) => {
      if (search && !c.user_id.toLowerCase().includes(search.toLowerCase())) return false;
      if (statusFilter !== "all" && deriveStatus(c) !== statusFilter) return false;
      return true;
    });
  }, [creators, search, statusFilter]);

  const counts = useMemo(() => {
    const out: Record<CreatorStatus, number> = {
      invited: 0,
      registered: 0,
      rewritten: 0,
      published: 0,
      looping: 0,
    };
    for (const c of creators) {
      out[deriveStatus(c)] += 1;
    }
    return out;
  }, [creators]);

  return { creators: filtered, total: creators.length, counts, isLoading, refresh };
}
