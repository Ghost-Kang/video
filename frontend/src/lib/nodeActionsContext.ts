import { createContext } from "react";
import type { NodeActions } from "../hooks/useNodeActions";

/**
 * 把 useNodeActions(review/execute/updateStatus…)注入画布自定义节点的通道。
 * App 在 Canvas 外层 <NodeActionsContext.Provider value={actions}>;节点上的
 * NodeActionBar(NodeToolbar)useContext 取用 —— 避免 actions 一路 props 钻到每个节点。
 * (单独成文件:fast-refresh 要求 context 与组件分开导出。)
 */
export const NodeActionsContext = createContext<NodeActions | null>(null);
