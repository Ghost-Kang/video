import { useEffect, useRef, useState } from "react";
import { ImageIcon, RefreshCw } from "lucide-react";
import type { RewriteShot } from "../../lib/cascadeMapper";
import { COPY } from "../../lib/cardCopy";
import { CARD_CLASS } from "../../lib/cardStyles";
import { useCanvasStore } from "../../store/canvasStore";

interface Props {
  shot: RewriteShot;
  /** 生成草稿图:发 [generate_first_frame: shot_index=N];Director 用最近 rewrite_id 调工具。
   *  不传 = 不显示草稿图区(灰度关 / 调用方不支持时向后兼容)。 */
  onGenerateFirstFrame?: (shotIndex: number) => void;
}

// 后端没回任何帧时的兜底超时(正常成功/失败都会推 shot_first_frame_returned,即时翻态;
// 这里只防"帧丢了/后端挂了"导致转圈不止)。
const _GEN_TIMEOUT_MS = 75_000;

// 改写后的镜头 — 台词 + 画面描述 + 可选「生成草稿图」(首帧参考)。
// 草稿图四态:IDLE(按钮)/ PENDING(转圈)/ DONE(图)/ FAILED(后端友好提示 + 重试)。
// DONE 由 store.firstFrameUrl 驱动;FAILED 由 store.firstFrameError 驱动(后端即时推,
// 不必等超时);PENDING 是本地瞬态。render 优先级 hasImage > error > generating,故本地
// generating 无需在 effect 里清(被前两者遮蔽),避开 set-state-in-effect。
export function RewriteShotCard({ shot, onGenerateFirstFrame }: Props) {
  const [generating, setGenerating] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const setError = useCanvasStore((s) => s.setRewriteShotFirstFrameError);

  const hasImage = Boolean(shot.firstFrameUrl);
  const error = shot.firstFrameError;

  const clearTimer = () => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  };

  // 帧到了(成功 firstFrameUrl 或失败 firstFrameError)→ 停兜底计时器即可(不 setState:
  // render 已按 hasImage/error 优先,本地 generating 自然失效)。
  useEffect(() => {
    if (shot.firstFrameUrl || shot.firstFrameError) clearTimer();
  }, [shot.firstFrameUrl, shot.firstFrameError]);

  // 卸载清理。
  useEffect(() => () => clearTimer(), []);

  const handleGenerate = () => {
    if (!onGenerateFirstFrame || generating) return;
    setError(shot.shot_index, null); // 清旧错误,让 render 落到 generating
    setGenerating(true);
    onGenerateFirstFrame(shot.shot_index);
    clearTimer();
    timerRef.current = setTimeout(() => {
      setError(shot.shot_index, COPY.shot_draft_timeout);
    }, _GEN_TIMEOUT_MS);
  };

  const btnClass =
    "flex items-center gap-2 rounded-lg bg-white/80 dark:bg-stone-900/60 hover:bg-white dark:hover:bg-stone-900 px-4 py-2 text-sm font-medium text-stone-700 dark:text-stone-200 shadow-sm border border-stone-200 dark:border-stone-700 transition-colors";

  return (
    <section
      className={`${CARD_CLASS} border-l-4 border-l-[#7c2d12] dark:border-l-[#ea580c]`}
      data-testid={`rewrite-shot-card-${shot.shot_index}`}
    >
      {onGenerateFirstFrame && (
        <div className="aspect-video w-full overflow-hidden rounded-xl bg-stone-100 dark:bg-stone-800 mb-3 flex items-center justify-center">
          {hasImage ? (
            <img src={shot.firstFrameUrl} alt="" className="h-full w-full object-cover" />
          ) : error ? (
            <div className="flex flex-col items-center gap-2 px-4 text-center">
              <p className="text-xs text-stone-500 dark:text-stone-400">{error}</p>
              <button
                type="button"
                onClick={handleGenerate}
                className={btnClass}
                data-testid={`rewrite-shot-card-${shot.shot_index}-retry`}
              >
                <RefreshCw className="h-4 w-4" aria-hidden />
                {COPY.shot_draft_retry}
              </button>
            </div>
          ) : generating ? (
            <div className="flex flex-col items-center gap-2 text-stone-500 dark:text-stone-400">
              <div
                className="h-6 w-6 animate-spin rounded-full border-2 border-stone-300 border-t-[#7c2d12] dark:border-t-[#ea580c]"
                aria-hidden
              />
              <span className="text-sm">{COPY.shot_draft_generating}</span>
            </div>
          ) : (
            <button
              type="button"
              onClick={handleGenerate}
              className={btnClass}
              data-testid={`rewrite-shot-card-${shot.shot_index}-generate`}
            >
              <ImageIcon className="h-4 w-4" aria-hidden />
              {COPY.shot_draft_generate}
            </button>
          )}
        </div>
      )}

      <h3 className="text-base font-medium text-stone-900 dark:text-stone-50 mb-2">
        {COPY.shot_label_prefix}
        {shot.shot_index}
        {COPY.shot_label_suffix}
      </h3>
      <p className="text-[15px] leading-[1.65] text-stone-800 dark:text-stone-200 mb-2">
        {shot.dialogue.trim() || COPY.shot_dialogue_placeholder}
      </p>
      <p className="text-sm text-stone-500 dark:text-stone-400">{shot.visual}</p>
    </section>
  );
}
