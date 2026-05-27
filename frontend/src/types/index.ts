export type {
  AssetStatus,
  CanvasData,
  CanvasEdge,
  CanvasNode,
  CanvasState,
  GenerationStatus,
  NodeStatus,
  NodeType,
} from "./canvas";
export type { WSCommand, WSEvent } from "./ws";
export type { WSEvent as WSIncoming } from "./ws";
export type {
  CreateEdgeMsg as WSCreateEdge,
  DeleteEdgeMsg as WSDeleteEdge,
  ExecuteNodeMsg as WSExecuteNode,
  GetSessionStateMsg as WSGetSessionState,
  OptimizePromptMsg as WSOptimizePrompt,
  ReorderEdgeMsg as WSReorderEdge,
  ReviewNodeMsg as WSReviewNode,
  UpdatePositionMsg as WSPositionUpdate,
  UserMessageMsg as WSUserMessage,
} from "./ws_generated";

export interface Shot {
  no: string;
  scene: string;
  description: string;
  duration: string;
  camera: string;
  transition: string;
  audio: string;
}

export interface ChatMessage {
  role: "user" | "agent";
  content: string;
}
