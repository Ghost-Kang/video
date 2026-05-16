import { useState, useCallback, useEffect, useRef } from "react";
import { Header } from "./components/Header";
import { Canvas } from "./components/Canvas";
import { ChatPanel } from "./components/ChatPanel";
import { useWebSocket } from "./hooks/useWebSocket";
import { useCanvasStore } from "./store/canvasStore";
import type { WSAgentResponse } from "./types";

export default function App() {
  const [threadId, setThreadId] = useState("demo-1");
  const [loading, setLoading] = useState(false);
  const messages = useCanvasStore((s) => s.messages);
  const setCanvas = useCanvasStore((s) => s.setCanvas);
  const addMessage = useCanvasStore((s) => s.addMessage);
  const clearMessages = useCanvasStore((s) => s.clear);

  const onResponse = useCallback(
    (res: WSAgentResponse) => {
      setLoading(false);
      addMessage("agent", res.content);
      if (res.canvas?.nodes) {
        setCanvas(res.canvas.nodes);
      } else if (res.canvas !== null) {
        setCanvas({});
      }
    },
    [addMessage, setCanvas]
  );

  const { connect, send, connected } = useWebSocket(onResponse);
  const didInit = useRef(false);
  const timerRef = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => {
    if (!didInit.current) {
      didInit.current = true;
      connect("demo-1");
    }
  }, [connect]);

  const handleConnect = useCallback(
    (newId: string) => {
      setThreadId(newId);
      clearMessages();
      setCanvas({});
      connect(newId);
    },
    [connect, clearMessages, setCanvas]
  );

  const handleSend = useCallback(
    (text: string) => {
      addMessage("user", text);
      const ok = send(text);
      if (!ok) {
        addMessage("agent", "未连接到后端服务，请先启动 backend");
        return;
      }
      setLoading(true);
      // 60 秒超时兜底
      timerRef.current = setTimeout(() => {
        setLoading(false);
        addMessage("agent", "请求超时，请检查后端是否正常运行");
      }, 60_000);
    },
    [addMessage, send]
  );

  // 收到响应时清除超时
  useEffect(() => {
    if (!loading) clearTimeout(timerRef.current);
  }, [loading]);

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh" }}>
      <Header threadId={threadId} onConnect={handleConnect} connected={connected} />
      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        <ChatPanel messages={messages} onSend={handleSend} loading={loading} />
        <Canvas />
      </div>
    </div>
  );
}
