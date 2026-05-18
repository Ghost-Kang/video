interface Props {
  sessionName: string;
  connected: boolean;
  connecting: boolean;
  sidebarOpen: boolean;
  onToggleSidebar: () => void;
  onNewSession: () => void;
}

export function Header({ sessionName, connected, connecting, sidebarOpen, onToggleSidebar, onNewSession }: Props) {
  return (
    <div style={S.bar}>
      <button onClick={onToggleSidebar} style={S.toggle} title={sidebarOpen ? "收起侧栏" : "展开侧栏"}>
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2">
          <path d={sidebarOpen ? "M10.5 3.5L5 8l5.5 4.5" : "M5.5 3.5L11 8l-5.5 4.5"} />
        </svg>
      </button>

      <span style={S.logo}>OpenRHTV</span>
      <span style={S.slogan}>Make it easy</span>
      <span style={connecting ? S.dot("connecting") : S.dot(connected ? "on" : "off")} />

      <span style={S.sessionName}>{sessionName}</span>

      <button onClick={onNewSession} style={S.plusBtn} title="新建会话">
        +
      </button>

      <span style={S.hint}>策划书 → image → video → audio</span>
    </div>
  );
}

const S = {
  bar: {
    height: 48,
    display: "flex",
    alignItems: "center",
    padding: "0 20px",
    borderBottom: "1px solid #e4e4e7",
    background: "#fff",
    fontSize: 13,
    color: "#71717a",
    gap: 10,
  } as React.CSSProperties,

  toggle: {
    width: 28,
    height: 28,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    background: "transparent",
    color: "#71717a",
    border: "none",
    borderRadius: 6,
    cursor: "pointer",
    padding: 0,
    transition: "background 0.1s",
  } as React.CSSProperties,

  logo: {
    fontWeight: 600,
    fontSize: 14,
    letterSpacing: "-0.01em",
    color: "#18181b",
  } as React.CSSProperties,

  slogan: {
    fontSize: 11,
    fontWeight: 400,
    color: "#a1a1aa",
    fontStyle: "italic",
    letterSpacing: "0.02em",
  } as React.CSSProperties,

  dot: (state: "on" | "off" | "connecting") => ({
    display: "inline-block",
    width: 7,
    height: 7,
    borderRadius: "50%",
    background: state === "on" ? "#22c55e" : state === "connecting" ? "#f59e0b" : "#ef4444",
    boxShadow:
      state === "on" ? "0 0 6px rgba(34,197,94,0.4)"
      : state === "connecting" ? "0 0 6px rgba(245,158,11,0.4)"
      : "0 0 6px rgba(239,68,68,0.4)",
  }) as React.CSSProperties,

  sessionName: {
    fontSize: 12,
    color: "#a1a1aa",
    marginLeft: 4,
  } as React.CSSProperties,

  plusBtn: {
    width: 24,
    height: 24,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    background: "transparent",
    color: "#71717a",
    border: "1px solid #e4e4e7",
    borderRadius: 6,
    cursor: "pointer",
    fontSize: 16,
    fontWeight: 300,
    lineHeight: 1,
    padding: 0,
    transition: "all 0.15s",
  } as React.CSSProperties,

  hint: {
    marginLeft: "auto",
    fontSize: 11,
    color: "#d4d4d8",
    letterSpacing: "0.02em",
  } as React.CSSProperties,
};
