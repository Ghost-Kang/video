import { useState } from "react";

interface Props {
  threadId: string;
  onConnect: (id: string) => void;
  connected: boolean;
}

export function Header({ threadId, onConnect, connected }: Props) {
  const [input, setInput] = useState(threadId);

  const handleConnect = () => {
    const tid = input.trim();
    if (tid) onConnect(tid);
  };

  return (
    <div style={styles.bar}>
      <span style={styles.logo}>OpenRHTV</span>
      <span style={{
        display: "inline-block",
        width: 8,
        height: 8,
        borderRadius: "50%",
        background: connected ? "#52c41a" : "#ff4d4f",
      }} />
      <div style={styles.session}>
        <label style={styles.label}>会话:</label>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleConnect()}
          style={styles.input}
        />
        <button onClick={handleConnect} style={styles.btn}>
          进入
        </button>
      </div>
      <span style={styles.hint}>script → storyboard → image → video → audio</span>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  bar: {
    height: 44,
    display: "flex",
    alignItems: "center",
    padding: "0 16px",
    borderBottom: "1px solid #e8e8e8",
    background: "#fff",
    fontSize: 13,
    color: "#666",
    gap: 16,
  },
  logo: { fontWeight: 700, fontSize: 15, color: "#333" },
  session: { display: "flex", alignItems: "center", gap: 6 },
  label: { fontSize: 12 },
  input: {
    width: 120,
    padding: "4px 8px",
    border: "1px solid #d9d9d9",
    borderRadius: 4,
    fontSize: 12,
    outline: "none",
  },
  btn: {
    padding: "4px 10px",
    background: "#1677ff",
    color: "#fff",
    border: "none",
    borderRadius: 4,
    cursor: "pointer",
    fontSize: 12,
  },
  hint: { marginLeft: "auto", fontSize: 11, color: "#bbb" },
};
