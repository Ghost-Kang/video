import { create } from "zustand";
import { useCanvasStore } from "./canvasStore";
import { useReviewStore } from "./reviewStore";
import { useSessionStore } from "./sessionStore";
import { useToastStore, type ToastAction } from "./toastStore";
import type { WSEvent } from "../types/ws";
import { mapRewriteShotsToScenes } from "../lib/cascadeMapper";
import { deriveSessionMeta } from "../lib/sessionTitle";
import { COPY } from "../lib/cardCopy";
import type { FailurePayload } from "../types/cascade";

// W5D3 P2 — runtime guard for the analysis_failed payload.
// Backend Pydantic typing is wider than the frontend FailurePayload union
// (the WS contract uses `str`, not an enum). If the backend ever ships a new
// code the frontend doesn't know about, we map it to a stable fallback.
const KNOWN_CODES: ReadonlySet<FailurePayload["code"]> = new Set([
  "S1_NO_SOURCE_URL",
  "S2_VERSION_MISMATCH",
  "S3_NO_FORMULA",
  "S4_SCENES_LEN_OUT_OF_RANGE",
  "S5_INVALID_PAYLOAD",
  "S6_NEGATIVE_COST",
  "S7_UPSTREAM_TIMEOUT",
  "S8_UPSTREAM_REFUSED",
  "S11_INTERNAL_ERROR",
] satisfies FailurePayload["code"][]);

const KNOWN_ACTIONS: ReadonlySet<FailurePayload["actions"][number]> = new Set([
  "RETRY_SAME_URL",
  "RETRY_SAME_URL_AFTER_30S",
  "RETRY_SAME_URL_AFTER_60S",
  "RETRY_WITH_NEW_URL",
  "PICK_FROM_FEATURED",
  "RELOAD",
  "REPORT",
] satisfies FailurePayload["actions"][number][]);

// W5D3 — sentinel for client-synthesized failures (NOT for UI display).
// Diagnostics chip checks `request_id === CLIENT_SYNTH_REQUEST_ID` and renders
// "client-synth" instead of the raw value, so this string never leaks visually
// while still allowing dev tools / event correlation to distinguish client
// fallback from a real backend failure (which always has a real hex request_id).
export const CLIENT_SYNTH_REQUEST_ID = "__client_synth__";

// W5D4 P1 — client-side timeout failure. Used ONLY when the *client* decides a
// run took too long (App.tsx 300s safety timer, AnalysisProgress hard-timeout,
// or the user's "换一条" pin-escape) — never to parse backend content. The old
// `synthesizeFailureFromContent` regex-matched agent_response text ("处理出错"
// etc.) and falsely flipped legitimate answers to `failed`; with P0-A delivering
// structured analysis_failed frames reliably + P0-B persisting failure for
// replay, that heuristic is gone. This is a plain literal, no content parsing.
export function synthesizeClientTimeout(): FailurePayload {
  return {
    code: "S7_UPSTREAM_TIMEOUT",
    hint: COPY.synth_failure_timeout_hint,
    actions: ["RETRY_SAME_URL_AFTER_60S", "PICK_FROM_FEATURED"],
    request_id: CLIENT_SYNTH_REQUEST_ID,
  };
}

// W5D3/W5D4 — coerce a backend failure (analysis_failed frame OR session_state
// resume) into a frontend-safe FailurePayload. The WS contract types code/actions
// as plain strings; map anything the union doesn't know to a stable fallback so a
// newly-shipped backend code never renders an undefined hint title.
export function normalizeFailurePayload(
  code: string,
  hint: string,
  actions: readonly string[] | undefined,
  request_id: string | undefined,
): FailurePayload {
  const normalizedCode: FailurePayload["code"] = KNOWN_CODES.has(
    code as FailurePayload["code"],
  )
    ? (code as FailurePayload["code"])
    : "S5_INVALID_PAYLOAD";
  const normalizedActions: FailurePayload["actions"] = (actions || []).filter(
    (a): a is FailurePayload["actions"][number] =>
      KNOWN_ACTIONS.has(a as FailurePayload["actions"][number]),
  );
  return {
    code: normalizedCode,
    hint,
    actions: normalizedActions.length > 0 ? normalizedActions : ["REPORT"],
    request_id: request_id || "",
  };
}


// 把后端 invalid_command code 映射成用户看得懂的中文标题。
// 未列的 code 一律 fallback 到通用 "请求出错"。
const ERROR_CODE_TITLES: Record<string, string> = {
  invalid_command: "请求格式不对",
  malformed_json: "数据格式不对",
  // P2 — backend refused a new message while a review gate is pending.
  review_pending: "先确认这一步生成",
};

const TOOL_LABELS: Record<string, string> = {
  script_writer: "🍳 在写开头脚本…",
  image_generate: "✨ 在生成画面参考…",
  analyze_source: "🔍 在拆解视频…",
  request_shallow_analysis: "🔍 在拆解视频…",
  rewrite_to_niche: "📝 在改写成你的版本…",
  storyboard: "🎬 在排分镜…",
  publish_pack: "📦 在准备发布包…",
};

function labelToolCall(name: string | undefined): string {
  if (!name) return "✨ 整理中…";
  return TOOL_LABELS[name] || "✨ 整理中…";
}

interface ConnectionStatus {
  connected?: boolean;
  connecting?: boolean;
  reconnectAttempt?: number;
}

interface WSStore {
  currentThreadId: string;
  thinking: string[];
  loading: boolean;
  // W4D5-T1: WS 连接状态共享给根级 <ConnectionBanner/>。useWebSocket 是 App
  // 内部 hook,banner 是全局组件,中间靠 store 解耦。
  connected: boolean;
  connecting: boolean;
  reconnectAttempt: number;
  lastAnswerAt: number | null;
  lastAnswerSnippet: string | null;
  // W5D3-T1 — real progress from backend `analysis_progress` WS frame.
  // Null = no event yet,前端 fall back to time-based ramp。
  progressStage: string | null;
  progressPercent: number | null;
  progressEta: number | null;
  progressDetail: string;
  // W5D4 P0-C — frames whose thread_id != currentThreadId are BUFFERED here
  // (per thread, bounded) instead of being silently dropped. Drained in order
  // when the user switches to that thread (setCurrentThreadId). This makes a
  // mid-run redirect/session-switch survivable: the running thread's frames are
  // kept, not lost, even before P0-A guarantees they keep arriving server-side.
  pendingByThread: Record<string, WSEvent[]>;
  setCurrentThreadId: (threadId: string) => void;
  setLoading: (loading: boolean) => void;
  resetThinking: () => void;
  setConnectionStatus: (status: ConnectionStatus) => void;
  dispatch: (event: WSEvent, userId: string) => void;
}

export const useWSStore = create<WSStore>((set, get) => ({
  currentThreadId: "",
  thinking: [],
  loading: false,
  connected: false,
  connecting: false,
  reconnectAttempt: 0,
  lastAnswerAt: null,
  lastAnswerSnippet: null,
  progressStage: null,
  progressPercent: null,
  progressEta: null,
  progressDetail: "",
  pendingByThread: {},

  setCurrentThreadId: (threadId) => {
    set({ currentThreadId: threadId });
    // W5D4 P0-C — drain any frames buffered while this thread wasn't current,
    // in arrival order, then clear the bucket. Re-dispatch runs them through the
    // normal reducer now that the guard will accept them (rid === currentThreadId).
    const buffered = get().pendingByThread[threadId];
    if (buffered && buffered.length) {
      set((s) => {
        const next = { ...s.pendingByThread };
        delete next[threadId];
        return { pendingByThread: next };
      });
      const userId = useSessionStore.getState().userId;
      for (const ev of buffered) get().dispatch(ev, userId);
    }
  },
  setLoading: (loading) => {
    // W5D3 Bug #1: starting a new run must reset stale progress state
    // from prior analysis (else AnalysisProgress paints 100% instantly).
    if (loading) {
      set({
        loading: true,
        progressStage: null,
        progressPercent: null,
        progressEta: null,
        progressDetail: "",
      });
    } else {
      set({ loading: false });
    }
  },
  resetThinking: () => set({ thinking: [] }),
  setConnectionStatus: (status) =>
    set((state) => ({
      connected: status.connected ?? state.connected,
      connecting: status.connecting ?? state.connecting,
      reconnectAttempt: status.reconnectAttempt ?? state.reconnectAttempt,
    })),

  dispatch: (event, userId) => {
    const canvas = useCanvasStore.getState();
    const sessions = useSessionStore.getState();

    if (event.type === "session_list") {
      const backendIds = event.sessions.map((s) => s.thread_id);
      // W5D4 — UNION, don't overwrite. The backend list only contains sessions
      // that already have persisted messages. A session the user JUST created
      // (landing → 拆解) has no messages yet, so it's absent from this list.
      // Overwriting `sessions` with the backend list dropped it, and App's
      // redirect effect then navigated away to sessions[0] — mid-run — which
      // changed currentThreadId and made the dispatch thread-guard discard all
      // of the running session's analysis_progress/analysis_returned frames
      // (symptom: 拆解中界面完全空白). Merge so locally-known sessions survive;
      // backend order leads (most-recent-active first), local-only ones append.
      //
      // setUserId first — it hydrates `sessions` from this user's localStorage
      // (which addSession already persisted) — then re-read fresh state so the
      // union sees the just-created session regardless of hydrate timing.
      sessions.setUserId(userId);
      const fresh = useSessionStore.getState();
      const localOnly = fresh.sessions.filter((id) => !backendIds.includes(id));
      const ids = [...backendIds, ...localOnly];
      // Preserve any local names we already had for these threads.
      const mergedNames: Record<string, string> = {};
      for (const id of ids) {
        if (fresh.names[id]) mergedNames[id] = fresh.names[id];
      }
      fresh.setSessions(ids);
      fresh.setNames(mergedNames);
      return;
    }

    const rid = "thread_id" in event ? event.thread_id : undefined;
    if (rid && rid !== get().currentThreadId) {
      // W5D4 P0-C — buffer (don't drop) frames for a non-current thread. A
      // mid-run redirect/session-switch used to silently discard the running
      // thread's analysis_progress/analysis_returned here → blank/卡死. Keep them
      // bounded per thread (drop-oldest past cap) and replay on switch.
      const CAP = 200;
      set((s) => {
        const bucket = s.pendingByThread[rid] ?? [];
        const nextBucket = bucket.length >= CAP ? [...bucket.slice(1), event] : [...bucket, event];
        return { pendingByThread: { ...s.pendingByThread, [rid]: nextBucket } };
      });
      return;
    }

    switch (event.type) {
      case "agent_response": {
        // W5D4 P1 — the old content-regex heuristic (flip to `failed` when the
        // reply text contained "请求超时/处理出错/系统暂时繁忙") is GONE. It
        // false-positived on legitimate answers mentioning those words. The
        // backend now delivers a structured `analysis_failed` frame for every
        // terminal failure (via the live registry, P0-A) and persists it for
        // replay (run_lifecycle, P0-B), so agent_response is always a success.
        set({ loading: false, thinking: [] });
        const last = get();
        if (
          last.lastAnswerAt !== null &&
          Date.now() - last.lastAnswerAt < 5000 &&
          last.lastAnswerSnippet &&
          event.content.startsWith(last.lastAnswerSnippet)
        ) {
          set({ lastAnswerAt: null, lastAnswerSnippet: null });
          useCanvasStore.setState({ streamingContent: "" });
          if (event.canvas) queueMicrotask(() => canvas.setCanvas(event.canvas!));
          break;
        }
        canvas.finalizeStreaming(event.content);
        if (event.canvas) queueMicrotask(() => canvas.setCanvas(event.canvas!));
        break;
      }
      case "canvas_updated":
        if (event.canvas) queueMicrotask(() => canvas.setCanvas(event.canvas!));
        break;
      case "node_versions_returned":
        // time-travel 回溯(P2 slice-2b)— 缓存该节点的版本快照,供 NodeVersionHistory 对比。
        queueMicrotask(() => canvas.setNodeVersions(event.node_id, event.versions));
        break;
      case "processing":
        break;
      case "session_state": {
        canvas.setMessages(event.messages);
        if (event.canvas) queueMicrotask(() => canvas.setCanvas(event.canvas!));
        // W5D4 — resume terminal run state on reconnect. Without this, a run
        // whose terminal frame (agent_response / analysis_failed) was lost to a
        // mid-run disconnect leaves the dock spinning at 95% forever.
        // run_status: "running" | "done" | "failed" | "idle" | "awaiting_review".
        const rs = event.run_status;
        // P2 — drop a stale review card if this thread is no longer awaiting
        // review (resolved on another tab, or reloaded after deciding). When it
        // IS awaiting_review, the backend re-pushes review_required right after
        // this frame, so reviewStore gets repopulated.
        if (rs !== "awaiting_review") {
          const rv = useReviewStore.getState();
          if (rv.pending?.threadId === event.thread_id) rv.clear();
        }
        if (rs === "failed" && event.failure) {
          const f = event.failure;
          set({ loading: false, thinking: [] });
          queueMicrotask(() => {
            useCanvasStore
              .getState()
              .setFailure(
                normalizeFailurePayload(f.code, f.hint, f.actions, f.request_id),
              );
            useCanvasStore.setState({ streamingContent: "" });
          });
        } else if (rs && rs !== "running" && rs !== "idle") {
          // done / failed / stale / awaiting_review — a genuine server-side
          // outcome; stop any orphaned spinner.
          //
          // NOT "idle": "idle" only means "no run row on the server". For a
          // freshly-created session (landing → 点案例 → /chat/<sid>?source_url=),
          // App mount fires get_session_state AND auto-sends the analysis. The
          // server answers get_session_state "idle" right BEFORE the auto-sent
          // run registers as "running"; clearing loading on that stale "idle"
          // collapsed AnalyzingHero back to the静态 idle 卡 mid-analysis (founder
          // 实测:点案例后无进度、卡静态、最终 S7 超时). "idle" can't distinguish
          // "never ran" from "client just started one" — so leave loading as-is;
          // the real terminal frames (analysis_returned / analysis_failed /
          // agent_response) own the spinner. A truly orphaned idle spinner is
          // still bounded by the 300s client timeout in App.sendChatMessage.
          set({ loading: false, thinking: [] });
        }
        break;
      }
      case "agent_stream":
        if (event.event === "tool_call") {
          set((state) => ({ thinking: [...state.thinking, labelToolCall(event.name ?? undefined)] }));
        } else if (event.event === "text" && event.content) {
          canvas.appendStreaming(event.content);
        }
        break;
      case "analysis_returned":
        // cascade_analyze tool 完成 → 装上分析卡 + 清 loading 让 ChatPanel
        // 切到 ready 状态。W5D3 bug: 之前没清 loading,dock 永远卡 95%
        // 进度条 + pin escape 误触发。
        set({
          loading: false,
          thinking: [],
          progressStage: "done",
          progressPercent: 100,
          progressEta: 0,
          progressDetail: "",
        });
        queueMicrotask(() => {
          useCanvasStore.getState().loadFromAnalysis(event.analysis);
          // Auto-name the history entry from the analysis so the sidebar shows
          // a meaningful title (主题 + 平台·时间) instead of "新会话". User
          // renames still win — sessionDisplayName prefers `names` over `meta`.
          const tid =
            ("thread_id" in event && event.thread_id) || get().currentThreadId;
          if (tid) {
            useSessionStore.getState().setMeta(tid, deriveSessionMeta(event.analysis));
          }
        });
        break;
      case "rewrite_returned":
        // cascade_rewrite 完成 → 只替换改写结果,保留源视频每一幕。
        // W5D3 Bug #3: 清 loading + progress, 否则 ChatPanel 卡 running
        // (loading > refine 优先级), AnalysisProgress 用 stale 100%
        // 触发 pin escape 误报。
        set({
          loading: false,
          thinking: [],
          progressStage: null,
          progressPercent: null,
          progressEta: null,
          progressDetail: "",
        });
        queueMicrotask(() => {
          const { setScript, setRewriteShots } = useCanvasStore.getState();
          setScript(event.rewrite.script_markdown);
          setRewriteShots(mapRewriteShotsToScenes(event.rewrite.shots));
        });
        break;
      case "shot_first_frame_returned":
        // 单镜首帧返回(成功带 image_url / 失败带 error)→ 打到对应 shot_index 的改写镜头。
        // error 让该镜头即时翻到「失败/重试」,不必等前端 75s 超时。成功兼容旧源镜头 ShotCard。
        queueMicrotask(() => {
          const cs = useCanvasStore.getState();
          if (event.error) {
            cs.setRewriteShotFirstFrameError(event.shot_index, event.error);
          } else if (event.image_url) {
            cs.updateRewriteShotFirstFrame(event.shot_index, event.image_url);
            cs.updateShotFirstFrame(event.shot_index, event.image_url);
          }
        });
        break;
      case "shot_video_returned":
        // 图生视频(后台几分钟后)→ 成功打 videoUrl,失败打 videoError(即时翻态)。
        queueMicrotask(() => {
          const cs = useCanvasStore.getState();
          if (event.error) cs.setRewriteShotVideoError(event.shot_index, event.error);
          else if (event.video_url) cs.setRewriteShotVideo(event.shot_index, event.video_url);
        });
        break;
      case "film_returned":
        // 合成整片(后台)→ 成功打 filmUrl,失败打 filmError。
        queueMicrotask(() => {
          const cs = useCanvasStore.getState();
          if (event.error) cs.setFilmError(event.error);
          else if (event.film_url) cs.setFilm(event.film_url);
        });
        break;
      case "analysis_answer_returned":
        canvas.addMessage("agent", event.answer);
        set({
          loading: false,
          thinking: [],
          lastAnswerAt: Date.now(),
          lastAnswerSnippet: event.answer.slice(0, 50),
        });
        break;
      case "analysis_progress":
        // W5D3-T1 — replaces fake progress estimation in AnalysisProgress.
        // backend pushes 4 stages: resolve_url (5%) → ark_overlay (15→85%)
        // → transcribe (90% — currently not emitted by doubao_direct path,
        // reserved) → done (100%). When stage="done", clear loading so the
        // pin escape doesn't fire.
        set({
          progressStage: event.stage,
          progressPercent: event.percent,
          progressEta: event.eta_seconds,
          progressDetail: event.detail,
        });
        break;
      case "analysis_failed":
        // W5D3 Risk 1 fix — structured failure push (replaces fragile
        // chat-message heuristic). Backend agent_runner pushes this in
        // exception handler with code + hint + actions + request_id.
        // ChatPanel's `failed` state derives from canvasStore.failure being
        // non-null,so this drives the UI directly without keyword matching.
        set({ loading: false, thinking: [] });
        queueMicrotask(() => {
          // W5D3 P2 / W5D4 — runtime-validate code/actions before downcasting
          // (the WS contract types them as plain strings). Shared with the
          // session_state reconnect resume via normalizeFailurePayload.
          useCanvasStore
            .getState()
            .setFailure(
              normalizeFailurePayload(
                event.code,
                event.hint,
                event.actions,
                event.request_id,
              ),
            );
          // Clear any in-flight streaming so it doesn't visually compete
          // with the failure banner.
          useCanvasStore.setState({ streamingContent: "" });
        });
        break;
      case "review_required":
        // P2 审核闸门 — Director 自主生成被 LangGraph interrupt 拦下,弹审核卡。
        // 清掉 loading/thinking(回合没结束但在等用户,spinner 该停),把卡交给
        // reviewStore;<ReviewGate/> 渲染 approve/reject。显式点生成不会走到这里
        // (后端自动批准),所以出现这帧 = Director 真的想自主烧钱,需用户拍板。
        set({ loading: false, thinking: [] });
        useReviewStore.getState().setPending({
          threadId: event.thread_id,
          reviews: event.reviews,
          summary: event.summary,
          interruptId: event.interrupt_id,
        });
        break;
      case "prompt_optimized":
        queueMicrotask(() => {
          useCanvasStore.setState((state) => ({
            nodes: state.nodes.map((node) =>
              node.id === event.node_id ? { ...node, description: event.optimized_prompt } : node
            ),
          }));
        });
        break;
      case "error": {
        // 仍保留 console 给开发期 debug。
        console.warn("[WS] error", event.code, event.message, event.bad_type);
        // 推到 toast 让用户实际看到 — 不然 Pydantic 校验失败完全静默。
        const title = ERROR_CODE_TITLES[event.code] ?? "请求出错";
        // body 用 bad_type 给开发者线索;不暴露 Pydantic 详细 message(那对用户无意义)。
        const body = event.bad_type ? `操作:${event.bad_type}` : undefined;

        // W4D5-T2 — 已知可一键恢复的 case 注入 action,其他不给(避免误导)。
        // - malformed_json: 多半是 JS 端序列化坏掉,reload 重置整个会话状态最简单。
        // - invalid_command: Pydantic 校验失败,用户没法主动恢复(是开发期 bug)。
        let action: ToastAction | undefined;
        if (event.code === "malformed_json") {
          action = {
            label: "刷新页面",
            onClick: () => window.location.reload(),
          };
        }

        useToastStore.getState().push({ kind: "error", title, body, action });
        break;
      }
    }
  },
}));
