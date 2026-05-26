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
    <div className="flex w-[220px] flex-col gap-1.5 overflow-auto border-r border-stone-200/70 dark:border-stone-800/70 bg-[var(--color-paper)]/40 dark:bg-stone-950/40 backdrop-blur-md p-4">
      <div className="px-2 pb-2 text-[10px] font-medium uppercase tracking-[0.18em] text-stone-400 dark:text-stone-600">
        历史
      </div>

      <div className="flex flex-col gap-0.5">
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
              className="w-full rounded-lg border border-[#7c2d12] dark:border-[#ea580c] bg-white dark:bg-stone-900 px-2.5 py-1.5 text-xs text-stone-900 dark:text-stone-100 outline-none focus:ring-2 focus:ring-[#7c2d12]/30 dark:focus:ring-[#ea580c]/30"
            />
          ) : (
            <div
              key={id}
              className={`session-row group flex items-center overflow-hidden rounded-lg transition-colors ${
                id === current
                  ? "bg-white dark:bg-stone-800/60 ring-1 ring-stone-200 dark:ring-stone-700 shadow-soft"
                  : "hover:bg-[var(--color-paper-deeper)]/70 dark:hover:bg-stone-800/40"
              }`}
            >
              <button
                onClick={() => onSwitch(id)}
                className="flex-1 cursor-pointer overflow-hidden text-ellipsis whitespace-nowrap bg-transparent px-3 py-2 text-left text-xs text-stone-900 dark:text-stone-100 font-inherit"
                type="button"
              >
                {displayName(id)}
              </button>
              <button
                onClick={() => setEditing(id)}
                className="action-btn flex h-[22px] w-[22px] items-center justify-center rounded text-stone-400 dark:text-stone-500 hover:text-[#7c2d12] dark:hover:text-[#ea580c] transition-colors"
                title="重命名"
                type="button"
              >
                <svg width="11" height="11" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M11.5 1.5l3 3-10 10H1.5v-3z" />
                </svg>
              </button>
              {sessions.length > 1 && (
                <button
                  onClick={() => onDelete(id)}
                  className="action-btn mr-1 flex h-[22px] w-[22px] items-center justify-center rounded text-stone-400 dark:text-stone-500 hover:text-rose-500 dark:hover:text-rose-400 transition-colors"
                  title="删除"
                  type="button"
                >
                  <svg width="11" height="11" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M2.5 4.5h11M5.5 4.5V3a1 1 0 011-1h3a1 1 0 011 1v1.5M6.5 7.5v5M9.5 7.5v5M3.5 4.5l1 9h7l1-9" />
                  </svg>
                </button>
              )}
            </div>
          )
        )}
        {sessions.length === 0 && (
          <div className="px-2.5 py-2 text-[11px] text-stone-400 dark:text-stone-600">还没有记录</div>
        )}
      </div>

      <style>{`
        .session-row .action-btn { opacity: 0; transition: opacity 0.15s; }
        .session-row:hover .action-btn { opacity: 1; }
      `}</style>
    </div>
  );
}
