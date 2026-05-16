import type { CanvasNode } from "../types";
import { useCanvasStore } from "../store/canvasStore";

export function NodeDetail() {
  const selectedId = useCanvasStore((s) => s.selectedNodeId);
  const node = useCanvasStore((s) => s.nodes.find((n) => n.id === selectedId));
  const selectNode = useCanvasStore((s) => s.selectNode);

  if (!node) return null;

  return (
    <div style={S.panel}>
      <div style={S.header}>
        <span style={S.title}>{node.title}</span>
        <button onClick={() => selectNode(null)} style={S.close}>✕</button>
      </div>
      <div style={S.body}>
        <div style={S.meta}>
          <span style={S.badge()}>{node.type}</span>
          <span style={S.status(node.status)}>{node.status}</span>
        </div>
        {node.description && (
          <section style={S.section}>
            <div style={S.label}>描述</div>
            <div style={S.text}>{node.description}</div>
          </section>
        )}
        {node.result && <ResultView node={node} />}
      </div>
    </div>
  );
}

function ResultView({ node }: { node: CanvasNode }) {
  const r = node.result! as Record<string, unknown>;

  switch (node.type) {
    case "script":
      return (
        <section style={S.section}>
          <div style={S.label}>剧本正文</div>
          <div style={S.text}>{(r.content as string) || ""}</div>
          {r.word_count != null && <div style={S.muted}>字数: {String(r.word_count)}</div>}
        </section>
      );

    case "storyboard":
      return (
        <section style={S.section}>
          <div style={S.label}>分镜表</div>
          {(r.shots as Array<Record<string, unknown>> | undefined)?.map((s, i) => (
            <div key={i} style={S.shot}>
              <span style={S.shotNo}>镜{String(s.no)}</span>
              <span style={S.muted}>{String(s.duration || 0)}s · {String(s.camera || "")}</span>
              <div style={S.text}>{String(s.description || "")}</div>
            </div>
          ))}
          {r.total_duration != null && (
            <div style={S.muted}>总时长: {String(r.total_duration)}s</div>
          )}
        </section>
      );

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
    flex: 1,
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

  status: (s: string) => ({
    padding: "2px 8px",
    borderRadius: 4,
    fontSize: 11,
    fontWeight: 500,
    background: s === "done" ? "#dcfce7" : s === "executing" ? "#dbeafe" : "#f4f4f5",
    color: s === "done" ? "#16a34a" : s === "executing" ? "#2563eb" : "#71717a",
  }),

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
};
