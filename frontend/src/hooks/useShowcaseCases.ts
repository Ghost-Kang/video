import { useEffect, useState } from "react";
import { SAMPLE_CASES, type SampleCase } from "../lib/sampleCases";

/**
 * 落地页案例数据源 —— 从 GET /api/showcase 动态拉「已发布」案例,与写死的种子案例
 * (SAMPLE_CASES)做并集(按 source_url 去重,DB 优先)。
 *
 * 为什么保留种子:① 首屏即时渲染,不等网络;② API 失败 / DB 为空时永不显示空白
 * (种子是兜底);③ 种子是「永远在场」的精选,DB 是「用户跑完自动上」的增量。
 *
 * 自动化闭环:用户跑完高置信度分析 → 后端 maybe_publish_showcase 自动入库 →
 * 下一个访客的落地页 fetch 到它 → 轮播自动多一张。无需改代码 / 重新部署。
 */
export function useShowcaseCases(): SampleCase[] {
  // 初始即种子 → 首屏立刻有内容(SSR/无网也不空)。
  const [cases, setCases] = useState<SampleCase[]>(SAMPLE_CASES);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch("/api/showcase");
        if (!res.ok) throw new Error("non-2xx");
        const data = await res.json();
        const fetched: SampleCase[] = Array.isArray(data?.cases) ? data.cases : [];
        if (cancelled) return;
        // 并集去重:DB 案例优先,种子里 source_url 没出现过的补在后面(保证种子永远在场)。
        const seen = new Set(fetched.map((c) => c.source_url));
        const merged = [...fetched, ...SAMPLE_CASES.filter((c) => !seen.has(c.source_url))];
        // fetched 可能为空(DB 还没有自动案例)→ merged 退化为纯种子,符合预期。
        setCases(merged.length > 0 ? merged : SAMPLE_CASES);
      } catch {
        // 网络/解析失败 → 保持种子(初始值),什么都不做。
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return cases;
}
