import { useEffect, useRef, useState } from "react";
import { ImageIcon, RefreshCw, Clapperboard } from "lucide-react";
import type { RewriteShot } from "../../lib/cascadeMapper";
import { COPY } from "../../lib/cardCopy";
import { CARD_CLASS } from "../../lib/cardStyles";
import { useCanvasStore } from "../../store/canvasStore";

interface Props {
  shot: RewriteShot;
  /** 生成草稿图:发 [generate_first_frame: shot_index=N]。 */
  onGenerateFirstFrame?: (shotIndex: number) => void;
  /** 图生视频:发 [generate_shot_video: shot_index=N](需先有草稿图)。 */
  onGenerateShotVideo?: (shotIndex: number) => void;
}

// 草稿图:同步生成(~30s),75s 兜底。视频:后台几分钟,12min 兜底(正常靠后端推帧翻态)。
const _IMG_TIMEOUT_MS = 75_000;
const _VIDEO_TIMEOUT_MS = 12 * 60_000;

// 改写后的镜头 — 台词 + 画面描述 + 草稿图(image)+ 图生视频(video,以草稿图为首帧)。
// 媒体区:有视频 → <video>(poster=草稿图);否则草稿图四态。视频控件:草稿图出图后才出现
// (image-grounded),四态(IDLE/PENDING/DONE/FAILED)。DONE/FAILED 由 store 驱动(后端推帧),
// PENDING 本地瞬态;render 优先级避开 set-state-in-effect。
export function RewriteShotCard({ shot, onGenerateFirstFrame, onGenerateShotVideo }: Props) {
  const [imgGenerating, setImgGenerating] = useState(false);
  const [vidGenerating, setVidGenerating] = useState(false);
  const imgTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const vidTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const setImgError = useCanvasStore((s) => s.setRewriteShotFirstFrameError);
  const setVidError = useCanvasStore((s) => s.setRewriteShotVideoError);

  const hasImage = Boolean(shot.firstFrameUrl);
  const hasVideo = Boolean(shot.videoUrl);
  const imgError = shot.firstFrameError;
  const vidError = shot.videoError;

  // 帧到了 → 停对应兜底计时器(不 setState:render 按 has*/error 优先,本地 generating 自然失效)。
  useEffect(() => {
    if ((shot.firstFrameUrl || shot.firstFrameError) && imgTimer.current) {
      clearTimeout(imgTimer.current);
      imgTimer.current = null;
    }
  }, [shot.firstFrameUrl, shot.firstFrameError]);
  useEffect(() => {
    if ((shot.videoUrl || shot.videoError) && vidTimer.current) {
      clearTimeout(vidTimer.current);
      vidTimer.current = null;
    }
  }, [shot.videoUrl, shot.videoError]);
  useEffect(
    () => () => {
      if (imgTimer.current) clearTimeout(imgTimer.current);
      if (vidTimer.current) clearTimeout(vidTimer.current);
    },
    []
  );

  const genImage = () => {
    if (!onGenerateFirstFrame || imgGenerating) return;
    setImgError(shot.shot_index, null);
    setImgGenerating(true);
    onGenerateFirstFrame(shot.shot_index);
    if (imgTimer.current) clearTimeout(imgTimer.current);
    imgTimer.current = setTimeout(() => setImgError(shot.shot_index, COPY.shot_draft_timeout), _IMG_TIMEOUT_MS);
  };

  const genVideo = () => {
    if (!onGenerateShotVideo || vidGenerating) return;
    setVidError(shot.shot_index, null);
    setVidGenerating(true);
    onGenerateShotVideo(shot.shot_index);
    if (vidTimer.current) clearTimeout(vidTimer.current);
    vidTimer.current = setTimeout(() => setVidError(shot.shot_index, COPY.shot_video_timeout), _VIDEO_TIMEOUT_MS);
  };

  const btnClass =
    "flex items-center gap-2 rounded-lg bg-white/80 dark:bg-stone-900/60 hover:bg-white dark:hover:bg-stone-900 px-4 py-2 text-sm font-medium text-stone-700 dark:text-stone-200 shadow-sm border border-stone-200 dark:border-stone-700 transition-colors";

  return (
    <section
      className={`${CARD_CLASS} border-l-4 border-l-[#7c2d12] dark:border-l-[#ea580c]`}
      data-testid={`rewrite-shot-card-${shot.shot_index}`}
    >
      {onGenerateFirstFrame && (
        <div className="aspect-video w-full overflow-hidden rounded-xl bg-stone-100 dark:bg-stone-800 mb-2 flex items-center justify-center">
          {hasVideo ? (
            <video
              src={shot.videoUrl}
              poster={shot.firstFrameUrl}
              controls
              playsInline
              className="h-full w-full object-cover"
              data-testid={`rewrite-shot-card-${shot.shot_index}-video`}
            />
          ) : hasImage ? (
            <img src={shot.firstFrameUrl} alt="" className="h-full w-full object-cover" />
          ) : imgError ? (
            <div className="flex flex-col items-center gap-2 px-4 text-center">
              <p className="text-xs text-stone-500 dark:text-stone-400">{imgError}</p>
              <button type="button" onClick={genImage} className={btnClass} data-testid={`rewrite-shot-card-${shot.shot_index}-retry`}>
                <RefreshCw className="h-4 w-4" aria-hidden />
                {COPY.shot_draft_retry}
              </button>
            </div>
          ) : imgGenerating ? (
            <div className="flex flex-col items-center gap-2 text-stone-500 dark:text-stone-400">
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-stone-300 border-t-[#7c2d12] dark:border-t-[#ea580c]" aria-hidden />
              <span className="text-sm">{COPY.shot_draft_generating}</span>
            </div>
          ) : (
            <button type="button" onClick={genImage} className={btnClass} data-testid={`rewrite-shot-card-${shot.shot_index}-generate`}>
              <ImageIcon className="h-4 w-4" aria-hidden />
              {COPY.shot_draft_generate}
            </button>
          )}
        </div>
      )}

      {/* 视频控件 — 草稿图出图后才出现(image-grounded);有视频后不再显示(播放器已在媒体区)。 */}
      {onGenerateShotVideo && hasImage && !hasVideo && (
        <div className="mb-3 flex items-center justify-center">
          {vidError ? (
            <div className="flex flex-col items-center gap-1.5 text-center">
              <p className="text-xs text-stone-500 dark:text-stone-400">{vidError}</p>
              <button type="button" onClick={genVideo} className={btnClass} data-testid={`rewrite-shot-card-${shot.shot_index}-video-retry`}>
                <RefreshCw className="h-4 w-4" aria-hidden />
                {COPY.shot_draft_retry}
              </button>
            </div>
          ) : vidGenerating ? (
            <span className="inline-flex items-center gap-2 text-sm text-stone-500 dark:text-stone-400">
              <span className="h-1.5 w-1.5 rounded-full bg-[#7c2d12] dark:bg-[#ea580c] animate-pulse" aria-hidden />
              {COPY.shot_video_generating}
            </span>
          ) : (
            <button type="button" onClick={genVideo} className={btnClass} data-testid={`rewrite-shot-card-${shot.shot_index}-video-generate`}>
              <Clapperboard className="h-4 w-4" aria-hidden />
              {COPY.shot_video_generate}
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
