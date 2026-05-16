import { useRef, useCallback, useState } from "react";
import type { WSAgentResponse } from "../types";

const WS_URL = "ws://localhost:8765";

export function useWebSocket(onResponse: (res: WSAgentResponse) => void) {
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);

  const connect = useCallback(
    (threadId: string) => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }

      const ws = new WebSocket(`${WS_URL}/${encodeURIComponent(threadId)}`);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        onResponse({
          type: "agent_response",
          content: `已加入会话: ${threadId}`,
          canvas: null,
        });
      };

      ws.onmessage = (e) => {
        const res: WSAgentResponse = JSON.parse(e.data);
        if (res.type === "agent_response") {
          onResponse(res);
        }
      };

      ws.onclose = () => {
        setConnected(false);
        wsRef.current = null;
      };

      ws.onerror = () => {
        setConnected(false);
      };
    },
    [onResponse]
  );

  const send = useCallback((content: string) => {
    if (wsRef.current?.readyState !== WebSocket.OPEN) return false;
    wsRef.current.send(JSON.stringify({ type: "user_message", content }));
    return true;
  }, []);

  return { connect, send, connected };
}
