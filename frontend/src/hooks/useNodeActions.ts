import { useCallback, useMemo } from "react";
import { useCanvasStore } from "../store/canvasStore";
import type { NodeStatus, NodeType } from "../types";
import type { WSCommand } from "../types/ws";

export interface NodeActions {
  handleReview: (nodeId: string, action: "approve" | "reject", feedback?: string) => void;
  handleExecuteNode: (
    nodeId: string,
    nodeType: NodeType,
    description: string,
    provider?: string,
    duration?: number,
    resolution?: string,
    generateAudio?: boolean,
  ) => void;
  handleUpdateNodeStatus: (nodeId: string, nodeStatus: NodeStatus) => void;
  handleOptimizePrompt: (nodeId: string, prompt: string, feedback: string) => void;
  handleCreateEdge: (source: string, target: string) => void;
  handleDeleteEdge: (edgeId: string) => void;
  handleReorderEdge: (edgeId: string, direction: "up" | "down") => void;
}

export function useNodeActions(
  threadId: string,
  sendCommand: <T extends WSCommand>(command: T) => void,
  sendChatMessage: (text: string) => void,
): NodeActions {
  const handleReview = useCallback(
    (nodeId: string, action: "approve" | "reject", feedback?: string) => {
      sendCommand({ type: "review_node", thread_id: threadId, node_id: nodeId, action, feedback });
      if (action === "reject") {
        const suffix = feedback ? `，反馈意见：${feedback}` : "";
        sendChatMessage(`驳回节点「${nodeId}」${suffix}\n节点 ${nodeId} 审核未通过，请根据反馈重新生成。`);
      }
    },
    [sendCommand, sendChatMessage, threadId],
  );

  const handleExecuteNode = useCallback(
    (nodeId: string, nodeType: NodeType, description: string, provider?: string, duration?: number, resolution?: string, generateAudio?: boolean) => {
      sendCommand({ type: "execute_node", thread_id: threadId, node_id: nodeId, node_type: nodeType, description, image_gen_provider: provider, duration, resolution, generate_audio: generateAudio });
    },
    [sendCommand, threadId],
  );

  const handleUpdateNodeStatus = useCallback(
    (nodeId: string, nodeStatus: NodeStatus) => {
      queueMicrotask(() => {
        useCanvasStore.setState((state) => ({
          nodes: state.nodes.map((node) => (node.id === nodeId ? { ...node, node_status: nodeStatus } : node)),
        }));
      });
      sendCommand({ type: "update_node_status", thread_id: threadId, node_id: nodeId, node_status: nodeStatus });
    },
    [sendCommand, threadId],
  );

  const handleOptimizePrompt = useCallback(
    (nodeId: string, prompt: string, feedback: string) => {
      sendCommand({ type: "optimize_prompt", thread_id: threadId, node_id: nodeId, prompt, feedback });
    },
    [sendCommand, threadId],
  );

  const handleCreateEdge = useCallback(
    (source: string, target: string) => sendCommand({ type: "create_edge", thread_id: threadId, source, target }),
    [sendCommand, threadId],
  );

  const handleDeleteEdge = useCallback(
    (edgeId: string) => sendCommand({ type: "delete_edge", thread_id: threadId, edge_id: edgeId }),
    [sendCommand, threadId],
  );

  const handleReorderEdge = useCallback(
    (edgeId: string, direction: "up" | "down") => sendCommand({ type: "reorder_edge", thread_id: threadId, edge_id: edgeId, direction }),
    [sendCommand, threadId],
  );

  return useMemo(
    () => ({
      handleReview,
      handleExecuteNode,
      handleUpdateNodeStatus,
      handleOptimizePrompt,
      handleCreateEdge,
      handleDeleteEdge,
      handleReorderEdge,
    }),
    [handleReview, handleExecuteNode, handleUpdateNodeStatus, handleOptimizePrompt, handleCreateEdge, handleDeleteEdge, handleReorderEdge],
  );
}
