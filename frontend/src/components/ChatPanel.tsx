import { useState, useRef, useEffect } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";

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
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "instant" });
  }, [messages, streaming, thinking]);

  const handleSend = () => {
    if (!input.trim() || loading) return;
    onSend(input.trim());
    setInput("");
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
        <div className="mb-2.5 flex flex-wrap gap-1.5">
          <button
            disabled={loading}
            onClick={() => onSend("继续下一步")}
            className={`${quickBtnCls} ${loading ? "opacity-40 cursor-not-allowed" : ""}`}
            type="button"
          >
            继续下一步
          </button>
          <button
            disabled={loading}
            onClick={() => onSend("开头再吸引人点")}
            className={`${quickBtnCls} ${loading ? "opacity-40 cursor-not-allowed" : ""}`}
            type="button"
          >
            开头再抓
          </button>
          <button
            disabled={loading}
            onClick={() => onSend("再口语化一点")}
            className={`${quickBtnCls} ${loading ? "opacity-40 cursor-not-allowed" : ""}`}
            type="button"
          >
            更口语
          </button>
        </div>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSend();
            }
          }}
          placeholder="想改哪里,直接说"
          rows={3}
          disabled={loading}
          className="w-full rounded-xl border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900 px-3.5 py-2.5 text-[13px] leading-[1.55] text-stone-900 dark:text-stone-100 outline-none placeholder:text-stone-400 dark:placeholder:text-stone-500 focus:border-stone-900 dark:focus:border-stone-100 transition-colors resize-y font-inherit"
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
