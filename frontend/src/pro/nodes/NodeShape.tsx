import { HTMLContainer, Rectangle2d, ShapeUtil, T, type Geometry2d, type TLBaseShape } from "tldraw";
import type { ProNodeTypeKey } from "../../types/pro";
import { NODE_W, nodeHeight } from "./layout";
import { ProNodeCard } from "./ProNodeCard";

/** Pro 计算图节点的 props。 */
export interface ProNodeProps {
  w: number;
  h: number;
  nodeType: ProNodeTypeKey;
  params: Record<string, string | number>;
  cached: boolean;
  cachedUrl: string | null;
  status: string; // idle | running | done | failed
  resultUrl: string | null;
}

/** Pro 计算图节点 = 一个 tldraw 自定义 shape。节点本体住 editor(源真相);连线住 proCanvasStore。 */
export type ProNodeShape = TLBaseShape<"pronode", ProNodeProps>;

// tldraw v5 把自定义 shape 注册进类型系统的官方姿势:augment TLGlobalShapePropsMap
// (TLShape = TLIndexedShapes[...],由它派生)。这样 ShapeUtil<ProNodeShape> / editor.createShape /
// s.type === "pronode" 全部原生类型安全,无需 cast。
declare module "@tldraw/tlschema" {
  interface TLGlobalShapePropsMap {
    pronode: ProNodeProps;
  }
}

export class ProNodeShapeUtil extends ShapeUtil<ProNodeShape> {
  static override type = "pronode" as const;

  static override props = {
    w: T.number,
    h: T.number,
    nodeType: T.string,
    params: T.dict(T.string, T.or(T.string, T.number)),
    cached: T.boolean,
    cachedUrl: T.string.nullable(),
    status: T.string,
    resultUrl: T.string.nullable(),
  };

  override getDefaultProps(): ProNodeProps {
    return {
      w: NODE_W,
      h: nodeHeight("Prompt"),
      nodeType: "Prompt",
      params: {},
      cached: false,
      cachedUrl: null,
      status: "idle",
      resultUrl: null,
    };
  }

  override getGeometry(shape: ProNodeShape): Geometry2d {
    return new Rectangle2d({ width: shape.props.w, height: shape.props.h, isFilled: true });
  }

  override getIndicatorPath(shape: ProNodeShape): Path2D {
    const path = new Path2D();
    path.rect(0, 0, shape.props.w, shape.props.h);
    return path;
  }

  override canResize() {
    return false;
  }
  override hideRotateHandle() {
    return true;
  }
  override canEdit() {
    return false;
  }

  override component(shape: ProNodeShape) {
    return (
      <HTMLContainer id={shape.id} style={{ width: shape.props.w, height: shape.props.h, pointerEvents: "all" }}>
        <ProNodeCard shape={shape} />
      </HTMLContainer>
    );
  }
}
