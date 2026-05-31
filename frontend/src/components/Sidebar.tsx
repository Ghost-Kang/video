import { useState, useRef, useEffect } from "react";
import { Clapperboard, Pencil, Trash2 } from "lucide-react";
import {
  sessionDisplayName,
  sessionSubtitle,
  type SessionMeta,
} from "../lib/sessionTitle";

interface Props {
  sessions: string[];
  current: string;
  names: Record<string, string>;
  meta: Record<string, SessionMeta>;
  onSwitch: (id: string) => void;
  onRename: (id: string, name: string) => void;
  onDelete: (id: string) => void;
  onClearEmpty?: () => void;
}

// 历史会话列表 — 每条显示从分析自动生成的标题(主题)+ 副标题(平台·相对时间),
// 未拆解的新会话显示「新会话 · 待拆解」。用户重命名优先于自动标题。
export function Sidebar({ sessions, current, names, meta, onSwitch, onRename, onDelete, onClearEmpty }: Props) {
  const [editing, setEditing] = useState<string | null>(null);
  const [confirmClear, setConfirmClear] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  // 「空会话」= 未拆解(无 meta)且未被用户重命名、且非当前会话。
  const clearableCount = sessions.filter(
    (id) => id !== current && !meta[id] && !names[id]?.trim(),
  ).length;

  useEffect(() => {
    if (editing) inputRef.current?.focus();
  }, [editing]);

  const submitRename = (id: string) => {
    const val = inputRef.current?.value.trim();
    if (val) onRename(id, val);
    setEditing(null);
  };

  return (
    <div className="flex w-[220px] flex-col gap-1.5 overflow-auto border-r border-stone-200/70 dark:border-stone-800/70 bg-[var(--color-paper)]/40 dark:bg-stone-950/40 backdrop-blur-md p-4">
      <div className="flex items-center justify-between px-2 pb-2">
        <span className="text-[10px] font-medium uppercase tracking-[0.18em] text-stone-400 dark:text-stone-600">
          历史
        </span>
        {onClearEmpty && clearableCount > 0 &&
          (confirmClear ? (
            <span className="flex items-center gap-2 text-[10px]">
              <button
                type="button"
                onClick={() => {
                  onClearEmpty();
                  setConfirmClear(false);
                }}
                className="font-medium text-rose-500 hover:text-rose-600 dark:text-rose-400"
              >
                清除 {clearableCount} 条
              </button>
              <button
                type="button"
                onClick={() => setConfirmClear(false)}
                className="text-stone-400 hover:text-stone-600 dark:text-stone-500"
              >
                取消
              </button>
            </span>
          ) : (
            <button
              type="button"
              onClick={() => setConfirmClear(true)}
              title="清理未拆解的空会话"
              className="text-[10px] text-stone-400 transition-colors hover:text-[#7c2d12] dark:text-stone-500 dark:hover:text-[#ea580c]"
            >
              清理空会话
            </button>
          ))}
      </div>

      <div className="flex flex-col gap-0.5">
        {sessions.map((id) =>
          editing === id ? (
            <input
              key={id}
              ref={inputRef}
              defaultValue={sessionDisplayName(names, meta, id)}
              onBlur={() => submitRename(id)}
              onKeyDown={(e) => {
                if (e.key === "Enter") submitRename(id);
                if (e.key === "Escape") setEditing(null);
              }}
              className="w-full rounded-lg border border-[#7c2d12] dark:border-[#ea580c] bg-white dark:bg-stone-900 px-2.5 py-1.5 text-xs text-stone-900 dark:text-stone-100 outline-none focus:ring-2 focus:ring-[#7c2d12]/30 dark:focus:ring-[#ea580c]/30"
            />
          ) : (
            (() => {
              const analyzed = !!meta[id];
              const title = sessionDisplayName(names, meta, id);
              const subtitle = sessionSubtitle(names, meta, id);
              const active = id === current;
              return (
                <div
                  key={id}
                  className={`session-row group flex items-center gap-2 overflow-hidden rounded-lg pl-2.5 transition-colors ${
                    active
                      ? "bg-white dark:bg-stone-800/60 ring-1 ring-stone-200 dark:ring-stone-700 shadow-soft"
                      : "hover:bg-[var(--color-paper-deeper)]/70 dark:hover:bg-stone-800/40"
                  }`}
                >
                  <Clapperboard
                    className={`h-3.5 w-3.5 shrink-0 ${
                      analyzed
                        ? "text-[#7c2d12] dark:text-[#ea580c]"
                        : "text-stone-300 dark:text-stone-600"
                    }`}
                    strokeWidth={1.75}
                  />
                  <button
                    onClick={() => onSwitch(id)}
                    className="flex-1 cursor-pointer overflow-hidden bg-transparent py-2 pr-1 text-left font-inherit"
                    type="button"
                    title={title}
                  >
                    <div
                      className={`overflow-hidden text-ellipsis whitespace-nowrap text-xs ${
                        analyzed || names[id]
                          ? "text-stone-900 dark:text-stone-100"
                          : "text-stone-400 dark:text-stone-500"
                      }`}
                    >
                      {title}
                    </div>
                    {subtitle && (
                      <div className="mt-0.5 overflow-hidden text-ellipsis whitespace-nowrap text-[10px] text-stone-400 dark:text-stone-500">
                        {subtitle}
                      </div>
                    )}
                  </button>
                  <button
                    onClick={() => setEditing(id)}
                    className="action-btn flex h-[22px] w-[22px] shrink-0 items-center justify-center rounded text-stone-400 dark:text-stone-500 hover:text-[#7c2d12] dark:hover:text-[#ea580c] transition-colors"
                    title="重命名"
                    type="button"
                  >
                    <Pencil className="h-[11px] w-[11px]" />
                  </button>
                  {sessions.length > 1 && (
                    <button
                      onClick={() => onDelete(id)}
                      className="action-btn mr-1 flex h-[22px] w-[22px] shrink-0 items-center justify-center rounded text-stone-400 dark:text-stone-500 hover:text-rose-500 dark:hover:text-rose-400 transition-colors"
                      title="删除"
                      type="button"
                    >
                      <Trash2 className="h-[11px] w-[11px]" />
                    </button>
                  )}
                </div>
              );
            })()
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
