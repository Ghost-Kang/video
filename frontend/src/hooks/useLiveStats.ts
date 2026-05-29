import { useEffect, useState } from "react";

interface LiveStats {
  runs: number;
  creators: number;
  loaded: boolean;
}

/**
 * 从 /api/stats/public 取服务端聚合的 runs / creators 计数;失败 fallback 到
 * 合理基线。
 *
 * 之前这里直接拉 /api/events?limit=500 在浏览器里算 unique run_id/user_id —
 * 那把 500 条原始事件(含源视频链接等)发给每个匿名 landing 访客,既是泄露
 * 也随 GET /api/events 收归 admin-only 而失效。改走 OPEN 的聚合端点,只回两个整数。
 */
export function useLiveStats(): LiveStats {
  const [stats, setStats] = useState<LiveStats>({ runs: 0, creators: 0, loaded: false });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch("/api/stats/public");
        if (!res.ok) throw new Error("non-2xx");
        const data = await res.json();
        const runs = Number(data.runs) || 0;
        const creators = Number(data.creators) || 0;
        if (!cancelled) {
          // 内测早期数据稀少,加一个温和基线(占位 demo signal)避免显示 "0"
          setStats({
            runs: Math.max(runs, 8),
            creators: Math.max(creators, 5),
            loaded: true,
          });
        }
      } catch {
        if (!cancelled) {
          setStats({ runs: 8, creators: 5, loaded: true });
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return stats;
}
