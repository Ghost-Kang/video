import { useState, useRef, useEffect } from "react";

interface Props {
  messages: { role: "user" | "agent"; content: string }[];
  onSend: (text: string) => void;
  loading: boolean;
}

export function ChatPanel({ messages, onSend, loading }: Props) {
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
    <div style={styles.panel}>
      <div style={styles.title}>OpenRHTV</div>
      <div style={styles.msgs}>
        {messages.map((m, i) => (
          <div key={i} style={m.role === "user" ? styles.userBubble : styles.agentBubble}>
            {m.content}
          </div>
        ))}
        {loading && <div style={styles.loading}>导演思考中...</div>}
        <div ref={bottomRef} />
      </div>
      <div style={styles.inputArea}>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
          }}
          placeholder="描述你的创作需求..."
          rows={3}
          style={styles.textarea}
          disabled={loading}
        />
        <button onClick={handleSend} disabled={loading} style={styles.btn}>
          发送
        </button>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  panel: {
    width: 360,
    display: "flex",
    flexDirection: "column",
    borderRight: "1px solid #e8e8e8",
    background: "#fafafa",
  },
  title: {
    padding: "16px",
    fontWeight: 700,
    fontSize: 16,
    borderBottom: "1px solid #e8e8e8",
    background: "#fff",
  },
  msgs: {
    flex: 1,
    overflow: "auto",
    padding: 12,
    display: "flex",
    flexDirection: "column",
    gap: 8,
  },
  userBubble: {
    alignSelf: "flex-end",
    background: "#1677ff",
    color: "#fff",
    padding: "8px 12px",
    borderRadius: 12,
    maxWidth: "85%",
    fontSize: 13,
  },
  agentBubble: {
    alignSelf: "flex-start",
    background: "#fff",
    border: "1px solid #e8e8e8",
    padding: "8px 12px",
    borderRadius: 12,
    maxWidth: "85%",
    fontSize: 13,
    whiteSpace: "pre-wrap",
  },
  loading: {
    alignSelf: "flex-start",
    color: "#999",
    fontSize: 12,
    padding: "4px 8px",
  },
  inputArea: {
    padding: 12,
    borderTop: "1px solid #e8e8e8",
    background: "#fff",
  },
  textarea: {
    width: "100%",
    border: "1px solid #d9d9d9",
    borderRadius: 8,
    padding: 8,
    fontSize: 13,
    resize: "vertical" as const,
    outline: "none",
  },
  btn: {
    marginTop: 8,
    width: "100%",
    padding: "8px",
    background: "#1677ff",
    color: "#fff",
    border: "none",
    borderRadius: 8,
    cursor: "pointer",
    fontSize: 14,
  },
};
