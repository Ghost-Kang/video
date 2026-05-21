import { useCallback, useEffect, useMemo, useState } from "react";
import { listAnchors, type Anchor } from "../lib/anchorApi";

export interface AnchorAggregate {
  total: number;
  totalReuses: number;
  avgReuseCount: number;
  maxReuseCount: number;
  topByReuse: Anchor[];
}

export interface AnchorAnalytics {
  anchors: Anchor[];
  totalAnchors: number;
  totalReuses: number;
  avgReuseCount: number;
  maxReuseCount: number;
  ratioCharacterToScene: number;
  oldestAnchorDays: number;
  topByReuse: Anchor[];
  distribution: Record<number, number>;
  byKind: { character: AnchorAggregate; scene: AnchorAggregate };
  isLoading: boolean;
  refresh: () => Promise<void>;
}

function buildAggregate(anchors: Anchor[]): AnchorAggregate {
  const total = anchors.length;
  const totalReuses = anchors.reduce((acc, a) => acc + (a.reuse_count || 0), 0);
  const max = anchors.reduce((acc, a) => Math.max(acc, a.reuse_count || 0), 0);
  const sorted = [...anchors].sort((a, b) => (b.reuse_count || 0) - (a.reuse_count || 0));
  return {
    total,
    totalReuses,
    avgReuseCount: total > 0 ? totalReuses / total : 0,
    maxReuseCount: max,
    topByReuse: sorted.slice(0, 5),
  };
}

function buildDistribution(anchors: Anchor[]): Record<number, number> {
  const dist: Record<number, number> = {};
  for (const a of anchors) {
    const k = a.reuse_count || 0;
    dist[k] = (dist[k] || 0) + 1;
  }
  return dist;
}

function daysSince(iso: string): number {
  if (!iso) return 0;
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return 0;
  return Math.max(0, Math.floor((Date.now() - then) / (1000 * 60 * 60 * 24)));
}

export function useAnchorAnalytics(): AnchorAnalytics {
  const [anchors, setAnchors] = useState<Anchor[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    const [characters, scenes] = await Promise.all([
      listAnchors("character"),
      listAnchors("scene"),
    ]);
    setAnchors([...characters, ...scenes]);
    setIsLoading(false);
  }, []);

  useEffect(() => {
    queueMicrotask(() => void refresh());
  }, [refresh]);

  return useMemo<AnchorAnalytics>(() => {
    const characters = anchors.filter((a) => a.kind === "character");
    const scenes = anchors.filter((a) => a.kind === "scene");
    const overall = buildAggregate(anchors);
    const charAgg = buildAggregate(characters);
    const sceneAgg = buildAggregate(scenes);
    const ratio = scenes.length > 0 ? characters.length / scenes.length : characters.length > 0 ? Infinity : 0;
    const oldestDays = anchors.reduce((acc, a) => Math.max(acc, daysSince(a.created_at)), 0);
    return {
      anchors,
      totalAnchors: overall.total,
      totalReuses: overall.totalReuses,
      avgReuseCount: overall.avgReuseCount,
      maxReuseCount: overall.maxReuseCount,
      ratioCharacterToScene: ratio,
      oldestAnchorDays: oldestDays,
      topByReuse: overall.topByReuse,
      distribution: buildDistribution(anchors),
      byKind: { character: charAgg, scene: sceneAgg },
      isLoading,
      refresh,
    };
  }, [anchors, isLoading, refresh]);
}
