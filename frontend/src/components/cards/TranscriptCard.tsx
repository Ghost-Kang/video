import { useState } from "react";
import { COPY } from "../../lib/cardCopy";
import { CARD_CLASS, BTN_SECONDARY } from "../../lib/cardStyles";
import { useToastStore } from "../../store/toastStore";

interface Props {
  transcript: string;
}

// 完整原片台词。空 transcript 时整张卡不渲染(避免空白噪音)。
// 默认折叠 — 完整 transcript 可能很长(MediaKit 返回值常 1-2k 字),不应该
// 一上来就刷屏盖住后续 ShotCard。
export function TranscriptCard({ transcript }: Props) {
  const [expanded, setExpanded] = useState(false);

  if (!transcript || !transcript.trim()) return null;

  const preview = transcript.slice(0, 60);
  const needsTruncation = transcript.length > 60;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(transcript);
      useToastStore.getState().push({ kind: "info", title: COPY.transcript_copied });
    } catch {
      useToastStore.getState().push({ kind: "error", title: "复制失败,手动选中再复制" });
    }
  };

  return (
    <section className={CARD_CLASS} data-testid="transcript-card">
      <div className="flex items-center justify-between mb-3">
        <h2 className="font-serif-cn text-lg font-medium text-stone-900 dark:text-stone-50 tracking-[-0.01em]">
          {COPY.transcript_header}
        </h2>
        <div className="flex items-center gap-2">
          <button
            type="button"
            className={BTN_SECONDARY}
            onClick={handleCopy}
            data-testid="transcript-copy-btn"
          >
            {COPY.transcript_copy}
          </button>
          {needsTruncation && (
            <button
              type="button"
              className={BTN_SECONDARY}
              onClick={() => setExpanded((v) => !v)}
              data-testid="transcript-toggle-btn"
            >
              {expanded ? COPY.transcript_collapse : COPY.transcript_expand}
            </button>
          )}
        </div>
      </div>
      {expanded ? (
        <pre className="max-h-80 overflow-auto rounded-xl bg-stone-50 dark:bg-stone-950/60 p-3 text-[14px] leading-[1.7] text-stone-800 dark:text-stone-200 whitespace-pre-wrap font-inherit">
          {transcript}
        </pre>
      ) : (
        <p className="text-[15px] leading-[1.65] text-stone-700 dark:text-stone-300">
          {preview}
          {needsTruncation ? "…" : ""}
        </p>
      )}
    </section>
  );
}
