/** 节点类型 */
export type NodeType = "script" | "storyboard" | "image" | "video" | "audio";

/** 画布节点 */
export interface CanvasNode {
  id: string;
  type: NodeType;
  title: string;
  description: string;
  status: "pending" | "executing" | "done" | "failed";
  result: Record<string, unknown> | null;
}

/** 画布数据 */
export interface CanvasData {
  nodes: Record<string, CanvasNode>;
  edges: unknown[];
}

/** WebSocket 消息：前端 → 后端 */
export interface WSUserMessage {
  type: "user_message";
  thread_id: string;
  content: string;
}

/** 画布节点 */
export interface CanvasNode {
  id: string;
  type: NodeType;
  title: string;
  description: string;
  status: "pending" | "executing" | "done" | "failed";
  result: Record<string, unknown> | null;
  x?: number;
  y?: number;
}

/** WebSocket 消息：后端 → 前端 */
export interface WSAgentResponse {
  type: "agent_response";
  content: string;
  canvas: CanvasData | null;
}

/** WebSocket 消息：前端 → 后端（节点位置更新） */
export interface WSPositionUpdate {
  type: "update_position";
  node_id: string;
  x: number;
  y: number;
}
