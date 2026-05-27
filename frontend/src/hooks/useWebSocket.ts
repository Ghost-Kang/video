import { useRef, useCallback, useState } from "react";
import type { WSCommand, WSEvent } from "../types/ws";

type Handler = (res: WSEvent) => void;

const WS_URL = `ws://${location.hostname}:8765`;
const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 30000;

export function useWebSocket(userId: string, onMessage: Handler) {
  const wsRef = useRef<WebSocket | null>(null);
  const pendingRef = useRef<string[]>([]);
  const retryRef = useRef(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [connected, setConnected] = useState(false);
  const [connecting, setConnecting] = useState(false);

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
      ws.send(JSON.stringify({ type: "auth", user_id: userId }));
      setConnecting(false);
      setConnected(true);
      retryRef.current = 0;
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
    const delay = Math.min(RECONNECT_BASE_MS * Math.pow(2, attempt - 1), RECONNECT_MAX_MS);
    console.log(`[WS] ${delay / 1000}s 后重连 (第${attempt}次)`);
    timerRef.current = setTimeout(() => connect(), delay);
  }, [connect]);

  const sendCommand = useCallback(<T extends WSCommand>(payload: T) => {
    const data = JSON.stringify(payload);
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      for (const msg of pendingRef.current) {
        wsRef.current.send(msg);
      }
      pendingRef.current = [];
      wsRef.current.send(data);
    } else {
      console.log(`[WS] 排队 type=${payload.type}`);
      pendingRef.current.push(data);
    }
  }, []);

  return { connect, sendCommand, connected, connecting };
}
