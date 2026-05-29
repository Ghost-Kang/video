import { useRef, useCallback, useState } from "react";
import { useToastStore } from "../store/toastStore";
import { useWSStore } from "../store/wsStore";
import type { WSCommand, WSEvent } from "../types/ws";

type Handler = (res: WSEvent) => void;

// Dev (vite dev server): connect directly to backend :8765 (no proxy).
// Prod (nginx behind https): same-origin /ws — nginx reverse-proxies to
// backend:8765 with Upgrade header. Both Cloudflare Tunnel and direct
// HTTPS deploys flow through this same /ws path.
const WS_URL = import.meta.env.DEV
  ? `ws://${location.hostname}:8765`
  : `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`;
const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 30000;

export function useWebSocket(userId: string, onMessage: Handler) {
  const wsRef = useRef<WebSocket | null>(null);
  const pendingRef = useRef<string[]>([]);
  const retryRef = useRef(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [connected, setConnected] = useState(false);
  const [connecting, setConnecting] = useState(false);
  // W4D5-T1: 暴露 attempt 计数给根级 <ConnectionBanner/>(经 wsStore 中转)。
  // 与 retryRef 双写 — retryRef 是 onopen 里同步读的真值,reconnectAttempt 是
  // React state 给 UI render 用,避免直接订阅 ref。
  const [reconnectAttempt, setReconnectAttempt] = useState(0);

  const connect = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setConnecting(true);
    setConnected(false);

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log("[WS] 已连接, 发送 auth");
      // 邀请码从 localStorage 读取 — InviteCode page 写入后,所有 WS 重连
      // 都自动携带。Backend 在 INVITE_CODES 非空时校验,空集放行。
      let inviteCode: string | null = null;
      try {
        inviteCode =
          localStorage.getItem("openrhtv_invite_code") ||
          sessionStorage.getItem("openrhtv_invite_code");
      } catch {
        // private mode — fall through with null
      }
      ws.send(
        JSON.stringify({
          type: "auth",
          user_id: userId,
          ...(inviteCode ? { invite_code: inviteCode } : {}),
        }),
      );
      // W4D5-T1: 检测从 disconnected→connected 切回(retryRef>0 说明经历过断
      // 连),给宝妈一个正向反馈。第一次冷启 onopen 时 retryRef=0,不弹。
      const wasReconnect = retryRef.current > 0;
      setConnecting(false);
      setConnected(true);
      retryRef.current = 0;
      setReconnectAttempt(0);
      if (wasReconnect) {
        useToastStore.getState().push({ kind: "info", title: "网络已恢复", ttlMs: 2000 });
        // W5D4 Fix B — after a reconnect (e.g. a corporate proxy that cuts the
        // WS on a fixed ~120s idle timer, ignoring ping/pong), re-request the
        // current thread's state so the backend replays run_status + any
        // analysis/rewrite that completed during the gap. Without this the
        // client silently waited for live frames that already came and went.
        // Cold start (retryRef===0) skips this — App's tid effect already asks.
        const tid = useWSStore.getState().currentThreadId;
        if (tid) {
          ws.send(JSON.stringify({ type: "get_session_state", thread_id: tid }));
        }
      }
      if (pendingRef.current.length) {
        console.log(`[WS] onopen 发送排队消息 x${pendingRef.current.length}`);
        for (const msg of pendingRef.current) {
          ws.send(msg);
        }
        pendingRef.current = [];
      }
    };

    ws.onmessage = (e) => {
      const res = JSON.parse(e.data);
      onMessage(res);
    };

    ws.onclose = () => {
      console.log("[WS] 已断开");
      setConnected(false);
      setConnecting(false);
      wsRef.current = null;
      scheduleReconnect();
    };

    ws.onerror = () => {
      console.log("[WS] 连接错误");
      setConnected(false);
      setConnecting(false);
      // onerror 通常后跟 onclose，由 onclose 统一触发重连
    };
  }, [onMessage]);

  const scheduleReconnect = useCallback(() => {
    const attempt = retryRef.current + 1;
    retryRef.current = attempt;
    setReconnectAttempt(attempt);
    const delay = Math.min(RECONNECT_BASE_MS * Math.pow(2, attempt - 1), RECONNECT_MAX_MS);
    console.log(`[WS] ${delay / 1000}s 后重连 (第${attempt}次)`);
    timerRef.current = setTimeout(() => connect(), delay);
  }, [connect]);

  const sendCommand = useCallback(<T extends WSCommand>(payload: T) => {
    // P3-2 cleanup: pendingRef 的 flush 只在 onopen 触发(单点),sendCommand 只决定
    // "现发 vs 入队"。之前的双 flush(此处再迭代一次)在 OPEN 分支下 pendingRef 始终
    // 为空,是 dead code + 误导;移除让 invariant 显式 — pendingRef 仅由 onopen 清空。
    const data = JSON.stringify(payload);
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(data);
    } else {
      console.log(`[WS] 排队 type=${payload.type}`);
      pendingRef.current.push(data);
    }
  }, []);

  return { connect, sendCommand, connected, connecting, reconnectAttempt };
}
