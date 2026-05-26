import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ArrowLeft } from "lucide-react";
import { PageShell } from "../components/PageShell";

const DOC_FILE: Record<string, string> = {
  "user-agreement": "/legal/user_agreement_v0.md",
  privacy: "/legal/privacy_v0.md",
};

const DOC_TITLE: Record<string, string> = {
  "user-agreement": "用户协议",
  privacy: "隐私政策",
};

const DOC_EYEBROW: Record<string, string> = {
  "user-agreement": "Terms · v0",
  privacy: "Privacy · v0",
};

export function LegalDoc() {
  const { slug = "" } = useParams();
  const filePath = DOC_FILE[slug];
  const title = DOC_TITLE[slug] ?? "Legal";
  const eyebrow = DOC_EYEBROW[slug] ?? "Legal · v0";
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
    <PageShell>
      <main className="px-6 pt-20 pb-24 md:pt-28">
        <div className="mx-auto max-w-3xl">
          {/* back link */}
          <a
            href="/"
            className="anim-fade-up inline-flex items-center gap-1.5 text-xs uppercase tracking-[0.18em] text-stone-500 dark:text-stone-400 hover:text-[#7c2d12] dark:hover:text-[#ea580c] mb-8 transition-colors group"
            style={{ animationDelay: "0ms" }}
          >
            <ArrowLeft className="h-3.5 w-3.5 group-hover:-translate-x-0.5 transition-transform" aria-hidden />
            回到首页
          </a>

          {/* eyebrow */}
          <p
            className="anim-fade-up text-[11px] uppercase tracking-[0.22em] text-stone-500 dark:text-stone-400 mb-4"
            style={{ animationDelay: "120ms" }}
          >
            {eyebrow}
          </p>

          {/* hero title */}
          <h1
            className="anim-fade-up font-serif-cn text-4xl md:text-5xl text-stone-900 dark:text-stone-50 leading-[1.3] mb-10"
            style={{ animationDelay: "240ms" }}
          >
            {title}
          </h1>

          {error && (
            <div className="rounded-2xl border border-rose-200 dark:border-rose-900/50 bg-rose-50 dark:bg-rose-950/30 p-4 text-sm text-rose-800 dark:text-rose-300">
              加载文档失败:{error}
            </div>
          )}
          {!error && content === null && (
            <div className="text-sm text-stone-500 dark:text-stone-400">载入中…</div>
          )}
          {content !== null && (
            <article
              className="anim-fade-up prose prose-stone dark:prose-invert max-w-none prose-headings:font-serif-cn prose-headings:font-medium prose-h1:text-3xl prose-h2:text-2xl prose-h3:text-lg prose-a:text-[#7c2d12] dark:prose-a:text-[#ea580c] prose-strong:text-stone-900 dark:prose-strong:text-stone-50"
              style={{ animationDelay: "360ms" }}
            >
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
            </article>
          )}
          {!error && (
            <div className="mt-12 border-t border-stone-200/70 dark:border-stone-800/70 pt-5 text-[11px] uppercase tracking-[0.18em] text-stone-400 dark:text-stone-600">
              {title} · 2026-05-22 起效 · Phase 1 试用期至 2026-07-02
            </div>
          )}
        </div>
      </main>
    </PageShell>
  );
}
