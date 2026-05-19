import { useRef, useCallback, useState } from "react";
import type { WSIncoming, WSPositionUpdate, WSReviewNode, WSExecuteNode, WSOptimizePrompt, NodeStatus } from "../types";

type Handler = (res: WSIncoming) => void;

const WS_URL = `ws://${location.hostname}:8765`;

export function useWebSocket(userId: string, onMessage: Handler) {
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
      console.log("[WS] 已连接, 发送 auth");
      // 首条消息：鉴权
      ws.send(JSON.stringify({ type: "auth", user_id: userId }));
      setConnecting(false);
      setConnected(true);
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

  const sendReviewNode = useCallback((review: WSReviewNode) => {
    console.log(`[WS] 发送 review_node action=${review.action} node=${review.node_id}`);
    _send(review);
  }, [_send]);

  const sendExecuteNode = useCallback((payload: WSExecuteNode) => {
    console.log(`[WS] 发送 execute_node node=${payload.node_id}`);
    _send(payload);
  }, [_send]);

  const sendUpdateNodeStatus = useCallback((threadId: string, nodeId: string, nodeStatus: NodeStatus) => {
    console.log(`[WS] 发送 update_node_status node=${nodeId} ${nodeStatus}`);
    _send({ type: "update_node_status", thread_id: threadId, node_id: nodeId, node_status: nodeStatus });
  }, [_send]);

  const sendOptimizePrompt = useCallback((payload: WSOptimizePrompt) => {
    console.log(`[WS] 发送 optimize_prompt node=${payload.node_id}`);
    _send(payload);
  }, [_send]);

  const sendCreateEdge = useCallback((threadId: string, source: string, target: string) => {
    console.log(`[WS] 发送 create_edge ${source} → ${target}`);
    _send({ type: "create_edge", thread_id: threadId, source, target });
  }, [_send]);

  const sendDeleteEdge = useCallback((threadId: string, edgeId: string) => {
    console.log(`[WS] 发送 delete_edge ${edgeId}`);
    _send({ type: "delete_edge", thread_id: threadId, edge_id: edgeId });
  }, [_send]);

  const sendReorderEdge = useCallback((threadId: string, edgeId: string, direction: "up" | "down") => {
    _send({ type: "reorder_edge", thread_id: threadId, edge_id: edgeId, direction });
  }, [_send]);

  return { connect, sendMessage, sendPosition, sendGetSessionState, sendReviewNode, sendExecuteNode, sendUpdateNodeStatus, sendOptimizePrompt, sendCreateEdge, sendDeleteEdge, sendReorderEdge, connected, connecting };
}
