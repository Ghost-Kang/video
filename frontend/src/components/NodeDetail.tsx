import { useState, useEffect } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { CanvasNode, Shot } from "../types";
import type { NodeActions } from "../hooks/useNodeActions";
import { useCanvasStore } from "../store/canvasStore";
import { useToastStore } from "../store/toastStore";
import { buildCanvasPublishPack } from "../lib/buildPublishPack";
import { NodeVersionHistory } from "./NodeVersionHistory";

interface Props {
  actions: NodeActions;
}

export function NodeDetail({ actions }: Props) {
  const selectedId = useCanvasStore((s) => s.selectedNodeId);
  const node = useCanvasStore((s) => s.nodes.find((n) => n.id === selectedId));
  const allNodes = useCanvasStore((s) => s.nodes);
  const edges = useCanvasStore((s) => s.edges);
  const selectNode = useCanvasStore((s) => s.selectNode);

  // 面板可拖宽(默认 440,边界 360–720)+ 窄屏覆盖式(<760px 浮在画布上,带半透背景)。
  // 所有 hook 必须在 `if (!node)` early-return 之前(rules-of-hooks 铁律,否则切到无选中
  // 节点会少调 hook → React #310 白屏)。
  const [width, setWidth] = useState(440);
  const [narrow, setNarrow] = useState(() => typeof window !== "undefined" && window.innerWidth < 760);
  const [dragging, setDragging] = useState(false);

  useEffect(() => {
    const onResize = () => setNarrow(window.innerWidth < 760);
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  useEffect(() => {
    if (!dragging) return;
    const onMove = (e: MouseEvent) => setWidth(Math.min(720, Math.max(360, window.innerWidth - e.clientX)));
    const onUp = () => setDragging(false);
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    document.body.style.userSelect = "none";
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
      document.body.style.userSelect = "";
    };
  }, [dragging]);

  if (!node) return null;

  const panelStyle: React.CSSProperties = narrow
    ? { ...S.panel, position: "fixed", top: 0, right: 0, bottom: 0, width: "min(92vw, 460px)", zIndex: 60, boxShadow: "-12px 0 40px rgba(124,45,18,0.18)" }
    : { ...S.panel, width };

  // 找上游节点作为参考图 / 待合成视频
  const parentIds = edges
    .filter((e) => e.target === node.id)
    .map((e) => e.source);
  const nodeMap = new Map(allNodes.map((n) => [n.id, n]));
  const refImages = parentIds
    .map((pid) => nodeMap.get(pid))
    .filter((n): n is CanvasNode => !!n && (n.type === "image" || n.type === "video") && !!n.result?.url)
    .map((n) => ({ id: n.id, title: n.title, url: n.result!.url as string, type: n.type }));

  const isMedia = node.type === "image" || node.type === "video" || node.type === "composite";

  return (
    <>
      {narrow && <div style={S.backdrop} onClick={() => selectNode(null)} data-testid="nodedetail-backdrop" />}
      <div style={panelStyle} data-testid="node-detail">
      {/* 拖宽手柄(窄屏覆盖态不显示)。 */}
      {!narrow && (
        <div
          style={{ ...S.resizeHandle, background: dragging ? "rgba(124,45,18,0.25)" : "transparent" }}
          onMouseDown={() => setDragging(true)}
          title="拖动调整宽度"
          data-testid="nodedetail-resize"
        />
      )}
      <div style={S.header}>
        <span style={S.title}>{node.title}</span>
        {isMedia && <NodeStatusToggle node={node} onUpdate={actions.handleUpdateNodeStatus} />}
        <button onClick={() => selectNode(null)} style={S.close}>✕</button>
      </div>
      <div style={S.body}>
        {!isMedia && (
          <div style={S.meta}>
            <span style={S.badge()}>{node.type}</span>
            {node.subtype && <span style={S.subtype()}>{node.subtype}</span>}
            <NodeStatusToggle node={node} onUpdate={actions.handleUpdateNodeStatus} />
          </div>
        )}

        {/* 参考图（仅媒体节点） */}
        {isMedia && refImages.length > 0 && (
          <section style={S.section}>
            <div style={S.label}>{node.type === "composite" ? "待合成视频" : "参考图"}</div>
            <div style={S.refGrid}>
              {refImages.map((img, idx) => {
                const edge = edges.find((e) => e.source === img.id && e.target === node.id);
                const total = refImages.length;
                return (
                  <div key={img.id} style={S.refItem}>
                    <span style={S.refTitle}>{img.title}</span>
                    <div style={{ position: "relative" }}>
                      {img.type === "video" ? (
                        <video src={img.url} style={S.refImg} preload="metadata" />
                      ) : (
                        <img src={img.url} alt={img.title} style={S.refImg} />
                      )}
                      <button
                        onClick={() => edge && actions.handleDeleteEdge(edge.id)}
                        style={S.refDelete}
                        title="删除参考图"
                      >
                        ✕
                      </button>
                      {total > 1 && idx < total - 1 && (
                        <button
                          onClick={() => edge && actions.handleReorderEdge(edge.id, "down")}
                          style={{ ...S.refArrow, right: -10, top: "50%", transform: "translateY(-50%)" }}
                          title="右移"
                        >
                          ›
                        </button>
                      )}
                      {total > 1 && idx > 0 && (
                        <button
                          onClick={() => edge && actions.handleReorderEdge(edge.id, "up")}
                          style={{ ...S.refArrow, left: -10, top: "50%", transform: "translateY(-50%)" }}
                          title="左移"
                        >
                          ‹
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        )}

        {/* 提示词（仅媒体节点） */}
        {isMedia && (
          <MediaPanel key={node.id} node={node} actions={actions} />
        )}

        {/* 生成结果 */}
        {isMedia && node.result && <ResultView node={node} />}
        {node.type === "script" && node.result && <ResultView node={node} />}

        {/* 版本历史 + 新旧对比(time-travel 回溯 P2 slice-2b)。key=node.id → 切节点 remount 重置选中态。 */}
        <NodeVersionHistory key={node.id} node={node} actions={actions} />
      </div>
      </div>
    </>
  );
}

function NodeStatusToggle({ node, onUpdate }: { node: CanvasNode; onUpdate: NodeActions["handleUpdateNodeStatus"] }) {
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

function MediaPanel({ node, actions }: {
  node: CanvasNode;
  actions: NodeActions;
}) {
  const resultPrompt = (node.result as Record<string, unknown> | null)?.prompt as string | undefined;
  const [prompt, setPrompt] = useState(resultPrompt || node.description || "");
  const [provider, setProvider] = useState(node.image_gen_provider || "seedream");
  const [duration, setDuration] = useState(5);
  const [resolution, setResolution] = useState("720p");
  const [generateAudio, setGenerateAudio] = useState(true);
  useEffect(() => {
    const rp = (node.result as Record<string, unknown> | null)?.prompt as string | undefined;
    setPrompt(rp || node.description || "");
    setProvider(node.image_gen_provider || "seedream");
  }, [node.id, node.description, node.asset_status]);
  const [showPolish, setShowPolish] = useState(false);
  const [feedback, setFeedback] = useState("");

  const handleGenerate = () => {
    const isComposite = node.type === "composite";
    actions.handleExecuteNode(node.id, node.type, prompt, isComposite ? undefined : provider, isComposite ? undefined : duration, isComposite ? undefined : resolution, isComposite ? undefined : generateAudio);
  };

  const handlePolish = () => {
    actions.handleOptimizePrompt(node.id, prompt, feedback);
    setShowPolish(false);
    setFeedback("");
  };

  const isGenerating = node.asset_status === "generating";
  const isVideo = node.type === "video";
  const isComposite = node.type === "composite";
  const btnLabel = isComposite ? (isGenerating ? "合成中..." : "合成") : isGenerating ? "生成中..." : "生成";
  const btnDisabled = isGenerating;

  // M6 — 生成前给用户一个成本预期(此前画布全程不暴露花费,撞 cap 才哑失败)。
  // 与后端 cost_guard.predict_generation_cost 口径一致:图 ¥1.5/张、视频 ¥0.30/秒、合成本地免费。
  const estCny = isComposite ? 0 : isVideo ? duration * 0.3 : 1.5;
  const costHint = isComposite ? "本地合成 · 免费" : `预计 ¥${estCny.toFixed(estCny % 1 === 0 ? 0 : 1)}`;

  return (
    <section style={S.section}>
      {!isVideo && !isComposite && (
        <>
          <div style={S.label}>Provider</div>
          <select value={provider} onChange={(e) => {
            const v = e.target.value;
            setProvider(v);
            useCanvasStore.setState((s) => ({
              nodes: s.nodes.map((n) => n.id === node.id ? { ...n, image_gen_provider: v } : n),
            }));
          }} style={S.providerSelect}>
            {/* seedream(火山·境内)= 后端 IMAGE_GEN_PROVIDER 默认,复用 ARK key、境内合规。
                之前默认 apimart(常无 key→生成失败)且 google 会让 prompt+参考图跨境(H3)。 */}
            <option value="seedream">Seedream(火山·境内)</option>
            <option value="apimart">Apimart</option>
            <option value="google">Google Gemini(跨境)</option>
          </select>
        </>
      )}

      {isVideo && (
        <div style={{ display: "flex", gap: 8 }}>
          <div style={{ flex: 1 }}>
            <div style={S.label}>时长</div>
            <select value={duration} onChange={(e) => setDuration(Number(e.target.value))} style={S.providerSelect}>
              {[4,5,6,7,8,9,10,11,12,13,14,15].map((s) => (
                <option key={s} value={s}>{s}s</option>
              ))}
            </select>
          </div>
          <div style={{ flex: 1 }}>
            <div style={S.label}>分辨率</div>
            <select value={resolution} onChange={(e) => setResolution(e.target.value)} style={S.providerSelect}>
              <option value="480p">480p</option>
              <option value="720p">720p</option>
              <option value="1080p">1080p</option>
            </select>
          </div>
          <div style={{ flex: 0 }}>
            <div style={S.label}>声音</div>
            <button
              onClick={() => setGenerateAudio(!generateAudio)}
              style={generateAudio ? S.toggleOn : S.toggleOff}
            >
              {generateAudio ? "ON" : "OFF"}
            </button>
          </div>
        </div>
      )}

      {!isComposite && (
        <>
          <div style={S.label}>Prompt</div>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            rows={4}
            style={S.promptInput}
          />
        </>
      )}

      <div style={{ ...S.muted, marginTop: 4 }}>{costHint}</div>
      <div style={S.actions}>
        <button
          onClick={handleGenerate}
          style={S.generateBtn(isGenerating)}
          disabled={btnDisabled}
        >
          {btnLabel}
        </button>
        {!isComposite && (
          <button
            onClick={() => setShowPolish(!showPolish)}
            style={S.agentBtn}
          >
            润色
          </button>
        )}
      </div>
      {showPolish && !isComposite && (
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
    case "composite":
      return (
        <>
          <section style={S.section}>
            <div style={S.label}>{node.type === "composite" ? "合成结果" : "生成结果"}</div>
            {r.url ? (
              node.type === "image"
                ? <img src={String(r.url)} alt={node.title} style={S.resultImg} />
                : <video
                    src={String(r.url)}
                    controls
                    style={S.resultVideo}
                    onPlay={(e) => {
                      document.querySelectorAll("video").forEach((v) => {
                        if (v !== e.currentTarget) v.pause();
                      });
                    }}
                  />
            ) : (
              <div style={S.muted}>
                {node.asset_status === "generating" ? "生成中..." : node.asset_status === "failed" ? (r.error ? `失败: ${String(r.error)}` : "生成失败") : node.asset_status === "timeout" ? (r.error ? `超时: ${String(r.error)}` : "超时") : "等待生成"}
              </div>
            )}
          </section>
          {/* H1:成片做完即出「一键复制发布包」—— 画布闭环最后一公里(此前 publish 只活在
              被 flag 暂挂的 CardStack)。从策划书/图片/本节点成片就地组装。 */}
          {node.type === "composite" && <CompositePublishPack node={node} />}
        </>
      );

    default:
      return null;
  }
}

/** 合成节点的发布包(H1)。成片完成时出一键复制:标题候选 + 标签 + 完整脚本 + 镜头图 + 成片链接。
 *  数据就地从画布节点取(策划书节点→脚本,image 节点→镜头图,本 composite 节点→成片)。 */
function CompositePublishPack({ node }: { node: CanvasNode }) {
  const nodes = useCanvasStore((s) => s.nodes);
  const analysis = useCanvasStore((s) => s.analysis);
  const rewriteShots = useCanvasStore((s) => s.rewriteShots);
  const pushToast = useToastStore((s) => s.push);
  const [copied, setCopied] = useState(false);

  const filmUrl = (node.result as Record<string, unknown> | null)?.url as string | undefined;
  if (!filmUrl) return null; // 成片未完成时不出发布包(hooks 已全部在此之前调用)

  const handleCopy = async () => {
    const scriptNode = nodes.find((n) => n.type === "script");
    const sr = scriptNode?.result as Record<string, unknown> | null;
    const scriptText = (sr?.content as string) || scriptNode?.description || "";
    const shotImageUrls = nodes
      .filter((n) => n.type === "image" && (n.result as Record<string, unknown> | null)?.url)
      .sort((a, b) => (Number(a.shot_no) || 1e9) - (Number(b.shot_no) || 1e9))
      .map((n) => String((n.result as Record<string, unknown>).url));
    const pack = buildCanvasPublishPack({ scriptText, shotImageUrls, filmUrl, analysis, rewriteShots });
    try {
      await navigator.clipboard.writeText(pack);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
      pushToast({ kind: "info", title: "发布包已复制", body: "标题/标签/脚本/镜头图/成片已进剪贴板" });
    } catch {
      pushToast({ kind: "error", title: "复制失败", body: "请手动选中文本复制" });
    }
  };

  return (
    <section style={S.section}>
      <div style={S.label}>发布包</div>
      <button onClick={handleCopy} style={S.generateBtn(false)}>
        {copied ? "✓ 已复制" : "一键复制发布包"}
      </button>
      <div style={S.muted}>标题候选 · 标签 · 完整脚本 · 镜头图 · 成片链接</div>
    </section>
  );
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
    flexShrink: 0,
    position: "relative",
    display: "flex",
    flexDirection: "column",
    background: "var(--color-paper, #faf8f3)",
    borderLeft: "1px solid rgba(124,45,18,0.12)",
    boxShadow: "-8px 0 24px rgba(124,45,18,0.05)",
    overflow: "hidden",
  } as React.CSSProperties,

  resizeHandle: {
    position: "absolute",
    left: 0,
    top: 0,
    bottom: 0,
    width: 6,
    cursor: "col-resize",
    zIndex: 2,
    transition: "background 0.15s",
  } as React.CSSProperties,

  backdrop: {
    position: "fixed",
    inset: 0,
    background: "rgba(28,25,23,0.28)",
    backdropFilter: "blur(2px)",
    WebkitBackdropFilter: "blur(2px)",
    zIndex: 55,
  } as React.CSSProperties,

  header: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    padding: "12px 16px",
    borderBottom: "1px solid #ece4d8",
  },

  title: {
    fontWeight: 600,
    fontSize: 14,
    color: "#292524",
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
    color: "#a8a29e",
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
    background: "#f3ede3",
    color: "#78716c",
  }),

  subtype: () => ({
    padding: "2px 8px",
    borderRadius: 4,
    fontSize: 11,
    fontWeight: 500,
    background: "#f0e6d8",
    color: "#c2410c",
  }),

  statusToggle: {
    display: "flex",
    border: "1px solid #ddd2c2",
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
    background: v === current ? "#7c2d12" : "#fff",
    color: v === current ? "#faf8f3" : "#78716c",
    borderRight: v === "reviewing" ? "1px solid #ddd2c2" : "none",
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
    color: "#a8a29e",
    textTransform: "uppercase" as const,
    letterSpacing: "0.05em",
  },

  toggleOn: {
    padding: "3px 10px",
    border: "none",
    borderRadius: 4,
    background: "#22c55e",
    color: "#fff",
    cursor: "pointer",
    fontSize: 11,
    fontWeight: 600,
    marginTop: 4,
    minWidth: 44,
  } as React.CSSProperties,

  toggleOff: {
    padding: "3px 10px",
    border: "1px solid #ddd2c2",
    borderRadius: 4,
    background: "#f3ede3",
    color: "#a8a29e",
    cursor: "pointer",
    fontSize: 11,
    fontWeight: 600,
    marginTop: 4,
    minWidth: 44,
  } as React.CSSProperties,

  providerSelect: {
    width: "100%",
    padding: "6px 8px",
    border: "1px solid #ece4d8",
    borderRadius: 6,
    fontSize: 12,
    fontFamily: "inherit",
    outline: "none",
    background: "#fff",
    color: "#292524",
    cursor: "pointer",
  } as React.CSSProperties,

  promptInput: {
    width: "100%",
    padding: "8px",
    border: "1px solid #ece4d8",
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
    background: generating ? "#c4b8a8" : "#7c2d12",
    color: "#faf8f3",
    border: "none",
    borderRadius: 6,
    cursor: generating ? "not-allowed" : "pointer",
    fontSize: 12,
    fontWeight: 600,
  }),

  agentBtn: {
    flex: 1,
    padding: "6px 0",
    background: "#f3ede3",
    color: "#78716c",
    border: "1px solid #ece4d8",
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
    background: "#f3ede3",
    borderRadius: 6,
    border: "1px solid #ddd2c2",
  } as React.CSSProperties,

  polishInput: {
    width: "100%",
    padding: "6px 8px",
    border: "1px solid #ddd2c2",
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
    background: "#292524",
    color: "#fff",
    border: "none",
    borderRadius: 4,
    cursor: "pointer",
    fontSize: 11,
  },

  polishCancel: {
    padding: "4px 12px",
    background: "transparent",
    color: "#78716c",
    border: "1px solid #ddd2c2",
    borderRadius: 4,
    cursor: "pointer",
    fontSize: 11,
  },

  refGrid: {
    display: "flex",
    gap: 20,
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
    border: "1px solid #ece4d8",
  },

  refArrow: {
    position: "absolute",
    width: 16,
    height: 16,
    borderRadius: "50%",
    background: "rgba(0,0,0,0.5)",
    color: "#fff",
    border: "none",
    fontSize: 12,
    fontWeight: 600,
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: 0,
    lineHeight: 1,
    zIndex: 2,
  } as React.CSSProperties,

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
    color: "#a8a29e",
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
    border: "1px solid #ece4d8",
    background: "#faf8f3",
  },

  resultVideo: {
    width: "100%",
    borderRadius: 6,
  },

  text: {
    fontSize: 13,
    color: "#44403c",
    lineHeight: 1.6,
    whiteSpace: "pre-wrap" as const,
    wordBreak: "break-word" as const,
  },

  muted: {
    fontSize: 12,
    color: "#a8a29e",
  },

  reviewSection: {
    padding: 10,
    background: "#f3ede3",
    borderRadius: 8,
    border: "1px solid #ddd2c2",
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
    background: "#292524",
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
    color: "#78716c",
    border: "1px solid #ddd2c2",
    borderRadius: 6,
    cursor: "pointer",
    fontSize: 13,
    fontWeight: 500,
  },

  cancelBtn: {
    flex: 1,
    padding: "6px 0",
    background: "transparent",
    color: "#78716c",
    border: "1px solid #ece4d8",
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
    borderBottom: "1px solid #f3ede3",
    display: "flex",
    flexDirection: "column",
    gap: 2,
  } as React.CSSProperties,

  shotNo: {
    fontSize: 12,
    fontWeight: 600,
    color: "#292524",
  },

  // markdown
  mdP: { fontSize: 13, color: "#44403c", lineHeight: 1.7, margin: "6px 0", whiteSpace: "pre-wrap" as const, wordBreak: "break-word" as const },
  mdH: { fontSize: 14, fontWeight: 600, color: "#292524", margin: "12px 0 4px" },
  mdList: { margin: "4px 0", paddingLeft: 20 },
  mdLi: { fontSize: 13, color: "#44403c", lineHeight: 1.6, margin: "2px 0" },
  mdStrong: { fontWeight: 600, color: "#292524" },
  mdEm: { fontStyle: "italic", color: "#78716c" },
  mdCode: { fontFamily: "monospace", fontSize: 12, background: "#f3ede3", padding: "1px 4px", borderRadius: 3 },
  mdQuote: { borderLeft: "2px solid #ece4d8", paddingLeft: 10, margin: "6px 0", color: "#78716c" },
  mdHr: { border: "none", borderTop: "1px solid #ece4d8", margin: "12px 0" },
  mdTable: { width: "100%", borderCollapse: "collapse", margin: "6px 0", fontSize: 12 } as React.CSSProperties,
  mdTh: { border: "1px solid #ece4d8", padding: "4px 8px", background: "#f3ede3", fontWeight: 600, textAlign: "left" as const },
  mdTd: { border: "1px solid #ece4d8", padding: "4px 8px", color: "#44403c" },
};
