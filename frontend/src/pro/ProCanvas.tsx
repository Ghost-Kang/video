import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { Tldraw, type Editor, type TLComponents } from "tldraw";
import "tldraw/tldraw.css";

import { useToastStore } from "../store/toastStore";
import { useProCanvasStore } from "../store/proCanvasStore";
import { useWebSocket } from "../hooks/useWebSocket";
import type { WSEvent } from "../types/ws";
import type { ProGraph, ProRunEvent } from "../types/pro";
import { ProNodeShapeUtil, type ProNodeShape } from "./nodes/NodeShape";
import { EdgeLayer } from "./EdgeLayer";
import { ProToolbar } from "./ProToolbar";
import { NodeParamPanel } from "./NodeParamPanel";
import { RunOutputs } from "./RunOutputs";
import { CostModal } from "./CostModal";
import { compileGraph, loadGraph, pronodeShapes, updateProNode } from "./graphIO";
import { buildSubmitCommand, estimateGraph, fetchSeedGraph, proErrorTitle, ProApiError } from "./proExecution";

const PRO_SHAPE_UTILS = [ProNodeShapeUtil];

// 收敛 tldraw 默认 UI:只留导航/缩放 + 我们的 overlay(不要绘图工具栏/样式面板等)。
const PRO_COMPONENTS: TLComponents = {
  OnTheCanvas: EdgeLayer,
  Toolbar: null,
  StylePanel: null,
  PageMenu: null,
  MainMenu: null,
  ActionsMenu: null,
  QuickActions: null,
  HelpMenu: null,
  DebugMenu: null,
  KeyboardShortcutsDialog: null,
};

function parseSeed(params: URLSearchParams): string | null {
  const seed = params.get("seed");
  if (seed) return seed.startsWith("analysis:") ? seed.slice("analysis:".length) : seed;
  return params.get("analysis_id");
}

function isProRunEvent(ev: WSEvent): ev is ProRunEvent {
  return (
    ev.type === "pro_run_progress" ||
    ev.type === "pro_run_node_done" ||
    ev.type === "pro_run_done" ||
    ev.type === "pro_run_failed"
  );
}

function setStatus(editor: Editor, pick: (s: ProNodeShape) => boolean, status: string) {
  const shapes = pronodeShapes(editor).filter(pick);
  if (!shapes.length) return;
  editor.run(() => {
    for (const s of shapes) updateProNode(editor, s.id, { status });
  });
}

export default function ProCanvas({ userId }: { userId: string }) {
  const { threadId = "" } = useParams();
  const [searchParams] = useSearchParams();
  const editorRef = useRef<Editor | null>(null);
  const graphRef = useRef<ProGraph | null>(null);
  const [editorReady, setEditorReady] = useState(false);
  const seededRef = useRef(false);

  const openCostModal = useProCanvasStore((s) => s.openCostModal);
  const resetRun = useProCanvasStore((s) => s.resetRun);

  const onMessage = useCallback(
    (ev: WSEvent) => {
      if (ev.type === "error") {
        useToastStore.getState().push({ kind: "error", title: "操作出错", body: ev.message });
        return;
      }
      if (!isProRunEvent(ev)) return;
      if (ev.thread_id !== threadId) return;
      useProCanvasStore.getState().applyProRunEvent(ev);
      const editor = editorRef.current;
      if (!editor) return;
      if (ev.type === "pro_run_progress") {
        if (ev.status === "running" || ev.status === "submitting") setStatus(editor, () => true, "running");
        else if (ev.status === "cancelled") setStatus(editor, () => true, "idle");
      } else if (ev.type === "pro_run_done") {
        const previews = pronodeShapes(editor).filter((s) => s.props.nodeType === "Preview");
        editor.run(() => {
          for (const s of pronodeShapes(editor)) {
            if (s.props.nodeType === "Generate" || s.props.nodeType === "Preview")
              updateProNode(editor, s.id, { status: "done" });
          }
          previews.forEach((s, i) => {
            if (ev.outputs[i]) updateProNode(editor, s.id, { status: "done", resultUrl: ev.outputs[i] });
          });
        });
      } else if (ev.type === "pro_run_failed") {
        setStatus(editor, (s) => s.props.nodeType === "Generate" || s.props.nodeType === "Preview", "failed");
      }
    },
    [threadId],
  );

  const { connect, sendCommand, connected } = useWebSocket(userId, onMessage);

  useEffect(() => {
    connect();
  }, [connect]);

  // Esc 取消进行中的连线
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") useProCanvasStore.getState().cancelConnection();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  // 卸载时清状态(切线程/离开)
  useEffect(() => () => useProCanvasStore.getState().reset(), []);

  // 种子图:?seed=analysis:<id> / ?analysis_id=<id> → 灌进画布(只一次)
  useEffect(() => {
    if (!editorReady || seededRef.current) return;
    const analysisId = parseSeed(searchParams);
    if (!analysisId) return;
    seededRef.current = true;
    const editor = editorRef.current;
    if (!editor) return;
    fetchSeedGraph(analysisId, threadId)
      .then((g) => loadGraph(editor, g))
      .catch((e) => {
        const err = e as ProApiError;
        useToastStore.getState().push({ kind: "error", title: proErrorTitle(err.code), body: err.detail });
      });
  }, [editorReady, searchParams, threadId]);

  const handleRun = useCallback(async () => {
    const editor = editorRef.current;
    if (!editor) return;
    const graph = compileGraph(editor);
    if (!graph.nodes.length) {
      useToastStore.getState().push({ kind: "info", title: "先搭一张图", body: "从左上角添加节点并连线。" });
      return;
    }
    try {
      const est = await estimateGraph(graph);
      graphRef.current = graph;
      openCostModal(est);
    } catch (e) {
      const err = e as ProApiError;
      useToastStore.getState().push({ kind: "error", title: proErrorTitle(err.code), body: err.detail });
    }
  }, [openCostModal]);

  const handleConfirmRun = useCallback(() => {
    const graph = graphRef.current;
    if (!graph) return;
    resetRun();
    const editor = editorRef.current;
    if (editor) {
      editor.run(() => {
        for (const s of pronodeShapes(editor))
          updateProNode(editor, s.id, { status: "idle", resultUrl: s.props.cached ? s.props.cachedUrl : null });
      });
    }
    sendCommand(buildSubmitCommand(threadId, graph));
  }, [resetRun, sendCommand, threadId]);

  return (
    <div style={{ position: "fixed", inset: 0 }} data-testid="pro-canvas">
      {!connected && (
        <div className="absolute right-3 top-3 z-40 rounded-full bg-[var(--color-ink)]/70 px-2 py-0.5 text-[10px] text-white">
          连接中…
        </div>
      )}
      <Tldraw
        shapeUtils={PRO_SHAPE_UTILS}
        components={PRO_COMPONENTS}
        onMount={(editor) => {
          editorRef.current = editor;
          setEditorReady(true);
        }}
      >
        <ProToolbar onRun={handleRun} threadId={threadId} />
        <NodeParamPanel />
        <RunOutputs />
        <CostModal onConfirm={handleConfirmRun} />
      </Tldraw>
    </div>
  );
}
