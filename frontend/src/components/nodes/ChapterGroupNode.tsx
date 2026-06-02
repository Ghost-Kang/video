import type { NodeProps } from "@xyflow/react";

/**
 * 章节容器节点(ReactFlow sub-flow group)。把 video 成片镜头按叙事章节
 * (① 开场 / ② 发展 / ③ 高潮 / ④ 结尾)框起来,长片画布结构一目了然
 * (CANVAS_DESIGN 章节层 / ROADMAP V2)。
 *
 * 章节当前由前端按 shot_no 在总镜数中的位置推断(见 Canvas.chapterIndex);
 * 后续可由 Director 按剧本叙事精确标注。只框 video(成片镜头),不框策划书/锚点/宫格
 * (那些是素材准备,留在左侧 absolute 区,参考链 edge 不被打断)。
 */
export function ChapterGroupNode({ data }: NodeProps) {
  const label = (data?.label as string) ?? "";
  const count = (data?.count as number) ?? 0;
  return (
    <div style={S.group}>
      <div style={S.label}>
        {label} · {count} 镜
      </div>
    </div>
  );
}

const S: Record<string, React.CSSProperties> = {
  group: {
    width: "100%",
    height: "100%",
    border: "2px dashed #d4a574",
    borderRadius: 14,
    background: "rgba(124,45,18,0.035)",
    boxSizing: "border-box",
  },
  label: {
    padding: "6px 12px",
    fontSize: 12,
    fontWeight: 600,
    color: "#7c2d12",
    letterSpacing: "0.02em",
  },
};
