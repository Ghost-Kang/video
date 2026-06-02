import { useEffect, useRef, useState } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { COPY } from "../lib/cardCopy";

interface Props {
  messages: { role: "user" | "agent"; content: string }[];
  streaming: string;
  thinking: string[];
  onSend: (text: string) => void;
  loading: boolean;
  onToggleCollapse: () => void;
}

/**
 * pro-view 画布创作对话 dock。
 *
 * 与 CardStack 配套的 ChatPanel(5 状态机:idle/running/failed/ready/refine,为「粘链接拆解」
 * 设计)不同 —— 画布创作是**自由对话驱动 Director 编排节点**:用户描述创作意图 → user_message
 * → Director 按 director.md §1-6 在画布上搭 策划书→角色→场景→宫格→视频 节点(canvas_updated
 * 推帧,Canvas 渲染),人在画布上审核确认/生成。所以这里始终可输入,顶上显示 Director 实时
 * thinking(正在编排哪个节点),不套用拆解流程的状态机。
 */
export function CanvasChatDock({
  messages,
  streaming,
  thinking,
  onSend,
  loading,
  onToggleCollapse,
}: Props) {
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "instant" });
  }, [messages, streaming, thinking]);

  const handleSend = () => {
    if (!input.trim() || loading) return;
    onSend(input.trim());
    setInput("");
  };

  const lastThinking = thinking.length > 0 ? thinking[thinking.length - 1] : "";
  const hasContent = messages.length > 0 || Boolean(streaming);

  return (
    <div
      className="dock-chat flex w-full flex-col border-t border-stone-200/70 dark:border-stone-800/70 bg-[var(--color-paper)]/80 dark:bg-stone-950/80 backdrop-blur-md max-h-[50vh]"
      data-testid="canvas-chat-dock"
    >
      <div className="flex items-center justify-between border-b border-stone-200/70 dark:border-stone-800/70 px-5 py-2.5">
        <span className="font-serif-cn font-medium text-[14px] tracking-[-0.01em] text-stone-900 dark:text-stone-50">
          {COPY.canvas_dock_title}
        </span>
        <button
          onClick={onToggleCollapse}
          className="flex h-6 w-6 items-center justify-center rounded text-stone-400 dark:text-stone-500 hover:text-stone-900 dark:hover:text-stone-100 transition-colors"
          title={COPY.dock_collapse_label}
          aria-label={COPY.dock_collapse_label}
          type="button"
        >
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M3.5 10.5L8 6l4.5 4.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      </div>

      <div className="flex flex-1 flex-col gap-3 overflow-y-auto px-5 py-3">
        {!hasContent && (
          <p className="anim-fade-in rounded-2xl border border-dashed border-stone-300/70 dark:border-stone-700/70 px-4 py-4 text-[12.5px] leading-[1.7] text-stone-600 dark:text-stone-400">
            {COPY.canvas_dock_hint}
          </p>
        )}
        {messages.map((m, i) => (
          <div
            key={i}
            data-testid={m.role === "user" ? "canvas-chat-user" : "canvas-chat-agent"}
            className={
              m.role === "user"
                ? "self-end max-w-[85%] rounded-2xl rounded-br-sm bg-stone-900 dark:bg-[#7c2d12] px-3.5 py-2.5 text-[13px] leading-[1.55] text-[#faf8f3] overflow-hidden break-words"
                : "agent-msg self-start max-w-[85%] rounded-2xl rounded-bl-sm border border-stone-200 dark:border-stone-800 bg-white dark:bg-stone-950 px-4 py-3 text-[13px] leading-[1.65] text-stone-900 dark:text-stone-100 break-words"
            }
          >
            {m.role === "agent" ? (
              <Markdown remarkPlugins={[remarkGfm]}>{m.content}</Markdown>
            ) : (
              m.content
            )}
          </div>
        ))}
        {streaming && (
          <div className="agent-msg self-start max-w-[85%] rounded-2xl rounded-bl-sm border border-stone-200 dark:border-stone-800 bg-white dark:bg-stone-950 px-4 py-3 text-[13px] leading-[1.65] text-stone-900 dark:text-stone-100">
            <Markdown remarkPlugins={[remarkGfm]}>{streaming}</Markdown>
          </div>
        )}
        {loading && lastThinking && !streaming && (
          <div
            className="self-start inline-flex items-center gap-2 text-[11px] text-[#7c2d12] dark:text-[#ea580c]"
            data-testid="canvas-chat-thinking"
            role="status"
            aria-live="polite"
          >
            <span className="h-1.5 w-1.5 rounded-full bg-[#ea580c] animate-pulse" aria-hidden />
            {COPY.canvas_dock_thinking_prefix} · {lastThinking}
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="border-t border-stone-200/70 dark:border-stone-800/70 bg-[var(--color-paper)]/40 dark:bg-stone-950/40 px-5 py-4">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSend();
            }
          }}
          placeholder={COPY.canvas_dock_placeholder}
          rows={2}
          disabled={loading}
          aria-label={COPY.canvas_dock_placeholder}
          data-testid="canvas-chat-input"
          className="w-full rounded-xl border border-stone-300 dark:border-stone-700 bg-white/90 dark:bg-stone-900/80 backdrop-blur-sm px-3.5 py-2.5 text-[13px] leading-[1.55] text-stone-900 dark:text-stone-100 outline-none placeholder:text-stone-400 dark:placeholder:text-stone-500 focus:border-[#7c2d12] dark:focus:border-[#ea580c] transition-all resize-y font-inherit"
        />
        <button
          onClick={handleSend}
          disabled={loading}
          type="button"
          data-testid="canvas-chat-send"
          className={`mt-2.5 w-full rounded-xl bg-stone-900 dark:bg-[#7c2d12] py-2.5 text-[13px] font-medium tracking-[0.01em] text-[#faf8f3] transition-all hover:bg-stone-800 dark:hover:bg-[#9a3412] font-inherit ${
            loading ? "opacity-40 cursor-not-allowed" : "cursor-pointer"
          }`}
        >
          发送
        </button>
      </div>
    </div>
  );
}
