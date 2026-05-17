export type NodeType = "script" | "storyboard" | "image" | "video" | "audio";

export interface Shot {
  no: string;
  scene: string;
  description: string;
  duration: string;
  camera: string;
  transition: string;
  audio: string;
}

export interface CanvasNode {
  id: string;
  type: NodeType;
  title: string;
  description: string;
  status: "pending" | "approved" | "executing" | "awaiting_review" | "done" | "failed";
  result: Record<string, unknown> | null;
  subtype?: string | null;
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

export interface WSReviewNode {
  type: "review_node";
  thread_id: string;
  node_id: string;
  action: "approve" | "reject";
  feedback?: string;
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

export interface WSAgentStream {
  type: "agent_stream";
  thread_id: string;
  event: "tool_call" | "text";
  name?: string;
  args?: string;
  content?: string;
}

export interface WSCanvasUpdated {
  type: "canvas_updated";
  thread_id: string;
  canvas: CanvasData | null;
}

export type WSIncoming = WSAgentResponse | WSProcessing | WSSessionState | WSAgentStream | WSCanvasUpdated;
