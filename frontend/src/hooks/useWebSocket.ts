import { useRef, useCallback, useState } from "react";
import type { WSIncoming, WSPositionUpdate } from "../types";

type Handler = (res: WSIncoming) => void;

const WS_URL = "ws://localhost:8765";

export function useWebSocket(onMessage: Handler) {
  const wsRef = useRef<WebSocket | null>(null);
  const pendingRef = useRef<string[]>([]);
  const [connected, setConnected] = useState(false);
  const [connecting, setConnecting] = useState(false);

  const connect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setConnecting(true);
    setConnected(false);
    pendingRef.current = [];

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log("[WS] 已连接");
      setConnecting(false);
      setConnected(true);
      // 发送排队消息
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
    };

    ws.onerror = () => {
      console.log("[WS] 连接错误");
      setConnected(false);
      setConnecting(false);
    };
  }, [onMessage]);

  const _flushPending = useCallback(() => {
    if (wsRef.current?.readyState !== WebSocket.OPEN) return;
    for (const msg of pendingRef.current) {
      wsRef.current.send(msg);
    }
    pendingRef.current = [];
  }, []);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const _send = useCallback((payload: Record<string, any>) => {
    const data = JSON.stringify(payload);
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      // 顺手清掉可能残留的排队消息
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

  const sendMessage = useCallback((threadId: string, content: string) => {
    console.log(`[WS] 发送 user_message thread=${threadId}`);
    _send({ type: "user_message", thread_id: threadId, content });
  }, [_send]);

  const sendPosition = useCallback((update: WSPositionUpdate) => {
    _send(update);
  }, [_send]);

  const sendGetSessionState = useCallback((threadId: string) => {
    console.log(`[WS] 发送 get_session_state thread=${threadId}`);
    _send({ type: "get_session_state", thread_id: threadId });
  }, [_send]);

  return { connect, sendMessage, sendPosition, sendGetSessionState, connected, connecting };
}
