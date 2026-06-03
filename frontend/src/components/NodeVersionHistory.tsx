import { useEffect, useState } from "react";
import type { CanvasNode } from "../types";
import type { NodeActions } from "../hooks/useNodeActions";
import { useCanvasStore } from "../store/canvasStore";

/**
 * time-travel 回溯(P2 slice-2b)版本历史 + 「当前 vs 选中旧版」对比(只读)。
 *
 * 选中节点时拉取 `list_node_versions`(经 node_versions_returned 落 canvasStore.nodeVersions),
 * 列出 append-only 旧版快照,默认对比「当前 live 产物 vs 最近一次旧版」(末项=当前的前一版)。
 * 点列表行切换对比的旧版。回滚(restore)留 2c,本片纯只读。
 *
 * 由 NodeDetail 以 `key={node.id}` 挂载 —— 切节点即 remount,本地选中态自然重置(避免在 effect
 * 里 setState 触发 react-hooks/set-state-in-effect)。effect 只发拉取命令,不 setState。
 */
export function NodeVersionHistory({ node, actions }: { node: CanvasNode; actions: NodeActions }) {
  const versions = useCanvasStore((s) => s.nodeVersions[node.id]);
  const [selectedSeq, setSelectedSeq] = useState<number | null>(null);
  const { handleListNodeVersions } = actions;

  // node.id 切节点时重取;node.asset_status 在「原地重生(done→generating)」与「生成完成
  // (generating→done)」时翻转 —— 借它在面板不关、node.id 不变的原地重生后自动重取,否则
  // 刚归档的旧版不会出现在列表/计数里(stale)。effect 只发拉取命令,不 setState。
  useEffect(() => {
    handleListNodeVersions(node.id);
  }, [node.id, node.asset_status, handleListNodeVersions]);

  // 默认对比「当前 vs 最近一次旧版」:versions 末项 = 最近快照 = 当前产物的前一版。
  // 纯派生,不走 effect setState(remount 已重置 selectedSeq)。
  const effectiveSeq =
    selectedSeq ?? (versions && versions.length ? versions[versions.length - 1].version_seq : null);
  const selected = versions?.find((v) => v.version_seq === effectiveSeq) ?? null;

  return (
    <section style={S.section} data-testid="node-version-history">
      <div style={S.label}>版本历史{versions ? ` (${versions.length})` : ""}</div>

      {versions === undefined ? (
        <div style={S.muted}>加载中…</div>
      ) : versions.length === 0 ? (
        <div style={S.muted}>暂无历史版本 —— 重生此节点后,旧版会存档在这里。</div>
      ) : (
        <>
          <div style={S.list}>
            {versions.map((v) => (
              <button
                key={v.version_seq}
                type="button"
                onClick={() => setSelectedSeq(v.version_seq)}
                style={v.version_seq === effectiveSeq ? S.rowActive : S.row}
                data-testid={`version-row-${v.version_seq}`}
              >
                <span style={S.seq}>v{v.version_seq}</span>
                <span style={S.reason}>{v.reason}</span>
                <span style={S.time}>{fmtTime(v.created_at)}</span>
              </button>
            ))}
          </div>

          {selected && (
            <div style={S.compare} data-testid="version-compare">
              <div style={S.col}>
                <div style={S.colHeadNew}>当前(新)</div>
                {!node.result && node.asset_status === "generating" ? (
                  <div style={S.empty}>生成中…</div>
                ) : (
                  renderProduct(node.result, node.type, "当前产物")
                )}
                <div style={S.muted}>asset: {node.asset_status}</div>
              </div>
              <div style={S.col}>
                <div style={S.colHeadOld}>
                  v{selected.version_seq} · {selected.reason}
                </div>
                {renderProduct(selected.result, node.type, `第 ${selected.version_seq} 版产物`)}
                <div style={S.muted}>
                  {fmtTime(selected.created_at)} · {selected.asset_status}
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </section>
  );
}

function fmtTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString("zh-CN", {
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

function renderProduct(result: Record<string, unknown> | null, type: string, alt: string) {
  const url = result?.url as string | undefined;
  if (type === "image") {
    return url ? <img src={url} alt={alt} style={S.media} /> : <div style={S.empty}>无图</div>;
  }
  if (type === "video" || type === "composite") {
    return url ? <video src={url} controls style={S.media} /> : <div style={S.empty}>无视频</div>;
  }
  const content = (result?.content as string) ?? "";
  return content ? <pre style={S.script}>{content.slice(0, 280)}</pre> : <div style={S.empty}>无内容</div>;
}

const S: Record<string, React.CSSProperties> = {
  section: { display: "flex", flexDirection: "column", gap: 6, paddingTop: 4 },
  label: {
    fontSize: 11,
    fontWeight: 500,
    color: "#a1a1aa",
    textTransform: "uppercase",
    letterSpacing: "0.05em",
  },
  muted: { fontSize: 12, color: "#a1a1aa" },
  list: { display: "flex", flexDirection: "column", gap: 3 },
  row: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    padding: "5px 8px",
    border: "1px solid #e4e4e7",
    borderRadius: 6,
    background: "#fafafa",
    cursor: "pointer",
    textAlign: "left",
    width: "100%",
  },
  rowActive: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    padding: "5px 8px",
    border: "1px solid #b45309",
    borderRadius: 6,
    background: "#fef3c7",
    cursor: "pointer",
    textAlign: "left",
    width: "100%",
  },
  seq: { fontSize: 11, fontWeight: 600, color: "#7c2d12", flexShrink: 0, minWidth: 22 },
  reason: { fontSize: 12, color: "#3f3f46", flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" },
  time: { fontSize: 11, color: "#a1a1aa", flexShrink: 0 },
  compare: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginTop: 4 },
  col: { display: "flex", flexDirection: "column", gap: 4, minWidth: 0 },
  colHeadNew: { fontSize: 11, fontWeight: 600, color: "#16a34a" },
  colHeadOld: {
    fontSize: 11,
    fontWeight: 600,
    color: "#b45309",
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  },
  media: { width: "100%", maxHeight: 130, borderRadius: 4, objectFit: "contain", background: "#f4f4f5" },
  script: {
    fontSize: 11,
    color: "#3f3f46",
    whiteSpace: "pre-wrap",
    wordBreak: "break-word",
    maxHeight: 130,
    overflow: "hidden",
    margin: 0,
    fontFamily: "inherit",
  },
  empty: {
    fontSize: 12,
    color: "#a1a1aa",
    padding: "16px 0",
    textAlign: "center",
    background: "#f4f4f5",
    borderRadius: 4,
  },
};
