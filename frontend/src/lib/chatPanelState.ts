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
}

export function deriveChatPanelState(i: ChatPanelInputs): ChatPanelState {
  if (i.failure) return "failed";
  if (i.loading) return "running";
  if (i.script) return "refine";
  if (i.analysis) return "ready";
  if (i.messagesLength > 0) return "running"; // edge: sent but no flags yet
  return "idle";
}
