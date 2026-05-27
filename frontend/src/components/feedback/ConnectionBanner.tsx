/**
 * 全局 WS 连接状态 banner — W4D5-T1。
 *
 * 显示条件:`!connected && reconnectAttempt >= 3`。
 *   - Header 角落已经有小绿/黄/灰点表示瞬时状态。
 *   - 第 3 次重连失败仍未恢复,意味着用户可能真的断网了 —
 *     这条横幅做"持续状态"提示,补 toast 自动消失的不足。
 *   - `connected === true` → 自动消失;useWebSocket onopen 会 reset
 *     `reconnectAttempt`,这里只渲染当前 store 值。
 *
 * Z-index = 55,Toast 是 60,banner 永远在 toast 下面。
 *
 * 不阻断用户操作 — 顶部条状,纯视觉提示。
 */

import { useWSStore } from "../../store/wsStore";

export function ConnectionBanner() {
  const connected = useWSStore((s) => s.connected);
  const connecting = useWSStore((s) => s.connecting);
  const reconnectAttempt = useWSStore((s) => s.reconnectAttempt);

  const show = !connected && reconnectAttempt >= 3;
  if (!show) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      data-testid="connection-banner"
      className="fixed inset-x-0 top-0 z-[55] border-b border-amber-200/80 bg-amber-50/95 px-4 py-2 text-center text-xs text-amber-900 backdrop-blur-md dark:border-amber-900/50 dark:bg-amber-950/90 dark:text-amber-200"
    >
      <span className="inline-flex items-center gap-2">
        <span
          className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-amber-600 dark:bg-amber-400"
          aria-hidden
        />
        {connecting
          ? `正在重连…(第 ${reconnectAttempt} 次)`
          : `连接断开,正在重试(已 ${reconnectAttempt} 次)`}
      </span>
    </div>
  );
}
