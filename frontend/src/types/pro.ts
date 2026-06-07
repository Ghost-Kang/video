/**
 * Pro 高级子画布(ComfyUI 计算图)前端类型 + 节点规格镜像 + WS 帧。
 *
 * 节点规格镜像 PRO_NODE_SPECS 与后端 `backend/src/agent/comfyui/node_registry.py` 一一对应
 * (key / 端口名 / 参数名必须一致 —— 后端 compiler.validate_graph 是真正的校验闸)。前端只多带
 * UI 元信息(颜色/分组)。WS 帧手写在此(同 ws.ts 里 DeleteSessionsMsg 等单命令的先例,不跑 codegen)。
 */

export type ProPortType = "image" | "text" | "model" | "any";

export type ProNodeTypeKey =
  | "Model"
  | "Prompt"
  | "LoadImage"
  | "Anchor"
  | "Generate"
  | "Preview";

export interface ProPort {
  name: string;
  type: ProPortType;
  required?: boolean;
}

export interface ProParamSpec {
  name: string;
  type: "str" | "int" | "float";
  default: string | number;
  label: string;
  choices?: string[];
  min?: number;
  max?: number;
}

export interface ProNodeSpec {
  key: ProNodeTypeKey;
  label: string;
  category: "model" | "prompt" | "input" | "generate" | "output";
  billable: boolean;
  inputs: ProPort[];
  outputs: ProPort[];
  params: ProParamSpec[];
  /** 暖色科技皮:节点强调色(CSS 颜色)。 */
  accent: string;
}

// ── 节点 graph 形状(发后端 / seed 返回) ─────────────────────────────────────────
export interface ProNode {
  id: string;
  type: ProNodeTypeKey;
  params?: Record<string, string | number>;
  cached?: boolean;
  cached_url?: string | null;
  x?: number;
  y?: number;
}

export interface ProEdge {
  id: string;
  source: string;
  sourceHandle: string;
  target: string;
  targetHandle: string;
}

export interface ProGraph {
  version: number;
  nodes: ProNode[];
  edges: ProEdge[];
  workflowId?: string;
  meta?: Record<string, unknown>;
}

export interface ProEstimate {
  billable_node_count: number;
  cached_skipped: number;
  cost_cny: number;
}

// ── WS 帧(手写,加入 ws.ts 的 WSCommand/WSEvent 联合) ───────────────────────────
export interface ProRunSubmitMsg {
  type: "pro_run_submit";
  thread_id: string;
  graph: ProGraph;
  provider?: string | null;
}

export interface ProRunCancelMsg {
  type: "pro_run_cancel";
  thread_id: string;
  run_id: string;
}

export interface ProRunProgressEvent {
  type: "pro_run_progress";
  thread_id: string;
  run_id: string;
  status: string; // queued | submitting | running | cancelled
  pct: number;
}

export interface ProRunNodeDoneEvent {
  type: "pro_run_node_done";
  thread_id: string;
  run_id: string;
  output_url: string;
}

export interface ProRunDoneEvent {
  type: "pro_run_done";
  thread_id: string;
  run_id: string;
  outputs: string[];
}

export interface ProRunFailedEvent {
  type: "pro_run_failed";
  thread_id: string;
  run_id: string;
  error: string;
}

export type ProRunEvent =
  | ProRunProgressEvent
  | ProRunNodeDoneEvent
  | ProRunDoneEvent
  | ProRunFailedEvent;

// ── 节点规格镜像(对齐 node_registry.py) ─────────────────────────────────────────
const CKPT_DEFAULT = "sd_xl_base_1.0.safetensors";

export const PRO_NODE_SPECS: Record<ProNodeTypeKey, ProNodeSpec> = {
  Model: {
    key: "Model",
    label: "模型",
    category: "model",
    billable: false,
    accent: "#7c2d12",
    inputs: [],
    outputs: [{ name: "model", type: "model" }],
    params: [{ name: "ckpt_name", type: "str", default: CKPT_DEFAULT, label: "检查点模型" }],
  },
  Prompt: {
    key: "Prompt",
    label: "提示词",
    category: "prompt",
    billable: false,
    accent: "#0f766e",
    inputs: [],
    outputs: [{ name: "text", type: "text" }],
    params: [
      { name: "text", type: "str", default: "", label: "文本" },
      { name: "role", type: "str", default: "positive", label: "角色", choices: ["positive", "negative"] },
    ],
  },
  LoadImage: {
    key: "LoadImage",
    label: "加载图片",
    category: "input",
    billable: false,
    accent: "#a16207",
    inputs: [],
    outputs: [{ name: "image", type: "image" }],
    params: [{ name: "image_url", type: "str", default: "", label: "图片地址" }],
  },
  Anchor: {
    key: "Anchor",
    label: "锚点",
    category: "input",
    billable: false,
    accent: "#9333ea",
    inputs: [],
    outputs: [{ name: "image", type: "image" }],
    params: [
      { name: "anchor_id", type: "str", default: "", label: "锚点ID" },
      { name: "image_url", type: "str", default: "", label: "图片地址" },
      { name: "label", type: "str", default: "", label: "名称" },
      { name: "kind", type: "str", default: "character", label: "类型", choices: ["character", "scene"] },
    ],
  },
  Generate: {
    key: "Generate",
    label: "生成图像",
    category: "generate",
    billable: true,
    accent: "#c2410c",
    inputs: [
      { name: "model", type: "model", required: true },
      { name: "positive", type: "text", required: true },
      { name: "negative", type: "text", required: false },
      { name: "image", type: "image", required: false },
    ],
    outputs: [{ name: "image", type: "image" }],
    params: [
      { name: "seed", type: "int", default: 0, label: "随机种子", min: 0 },
      { name: "steps", type: "int", default: 20, label: "步数", min: 1, max: 150 },
      { name: "cfg", type: "float", default: 7.0, label: "CFG", min: 0, max: 30 },
      { name: "sampler_name", type: "str", default: "euler", label: "采样器" },
      { name: "scheduler", type: "str", default: "normal", label: "调度器" },
      { name: "denoise", type: "float", default: 1.0, label: "重绘幅度", min: 0, max: 1 },
      { name: "width", type: "int", default: 1024, label: "宽", min: 64, max: 4096 },
      { name: "height", type: "int", default: 1024, label: "高", min: 64, max: 4096 },
    ],
  },
  Preview: {
    key: "Preview",
    label: "预览",
    category: "output",
    billable: false,
    accent: "#1c1917",
    inputs: [{ name: "image", type: "image", required: true }],
    outputs: [],
    params: [],
  },
};

export const PRO_NODE_ORDER: ProNodeTypeKey[] = [
  "Model",
  "Prompt",
  "LoadImage",
  "Anchor",
  "Generate",
  "Preview",
];

/** Pro 级端口类型兼容(MVP 弱校验,与后端 _ports_compatible 同口径)。 */
export function proPortsCompatible(src: ProPortType, dst: ProPortType): boolean {
  return src === dst || src === "any" || dst === "any";
}
