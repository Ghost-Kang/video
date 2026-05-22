import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const DOC_FILE: Record<string, string> = {
  "user-agreement": "/legal/user_agreement_v0.md",
  privacy: "/legal/privacy_v0.md",
};

const DOC_TITLE: Record<string, string> = {
  "user-agreement": "用户协议 (v0 试用版)",
  privacy: "隐私政策 (v0 试用版)",
};

export function LegalDoc() {
  const { slug = "" } = useParams();
  const filePath = DOC_FILE[slug];
  const title = DOC_TITLE[slug] ?? "Legal";
  const [content, setContent] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!filePath) {
      setError("未找到该文档");
      return;
    }
    let cancelled = false;
    fetch(filePath)
      .then((r) => {
        if (!r.ok) throw new Error(`fetch failed: ${r.status}`);
        return r.text();
      })
      .then((text) => {
        if (!cancelled) setContent(text);
      })
      .catch((e) => {
        if (!cancelled) setError(String(e));
      });
    return () => {
      cancelled = true;
    };
  }, [filePath]);

  return (
    <main className="min-h-screen bg-stone-50 px-4 py-10">
      <div className="mx-auto max-w-[760px]">
        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">
            加载文档失败:{error}
          </div>
        )}
        {!error && content === null && (
          <div className="text-sm text-stone-500">载入中…</div>
        )}
        {content !== null && (
          <article className="prose prose-stone max-w-none prose-headings:font-medium prose-h1:text-2xl prose-h2:text-xl prose-h3:text-lg">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
          </article>
        )}
        {!error && (
          <div className="mt-8 border-t border-stone-200 pt-4 text-xs text-stone-500">
            {title} · 2026-05-22 起效 · Phase 1 试用期至 2026-07-02
          </div>
        )}
      </div>
    </main>
  );
}
