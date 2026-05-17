import { useState } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { CanvasNode, Shot } from "../types";
import { useCanvasStore } from "../store/canvasStore";

interface Props {
  onReview: (nodeId: string, action: "approve" | "reject", feedback?: string) => void;
}

export function NodeDetail({ onReview }: Props) {
  const selectedId = useCanvasStore((s) => s.selectedNodeId);
  const node = useCanvasStore((s) => s.nodes.find((n) => n.id === selectedId));
  const selectNode = useCanvasStore((s) => s.selectNode);

  if (!node) return null;

  const showReview = node.status === "pending" || node.status === "awaiting_review";

  return (
    <div style={S.panel}>
      <div style={S.header}>
        <span style={S.title}>{node.title}</span>
        <button onClick={() => selectNode(null)} style={S.close}>✕</button>
      </div>
      <div style={S.body}>
        <div style={S.meta}>
          <span style={S.badge()}>{node.type}</span>
          {node.subtype && <span style={S.subtype()}>{node.subtype}</span>}
          <span style={S.status(node.status)}>{node.status}</span>
        </div>

        {showReview && (
          <ReviewSection nodeId={node.id} onReview={onReview} />
        )}

        {node.description && (
          <section style={S.section}>
            <div style={S.label}>描述</div>
            <Markdown remarkPlugins={[remarkGfm]} components={mdComponents}>{node.description}</Markdown>
          </section>
        )}
        {node.result && <ResultView node={node} />}
      </div>
    </div>
  );
}

function ReviewSection({ nodeId, onReview }: { nodeId: string; onReview: Props["onReview"] }) {
  const [showFeedback, setShowFeedback] = useState(false);
  const [feedback, setFeedback] = useState("");

  return (
    <section style={S.reviewSection}>
      {showFeedback ? (
        <>
          <textarea
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            placeholder="告诉 agent 哪里需要改..."
            rows={2}
            style={S.feedbackInput}
            autoFocus
          />
          <div style={S.reviewBtns}>
            <button
              onClick={() => {
                onReview(nodeId, "reject", feedback);
                setShowFeedback(false);
                setFeedback("");
              }}
              style={S.rejectBtn}
            >
              驳回并反馈
            </button>
            <button onClick={() => setShowFeedback(false)} style={S.cancelBtn}>取消</button>
          </div>
        </>
      ) : (
        <div style={S.reviewBtns}>
          <button onClick={() => onReview(nodeId, "approve")} style={S.approveBtn}>
            通过
          </button>
          <button onClick={() => setShowFeedback(true)} style={S.rejectBtn}>
            驳回
          </button>
        </div>
      )}
    </section>
  );
}

function ResultView({ node }: { node: CanvasNode }) {
  const r = node.result! as Record<string, unknown>;

  switch (node.type) {
    case "script":
      return (
        <section style={S.section}>
          <div style={S.label}>剧本正文</div>
          <Markdown remarkPlugins={[remarkGfm]} components={mdComponents}>{(r.content as string) || ""}</Markdown>
          {r.word_count != null && <div style={S.muted}>字数: {String(r.word_count)}</div>}
        </section>
      );

    case "storyboard": {
      const shots = r.shots as Shot[] | undefined;
      return (
        <section style={S.section}>
          <div style={S.label}>分镜表</div>
          {shots ? (
            shots.map((s, i) => (
              <div key={i} style={S.shot}>
                <span style={S.shotNo}>镜{s.no}</span>
                <span style={S.muted}>{s.duration} · {s.camera} · {s.transition}</span>
                <div style={S.text}>{s.description}</div>
                {s.audio && <div style={S.muted}>🔊 {s.audio}</div>}
              </div>
            ))
          ) : (
            <Markdown remarkPlugins={[remarkGfm]} components={mdComponents}>{(r.content as string) || ""}</Markdown>
          )}
        </section>
      );
    }

    case "image":
    case "video":
      return (
        <section style={S.section}>
          <div style={S.label}>生成参数</div>
          {r.url ? <div style={S.text}>{String(r.url)}</div> : null}
          {r.prompt ? (
            <>
              <div style={S.label}>Prompt</div>
              <div style={S.text}>{String(r.prompt)}</div>
            </>
          ) : null}
          {r.resolution != null && <div style={S.muted}>分辨率: {String(r.resolution)}</div>}
          {r.duration_seconds != null && <div style={S.muted}>时长: {String(r.duration_seconds)}s</div>}
        </section>
      );

    case "audio":
      return (
        <section style={S.section}>
          <div style={S.label}>配音参数</div>
          {r.text ? <div style={S.text}>{String(r.text)}</div> : null}
          {r.voice ? <div style={S.muted}>音色: {String(r.voice)}</div> : null}
          {r.duration_seconds != null && <div style={S.muted}>时长: {String(r.duration_seconds)}s</div>}
        </section>
      );

    default:
      return null;
  }
}

const mdComponents = {
  p: (props: React.HTMLAttributes<HTMLParagraphElement>) => <p style={S.mdP} {...props} />,
  h1: (props: React.HTMLAttributes<HTMLHeadingElement>) => <h3 style={S.mdH} {...props} />,
  h2: (props: React.HTMLAttributes<HTMLHeadingElement>) => <h4 style={S.mdH} {...props} />,
  h3: (props: React.HTMLAttributes<HTMLHeadingElement>) => <h5 style={S.mdH} {...props} />,
  ul: (props: React.HTMLAttributes<HTMLUListElement>) => <ul style={S.mdList} {...props} />,
  ol: (props: React.HTMLAttributes<HTMLOListElement>) => <ol style={S.mdList} {...props} />,
  li: (props: React.LiHTMLAttributes<HTMLLIElement>) => <li style={S.mdLi} {...props} />,
  strong: (props: React.HTMLAttributes<HTMLElement>) => <strong style={S.mdStrong} {...props} />,
  em: (props: React.HTMLAttributes<HTMLElement>) => <em style={S.mdEm} {...props} />,
  code: (props: React.HTMLAttributes<HTMLElement>) => <code style={S.mdCode} {...props} />,
  blockquote: (props: React.BlockquoteHTMLAttributes<HTMLQuoteElement>) => <blockquote style={S.mdQuote} {...props} />,
  hr: () => <hr style={S.mdHr} />,
  table: (props: React.TableHTMLAttributes<HTMLTableElement>) => <table style={S.mdTable} {...props} />,
  th: (props: React.ThHTMLAttributes<HTMLTableCellElement>) => <th style={S.mdTh} {...props} />,
  td: (props: React.TdHTMLAttributes<HTMLTableCellElement>) => <td style={S.mdTd} {...props} />,
};

const S = {
  panel: {
    width: 320,
    display: "flex",
    flexDirection: "column",
    background: "#fff",
    borderLeft: "1px solid #e4e4e7",
    overflow: "auto",
  } as React.CSSProperties,

  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "12px 16px",
    borderBottom: "1px solid #e4e4e7",
  },

  title: {
    fontWeight: 600,
    fontSize: 14,
    color: "#18181b",
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap" as const,
    flex: "1",
  },

  close: {
    background: "transparent",
    border: "none",
    cursor: "pointer",
    fontSize: 14,
    color: "#a1a1aa",
    padding: 4,
  },

  body: {
    padding: "12px 16px",
    display: "flex",
    flexDirection: "column",
    gap: 12,
    flex: "1",
    overflow: "auto",
  } as React.CSSProperties,

  meta: {
    display: "flex",
    gap: 8,
    alignItems: "center",
  },

  badge: () => ({
    padding: "2px 8px",
    borderRadius: 4,
    fontSize: 11,
    fontWeight: 500,
    background: "#f4f4f5",
    color: "#71717a",
  }),

  subtype: () => ({
    padding: "2px 8px",
    borderRadius: 4,
    fontSize: 11,
    fontWeight: 500,
    background: "#ede9fe",
    color: "#7c3aed",
  }),

  status: (s: string) => ({
    padding: "2px 8px",
    borderRadius: 4,
    fontSize: 11,
    fontWeight: 500,
    background:
      s === "done" ? "#dcfce7"
      : s === "approved" ? "#dbeafe"
      : s === "awaiting_review" ? "#fef3c7"
      : s === "executing" ? "#dbeafe"
      : s === "failed" ? "#fee2e2"
      : "#f4f4f5",
    color:
      s === "done" ? "#16a34a"
      : s === "approved" ? "#2563eb"
      : s === "awaiting_review" ? "#d97706"
      : s === "executing" ? "#2563eb"
      : s === "failed" ? "#dc2626"
      : "#71717a",
  }),

  reviewSection: {
    padding: 10,
    background: "#fef3c7",
    borderRadius: 8,
    border: "1px solid #fcd34d",
    display: "flex",
    flexDirection: "column",
    gap: 8,
  } as React.CSSProperties,

  reviewBtns: {
    display: "flex",
    gap: 8,
  },

  approveBtn: {
    flex: 1,
    padding: "6px 0",
    background: "#16a34a",
    color: "#fff",
    border: "none",
    borderRadius: 6,
    cursor: "pointer",
    fontSize: 13,
    fontWeight: 500,
  },

  rejectBtn: {
    flex: 1,
    padding: "6px 0",
    background: "#fef3c7",
    color: "#d97706",
    border: "1px solid #fcd34d",
    borderRadius: 6,
    cursor: "pointer",
    fontSize: 13,
    fontWeight: 500,
  },

  cancelBtn: {
    flex: 1,
    padding: "6px 0",
    background: "transparent",
    color: "#71717a",
    border: "1px solid #e4e4e7",
    borderRadius: 6,
    cursor: "pointer",
    fontSize: 13,
  },

  feedbackInput: {
    width: "100%",
    padding: "6px 8px",
    border: "1px solid #fcd34d",
    borderRadius: 6,
    fontSize: 12,
    outline: "none",
    resize: "vertical" as const,
    fontFamily: "inherit",
    background: "#fff",
  },

  section: {
    display: "flex",
    flexDirection: "column",
    gap: 6,
    padding: 0,
  } as React.CSSProperties,

  label: {
    fontSize: 11,
    fontWeight: 500,
    color: "#a1a1aa",
    textTransform: "uppercase" as const,
    letterSpacing: "0.05em",
  },

  text: {
    fontSize: 13,
    color: "#3f3f46",
    lineHeight: 1.6,
    whiteSpace: "pre-wrap" as const,
    wordBreak: "break-word" as const,
  },

  muted: {
    fontSize: 12,
    color: "#a1a1aa",
  },

  shot: {
    padding: "8px 0",
    borderBottom: "1px solid #f4f4f5",
    display: "flex",
    flexDirection: "column",
    gap: 2,
  } as React.CSSProperties,

  shotNo: {
    fontSize: 12,
    fontWeight: 600,
    color: "#18181b",
  },

  // markdown
  mdP: { fontSize: 13, color: "#3f3f46", lineHeight: 1.7, margin: "6px 0", whiteSpace: "pre-wrap" as const, wordBreak: "break-word" as const },
  mdH: { fontSize: 14, fontWeight: 600, color: "#18181b", margin: "12px 0 4px" },
  mdList: { margin: "4px 0", paddingLeft: 20 },
  mdLi: { fontSize: 13, color: "#3f3f46", lineHeight: 1.6, margin: "2px 0" },
  mdStrong: { fontWeight: 600, color: "#18181b" },
  mdEm: { fontStyle: "italic", color: "#71717a" },
  mdCode: { fontFamily: "monospace", fontSize: 12, background: "#f4f4f5", padding: "1px 4px", borderRadius: 3 },
  mdQuote: { borderLeft: "2px solid #e4e4e7", paddingLeft: 10, margin: "6px 0", color: "#71717a" },
  mdHr: { border: "none", borderTop: "1px solid #e4e4e7", margin: "12px 0" },
  mdTable: { width: "100%", borderCollapse: "collapse", margin: "6px 0", fontSize: 12 } as React.CSSProperties,
  mdTh: { border: "1px solid #e4e4e7", padding: "4px 8px", background: "#f4f4f5", fontWeight: 600, textAlign: "left" as const },
  mdTd: { border: "1px solid #e4e4e7", padding: "4px 8px", color: "#3f3f46" },
};
