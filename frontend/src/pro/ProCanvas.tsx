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
import {
  buildSubmitCommand,
  estimateGraph,
  fetchSeedGraph,
  loadSavedGraph,
  proErrorTitle,
  ProApiError,
  saveGraph,
  seedFromThread,
} from "./proExecution";
import { ProThemeInput } from "./ProThemeInput";

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
  const [restored, setRestored] = useState(false);
  const seededRef = useRef(false);
  const restoredRef = useRef(false);

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
            if (["Generate", "Video", "Compose", "Preview"].includes(s.props.nodeType))
              updateProNode(editor, s.id, { status: "done" });
          }
          previews.forEach((s, i) => {
            if (ev.outputs[i]) updateProNode(editor, s.id, { status: "done", resultUrl: ev.outputs[i] });
          });
        });
      } else if (ev.type === "pro_run_failed") {
        setStatus(editor, (s) => ["Generate", "Video", "Compose", "Preview"].includes(s.props.nodeType), "failed");
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

  // 挂载恢复(只一次):已保存的图 **优先**于 seed —— 这样带 ?seed= 的 URL 刷新不会覆盖用户的
  // 编辑(seed 只在该 thread 还没存过图时消费一次)。都没有则空白画布。
  useEffect(() => {
    if (!editorReady || seededRef.current) return;
    seededRef.current = true;
    const editor = editorRef.current;
    if (!editor) return;
    const analysisId = parseSeed(searchParams);
    (async () => {
      try {
        const saved = await loadSavedGraph(threadId);
        if (saved && Array.isArray(saved.nodes) && saved.nodes.length) {
          loadGraph(editor, saved);
        } else if (analysisId) {
          loadGraph(editor, await fetchSeedGraph(analysisId, threadId));
        } else {
          // 进 Pro 自动种子:该 thread 有分析则铺出创作图;没有则留空 → ProThemeInput 显示
          const g = await seedFromThread(threadId);
          if (g && Array.isArray(g.nodes) && g.nodes.length) loadGraph(editor, g);
        }
      } catch (e) {
        const err = e as ProApiError;
        useToastStore.getState().push({ kind: "error", title: proErrorTitle(err.code), body: err.detail });
      } finally {
        restoredRef.current = true; // 解锁 autosave(在此之前的 store 变更不触发保存)
        setRestored(true);
      }
    })();
  }, [editorReady, searchParams, threadId]);

  // 自动保存(debounce):节点拖动/参数改 + 连线变更 → 序列化整图存后端。restoredRef 守卫确保
  // 恢复阶段灌图引发的 store 变更不会反过来触发保存。
  useEffect(() => {
    if (!editorReady) return;
    const editor = editorRef.current;
    if (!editor) return;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const schedule = () => {
      if (!restoredRef.current) return;
      clearTimeout(timer);
      timer = setTimeout(() => void saveGraph(threadId, compileGraph(editor)), 1200);
    };
    const unlistenEditor = editor.store.listen(schedule, { scope: "document", source: "user" });
    const unsubStore = useProCanvasStore.subscribe((s, prev) => {
      if (s.edges !== prev.edges) schedule();
    });
    return () => {
      clearTimeout(timer);
      unlistenEditor();
      unsubStore();
    };
  }, [editorReady, threadId]);

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
        <ProThemeInput threadId={threadId} ready={restored} />
        <CostModal onConfirm={handleConfirmRun} />
      </Tldraw>
    </div>
  );
}
