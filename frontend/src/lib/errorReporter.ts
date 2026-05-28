/**
 * Frontend Sentry-lite (W5D2-E) — 把 window 级 / React 级 JS 报错往 backend
 * `/api/client_error` 投递,founder 通过 events.db 里的 client_error 行回溯
 * 内测期间的浏览器问题。
 *
 * 设计取舍:
 * - **静默失败**:reporter 本身报错(网络挂、CORS、JSON 序列化爆)绝对不再
 *   抛/不再 retry。如果 reporter 自己又 throw 进 window.error 会形成无限循环
 *   把 backend 打爆 — 唯一安全的姿势就是 catch + console.warn。
 * - **dedup 1 分钟**:同一个 (kind + message.slice(0,80)) 的 key,1 分钟内
 *   只投一次。避免循环 / setInterval 里的同 stack 报错把后端撑爆。in-memory
 *   Map(进程级,刷页就清空 — 这就够了)。
 * - **非阻塞**:fetch 用 `setTimeout(..., 0)` 异步触发。即使在 window.error
 *   handler 同步路径里调,也不阻 main thread,也不让 fetch 失败再触发新的
 *   window.error。
 * - **PII**:不带 chat 输入,不带 cookies/localStorage 全量。只 user_id +
 *   thread_id + truncated ua + truncated stack + filename/lineno/colno + url。
 */

export interface ClientErrorPayload {
  /** "window_error" | "unhandled_rejection" | "react_error_boundary" + 可扩展 */
  kind: string;
  /** 报错信息,任意长度;backend 自行裁剪 */
  message: string;
  /** JS stack,前端在投递前截 4000 字 */
  stack?: string;
  /** window.error 提供;rejection / boundary 通常 undefined */
  filename?: string;
  lineno?: number;
  colno?: number;
  /** location.href 投递时刻 */
  url: string;
  /** localStorage.rhtv_user;匿名用户可能 null */
  user_id: string | null;
  /** 当前 URL 里的 threadId(如果在 /chat/:threadId 路由下) */
  thread_id?: string | null;
  /** navigator.userAgent 前 200 字 */
  ua: string;
  /** React ErrorBoundary 才有,componentStack truncate 2000 */
  component_stack?: string;
}

const DEDUP_WINDOW_MS = 60_000;
const STACK_MAX = 4000;
const UA_MAX = 200;
const COMPONENT_STACK_MAX = 2000;

const recent = new Map<string, number>();

function truncate(s: string | undefined, max: number): string | undefined {
  if (s === undefined || s === null) return undefined;
  return s.length > max ? s.slice(0, max) : s;
}

function dedupKey(kind: string, message: string): string {
  return `${kind}::${message.slice(0, 80)}`;
}

function shouldSkip(kind: string, message: string, now: number): boolean {
  const key = dedupKey(kind, message);
  const last = recent.get(key);
  if (last !== undefined && now - last < DEDUP_WINDOW_MS) {
    return true;
  }
  recent.set(key, now);
  // Opportunistic GC — 防止 Map 长尾膨胀。entries 一旦超过 200 就清掉
  // 已过窗口的 key。常态根本到不了 200,这只是边界保险。
  if (recent.size > 200) {
    for (const [k, t] of recent) {
      if (now - t >= DEDUP_WINDOW_MS) recent.delete(k);
    }
  }
  return false;
}

/**
 * Test-only — 清空 dedup 状态。生产路径里不调用。
 */
export function _resetReporterStateForTests(): void {
  recent.clear();
}

export function reportClientError(input: ClientErrorPayload): void {
  try {
    const now = Date.now();
    if (shouldSkip(input.kind, input.message ?? "", now)) {
      return;
    }
    const payload: ClientErrorPayload = {
      kind: input.kind,
      message: input.message ?? "",
      stack: truncate(input.stack, STACK_MAX),
      filename: input.filename,
      lineno: input.lineno,
      colno: input.colno,
      url: input.url,
      user_id: input.user_id ?? null,
      thread_id: input.thread_id ?? null,
      ua: truncate(input.ua ?? "", UA_MAX) ?? "",
      component_stack: truncate(input.component_stack, COMPONENT_STACK_MAX),
    };
    // 异步投递 — 防止在 window.error handler 里 fetch 失败再触发 unhandled
    // rejection 形成循环。setTimeout(.., 0) 把 fetch 推到下一个 tick,
    // 同时保证主线程不被阻塞。
    setTimeout(() => {
      try {
        void fetch("/api/client_error", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify(payload),
          // keepalive 保证 onbeforeunload 时仍能发出 — 浏览器 max 64KB,我们
          // 远低于这个上限。
          keepalive: true,
        }).catch((err) => {
          // 静默 — 不 retry,不 throw,不再投递自己的失败(防循环)
          // eslint-disable-next-line no-console
          console.warn("[errorReporter] post failed", err);
        });
      } catch (err) {
        // eslint-disable-next-line no-console
        console.warn("[errorReporter] fetch threw", err);
      }
    }, 0);
  } catch (err) {
    // 万一 dedup / truncate / 任何同步路径炸了,也不能让 reporter 再触发
    // 上层的 unhandled rejection。
    // eslint-disable-next-line no-console
    console.warn("[errorReporter] internal error", err);
  }
}

/**
 * 抽出 URL path 里 /chat/:threadId 的 threadId — 用于诊断 payload。匹配不到
 * 返回 null(/admin/* 等不是 chat 路由)。
 */
export function extractThreadId(pathname: string): string | null {
  const m = pathname.match(/^\/chat\/([^/?#]+)/);
  return m ? m[1] : null;
}
