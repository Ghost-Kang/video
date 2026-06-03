import { create } from "zustand";
import type { ReviewItem } from "../types/ws";

/**
 * P2 审核闸门 — 持有「当前待用户确认的生成审核卡」。
 *
 * 后端 Director 自主调生成工具时 graph 暂停,推 `review_required` 帧;wsStore 把它
 * 落到这里。`<ReviewGate/>` 订阅 `pending`,仅当 `pending.threadId === 当前 thread`
 * 时渲染(跨线程帧由 wsStore 的 P0-C 缓冲机制保证只在切到该 thread 时才 dispatch,
 * 所以这里通常已是当前 thread;组件再做一次 threadId 比对兜底)。
 *
 * 用户决策(approve/reject)后清空,前端发 `review_decision`,后端 resume graph。
 */
export interface PendingReview {
  threadId: string;
  reviews: ReviewItem[];
  summary: string;
  /** 本轮 review 的 interrupt id;决策时回带,后端用它挡陈旧决策(review #3)。 */
  interruptId: string;
}

interface ReviewStore {
  pending: PendingReview | null;
  setPending: (p: PendingReview) => void;
  /** 清空当前审核卡(用户已决策,或切换/重置会话)。 */
  clear: () => void;
}

export const useReviewStore = create<ReviewStore>((set) => ({
  pending: null,
  setPending: (p) => set({ pending: p }),
  clear: () => set({ pending: null }),
}));
