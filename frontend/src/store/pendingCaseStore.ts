import { create } from "zustand";
import type { SampleCase } from "../lib/sampleCases";

/**
 * 「待拆解案例」素材的过渡仓。
 *
 * 落地页点 CaseShowcase 富视频卡时,把该案例的完整素材(封面/逐幕 clip/标题/钩子)
 * 按目标 thread 存一份;/chat 进入「分析中」态时,主画面 AnalyzingHero 据此把
 * 「用户刚点的那条」连续地带进等待态 —— 零新后端接口,素材前端早已持有。
 *
 * 按 thread 索引:同一 tab 可切多个会话,各自的待拆解素材互不串台。分析落地/失败后
 * 该条无害可留,会话切换 / 清理空会话时由 App 调 clearPendingCase 回收。
 */
interface PendingCaseStore {
  byThread: Record<string, SampleCase>;
  setPendingCase: (threadId: string, c: SampleCase) => void;
  clearPendingCase: (threadId: string) => void;
}

export const usePendingCaseStore = create<PendingCaseStore>((set) => ({
  byThread: {},
  setPendingCase: (threadId, c) =>
    set((s) => ({ byThread: { ...s.byThread, [threadId]: c } })),
  clearPendingCase: (threadId) =>
    set((s) => {
      if (!(threadId in s.byThread)) return s;
      const next = { ...s.byThread };
      delete next[threadId];
      return { byThread: next };
    }),
}));
