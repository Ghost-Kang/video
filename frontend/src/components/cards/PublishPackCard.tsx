import { useState } from "react";
import { Copy } from "lucide-react";
import type { CascadeAnalysisContract } from "../../types/cascade";
import { COPY } from "../../lib/cardCopy";
import {
  buildPublishPack,
  getPublishTags,
  getPublishTitles,
} from "../../lib/buildPublishPack";
import { CARD_CLASS, BTN_PRIMARY } from "../../lib/cardStyles";
import { apiFetch } from "../../lib/apiClient";
import { useCanvasStore } from "../../store/canvasStore";
import { useNicheStore } from "../../store/nicheStore";

interface Props {
  script: string;
  analysis: CascadeAnalysisContract;
}

export function PublishPackCard({ script, analysis }: Props) {
  const [toast, setToast] = useState<string | null>(null);
  // 标题/标签描述的是「创作者改完的版本」:标题优先取改写稿口吻,标签按所选方向 ——
  // 都不再从源片分析里拿(否则把别的赛道视频改成辅食后,会泄漏源片标签/受众,缺陷 E)。
  const rewriteShots = useCanvasStore((s) => s.rewriteShots);
  const niche = useNicheStore((s) => s.niche);
  const titles = getPublishTitles(analysis, rewriteShots, niche);
  const tags = getPublishTags(niche);

  const handleCopy = async () => {
    const payload = buildPublishPack(script, analysis, [], rewriteShots, niche);
    try {
      await navigator.clipboard.writeText(payload);
      apiFetch("/api/events", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          event_name: "publish_pack_copied",
          user_id: "default",
          run_id: analysis.analysis_id,
          payload: {
            rewrite_id: "local",
            shots_count: analysis.scenes.length,
            titles_offered: titles.length,
            tags_count: tags.length,
            payload_size_chars: payload.length,
          },
        }),
      }).catch(() => {
        const queued = JSON.parse(localStorage.getItem("publish_pack_events") || "[]");
        queued.push({ analysis_id: analysis.analysis_id, payload_size_chars: payload.length });
        localStorage.setItem("publish_pack_events", JSON.stringify(queued));
      });
      setToast(COPY.copy_success);
      window.setTimeout(() => setToast(null), 3000);
    } catch {
      setToast("复制没成功，请再试一次");
      window.setTimeout(() => setToast(null), 3000);
    }
  };

  return (
    <section className={CARD_CLASS} data-testid="publish-pack-card">
      <h2 className="text-lg font-medium text-stone-900 mb-4">
        {COPY.publish_header}
      </h2>

      <p className="text-sm text-stone-500 mb-2">{COPY.suggested_titles}</p>
      <ol className="list-decimal list-inside space-y-1 mb-5 text-base text-stone-700">
        {titles.map((t) => (
          <li key={t}>{t}</li>
        ))}
      </ol>

      <p className="text-sm text-stone-500 mb-2">{COPY.tags_label}</p>
      <div className="flex flex-wrap gap-2 mb-6">
        {tags.map((tag) => (
          <span
            key={tag}
            className="rounded-full bg-stone-100 px-3 py-1 text-sm text-stone-700 border border-stone-200"
          >
            #{tag}
          </span>
        ))}
      </div>

      <button type="button" className={`${BTN_PRIMARY} w-full flex items-center justify-center gap-2`} onClick={handleCopy}>
        <Copy className="h-4 w-4" aria-hidden />
        {COPY.copy_button}
      </button>

      {toast && (
        <p className="mt-3 text-sm text-orange-600 text-center" role="status">
          {toast}
        </p>
      )}
    </section>
  );
}
