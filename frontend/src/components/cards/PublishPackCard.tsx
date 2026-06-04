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
  const filmUrl = useCanvasStore((s) => s.filmUrl);
  const niche = useNicheStore((s) => s.niche);
  const titles = getPublishTitles(analysis, rewriteShots, niche);
  // P2 去 niche:传 analysis 让无 niche 时标签从 theme 派生(不再默认辅食)。
  const tags = getPublishTags(niche, analysis);

  const handleCopy = async () => {
    // 发布收尾(P2):把每镜的草稿图 url 接进发布包(此前恒传空 → 发布包永远「待补充」)。
    // 按镜头顺序对齐(缺图留空字串,buildPublishPack 会按 index 标号后跳过,不错位重编号)。
    const shotImages = rewriteShots.map((s) => s.firstFrameUrl ?? "");
    const payload = buildPublishPack(script, analysis, shotImages, rewriteShots, niche, filmUrl || undefined);
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

  // 分字段复制(抖音/小红书发布表单是分字段的:标题 / 正文 / 话题各一格)——
  // 整段复制会把所有东西塞进一格,创作者还得手动拆。给每段单独的复制按钮。
  const copyField = async (text: string, ok: string) => {
    if (!text.trim()) return;
    try {
      await navigator.clipboard.writeText(text);
      setToast(ok);
    } catch {
      setToast("复制没成功，请再试一次");
    }
    window.setTimeout(() => setToast(null), 3000);
  };
  const tagLine = tags.map((t) => `#${t}`).join(" ");

  return (
    <section className={CARD_CLASS} data-testid="publish-pack-card">
      <h2 className="text-lg font-medium text-stone-900 mb-4">
        {COPY.publish_header}
      </h2>

      <div className="flex items-center justify-between mb-2">
        <p className="text-sm text-stone-500">{COPY.suggested_titles}</p>
        <button
          type="button"
          onClick={() => copyField(titles[0] ?? "", "标题已复制")}
          className="text-xs text-stone-400 hover:text-orange-600 transition-colors"
          data-testid="copy-title"
        >
          复制标题
        </button>
      </div>
      <ol className="list-decimal list-inside space-y-1 mb-5 text-base text-stone-700">
        {titles.map((t) => (
          <li key={t}>{t}</li>
        ))}
      </ol>

      <div className="flex items-center justify-between mb-2">
        <p className="text-sm text-stone-500">{COPY.tags_label}</p>
        <button
          type="button"
          onClick={() => copyField(tagLine, "话题标签已复制")}
          className="text-xs text-stone-400 hover:text-orange-600 transition-colors"
          data-testid="copy-tags"
        >
          复制话题
        </button>
      </div>
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

      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => copyField(script.trim(), "脚本已复制")}
          className="shrink-0 rounded-lg border border-stone-200 bg-white/70 hover:bg-white px-4 py-2 text-sm font-medium text-stone-700 transition-colors"
          data-testid="copy-script"
        >
          复制脚本
        </button>
        <button type="button" className={`${BTN_PRIMARY} flex-1 flex items-center justify-center gap-2`} onClick={handleCopy} data-testid="copy-all">
          <Copy className="h-4 w-4" aria-hidden />
          {COPY.copy_button}
        </button>
      </div>

      {toast && (
        <p className="mt-3 text-sm text-orange-600 text-center" role="status">
          {toast}
        </p>
      )}
    </section>
  );
}
