export type NodeType = "script" | "image" | "video" | "composite";
export type NodeStatus = "reviewing" | "confirmed";
export type AssetStatus = "idle" | "generating" | "done" | "failed" | "timeout";
export type GenerationStatus = "idle" | "pending" | "submitted" | "polling" | "done" | "failed";

export interface CanvasNode {
  id: string;
  type: NodeType;
  title: string;
  description: string;
  status: string;
  node_status: NodeStatus;
  asset_status: AssetStatus;
  result: Record<string, unknown> | null;
  subtype: string | null;
  shot_no: string | null;
  image_gen_provider: string | null;
  feedback: string | null;
  generation_status: GenerationStatus;
  generation_task_id: string | null;
  generation_error: string | null;
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
