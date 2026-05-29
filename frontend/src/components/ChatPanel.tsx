import { useState, useEffect } from "react";
import { COPY } from "../lib/cardCopy";
import { extractThreadId } from "../lib/errorReporter";
import { useToastStore } from "../store/toastStore";
import { useCanvasStore } from "../store/canvasStore";
import { SampleUrlChips } from "./onboarding/SampleUrlChips";
import { AnalysisProgress } from "./chat/AnalysisProgress";
import {
  deriveChatPanelState,
  type ChatPanelState,
} from "../lib/chatPanelState";
import type { CascadeAnalysisContract, FailurePayload } from "../types/cascade";
import { MessagesOverlay } from "./chat/MessagesOverlay";

/**
 * W5D2-B: 内测期诊断 chip。点 → 把 user_id / thread_id / 最近一条 messages
 * 前 80 字 / UA / URL / 时间打包到剪贴板,创作者发给客服,founder 就能在
 * events.db 里精准检索。**不抢视觉**:输入框下方,跟「发送」一行右边的小
 * 灰链接,字号小一档,无 border。
 */
function buildDiagnostic(lastUserVisibleMessage: string | undefined): string {
  const userId =
    typeof localStorage !== "undefined" ? localStorage.getItem("rhtv_user") : null;
  const threadId =
    typeof location !== "undefined" ? extractThreadId(location.pathname) : null;
  const ua =
    typeof navigator !== "undefined" ? navigator.userAgent.slice(0, 80) : "";
  const url = typeof location !== "undefined" ? location.href : "";
  const lastMsg = (lastUserVisibleMessage ?? "").slice(0, 80);
  return [
    "=== Cascade 诊断信息 ===",
    `user_id: ${userId ?? "(未登录)"}`,
    `thread_id: ${threadId ?? "(非对话页)"}`,
    `最近消息: ${lastMsg}`,
    `浏览器: ${ua}`,
    `URL: ${url}`,
    `时间: ${new Date().toISOString()}`,
    "=========================",
  ].join("\n");
}

interface Props {
  messages: { role: "user" | "agent"; content: string }[];
  streaming: string;
  thinking: string[];
  onSend: (text: string) => void;
  loading: boolean;
  onToggleCollapse: () => void;
  /** Optional overrides for tests; default to canvasStore values. */
  analysis?: CascadeAnalysisContract | null;
  script?: string;
  failure?: FailurePayload | null;
}

const TITLE_BY_STATE: Record<ChatPanelState, string> = {
  idle: COPY.side_title_idle,
  running: COPY.side_title_running,
  failed: COPY.side_title_failed,
  ready: COPY.side_title_ready,
  refine: COPY.side_title_refine,
};

export function ChatPanel({
  messages,
  streaming,
  thinking,
  onSend,
  loading,
  onToggleCollapse,
  analysis: analysisProp,
  script: scriptProp,
  failure: failureProp,
}: Props) {
  const [input, setInput] = useState("");
  const [askOpen, setAskOpen] = useState(false);
  const [askInput, setAskInput] = useState("");
  const [messagesOverlayOpen, setMessagesOverlayOpen] = useState(false);

  // Store subscriptions — selector form keeps re-renders narrow. Test props,
  // when provided, fully replace the store values for that field.
  const storeAnalysis = useCanvasStore((s) => s.analysis);
  const storeScript = useCanvasStore((s) => s.script);
  const storeFailure = useCanvasStore((s) => s.failure);
  const analysis = analysisProp !== undefined ? analysisProp : storeAnalysis;
  const script = scriptProp !== undefined ? scriptProp : storeScript;
  const failure = failureProp !== undefined ? failureProp : storeFailure;

  const state = deriveChatPanelState({
    analysis,
    script,
    loading,
    failure,
    messagesLength: messages.length,
  });

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const active = document.activeElement;
      const typing =
        active instanceof HTMLInputElement || active instanceof HTMLTextAreaElement;
      if (event.key === "Escape" && !typing) {
        if (messagesOverlayOpen) setMessagesOverlayOpen(false);
        else onToggleCollapse();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [messagesOverlayOpen, onToggleCollapse]);

  const handleSend = () => {
    if (!input.trim() || loading) return;
    onSend(input.trim());
    setInput("");
  };

  const handleSampleUrl = (url: string) => {
    if (loading) return;
    // W5D3 Bug #5: clear stale analysis/script/shots before a fresh
    // sample run, else CardStack keeps rendering the PREVIOUS analysis's
    // cards under the new running progress bar.
    useCanvasStore.getState().clear();
    setMessagesOverlayOpen(false);
    onSend(url);
  };

  const handleCopyDiagnostic = async () => {
    const lastContent = messages.length > 0 ? messages[messages.length - 1].content : "";
    const text = buildDiagnostic(lastContent);
    try {
      await navigator.clipboard.writeText(text);
      useToastStore.getState().push({ kind: "info", title: "已复制,可发给客服" });
    } catch {
      useToastStore.getState().push({ kind: "error", title: "复制失败,手动选中再复制" });
    }
  };

  const handleAskSubmit = () => {
    if (!askInput.trim() || loading) return;
    // 前缀触发 Director §0.8: cascade_ask tool。前端文案不进 cardCopy
    // 里(用户看不到这串 token,纯协议层)。
    onSend(`[ask: ${askInput.trim()}]`);
    setAskInput("");
    setAskOpen(false);
  };

  const quickBtnCls =
    "rounded-full border border-stone-300 dark:border-stone-700 bg-transparent px-3 py-1 text-xs text-stone-600 dark:text-stone-400 hover:border-[#7c2d12] dark:hover:border-[#ea580c] hover:text-[#7c2d12] dark:hover:text-[#ea580c] transition-all font-inherit";

  // Whether the bottom input box is visible. Only `refine` lets the user type
  // refinement requests; every other state would either be useless or
  // confusing (e.g. typing during analysis).
  const showInput = state === "refine";
  const hasHistory = messages.length > 0 || Boolean(streaming);

  return (
    <>
      {messagesOverlayOpen && (
        <MessagesOverlay
          messages={messages}
          streaming={streaming}
          onClose={() => setMessagesOverlayOpen(false)}
        />
      )}
      <div
        className="dock-chat flex w-full flex-col border-t border-stone-200/70 dark:border-stone-800/70 bg-[var(--color-paper)]/80 dark:bg-stone-950/80 backdrop-blur-md max-h-[50vh]"
        data-testid="dock-chat"
        data-state={state}
        onMouseDown={() => setMessagesOverlayOpen(false)}
      >
      <div className="flex items-center justify-between border-b border-stone-200/70 dark:border-stone-800/70 px-5 py-2.5">
        <span
          className="font-serif-cn font-medium text-[14px] tracking-[-0.01em] text-stone-900 dark:text-stone-50"
          data-testid="side-title"
          data-state={state}
        >
          {TITLE_BY_STATE[state]}
        </span>
        <div className="flex items-center gap-2">
          {hasHistory && (
            <button
              type="button"
              data-testid="history-toggle"
              aria-expanded={messagesOverlayOpen}
              onMouseDown={(event) => event.stopPropagation()}
              onClick={() => setMessagesOverlayOpen((open) => !open)}
              className="rounded-full border border-stone-300 dark:border-stone-700 px-3 py-1 text-[11px] text-stone-600 dark:text-stone-400 hover:border-[#7c2d12] dark:hover:border-[#ea580c] hover:text-[#7c2d12] dark:hover:text-[#ea580c] transition-colors font-inherit"
            >
              {COPY.dock_history_label} ▲ ({messages.length})
            </button>
          )}
          <button
            onClick={onToggleCollapse}
            onDoubleClick={onToggleCollapse}
            className="flex h-6 w-6 items-center justify-center rounded text-stone-400 dark:text-stone-500 hover:text-stone-900 dark:hover:text-stone-100 transition-colors cursor-grab active:cursor-grabbing"
            title={COPY.dock_collapse_label}
            aria-label={COPY.dock_collapse_label}
            type="button"
          >
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M3.5 10.5L8 6l4.5 4.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        </div>
      </div>

      <div className="flex flex-1 flex-col gap-3 overflow-hidden px-5 py-3">
        {/* State 1 — 等待粘链接。隐藏聊天历史(本来也是空的),给一段引导文案 + sample chips。 */}
        {state === "idle" && (
          <div
            className="anim-fade-in rounded-2xl border border-dashed border-stone-300/70 dark:border-stone-700/70 px-4 py-4 text-[12.5px] leading-[1.7] text-stone-600 dark:text-stone-400"
            data-testid="side-idle"
          >
            <p className="font-serif-cn text-[13px] text-stone-900 dark:text-stone-100 mb-2">
              {COPY.side_idle_hint}
            </p>
            <p className="mb-3 text-stone-500 dark:text-stone-400">
              {COPY.side_idle_sample_label}
            </p>
            <SampleUrlChips onPick={handleSampleUrl} disabled={loading} variant="inline" />
          </div>
        )}

        {/* State 2 — 拆解中。进度条 + 阶段 + 剩余秒。无输入框(中断没意义)。 */}
        {state === "running" && <AnalysisProgress thinking={thinking} />}

        {/* State 3 — 出错了。banner + 「再试一条样本」+ 「告诉客服这条」。 */}
        {state === "failed" && failure && (
          <div
            className="anim-fade-in rounded-2xl border border-red-300/70 dark:border-red-900/70 bg-red-50/60 dark:bg-red-950/30 p-4"
            data-testid="side-failed"
            role="alert"
          >
            <p className="text-[13px] leading-[1.6] text-stone-800 dark:text-stone-100 mb-3">
              {failure.hint}
            </p>
            <div className="mb-3">
              <p className="mb-2 text-[11px] text-stone-500 dark:text-stone-400">
                {COPY.side_failed_retry_sample}
              </p>
              <SampleUrlChips
                onPick={handleSampleUrl}
                disabled={loading}
                variant="inline"
              />
            </div>
            <button
              type="button"
              onClick={handleCopyDiagnostic}
              data-testid="side-failed-report"
              className="text-[11px] text-stone-500 dark:text-stone-400 hover:text-[#7c2d12] dark:hover:text-[#ea580c] underline underline-offset-4 decoration-dotted transition-colors font-inherit"
            >
              📋 {COPY.side_failed_report}
            </button>
            <p className="mt-3 text-[10px] text-stone-400 dark:text-stone-600 tabular">
              {COPY.side_failed_code_prefix}
              {failure.code}
              {failure.request_id && failure.request_id !== "__client_synth__"
                ? ` · ${failure.request_id}`
                : ""}
            </p>
          </div>
        )}

        {/* State 4 — 分析好了,等用户决定改写方向(左侧 ScriptCard 选 niche)。 */}
        {state === "ready" && (
          <div
            className="anim-fade-in rounded-2xl border border-stone-200 dark:border-stone-800 bg-white/70 dark:bg-stone-900/70 p-4 shadow-soft"
            data-testid="side-ready"
          >
            <p className="font-serif-cn text-[14px] text-stone-900 dark:text-stone-50 mb-1.5">
              {COPY.side_ready_headline}
            </p>
            <p className="text-[12px] leading-[1.6] text-stone-600 dark:text-stone-400">
              {COPY.side_ready_hint}
            </p>
          </div>
        )}
      </div>

      <style>{`
        .agent-msg p { margin: 4px 0; }
        .agent-msg ul, .agent-msg ol { margin: 4px 0; padding-left: 18px; }
        .agent-msg li { margin: 2px 0; }
        .agent-msg h1, .agent-msg h2, .agent-msg h3 { font-size: 14px; margin: 8px 0 4px; font-family: "Source Han Serif SC", "Songti SC", serif; }
        .agent-msg code { font-family: ui-monospace, monospace; font-size: 12px; background: rgba(124, 45, 18, 0.08); padding: 1px 5px; border-radius: 4px; color: #7c2d12; }
        .dark .agent-msg code { background: rgba(234, 88, 12, 0.15); color: #ea580c; }
        .agent-msg pre { background: rgba(124, 45, 18, 0.06); padding: 10px; border-radius: 8px; overflow-x: auto; font-size: 12px; }
        .dark .agent-msg pre { background: rgba(234, 88, 12, 0.10); }
        .agent-msg blockquote { border-left: 2px solid #d6d3d1; padding-left: 12px; color: #78716c; margin: 4px 0; }
        .dark .agent-msg blockquote { border-left-color: #44403c; color: #a8a29e; }
        .agent-msg table { border-collapse: collapse; font-size: 12px; }
        .agent-msg th, .agent-msg td { border: 1px solid #e7e5e4; padding: 4px 8px; text-align: left; }
        .dark .agent-msg th, .dark .agent-msg td { border-color: #292524; }
        .agent-msg th { background: #faf8f3; font-weight: 500; }
        .dark .agent-msg th { background: #292524; }
      `}</style>

      {/* Refine state owns the entire input/chip footer. Other states drop it
          entirely — that's the whole point of the redesign: no input when
          there's nothing useful to type. */}
      {showInput && (
        <div className="border-t border-stone-200/70 dark:border-stone-800/70 bg-[var(--color-paper)]/40 dark:bg-stone-950/40 px-5 py-4">
          <div className="mb-2.5 flex flex-wrap gap-1.5">
            <button
              disabled={loading}
              onClick={() => onSend(COPY.chat_quick_continue)}
              className={`${quickBtnCls} ${loading ? "opacity-40 cursor-not-allowed" : ""}`}
              type="button"
            >
              {COPY.chat_quick_continue}
            </button>
            <button
              disabled={loading}
              onClick={() => onSend("开头再吸引人点")}
              className={`${quickBtnCls} ${loading ? "opacity-40 cursor-not-allowed" : ""}`}
              type="button"
            >
              {COPY.chat_quick_hook}
            </button>
            <button
              disabled={loading}
              onClick={() => onSend("再口语化一点")}
              className={`${quickBtnCls} ${loading ? "opacity-40 cursor-not-allowed" : ""}`}
              type="button"
            >
              {COPY.chat_quick_oral}
            </button>
            <button
              disabled={loading}
              onClick={() => setAskOpen((v) => !v)}
              className={`${quickBtnCls} ${loading ? "opacity-40 cursor-not-allowed" : ""} ${askOpen ? "border-[#7c2d12] dark:border-[#ea580c] text-[#7c2d12] dark:text-[#ea580c]" : ""}`}
              type="button"
              aria-expanded={askOpen}
              data-testid="ask-chip"
            >
              💡 {COPY.ask_chip_label}
            </button>
          </div>
          {askOpen && (
            <div className="mb-2.5 anim-fade-in rounded-xl border border-[#7c2d12]/40 dark:border-[#ea580c]/50 bg-white/50 dark:bg-stone-900/50 p-3">
              <p className="text-[11px] text-stone-500 dark:text-stone-400 mb-2">
                {COPY.ask_hint}
              </p>
              <textarea
                value={askInput}
                onChange={(e) => setAskInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleAskSubmit();
                  }
                }}
                placeholder={COPY.ask_placeholder}
                rows={2}
                disabled={loading}
                aria-label={COPY.ask_placeholder}
                data-testid="ask-textarea"
                className="w-full rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-950 px-2.5 py-2 text-[13px] leading-[1.5] text-stone-900 dark:text-stone-100 outline-none placeholder:text-stone-400 dark:placeholder:text-stone-500 focus:border-[#7c2d12] dark:focus:border-[#ea580c] resize-y font-inherit"
              />
              <button
                type="button"
                onClick={handleAskSubmit}
                disabled={loading || !askInput.trim()}
                data-testid="ask-submit"
                className={`mt-2 w-full rounded-lg bg-[#7c2d12] dark:bg-[#ea580c] py-2 text-[12px] font-medium text-[#faf8f3] transition-colors hover:bg-[#9a3412] dark:hover:bg-[#c2410c] font-inherit ${
                  loading || !askInput.trim() ? "opacity-40 cursor-not-allowed" : "cursor-pointer"
                }`}
              >
                {COPY.ask_submit}
              </button>
            </div>
          )}
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder={COPY.side_refine_placeholder}
            rows={3}
            disabled={loading}
            aria-label={COPY.side_refine_placeholder}
            data-testid="refine-textarea"
            className="w-full rounded-xl border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900 px-3.5 py-2.5 text-[13px] leading-[1.55] text-stone-900 dark:text-stone-100 outline-none placeholder:text-stone-400 dark:placeholder:text-stone-500 focus:border-stone-900 dark:focus:border-stone-100 transition-colors resize-y font-inherit"
          />
          <div className="mt-2.5 flex items-center gap-2">
            <button
              onClick={handleSend}
              disabled={loading}
              className={`flex-1 rounded-xl bg-stone-900 dark:bg-[#7c2d12] py-2.5 text-[13px] font-medium tracking-[0.01em] text-[#faf8f3] transition-colors hover:bg-stone-800 dark:hover:bg-[#9a3412] font-inherit ${
                loading ? "opacity-40 cursor-not-allowed" : "cursor-pointer"
              }`}
              type="button"
            >
              发送
            </button>
            {/* W5D2-B: 诊断信息复制 chip。视觉降级 — 灰文 + 无 border + 小字号,
                不抢「发送」按钮的注意力,但有需要时就在那里。 */}
            <button
              onClick={handleCopyDiagnostic}
              type="button"
              data-testid="diagnostic-copy-btn"
              aria-label="复制诊断信息"
              title="把 user_id / 会话 ID / UA 一键复制,发给客服好定位问题"
              className="shrink-0 text-[11px] text-stone-400 dark:text-stone-500 hover:text-[#7c2d12] dark:hover:text-[#ea580c] underline underline-offset-4 decoration-dotted transition-colors font-inherit px-1.5 py-1"
            >
              📋 复制诊断
            </button>
          </div>
        </div>
      )}
      </div>
    </>
  );
}
