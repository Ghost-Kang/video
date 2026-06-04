export type NodeType = "script" | "image" | "video" | "composite";
export type NodeStatus = "reviewing" | "confirmed";
export type AssetStatus = "idle" | "generating" | "done" | "failed" | "timeout";
export type GenerationStatus = "idle" | "pending" | "submitted" | "polling" | "done" | "failed" | "cancelled";

export interface CanvasNode {
  id: string;
  type: NodeType;
  title: string;
  description: string;
  status: string;
  node_status: NodeStatus;
  asset_status: AssetStatus;
  result: Record<string, unknown> | null;
  // time-travel 回溯(P2 slice-2)— 上游被重生后,下游产物已过时(需重生)。后端
  // canvas_data 永远带此字段(默认 false),见 canvas.py get_canvas_state / canvas_data。
  needs_regen: boolean;
  subtype: string | null;
  shot_no: string | null;
  image_gen_provider: string | null;
  feedback: string | null;
  generation_status: GenerationStatus;
  generation_task_id: string | null;
  generation_error: string | null;
  generation_attempt_count: number;
  generation_lease_until: string | null;
  generation_next_retry_at: string | null;
  user_id: string;
  thread_id: string;
  x: number | null;
  y: number | null;
}

export interface CanvasEdge {
  id: string;
  source: string;
  target: string;
  position: number;
}

export interface CanvasState {
  nodes: Record<string, CanvasNode>;
  edges: CanvasEdge[];
}

export type CanvasData = CanvasState;
