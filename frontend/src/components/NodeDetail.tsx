import { useState, useEffect } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { CanvasNode, Shot, NodeStatus } from "../types";
import { useCanvasStore } from "../store/canvasStore";

interface Props {
  onReview: (nodeId: string, action: "approve" | "reject", feedback?: string) => void;
  onExecuteNode: (nodeId: string, nodeType: string, description: string, provider?: string) => void;
  onUpdateNodeStatus: (nodeId: string, nodeStatus: NodeStatus) => void;
  onOptimizePrompt: (nodeId: string, prompt: string, feedback: string) => void;
  onDeleteEdge: (edgeId: string) => void;
}

export function NodeDetail({ onReview, onExecuteNode, onUpdateNodeStatus, onOptimizePrompt, onDeleteEdge }: Props) {
  const selectedId = useCanvasStore((s) => s.selectedNodeId);
  const node = useCanvasStore((s) => s.nodes.find((n) => n.id === selectedId));
  const allNodes = useCanvasStore((s) => s.nodes);
  const edges = useCanvasStore((s) => s.edges);
  const selectNode = useCanvasStore((s) => s.selectNode);

  if (!node) return null;

  // 找上游图片节点作为参考图
  const parentIds = edges
    .filter((e) => e.target === node.id)
    .map((e) => e.source);
  const nodeMap = new Map(allNodes.map((n) => [n.id, n]));
  const refImages = parentIds
    .map((pid) => nodeMap.get(pid))
    .filter((n): n is CanvasNode => !!n && (n.type === "image" || n.type === "video") && !!n.result?.url)
    .map((n) => ({ id: n.id, title: n.title, url: n.result!.url as string }));

  const isMedia = node.type === "image" || node.type === "video";

  return (
    <div style={S.panel}>
      <div style={S.header}>
        <span style={S.title}>{node.title}</span>
        {isMedia && <NodeStatusToggle node={node} onUpdate={onUpdateNodeStatus} />}
        <button onClick={() => selectNode(null)} style={S.close}>✕</button>
      </div>
      <div style={S.body}>
        {!isMedia && (
          <div style={S.meta}>
            <span style={S.badge()}>{node.type}</span>
            {node.subtype && <span style={S.subtype()}>{node.subtype}</span>}
            <NodeStatusToggle node={node} onUpdate={onUpdateNodeStatus} />
          </div>
        )}

        {/* 参考图（仅媒体节点） */}
        {isMedia && refImages.length > 0 && (
          <section style={S.section}>
            <div style={S.label}>参考图</div>
            <div style={S.refGrid}>
              {refImages.map((img) => {
                const edge = edges.find((e) => e.source === img.id && e.target === node.id);
                return (
                  <div key={img.id} style={S.refItem}>
                    <div style={{ position: "relative" }}>
                      <img src={img.url} alt={img.title} style={S.refImg} />
                      <button
                        onClick={() => edge && onDeleteEdge(edge.id)}
                        style={S.refDelete}
                        title="删除参考图"
                      >
                        ✕
                      </button>
                    </div>
                    <span style={S.refTitle}>{img.title}</span>
                  </div>
                );
              })}
            </div>
          </section>
        )}

        {/* 提示词（仅媒体节点） */}
        {isMedia && (
          <MediaPanel node={node} onExecuteNode={onExecuteNode} onReview={onReview} onOptimizePrompt={onOptimizePrompt} />
        )}

        {/* 生成结果 */}
        {isMedia && node.result && <ResultView node={node} />}
        {node.type === "script" && node.result && <ResultView node={node} />}
      </div>
    </div>
  );
}

function NodeStatusToggle({ node, onUpdate }: { node: CanvasNode; onUpdate: Props["onUpdateNodeStatus"] }) {
  const current = node.node_status || "reviewing";
  return (
    <div style={S.statusToggle}>
      <button
        onClick={() => onUpdate(node.id, "reviewing")}
        style={S.statusBtn("reviewing", current)}
      >
        审核中
      </button>
      <button
        onClick={() => onUpdate(node.id, "confirmed")}
        style={S.statusBtn("confirmed", current)}
      >
        已确认
      </button>
    </div>
  );
}

function MediaPanel({ node, onExecuteNode, onOptimizePrompt }: {
  node: CanvasNode;
  onExecuteNode: Props["onExecuteNode"];
  onReview: Props["onReview"];
  onOptimizePrompt: Props["onOptimizePrompt"];
}) {
  const resultPrompt = (node.result as Record<string, unknown> | null)?.prompt as string | undefined;
  const [prompt, setPrompt] = useState(resultPrompt || node.description || "");
  const [provider, setProvider] = useState(node.image_gen_provider || "apimart");
  useEffect(() => {
    const rp = (node.result as Record<string, unknown> | null)?.prompt as string | undefined;
    setPrompt(rp || node.description || "");
    setProvider(node.image_gen_provider || "apimart");
  }, [node.id, node.description, node.asset_status]);
  const [showPolish, setShowPolish] = useState(false);
  const [feedback, setFeedback] = useState("");

  const handleGenerate = () => {
    onExecuteNode(node.id, node.type, prompt, provider);
  };

  const handlePolish = () => {
    onOptimizePrompt(node.id, prompt, feedback);
    setShowPolish(false);
    setFeedback("");
  };

  const isGenerating = node.asset_status === "generating";
  const btnLabel = isGenerating ? "生成中..." : "生成";
  const btnDisabled = isGenerating;

  return (
    <section style={S.section}>
      <div style={S.label}>Provider</div>
      <select
        value={provider}
        onChange={(e) => setProvider(e.target.value)}
        style={S.providerSelect}
      >
        <option value="apimart">Apimart</option>
        <option value="google">Google Gemini</option>
      </select>

      <div style={S.label}>Prompt</div>
      <textarea
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        rows={4}
        style={S.promptInput}
      />
      <div style={S.actions}>
        <button
          onClick={handleGenerate}
          style={S.generateBtn(isGenerating)}
          disabled={btnDisabled}
        >
          {btnLabel}
        </button>
        <button
          onClick={() => setShowPolish(!showPolish)}
          style={S.agentBtn}
        >
          润色
        </button>
      </div>
      {showPolish && (
        <div style={S.polishBox}>
          <textarea
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            placeholder="描述你想要的修改方向..."
            rows={2}
            style={S.polishInput}
            autoFocus
          />
          <div style={S.polishActions}>
            <button onClick={handlePolish} style={S.polishSubmit}>提交</button>
            <button onClick={() => setShowPolish(false)} style={S.polishCancel}>取消</button>
          </div>
        </div>
      )}
    </section>
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
    case "script": {
      const shots = r.shots as Shot[] | undefined;
      const content = ((r.content as string) || "");
      // 按 ## 标题拆分为三部分：剧本 | 分镜表 | 资产清单
      const storyboardIdx = content.indexOf("## 分镜表");
      const beforeStoryboard = storyboardIdx > -1 ? content.slice(0, storyboardIdx).trimEnd() : content;
      const afterStoryboard = storyboardIdx > -1 ? content.slice(storyboardIdx).trimStart() : "";

      // 从分镜表之后提取资产清单
      let assetSection = "";
      const assetIdx = afterStoryboard.indexOf("## 资产清单");
      if (assetIdx > -1) {
        assetSection = afterStoryboard.slice(assetIdx + "## 资产清单".length).trimStart();
      }

      return (
        <>
          <section style={S.section}>
            <div style={S.label}>剧本</div>
            <Markdown remarkPlugins={[remarkGfm]} components={mdComponents}>{beforeStoryboard}</Markdown>
            {r.word_count != null && <div style={S.muted}>字数: {String(r.word_count)}</div>}
          </section>
          {assetSection && (
            <section style={S.section}>
              <div style={S.label}>资产清单</div>
              <Markdown remarkPlugins={[remarkGfm]} components={mdComponents}>{assetSection}</Markdown>
            </section>
          )}
          {shots && shots.length > 0 && (
            <section style={S.section}>
              <div style={S.label}>分镜表 ({shots.length} 镜)</div>
              {shots.map((s, i) => (
                <div key={i} style={S.shot}>
                  <span style={S.shotNo}>镜{s.no}</span>
                  <span style={S.muted}>{s.duration} · {s.camera} · {s.transition}</span>
                  <div style={S.text}>{s.description}</div>
                  {s.audio && <div style={S.muted}>🔊 {s.audio}</div>}
                </div>
              ))}
            </section>
          )}
        </>
      );
    }

    case "image":
    case "video":
      return (
        <section style={S.section}>
          <div style={S.label}>生成结果</div>
          {r.url ? (
            node.type === "image"
              ? <img src={String(r.url)} alt={node.title} style={S.resultImg} />
              : <video src={String(r.url)} controls style={S.resultVideo} />
          ) : (
            <div style={S.muted}>{node.asset_status === "generating" ? "生成中..." : node.asset_status === "failed" ? "生成失败" : "等待生成"}</div>
          )}
        </section>
      );

    case "audio":
      return (
        <section style={S.section}>
          <div style={S.label}>配音参数</div>
          {r.text ? <div style={S.text}>{String(r.text)}</div> : null}
          {r.voice ? <div style={S.muted}>音色: {String(r.voice)}</div> : null}
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
    alignItems: "center",
    gap: 8,
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

  statusToggle: {
    display: "flex",
    border: "1px solid #d4d4d8",
    borderRadius: 4,
    overflow: "hidden",
  } as React.CSSProperties,

  statusBtn: (v: string, current: string) => ({
    padding: "2px 8px",
    fontSize: 11,
    fontWeight: 500,
    border: "none",
    cursor: "pointer",
    outline: "none",
    background: v === current ? "#18181b" : "#fff",
    color: v === current ? "#fff" : "#52525b",
    borderRight: v === "reviewing" ? "1px solid #d4d4d8" : "none",
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

  providerSelect: {
    width: "100%",
    padding: "6px 8px",
    border: "1px solid #e4e4e7",
    borderRadius: 6,
    fontSize: 12,
    fontFamily: "inherit",
    outline: "none",
    background: "#fff",
    color: "#18181b",
    cursor: "pointer",
  } as React.CSSProperties,

  promptInput: {
    width: "100%",
    padding: "8px",
    border: "1px solid #e4e4e7",
    borderRadius: 6,
    fontSize: 12,
    fontFamily: "inherit",
    resize: "vertical" as const,
    outline: "none",
    lineHeight: 1.5,
  },

  actions: {
    display: "flex",
    gap: 8,
    marginTop: 4,
  },

  generateBtn: (generating: boolean) => ({
    flex: 1,
    padding: "6px 0",
    background: generating ? "#a1a1aa" : "#18181b",
    color: "#fff",
    border: "none",
    borderRadius: 6,
    cursor: generating ? "not-allowed" : "pointer",
    fontSize: 12,
    fontWeight: 500,
  }),

  agentBtn: {
    flex: 1,
    padding: "6px 0",
    background: "#f4f4f5",
    color: "#52525b",
    border: "1px solid #e4e4e7",
    borderRadius: 6,
    cursor: "pointer",
    fontSize: 12,
    fontWeight: 500,
  },

  polishBox: {
    display: "flex",
    flexDirection: "column",
    gap: 6,
    padding: 8,
    background: "#f4f4f5",
    borderRadius: 6,
    border: "1px solid #d4d4d8",
  } as React.CSSProperties,

  polishInput: {
    width: "100%",
    padding: "6px 8px",
    border: "1px solid #d4d4d8",
    borderRadius: 4,
    fontSize: 12,
    fontFamily: "inherit",
    resize: "vertical" as const,
    outline: "none",
  },

  polishActions: {
    display: "flex",
    gap: 6,
    justifyContent: "flex-end",
  },

  polishSubmit: {
    padding: "4px 12px",
    background: "#18181b",
    color: "#fff",
    border: "none",
    borderRadius: 4,
    cursor: "pointer",
    fontSize: 11,
  },

  polishCancel: {
    padding: "4px 12px",
    background: "transparent",
    color: "#71717a",
    border: "1px solid #d4d4d8",
    borderRadius: 4,
    cursor: "pointer",
    fontSize: 11,
  },

  refGrid: {
    display: "flex",
    gap: 8,
    overflow: "auto",
  } as React.CSSProperties,

  refItem: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: 2,
    flexShrink: 0,
  } as React.CSSProperties,

  refImg: {
    width: 80,
    height: 60,
    objectFit: "cover" as const,
    borderRadius: 4,
    border: "1px solid #e4e4e7",
  },

  refDelete: {
    position: "absolute",
    top: -6,
    right: -6,
    width: 18,
    height: 18,
    borderRadius: "50%",
    background: "#ef4444",
    color: "#fff",
    border: "none",
    fontSize: 10,
    fontWeight: 700,
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: 0,
    lineHeight: 1,
  } as React.CSSProperties,

  refTitle: {
    fontSize: 10,
    color: "#a1a1aa",
    maxWidth: 80,
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap" as const,
  },

  resultImg: {
    width: "100%",
    maxHeight: 260,
    objectFit: "contain" as const,
    borderRadius: 6,
    border: "1px solid #e4e4e7",
    background: "#fafafa",
  },

  resultVideo: {
    width: "100%",
    borderRadius: 6,
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

  reviewSection: {
    padding: 10,
    background: "#f4f4f5",
    borderRadius: 8,
    border: "1px solid #d4d4d8",
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
    background: "#18181b",
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
    background: "#fff",
    color: "#52525b",
    border: "1px solid #d4d4d8",
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
