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
  AnalysisReturnedEvent,
  RewriteReturnedEvent,
  ShotFirstFrameReturnedEvent,
  AnalysisAnswerReturnedEvent,
  AnalysisFailedEvent,
  AnalysisProgressEvent,
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
  AnalysisReturnedEvent,
  RewriteReturnedEvent,
  ShotFirstFrameReturnedEvent,
  AnalysisAnswerReturnedEvent,
  AnalysisFailedEvent,
  AnalysisProgressEvent,
} from "./ws_generated";
import type { CanvasData } from "./canvas";
import type { CascadeAnalysisContract } from "./cascade";

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
  // W5D4 — run lifecycle for reconnect resume. Mirrors backend
  // ws_messages.SessionStateEvent (run `scripts/sync-ws-types.sh` to also pick
  // these up in the generated ws_generated.ts). Lets the client stop an orphaned
  // 95% spinner when the terminal frame was lost to a mid-run disconnect.
  run_status?: "running" | "done" | "failed" | "idle";
  failure?: {
    code: string;
    hint: string;
    actions: string[];
    request_id: string;
  } | null;
}

export interface CanvasUpdatedEventTyped extends Omit<CanvasUpdatedEvent, "canvas"> {
  canvas?: CanvasData | null;
}

export interface AgentResponseEventTyped extends Omit<AgentResponseEvent, "canvas"> {
  canvas?: CanvasData | null;
}

/** WS frame from `cascade_analyze` tool. `analysis` is the full Contract dump. */
export interface AnalysisReturnedEventTyped extends Omit<AnalysisReturnedEvent, "analysis"> {
  analysis: CascadeAnalysisContract;
}

/** WS frame from `cascade_rewrite` tool. `rewrite` matches backend RewriteResult. */
export interface RewriteReturnedEventTyped extends Omit<RewriteReturnedEvent, "rewrite"> {
  rewrite: {
    rewrite_id: string;
    analysis_id: string;
    niche: string;
    script_markdown: string;
    shots: { shot_index: number; dialogue: string; visual: string }[];
    parser_warnings: string[];
    confidence: number;
    cost_cny: number;
    model: string;
    hook_pattern_id?: string;
    source_classification?: string;
  };
}

/** 批量软删除会话(历史「清理空会话」)。后端一个事务删完 + 一次 session_list 推送。
 *  手写在此(非 ws_generated)以免为单个命令重跑 schema 生成器。 */
export interface DeleteSessionsMsg {
  type: "delete_sessions";
  thread_ids: string[];
}

/** 客户端 → 服务端 命令。Codex-D 把 useWebSocket 的 12 个 sendXxx 收敛到 sendCommand<T extends WSCommand>。*/
export type WSCommand =
  | AuthMsg
  | ListSessionsMsg
  | DeleteSessionMsg
  | DeleteSessionsMsg
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
  | AgentResponseEventTyped
  | AnalysisReturnedEventTyped
  | RewriteReturnedEventTyped
  | ShotFirstFrameReturnedEvent
  | AnalysisAnswerReturnedEvent
  | AnalysisFailedEvent
  | AnalysisProgressEvent;
