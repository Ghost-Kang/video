import { Zap } from "lucide-react";
import { useWSStore } from "../store/wsStore";

/**
 * Agent 模式 → Pro 高级子画布 的入口(plan §4.1 工具栏 / §6.4 分析卡)。
 * 灰度自门控:仅当后端 session_state.pro_canvas_enabled 为真时显示(flag OFF 零打扰)。
 *
 * 用普通 <a href>(非 router 钩子)—— 进 Pro 画布是一次「模式切换」到一张独立的重页(tldraw
 * 懒加载),整页跳转可接受;且不引入 router context 依赖,使内嵌它的卡片(ViralAnalysisCard /
 * Header)在隔离单测里无需 Router 包裹。threadId 取 wsStore.currentThreadId(当前活动 thread,
 * dispatch 线程守卫的同一真相源)。analysisId 在则附 ?seed=analysis:<id> 让 Pro 画布展开种子图。
 */
interface Props {
  analysisId?: string;
  variant?: "toolbar" | "card";
}

export function ProCanvasEntry({ analysisId, variant = "toolbar" }: Props) {
  const enabled = useWSStore((s) => s.proCanvasEnabled);
  const threadId = useWSStore((s) => s.currentThreadId);

  if (!enabled || !threadId) return null;

  const seed = analysisId ? `?seed=analysis:${encodeURIComponent(analysisId)}` : "";
  const href = `/pro/${encodeURIComponent(threadId)}${seed}`;

  if (variant === "card") {
    return (
      <a
        href={href}
        data-testid="pro-canvas-expand"
        className="group inline-flex shrink-0 items-center gap-1.5 rounded-full border border-stone-200/80 bg-white/50 px-3 py-1.5 text-[12px] font-medium text-stone-600 no-underline backdrop-blur transition-all hover:border-[#7c2d12]/40 hover:text-[#7c2d12] hover:shadow-[0_0_14px_-2px_rgba(234,88,12,0.4)] dark:border-stone-700 dark:bg-stone-900/40 dark:text-stone-300 dark:hover:text-[#ea580c]"
        title="把这条分析展开成一张可编辑的 ComfyUI 计算图,不改也能直接生成"
      >
        <Zap className="h-3.5 w-3.5 group-hover:anim-icon-breathe" />
        展开为计算图
      </a>
    );
  }

  return (
    <a
      href={href}
      data-testid="pro-canvas-entry"
      className="inline-flex items-center gap-1 rounded-md border border-stone-200 px-2 py-0.5 text-[11px] text-stone-500 no-underline transition-colors hover:border-[#7c2d12]/40 hover:text-[#7c2d12] dark:border-stone-700 dark:text-stone-400 dark:hover:text-[#ea580c]"
      title="进入 Pro 高级子画布(用户连线的 ComfyUI 计算图)"
    >
      <Zap className="h-3 w-3" />
      Pro 画布
    </a>
  );
}
