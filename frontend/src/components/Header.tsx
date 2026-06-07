import { ProViewToggle } from "./ProViewToggle";
import { ProCanvasEntry } from "../pro/ProCanvasEntry";

interface Props {
  userId: string;
  sessionName: string;
  connected: boolean;
  connecting: boolean;
  sidebarOpen: boolean;
  onToggleSidebar: () => void;
  onNewSession: () => void;
  onLogout: () => void;
  isProView?: boolean;
  onToggleProView?: () => void;
  hideProToggle?: boolean;
}

export function Header({
  userId,
  sessionName,
  connected,
  connecting,
  sidebarOpen,
  onToggleSidebar,
  onNewSession,
  onLogout,
  isProView = false,
  onToggleProView,
  hideProToggle = false,
}: Props) {
  const dotColor = connecting
    ? "bg-amber-500 dark:bg-amber-400"
    : connected
      ? "bg-emerald-500 dark:bg-emerald-400"
      : "bg-rose-500 dark:bg-rose-400";

  return (
    <div className="relative z-20 flex items-center gap-3 h-12 px-6 border-b border-stone-200/70 dark:border-stone-800/70 bg-[var(--color-paper)]/85 dark:bg-stone-950/85 backdrop-blur-md text-stone-500 dark:text-stone-400 text-[13px] tracking-[-0.005em]">
      <button
        onClick={onToggleSidebar}
        className="flex h-6 w-6 items-center justify-center rounded-md text-stone-500 dark:text-stone-400 hover:text-stone-900 dark:hover:text-stone-100 transition-colors"
        title={sidebarOpen ? "收起侧栏" : "展开侧栏"}
        type="button"
      >
        <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.75">
          <path d={sidebarOpen ? "M10.5 3.5L5 8l5.5 4.5" : "M5.5 3.5L11 8l-5.5 4.5"} />
        </svg>
      </button>

      <span className="font-medium text-[13px] tracking-[0.01em] text-stone-900 dark:text-stone-50">
        Cascade
      </span>

      <span className={`inline-block h-1.5 w-1.5 rounded-full ${dotColor}`} aria-hidden />

      <span className="text-[11px] font-normal text-stone-400 dark:text-stone-500">
        {sessionName}
      </span>

      <button
        onClick={onNewSession}
        className="flex h-[22px] w-[22px] items-center justify-center rounded-md border border-stone-200 dark:border-stone-700 text-stone-500 dark:text-stone-400 hover:border-stone-400 dark:hover:border-stone-500 hover:text-stone-900 dark:hover:text-stone-100 text-[14px] font-light leading-none transition-colors"
        title="新建"
        type="button"
      >
        +
      </button>

      <span className="ml-auto" />

      <ProCanvasEntry variant="toolbar" />

      {onToggleProView && (
        <ProViewToggle
          isProView={isProView}
          onToggle={onToggleProView}
          hidden={hideProToggle}
        />
      )}

      <span className="text-[11px] text-stone-400 dark:text-stone-500">{userId}</span>

      <button
        onClick={onLogout}
        className="rounded-md border border-stone-200 dark:border-stone-700 bg-transparent text-[11px] text-stone-500 dark:text-stone-400 hover:text-stone-900 dark:hover:text-stone-100 hover:border-stone-400 dark:hover:border-stone-500 px-2.5 py-0.5 transition-colors"
        title="退出"
        type="button"
      >
        退出
      </button>
    </div>
  );
}
