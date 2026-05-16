export type NodeType = "script" | "storyboard" | "image" | "video" | "audio";

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

export interface CanvasData {
  nodes: Record<string, CanvasNode>;
  edges: unknown[];
}

export interface ChatMessage {
  role: "user" | "agent";
  content: string;
}

// ---------- WS 消息（全部带 thread_id）----------

/** 前端 → 后端 */
export interface WSUserMessage {
  type: "user_message";
  thread_id: string;
  content: string;
}

export interface WSPositionUpdate {
  type: "update_position";
  thread_id: string;
  node_id: string;
  x: number;
  y: number;
}

export interface WSGetSessionState {
  type: "get_session_state";
  thread_id: string;
}

/** 后端 → 前端 */
export interface WSAgentResponse {
  type: "agent_response";
  thread_id: string;
  content: string;
  canvas: CanvasData | null;
}

export interface WSProcessing {
  type: "processing";
  thread_id: string;
}

export interface WSSessionState {
  type: "session_state";
  thread_id: string;
  messages: ChatMessage[];
  canvas: CanvasData | null;
}

export type WSIncoming = WSAgentResponse | WSProcessing | WSSessionState;
