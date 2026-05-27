import { useState, useRef, useEffect } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { COPY } from "../lib/cardCopy";
import { SampleUrlChips } from "./onboarding/SampleUrlChips";

interface Props {
  messages: { role: "user" | "agent"; content: string }[];
  streaming: string;
  thinking: string[];
  onSend: (text: string) => void;
  loading: boolean;
  onToggleCollapse: () => void;
}

function CascadeLoading({ thinking }: { thinking: string[] }) {
  const recent = thinking.slice(-3);
  return (
    <div className="self-start rounded-2xl bg-white dark:bg-stone-900 border border-stone-200 dark:border-stone-800 px-4 py-3 max-w-[90%] shadow-soft">
      <div className="flex items-center gap-1.5 mb-2" aria-hidden>
        <span className="inline-block h-1.5 w-1.5 rounded-full bg-stone-400 dark:bg-stone-500 animate-bounce [animation-delay:-0.3s]" />
        <span className="inline-block h-1.5 w-1.5 rounded-full bg-stone-400 dark:bg-stone-500 animate-bounce [animation-delay:-0.15s]" />
        <span className="inline-block h-1.5 w-1.5 rounded-full bg-stone-400 dark:bg-stone-500 animate-bounce" />
      </div>
      <p className="font-serif-cn text-sm text-stone-900 dark:text-stone-100 mb-1">
        Cascade 正在拆解…
      </p>
      {recent.length > 0 ? (
        <ul className="text-xs space-y-1 mt-2 text-stone-600 dark:text-stone-400">
          {recent.map((t, i) => (
            <li key={i} className={i === recent.length - 1 ? "text-stone-500 dark:text-stone-500" : "text-stone-700 dark:text-stone-300"}>
              <span className="text-stone-400 dark:text-stone-600 mr-1.5">{i === recent.length - 1 ? "○" : "✓"}</span>
              {t}
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-xs text-stone-400 dark:text-stone-500 mt-1">大约 30 秒</p>
      )}
    </div>
  );
}

export function ChatPanel({ messages, streaming, thinking, onSend, loading, onToggleCollapse }: Props) {
  const [input, setInput] = useState("");
  const [askOpen, setAskOpen] = useState(false);
  const [askInput, setAskInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "instant" });
  }, [messages, streaming, thinking]);

  const isEmpty = messages.length === 0;

  const handleSend = () => {
    if (!input.trim() || loading) return;
    onSend(input.trim());
    setInput("");
  };

  const handleSampleUrl = (url: string) => {
    if (loading) return;
    onSend(url);
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

  return (
    <div className="flex w-[360px] flex-col border-l border-stone-200/70 dark:border-stone-800/70 bg-[var(--color-paper)]/60 dark:bg-stone-950/60 backdrop-blur-md">
      <div className="flex items-center justify-between border-b border-stone-200/70 dark:border-stone-800/70 px-5 py-4">
        <span className="font-serif-cn font-medium text-[14px] tracking-[-0.01em] text-stone-900 dark:text-stone-50">
          问导演
        </span>
        <button
          onClick={onToggleCollapse}
          className="flex h-6 w-6 items-center justify-center rounded text-stone-400 dark:text-stone-500 hover:text-stone-900 dark:hover:text-stone-100 transition-colors"
          title="收起"
          type="button"
        >
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M5.5 3.5L11 8l-5.5 4.5" />
          </svg>
        </button>
      </div>

      <div className="flex flex-1 flex-col gap-3 overflow-auto p-5">
        {isEmpty && !streaming && !loading && (
          <div className="anim-fade-in rounded-2xl border border-dashed border-stone-300/70 dark:border-stone-700/70 px-4 py-4 text-[12.5px] leading-[1.7] text-stone-600 dark:text-stone-400">
            <p className="font-serif-cn text-[13px] text-stone-900 dark:text-stone-100 mb-1.5">
              第一次来?
            </p>
            <p>把抖音 / 小红书爆款链接 ↓ 粘到下面输入框,或直接点下面任一条样本。</p>
          </div>
        )}
        {messages.map((m, i) => (
          <div
            key={i}
            className={
              m.role === "user"
                ? "self-end max-w-[85%] rounded-2xl rounded-br-sm bg-stone-900 dark:bg-[#7c2d12] px-3.5 py-2.5 text-[13px] leading-[1.55] text-[#faf8f3]"
                : "agent-msg self-start max-w-[85%] rounded-2xl rounded-bl-sm border border-stone-200 dark:border-stone-800 bg-white dark:bg-stone-900 px-4 py-3 text-[13px] leading-[1.65] text-stone-900 dark:text-stone-100"
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
          <div className="agent-msg self-start max-w-[85%] rounded-2xl rounded-bl-sm border border-stone-200 dark:border-stone-800 bg-white dark:bg-stone-900 px-4 py-3 text-[13px] leading-[1.65] text-stone-900 dark:text-stone-100">
            <Markdown remarkPlugins={[remarkGfm]}>{streaming}</Markdown>
          </div>
        )}
        {loading && !streaming && <CascadeLoading thinking={thinking} />}
        <div ref={bottomRef} />
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

      <div className="border-t border-stone-200/70 dark:border-stone-800/70 bg-[var(--color-paper)]/40 dark:bg-stone-950/40 px-5 py-4">
        {isEmpty ? (
          <div className="mb-3">
            <SampleUrlChips onPick={handleSampleUrl} disabled={loading} />
          </div>
        ) : (
          <>
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
          </>
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
          placeholder={isEmpty ? COPY.chat_placeholder_empty : COPY.chat_placeholder_followup}
          rows={3}
          disabled={loading}
          aria-label={isEmpty ? COPY.chat_placeholder_empty : COPY.chat_placeholder_followup}
          className={
            "w-full rounded-xl border bg-white dark:bg-stone-900 px-3.5 py-2.5 text-[13px] leading-[1.55] text-stone-900 dark:text-stone-100 outline-none placeholder:text-stone-400 dark:placeholder:text-stone-500 focus:border-stone-900 dark:focus:border-stone-100 transition-colors resize-y font-inherit " +
            (isEmpty && !input
              ? "border-[#7c2d12]/30 dark:border-[#ea580c]/40 anim-input-glow"
              : "border-stone-300 dark:border-stone-700")
          }
        />
        <button
          onClick={handleSend}
          disabled={loading}
          className={`mt-2.5 w-full rounded-xl bg-stone-900 dark:bg-[#7c2d12] py-2.5 text-[13px] font-medium tracking-[0.01em] text-[#faf8f3] transition-colors hover:bg-stone-800 dark:hover:bg-[#9a3412] font-inherit ${
            loading ? "opacity-40 cursor-not-allowed" : "cursor-pointer"
          }`}
          type="button"
        >
          发送
        </button>
      </div>
    </div>
  );
}
