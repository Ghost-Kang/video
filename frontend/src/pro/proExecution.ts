/**
 * Pro 画布执行接线:估算(HTTP)/ 种子图(HTTP)/ 提交命令(WS)。
 * 执行在后端 ComfyUI,前端只「序列化图 + 发送 + 渲染进度/结果」(plan §4.2,比纯前端 pipeline 更薄)。
 */

import { apiFetch } from "../lib/apiClient";
import type { ProEstimate, ProGraph, ProRunCancelMsg, ProRunSubmitMsg } from "../types/pro";

export class ProApiError extends Error {
  code: string;
  detail?: string;
  constructor(code: string, detail?: string) {
    super(detail ? `${code}: ${detail}` : code);
    this.code = code;
    this.detail = detail;
  }
}

const PRO_ERROR_TITLES: Record<string, string> = {
  pro_canvas_disabled: "Pro 画布未开启",
  graph_required: "请先搭一张图",
  empty_graph: "图是空的",
  no_output: "缺少预览节点(Preview)",
  missing_required_input: "有节点缺必填输入",
  port_type_mismatch: "连线类型不兼容",
  multi_input: "一个输入口被连了多次",
  cycle: "图里有环(必须是 DAG)",
  unknown_node_type: "未知节点类型",
  duplicate_node_id: "节点 id 重复",
  analysis_id_required: "缺少分析 ID",
  analysis_not_found: "找不到对应分析",
};

export function proErrorTitle(code: string): string {
  return PRO_ERROR_TITLES[code] || "操作失败";
}

async function readError(res: Response): Promise<ProApiError> {
  let code = `http_${res.status}`;
  let detail: string | undefined;
  try {
    const data = await res.json();
    if (data && typeof data === "object") {
      code = (data.error as string) || code;
      detail = (data.message as string) || undefined;
    }
  } catch {
    /* non-json body */
  }
  return new ProApiError(code, detail);
}

/** 当前匿名身份(与 WS auth 同源:localStorage.rhtv_user)。
 * 2026-06-10 审计:pro HTTP 端点身份从 body/qs 取,前端此前从不传 → 服务端全部
 * 归因 "default"(pro_seeded 遥测失真 / 成片库全用户混库 / theme 成本闸池化)。
 * 所有 pro API 调用统一带上;per-user mapped 邀请码场景 dispatcher 仍会用
 * server-derived 身份覆盖 body.user_id(http_router 鉴权 A),此处不降低安全性。 */
function proUid(): string {
  try {
    return window.localStorage.getItem("rhtv_user") || "default";
  } catch {
    return "default";
  }
}

/** POST /api/pro/estimate → 整图成本估算(Run 前确认弹窗)。不花钱。 */
export async function estimateGraph(graph: ProGraph): Promise<ProEstimate> {
  const res = await apiFetch("/api/pro/estimate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ graph, user_id: proUid() }),
  });
  if (!res.ok) throw await readError(res);
  return res.json();
}

/** POST /api/pro/seed → 分析+改写+锚点 → 开箱可跑创作图。 */
export async function fetchSeedGraph(analysisId: string, threadId: string): Promise<ProGraph> {
  const res = await apiFetch("/api/pro/seed", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ analysis_id: analysisId, thread_id: threadId, user_id: proUid() }),
  });
  if (!res.ok) throw await readError(res);
  const data = await res.json();
  return data.graph as ProGraph;
}

/** 自动种子:只给 thread,后端从 session pointers 解析分析;无分析 → null(前端显示主题输入框)。 */
export async function seedFromThread(threadId: string): Promise<ProGraph | null> {
  try {
    const res = await apiFetch("/api/pro/seed", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ thread_id: threadId, user_id: proUid() }),
    });
    if (!res.ok) return null;
    return ((await res.json()).graph as ProGraph | null) ?? null;
  } catch {
    return null;
  }
}

/** 主题 → Doubao 脚本+分镜 → 创作图(空白入口)。 */
export async function seedFromTheme(theme: string, threadId: string): Promise<ProGraph> {
  const res = await apiFetch("/api/pro/seed_from_theme", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ theme, thread_id: threadId, user_id: proUid() }),
  });
  if (!res.ok) throw await readError(res);
  return (await res.json()).graph as ProGraph;
}

/** 脚本卡重生:编辑后的脚本 → Doubao 重拆分镜 → 创作图(替换画布)。 */
export async function regenFromScript(script: string, threadId: string): Promise<ProGraph> {
  const res = await apiFetch("/api/pro/regen_from_script", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ script, thread_id: threadId, user_id: proUid() }),
  });
  if (!res.ok) throw await readError(res);
  return (await res.json()).graph as ProGraph;
}

export function buildSubmitCommand(threadId: string, graph: ProGraph, provider?: string | null): ProRunSubmitMsg {
  return { type: "pro_run_submit", thread_id: threadId, graph, ...(provider ? { provider } : {}) };
}

export function buildCancelCommand(threadId: string, runId: string): ProRunCancelMsg {
  return { type: "pro_run_cancel", thread_id: threadId, run_id: runId };
}

// ── 持久化:当前图 autosave + 模板 ───────────────────────────────────────────────

export interface ProTemplateMeta {
  template_id: string;
  name: string;
  created_at: string;
}

/** 自动保存当前图(best-effort,失败不抛 —— 不打扰编辑)。 */
export async function saveGraph(threadId: string, graph: ProGraph): Promise<void> {
  try {
    await apiFetch("/api/pro/graph", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ thread_id: threadId, graph, user_id: proUid() }),
    });
  } catch {
    /* autosave 失败静默 */
  }
}

/** 恢复该 thread 上次保存的图;无/失败 → null(不阻断挂载)。 */
export async function loadSavedGraph(threadId: string): Promise<ProGraph | null> {
  try {
    const res = await apiFetch(`/api/pro/graph?thread_id=${encodeURIComponent(threadId)}&user_id=${encodeURIComponent(proUid())}`);
    if (!res.ok) return null;
    const data = await res.json();
    return (data.graph as ProGraph | null) ?? null;
  } catch {
    return null;
  }
}

export async function listTemplates(): Promise<ProTemplateMeta[]> {
  try {
    const res = await apiFetch("/api/pro/templates");
    if (!res.ok) return [];
    const data = await res.json();
    return (data.templates as ProTemplateMeta[]) ?? [];
  } catch {
    return [];
  }
}

export async function saveTemplate(name: string, graph: ProGraph): Promise<ProTemplateMeta> {
  const res = await apiFetch("/api/pro/template", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, graph, user_id: proUid() }),
  });
  if (!res.ok) throw await readError(res);
  return res.json();
}

export async function loadTemplate(templateId: string): Promise<ProGraph> {
  const res = await apiFetch(`/api/pro/template?id=${encodeURIComponent(templateId)}`);
  if (!res.ok) throw await readError(res);
  const data = await res.json();
  return data.graph as ProGraph;
}

export async function deleteTemplate(templateId: string): Promise<void> {
  await apiFetch("/api/pro/template/delete", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ template_id: templateId, user_id: proUid() }),
  });
}

// ── 我的成片库 ───────────────────────────────────────────────────────────────────

export interface ProFilm {
  film_id: string;
  video_url: string;
  title: string;
  thread_id: string;
  created_at: string;
}

export async function saveFilm(videoUrl: string, threadId: string, title = ""): Promise<ProFilm> {
  const res = await apiFetch("/api/pro/film", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ video_url: videoUrl, thread_id: threadId, title, user_id: proUid() }),
  });
  if (!res.ok) throw await readError(res);
  return res.json();
}

export async function listFilms(): Promise<ProFilm[]> {
  try {
    const res = await apiFetch(`/api/pro/films?user_id=${encodeURIComponent(proUid())}`);
    if (!res.ok) return [];
    return ((await res.json()).films as ProFilm[]) ?? [];
  } catch {
    return [];
  }
}

export async function deleteFilm(filmId: string): Promise<void> {
  await apiFetch("/api/pro/film/delete", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ film_id: filmId }),
  });
}
