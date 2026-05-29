// W5D3 — right-panel state machine. 5 mutually-exclusive UI modes derived
// from the same 4 store fields. Pure function, no side effects — easy to test.
//
// Priority order matters: `failed` beats `running` (a failure that lands
// while loading-flag is still set should still flip us to error UI), and
// `running` beats `ready/refine` (re-analyze keeps the busy view even when
// last analysis is still in the store).

import type { CascadeAnalysisContract, FailurePayload } from "../types/cascade";

export type ChatPanelState =
  | "idle" // 1. 等待粘链接
  | "running" // 2. 拆解中
  | "failed" // 3. 出错了
  | "ready" // 4. 分析好了,等改写方向
  | "refine"; // 5. 有 script 了,可 refine

export interface ChatPanelInputs {
  analysis: CascadeAnalysisContract | null;
  script: string;
  loading: boolean;
  failure: FailurePayload | null;
  messagesLength: number;
  // W5D4 — role of the LAST persisted message. Disambiguates the
  // "messages>0 but no analysis/script in store" case:
  //   - last === "user"  → sent, awaiting first ack → genuinely running
  //   - last === "agent" → a completed turn whose analysis/canvas was never
  //     persisted (analysis_returned is a transient WS push, not stored). On
  //     reload `get_session_state` returns canvas=null, so analysis is gone —
  //     but the turn IS done. Without this, such sessions fell through to the
  //     `messagesLength > 0 → running` fallback and span "整理输出 95%" forever.
  lastMessageRole?: "user" | "agent" | null;
}

export function deriveChatPanelState(i: ChatPanelInputs): ChatPanelState {
  if (i.failure) return "failed";
  if (i.loading) return "running";
  if (i.script) return "refine";
  if (i.analysis) return "ready";
  // Sent-but-not-yet-acked: only "running" while we're still waiting on the
  // agent. A trailing agent message means the turn already finished (its rich
  // result just wasn't persisted), so don't fake a spinner — fall to idle.
  if (i.messagesLength > 0 && i.lastMessageRole !== "agent") return "running";
  return "idle";
}
