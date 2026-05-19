import { useState, useCallback } from "react";

interface Props {
  onLogin: (userId: string) => void;
}

export function Login({ onLogin }: Props) {
  const [id, setId] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      const uid = id.trim();
      if (!uid) { setError("请输入工号"); return; }
      localStorage.setItem("rhtv_user", uid);
      onLogin(uid);
    },
    [id, onLogin]
  );

  return (
    <div style={S.outer}>
      <form onSubmit={handleSubmit} style={S.card}>
        <div style={S.logo}>OpenRHTV</div>
        <div style={S.sub}>输入工号开始创作</div>
        <input
          value={id}
          onChange={(e) => setId(e.target.value)}
          placeholder="请输入工号"
          style={S.input}
          autoFocus
        />
        {error && <div style={S.error}>{error}</div>}
        <button type="submit" style={S.btn} disabled={!id.trim()}>
          登录
        </button>
      </form>
    </div>
  );
}

const S = {
  outer: { display: "flex", alignItems: "center", justifyContent: "center", height: "100vh", background: "#18181b" } as React.CSSProperties,
  card: { display: "flex", flexDirection: "column", gap: 16, padding: "40px 32px", background: "#27272a", borderRadius: 16, width: 320 } as React.CSSProperties,
  logo: { fontSize: 24, fontWeight: 700, color: "#fff", textAlign: "center" as const, letterSpacing: "-0.02em" },
  sub: { fontSize: 13, color: "#a1a1aa", textAlign: "center" as const, marginBottom: 8 },
  input: { padding: "10px 14px", borderRadius: 8, border: "1px solid #3f3f46", background: "#18181b", color: "#fff", fontSize: 15, fontFamily: "inherit", outline: "none" },
  error: { color: "#ef4444", fontSize: 13, textAlign: "center" as const },
  btn: { padding: "10px 0", borderRadius: 8, border: "none", background: "#fff", color: "#18181b", fontSize: 15, fontWeight: 600, cursor: "pointer", fontFamily: "inherit" },
};
