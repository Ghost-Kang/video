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

export function ChatPanel({ messages, streaming, thinking, onSend, loading, onToggleCollapse }: Props) {
  const [input, setInput] = useState("");
  const [thinkOpen, setThinkOpen] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "instant" });
  }, [messages, streaming, thinking]);

  const handleSend = () => {
    if (!input.trim() || loading) return;
    onSend(input.trim());
    setInput("");
  };

  return (
    <div style={S.panel}>
      <div style={S.title}>
        <span style={S.titleText}>OpenRHTV</span>
        <button onClick={onToggleCollapse} style={S.collapseBtn} title="收起聊天">
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M10.5 3.5L5 8l5.5 4.5" />
          </svg>
        </button>
      </div>
      <div style={S.msgs}>
        {messages.map((m, i) => (
          <div key={i} style={m.role === "user" ? S.userBubble : S.agentBubble} className={m.role === "agent" ? "agent-msg" : ""}>
            {m.role === "agent" ? (
              <Markdown remarkPlugins={[remarkGfm]}>{m.content}</Markdown>
            ) : (
              m.content
            )}
          </div>
        ))}
        {streaming && (
          <div style={S.agentBubble} className="agent-msg">
            <Markdown remarkPlugins={[remarkGfm]}>{streaming}</Markdown>
          </div>
        )}
        {loading && !streaming && <div style={S.loading}>导演思考中...</div>}
        <div ref={bottomRef} />
      </div>

      {thinking.length > 0 && (
        <div style={S.thinkBar}>
          <button onClick={() => setThinkOpen(!thinkOpen)} style={S.thinkToggle}>
            {thinkOpen ? "▾" : "▸"} 思考中 ({thinking.length} 步)
          </button>
          {thinkOpen && (
            <div style={S.thinkLog}>
              {thinking.map((t, i) => (
                <div key={i} style={S.thinkLine}>{t}</div>
              ))}
            </div>
          )}
        </div>
      )}

      <style>{`
        .agent-msg p { margin: 4px 0; }
        .agent-msg ul, .agent-msg ol { margin: 4px 0; padding-left: 18px; }
        .agent-msg li { margin: 2px 0; }
        .agent-msg h1, .agent-msg h2, .agent-msg h3 { font-size: 14px; margin: 8px 0 4px; }
        .agent-msg code { font-family: monospace; font-size: 12px; background: #f4f4f5; padding: 1px 4px; border-radius: 3px; }
        .agent-msg pre { background: #f4f4f5; padding: 8px; border-radius: 6px; overflow-x: auto; font-size: 12px; }
        .agent-msg blockquote { border-left: 2px solid #e4e4e7; padding-left: 10px; color: #71717a; margin: 4px 0; }
        .agent-msg table { border-collapse: collapse; font-size: 12px; }
        .agent-msg th, .agent-msg td { border: 1px solid #e4e4e7; padding: 4px 8px; text-align: left; }
        .agent-msg th { background: #f4f4f5; }
      `}</style>

      <div style={S.inputArea}>
        <div style={S.quickPhrases}>
          <button
            disabled={loading}
            onClick={() => onSend("继续下一步")}
            style={{
              ...S.quickBtn,
              opacity: loading ? 0.4 : 1,
              cursor: loading ? "not-allowed" : "pointer",
            }}
          >
            继续下一步
          </button>
        </div>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
          }}
          placeholder="描述你的创作需求..."
          rows={3}
          style={S.textarea}
          disabled={loading}
        />
        <button onClick={handleSend} disabled={loading} style={{
          ...S.btn,
          opacity: loading ? 0.5 : 1,
          cursor: loading ? "not-allowed" : "pointer",
        }}>
          发送
        </button>
      </div>
    </div>
  );
}

const S: Record<string, React.CSSProperties> = {
  panel: {
    width: 360,
    display: "flex",
    flexDirection: "column",
    borderRight: "1px solid #e4e4e7",
    background: "#fafafa",
  },
  title: {
    padding: "16px 20px",
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    borderBottom: "1px solid #e4e4e7",
    background: "#fff",
  },
  titleText: { fontWeight: 600, fontSize: 15, letterSpacing: "-0.01em", color: "#18181b" },
  collapseBtn: {
    width: 24, height: 24, display: "flex", alignItems: "center", justifyContent: "center",
    background: "transparent", color: "#a1a1aa", border: "none", borderRadius: 4, cursor: "pointer", padding: 0,
  },
  msgs: { flex: 1, overflow: "auto", padding: "16px", display: "flex", flexDirection: "column", gap: 10 },
  userBubble: {
    alignSelf: "flex-end", background: "#18181b", color: "#fafafa", padding: "10px 14px",
    borderRadius: 16, borderBottomRightRadius: 4, maxWidth: "85%", fontSize: 13, lineHeight: 1.5,
  },
  agentBubble: {
    alignSelf: "flex-start", background: "#fff", border: "1px solid #e4e4e7", padding: "10px 14px",
    borderRadius: 16, borderBottomLeftRadius: 4, maxWidth: "85%", fontSize: 13, lineHeight: 1.6, color: "#3f3f46",
  },
  streaming: { alignSelf: "flex-start", color: "#a1a1aa", fontSize: 12, padding: "4px 8px" },
  loading: { alignSelf: "flex-start", color: "#a1a1aa", fontSize: 12, padding: "4px 8px" },
  thinkBar: { borderTop: "1px solid #e4e4e7", background: "#fafafa" },
  thinkToggle: {
    width: "100%", padding: "6px 16px", background: "transparent", border: "none",
    cursor: "pointer", fontSize: 11, color: "#a1a1aa", textAlign: "left" as const, fontWeight: 500,
  },
  thinkLog: { padding: "0 16px 8px", display: "flex", flexDirection: "column", gap: 2 },
  thinkLine: { fontSize: 11, color: "#a1a1aa", fontFamily: "monospace" },
  quickPhrases: { display: "flex", gap: 6, marginBottom: 8 },
  quickBtn: {
    padding: "4px 12px",
    fontSize: 12,
    color: "#3f3f46",
    background: "#f4f4f5",
    border: "1px solid #e4e4e7",
    borderRadius: 14,
    cursor: "pointer",
    transition: "background 0.15s",
  },
  inputArea: { padding: "12px 16px 16px", borderTop: "1px solid #e4e4e7", background: "#fff" },
  textarea: {
    width: "100%", border: "1px solid #e4e4e7", borderRadius: 10, padding: "10px 12px", fontSize: 13,
    resize: "vertical" as const, outline: "none", fontFamily: "inherit", color: "#18181b", background: "#fafafa",
  },
  btn: {
    marginTop: 10, width: "100%", padding: "10px 0", background: "#18181b", color: "#fff",
    border: "none", borderRadius: 10, cursor: "pointer", fontSize: 14, fontWeight: 500,
    letterSpacing: "0.02em", transition: "background 0.15s",
  },
};
