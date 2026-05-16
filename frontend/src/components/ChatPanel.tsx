import { useState, useRef, useEffect } from "react";

interface Props {
  messages: { role: "user" | "agent"; content: string }[];
  onSend: (text: string) => void;
  loading: boolean;
  onToggleCollapse: () => void;
}

export function ChatPanel({ messages, onSend, loading, onToggleCollapse }: Props) {
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

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
          <div key={i} style={m.role === "user" ? S.userBubble : S.agentBubble}>
            {m.content}
          </div>
        ))}
        {loading && <div style={S.loading}>导演思考中...</div>}
        <div ref={bottomRef} />
      </div>
      <div style={S.inputArea}>
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
  titleText: {
    fontWeight: 600,
    fontSize: 15,
    letterSpacing: "-0.01em",
    color: "#18181b",
  },
  collapseBtn: {
    width: 24,
    height: 24,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    background: "transparent",
    color: "#a1a1aa",
    border: "none",
    borderRadius: 4,
    cursor: "pointer",
    padding: 0,
    transition: "color 0.15s",
  },
  msgs: {
    flex: 1,
    overflow: "auto",
    padding: "16px",
    display: "flex",
    flexDirection: "column",
    gap: 10,
  },
  userBubble: {
    alignSelf: "flex-end",
    background: "#18181b",
    color: "#fafafa",
    padding: "10px 14px",
    borderRadius: 16,
    borderBottomRightRadius: 4,
    maxWidth: "85%",
    fontSize: 13,
    lineHeight: 1.5,
  },
  agentBubble: {
    alignSelf: "flex-start",
    background: "#fff",
    border: "1px solid #e4e4e7",
    padding: "10px 14px",
    borderRadius: 16,
    borderBottomLeftRadius: 4,
    maxWidth: "85%",
    fontSize: 13,
    lineHeight: 1.6,
    whiteSpace: "pre-wrap",
    color: "#3f3f46",
  },
  loading: {
    alignSelf: "flex-start",
    color: "#a1a1aa",
    fontSize: 12,
    padding: "4px 8px",
  },
  inputArea: {
    padding: "12px 16px 16px",
    borderTop: "1px solid #e4e4e7",
    background: "#fff",
  },
  textarea: {
    width: "100%",
    border: "1px solid #e4e4e7",
    borderRadius: 10,
    padding: "10px 12px",
    fontSize: 13,
    resize: "vertical" as const,
    outline: "none",
    fontFamily: "inherit",
    color: "#18181b",
    background: "#fafafa",
    transition: "border-color 0.15s",
  },
  btn: {
    marginTop: 10,
    width: "100%",
    padding: "10px 0",
    background: "#18181b",
    color: "#fff",
    border: "none",
    borderRadius: 10,
    cursor: "pointer",
    fontSize: 14,
    fontWeight: 500,
    letterSpacing: "0.02em",
    transition: "background 0.15s",
  },
};
