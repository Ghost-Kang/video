import { useState, useRef, useEffect } from "react";

interface Props {
  sessions: string[];
  current: string;
  names: Record<string, string>;
  onSwitch: (id: string) => void;
  onRename: (id: string, name: string) => void;
  onDelete: (id: string) => void;
}

export function Sidebar({ sessions, current, names, onSwitch, onRename, onDelete }: Props) {
  const [editing, setEditing] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editing) inputRef.current?.focus();
  }, [editing]);

  const submitRename = (id: string) => {
    const val = inputRef.current?.value.trim();
    if (val) onRename(id, val);
    setEditing(null);
  };

  const displayName = (id: string) => names[id] || "新会话";

  return (
    <div style={S.panel}>
      <div style={S.label}>历史会话</div>
      <div style={S.list}>
        {sessions.map((id) =>
          editing === id ? (
            <input
              key={id}
              ref={inputRef}
              defaultValue={displayName(id)}
              onBlur={() => submitRename(id)}
              onKeyDown={(e) => {
                if (e.key === "Enter") submitRename(id);
                if (e.key === "Escape") setEditing(null);
              }}
              style={S.editInput}
            />
          ) : (
            <div key={id} style={id === current ? S.rowActive : S.row} className="session-row">
              <button onClick={() => onSwitch(id)} style={S.name}>
                {displayName(id)}
              </button>
              <button onClick={() => setEditing(id)} style={S.actionBtn} className="action-btn" title="重命名">
                <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M11.5 1.5l3 3-10 10H1.5v-3z" />
                </svg>
              </button>
              {sessions.length > 1 && (
                <button onClick={() => onDelete(id)} style={S.actionBtn} className="action-btn" title="删除">
                  <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M2.5 4.5h11M5.5 4.5V3a1 1 0 011-1h3a1 1 0 011 1v1.5M6.5 7.5v5M9.5 7.5v5M3.5 4.5l1 9h7l1-9" />
                  </svg>
                </button>
              )}
            </div>
          )
        )}
        {sessions.length === 0 && <div style={S.empty}>暂无会话</div>}
      </div>
      <style>{`
        .session-row .action-btn { opacity: 0; }
        .session-row:hover .action-btn { opacity: 1; }
      `}</style>
    </div>
  );
}

const S = {
  panel: {
    width: 200,
    display: "flex",
    flexDirection: "column",
    background: "#fafafa",
    borderRight: "1px solid #e4e4e7",
    padding: 12,
    gap: 8,
    overflow: "auto",
  } as React.CSSProperties,

  label: {
    fontSize: 11,
    fontWeight: 500,
    color: "#a1a1aa",
    textTransform: "uppercase" as const,
    letterSpacing: "0.05em",
    padding: "0 4px",
  },

  list: {
    display: "flex",
    flexDirection: "column" as const,
    gap: 2,
  },

  row: {
    display: "flex",
    alignItems: "center",
    borderRadius: 6,
    overflow: "hidden",
  },

  rowActive: {
    display: "flex",
    alignItems: "center",
    background: "#fff",
    border: "1px solid #e4e4e7",
    borderRadius: 6,
    overflow: "hidden",
  },

  name: {
    flex: 1,
    padding: "8px 10px",
    background: "transparent",
    border: "none",
    cursor: "pointer",
    fontSize: 12,
    color: "#18181b",
    textAlign: "left" as const,
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap" as const,
  },

  actionBtn: {
    width: 24,
    height: 24,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    background: "transparent",
    border: "none",
    borderRadius: 4,
    cursor: "pointer",
    color: "#a1a1aa",
    padding: 0,
    flexShrink: 0,
    transition: "opacity 0.1s",
  },

  editInput: {
    width: "100%",
    padding: "6px 8px",
    border: "1px solid #18181b",
    borderRadius: 6,
    fontSize: 12,
    outline: "none",
    color: "#18181b",
    background: "#fff",
  },

  empty: {
    fontSize: 12,
    color: "#d4d4d8",
    padding: "8px 4px",
  },
};
