import { useState } from "react";
import { readAdminToken, writeAdminToken } from "../../lib/apiClient";

/**
 * Admin pages (events / creators / cost / health) read cross-user data that the
 * backend now gates behind X-Admin-Token. This bar lets the founder paste the
 * token once; it's stored in localStorage and injected by apiFetch. Without it
 * the admin data hooks just render empty/mock — no crash. Self-guards on the
 * /admin path so it can be mounted globally in PageShell.
 */
export function AdminTokenBar() {
  const onAdmin =
    typeof window !== "undefined" && window.location.pathname.startsWith("/admin");
  const [token, setToken] = useState(() => readAdminToken() ?? "");
  const [editing, setEditing] = useState(() => !readAdminToken());

  if (!onAdmin) return null;

  const save = () => {
    if (!token.trim()) return;
    writeAdminToken(token);
    // Reload so every admin data hook refetches with the token header set.
    window.location.reload();
  };

  if (!editing) {
    return (
      <div className="relative z-20 flex items-center justify-end gap-3 px-6 pt-3 text-xs text-stone-500 dark:text-stone-400">
        <span>🔑 管理令牌已设置</span>
        <button
          type="button"
          onClick={() => setEditing(true)}
          className="underline underline-offset-4 hover:text-[#7c2d12] dark:hover:text-[#ea580c] transition-colors"
        >
          修改
        </button>
      </div>
    );
  }

  return (
    <div className="relative z-20 flex flex-col sm:flex-row sm:items-center gap-2 px-6 pt-3">
      <input
        type="password"
        value={token}
        onChange={(e) => setToken(e.target.value)}
        placeholder="粘贴管理令牌 (X-Admin-Token)"
        aria-label="admin token"
        className="rounded-lg border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900 px-3 py-1.5 text-sm text-stone-900 dark:text-stone-100 outline-none focus:border-[#7c2d12] dark:focus:border-[#ea580c] sm:w-80"
      />
      <button
        type="button"
        onClick={save}
        disabled={!token.trim()}
        className="rounded-lg bg-[#7c2d12] dark:bg-[#ea580c] px-3 py-1.5 text-xs font-medium text-[#faf8f3] transition-colors hover:bg-[#9a3412] dark:hover:bg-[#c2410c] disabled:opacity-40 disabled:cursor-not-allowed"
      >
        保存并刷新
      </button>
      <span className="text-xs text-stone-400 dark:text-stone-500">
        管理数据需要令牌;没有令牌只会显示空数据。
      </span>
    </div>
  );
}
