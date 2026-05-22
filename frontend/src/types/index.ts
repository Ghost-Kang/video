export type NodeType = "script" | "image" | "video" | "composite";

export interface Shot {
  no: string;
  scene: string;
  description: string;
  duration: string;
  camera: string;
  transition: string;
  audio: string;
}

export type NodeStatus = "reviewing" | "confirmed";
export type AssetStatus = "idle" | "generating" | "done" | "failed" | "timeout";

export interface CanvasNode {
  id: string;
  type: NodeType;
  title: string;
  description: string;
  status: string;  // 兼容旧数据
  node_status: NodeStatus;
  asset_status: AssetStatus;
  result: Record<string, unknown> | null;
  subtype?: string | null;
  shot_no?: string | null;
  image_gen_provider?: string | null;
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

export interface WSExecuteNode {
  type: "execute_node";
  thread_id: string;
  node_id: string;
  node_type: NodeType;
  description: string;
  image_gen_provider?: string;  // "apimart" | "google"
  duration?: number;            // 视频时长 4-15
  resolution?: string;          // 视频分辨率 "480p" | "720p" | "1080p"
  generate_audio?: boolean;     // 是否生成音频
}

export interface WSCreateEdge {
  type: "create_edge";
  thread_id: string;
  source: string;
  target: string;
}

export interface WSDeleteEdge {
  type: "delete_edge";
  thread_id: string;
  edge_id: string;
}

export interface WSReorderEdge {
  type: "reorder_edge";
  thread_id: string;
  edge_id: string;
  direction: "up" | "down";
}

export interface WSOptimizePrompt {
  type: "optimize_prompt";
  thread_id: string;
  node_id: string;
  prompt: string;
  feedback: string;
}

export interface WSPromptOptimized {
  type: "prompt_optimized";
  thread_id: string;
  node_id: string;
  optimized_prompt: string;
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

export interface WSSessionInfo {
  thread_id: string;
  last_active: string;
}

export interface WSSessionList {
  type: "session_list";
  sessions: WSSessionInfo[];
}

export type WSIncoming = WSAgentResponse | WSProcessing | WSSessionState | WSAgentStream | WSCanvasUpdated | WSPromptOptimized | WSSessionList;
