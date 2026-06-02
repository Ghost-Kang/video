import { useEffect, useRef, useState } from "react";
import { ImageIcon, RefreshCw } from "lucide-react";
import type { RewriteShot } from "../../lib/cascadeMapper";
import { COPY } from "../../lib/cardCopy";
import { CARD_CLASS } from "../../lib/cardStyles";

interface Props {
  shot: RewriteShot;
  /** 生成草稿图:发 [generate_first_frame: shot_index=N];Director 用最近 rewrite_id 调工具。
   *  不传 = 不显示草稿图区(灰度关 / 调用方不支持时向后兼容)。 */
  onGenerateFirstFrame?: (shotIndex: number) => void;
}

// 生成草稿图等待上限。后端是一次工具调用(provider 内部 submit+poll),前端不轮询;
// 超时仍无图 → 判 FAILED 给重试入口(后端真失败也会在 chat 提示)。
const _GEN_TIMEOUT_MS = 75_000;

// 改写后的镜头 — 台词 + 画面描述 + 可选「生成草稿图」(首帧参考)。
// 草稿图四态:IDLE(按钮)/ PENDING(转圈)/ DONE(图)/ FAILED(重试)。
// DONE 由 store 的 shot.firstFrameUrl 驱动(WS 帧 shot_first_frame_returned 打进来);
// PENDING/FAILED 是组件本地瞬态。左竖条橙色 = 这是用户的版本草稿,不是源数据。
export function RewriteShotCard({ shot, onGenerateFirstFrame }: Props) {
  const [generating, setGenerating] = useState(false);
  const [failed, setFailed] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const hasImage = Boolean(shot.firstFrameUrl);

  // 图到了(WS 帧 → store.firstFrameUrl)→ 停计时器即可。不在此 setState:render 已按
  // hasImage 优先(有图就显示图,本地 generating/failed 自然失效),无需同步本地态
  // (React「you might not need an effect」)。
  useEffect(() => {
    if (shot.firstFrameUrl && timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, [shot.firstFrameUrl]);

  // 卸载清理计时器(防泄漏)。
  useEffect(
    () => () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    },
    []
  );

  const handleGenerate = () => {
    if (!onGenerateFirstFrame || generating) return;
    setFailed(false);
    setGenerating(true);
    onGenerateFirstFrame(shot.shot_index);
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      setGenerating(false);
      setFailed(true);
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
          ) : generating ? (
            <div className="flex flex-col items-center gap-2 text-stone-500 dark:text-stone-400">
              <div
                className="h-6 w-6 animate-spin rounded-full border-2 border-stone-300 border-t-[#7c2d12] dark:border-t-[#ea580c]"
                aria-hidden
              />
              <span className="text-sm">{COPY.shot_draft_generating}</span>
            </div>
          ) : failed ? (
            <button
              type="button"
              onClick={handleGenerate}
              className={btnClass}
              data-testid={`rewrite-shot-card-${shot.shot_index}-retry`}
            >
              <RefreshCw className="h-4 w-4" aria-hidden />
              {COPY.shot_draft_failed}·{COPY.shot_draft_retry}
            </button>
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
