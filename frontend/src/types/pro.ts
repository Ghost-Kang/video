/**
 * Pro 高级子画布(ComfyUI 计算图)前端类型 + 节点规格镜像 + WS 帧。
 *
 * 节点规格镜像 PRO_NODE_SPECS 与后端 `backend/src/agent/comfyui/node_registry.py` 一一对应
 * (key / 端口名 / 参数名必须一致 —— 后端 compiler.validate_graph 是真正的校验闸)。前端只多带
 * UI 元信息(颜色/分组)。WS 帧手写在此(同 ws.ts 里 DeleteSessionsMsg 等单命令的先例,不跑 codegen)。
 */

export type ProPortType = "image" | "text" | "model" | "video" | "any";

export type ProNodeTypeKey =
  | "Model"
  | "Prompt"
  | "LoadImage"
  | "Anchor"
  | "Generate"
  | "Upscale"
  | "Video"
  | "Script"
  | "Compose"
  | "Preview";

export interface ProPort {
  name: string;
  type: ProPortType;
  required?: boolean;
  /** 多输入端口(如 Compose.videos):可接多条连线。 */
  multi?: boolean;
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
  category: "model" | "prompt" | "input" | "generate" | "output" | "script";
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
  /** 实例标签(如「镜1·画面」),卡片头部 badge 显示。 */
  label?: string;
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
      { name: "backend", type: "str", default: "境内", label: "执行后端", choices: ["境内", "ComfyUI"] },
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
  Upscale: {
    key: "Upscale",
    label: "放大",
    category: "generate",
    billable: false,
    accent: "#0369a1",
    inputs: [{ name: "image", type: "image", required: true }],
    outputs: [{ name: "image", type: "image" }],
    params: [
      { name: "upscale_method", type: "str", default: "lanczos", label: "插值", choices: ["nearest-exact", "bilinear", "area", "bicubic", "lanczos"] },
      { name: "scale_by", type: "float", default: 2.0, label: "倍数", min: 1.0, max: 8.0 },
    ],
  },
  Video: {
    key: "Video",
    label: "生成视频",
    category: "generate",
    billable: true,
    accent: "#be185d",
    inputs: [{ name: "image", type: "image", required: true }],
    outputs: [{ name: "video", type: "video" }],
    params: [
      { name: "backend", type: "str", default: "境内", label: "执行后端", choices: ["境内", "ComfyUI"] },
      { name: "duration", type: "int", default: 5, label: "时长(秒)", min: 1, max: 10 },
      { name: "fps", type: "int", default: 8, label: "帧率", min: 1, max: 30 },
      { name: "motion", type: "int", default: 127, label: "运动强度", min: 0, max: 255 },
      { name: "video_ckpt", type: "str", default: "svd_xt.safetensors", label: "视频模型" },
    ],
  },
  Script: {
    key: "Script",
    label: "脚本",
    category: "script",
    billable: false,
    accent: "#475569",
    inputs: [],
    outputs: [],
    params: [
      { name: "theme", type: "str", default: "", label: "主题" },
      { name: "script_markdown", type: "str", default: "", label: "脚本" },
    ],
  },
  Compose: {
    key: "Compose",
    label: "合成成片",
    category: "output",
    billable: false,
    accent: "#9333ea",
    // videos 多输入:收所有分镜视频 → ffmpeg 拼接成片(境内执行)。
    inputs: [{ name: "videos", type: "video", required: true, multi: true }],
    outputs: [{ name: "video", type: "video" }],
    params: [],
  },
  Preview: {
    key: "Preview",
    label: "预览",
    category: "output",
    billable: false,
    accent: "#1c1917",
    // ANY 以同时接 image / video(与后端 node_registry 对齐)。
    inputs: [{ name: "image", type: "any", required: true }],
    outputs: [],
    params: [],
  },
};

export const PRO_NODE_ORDER: ProNodeTypeKey[] = [
  "Script",
  "Prompt",
  "LoadImage",
  "Anchor",
  "Generate",
  "Video",
  "Upscale",
  "Compose",
  "Preview",
  "Model",
];

/** Pro 级端口类型兼容(MVP 弱校验,与后端 _ports_compatible 同口径)。 */
export function proPortsCompatible(src: ProPortType, dst: ProPortType): boolean {
  return src === dst || src === "any" || dst === "any";
}
