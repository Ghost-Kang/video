/**
 * WS wire contract — re-export 自 codegen 出来的 `ws_generated.ts`,加上人类友好的
 * `WSCommand` / `WSEvent` discriminated union 别名。
 *
 * codegen 流程见 `scripts/sync-ws-types.sh`:Pydantic 模型 →
 * `backend/scripts/export_ws_schema.py` → `frontend/scripts/ws_schema.json` →
 * `json2ts` → `ws_generated.ts`。
 *
 * **不要手动改 `ws_generated.ts`**(下次 sync 会覆盖)。
 */

export type {
  AuthMsg,
  ListSessionsMsg,
  DeleteSessionMsg,
  GetSessionStateMsg,
  ReorderEdgeMsg,
  CreateEdgeMsg,
  DeleteEdgeMsg,
  UpdatePositionMsg,
  ReviewNodeMsg,
  ExecuteNodeMsg,
  UpdateNodeStatusMsg,
  OptimizePromptMsg,
  UserMessageMsg,
  ErrorEvent,
  SessionListEvent,
  SessionStateEvent,
  CanvasUpdatedEvent,
  PromptOptimizedEvent,
  ProcessingEvent,
  AgentStreamEvent,
  AgentResponseEvent,
} from "./ws_generated";

import type {
  AuthMsg,
  ListSessionsMsg,
  DeleteSessionMsg,
  GetSessionStateMsg,
  ReorderEdgeMsg,
  CreateEdgeMsg,
  DeleteEdgeMsg,
  UpdatePositionMsg,
  ReviewNodeMsg,
  ExecuteNodeMsg,
  UpdateNodeStatusMsg,
  OptimizePromptMsg,
  UserMessageMsg,
  ErrorEvent,
  SessionListEvent,
  SessionStateEvent,
  CanvasUpdatedEvent,
  PromptOptimizedEvent,
  ProcessingEvent,
  AgentStreamEvent,
  AgentResponseEvent,
} from "./ws_generated";
import type { CanvasData } from "./canvas";

export interface ChatMessageEvent {
  role: "user" | "agent";
  content: string;
}

export interface WSSessionInfo {
  thread_id: string;
  last_active: string;
}

export interface SessionListEventTyped extends Omit<SessionListEvent, "sessions"> {
  sessions: WSSessionInfo[];
}

export interface SessionStateEventTyped extends Omit<SessionStateEvent, "messages" | "canvas"> {
  messages: ChatMessageEvent[];
  canvas?: CanvasData | null;
}

export interface CanvasUpdatedEventTyped extends Omit<CanvasUpdatedEvent, "canvas"> {
  canvas?: CanvasData | null;
}

export interface AgentResponseEventTyped extends Omit<AgentResponseEvent, "canvas"> {
  canvas?: CanvasData | null;
}

/** 客户端 → 服务端 命令。Codex-D 把 useWebSocket 的 12 个 sendXxx 收敛到 sendCommand<T extends WSCommand>。*/
export type WSCommand =
  | AuthMsg
  | ListSessionsMsg
  | DeleteSessionMsg
  | GetSessionStateMsg
  | ReorderEdgeMsg
  | CreateEdgeMsg
  | DeleteEdgeMsg
  | UpdatePositionMsg
  | ReviewNodeMsg
  | ExecuteNodeMsg
  | UpdateNodeStatusMsg
  | OptimizePromptMsg
  | UserMessageMsg;

/** 服务端 → 客户端 推送。app 用 switch on `event.type` 分发。*/
export type WSEvent =
  | ErrorEvent
  | SessionListEventTyped
  | SessionStateEventTyped
  | CanvasUpdatedEventTyped
  | PromptOptimizedEvent
  | ProcessingEvent
  | AgentStreamEvent
  | AgentResponseEventTyped;
