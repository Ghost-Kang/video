import { useEffect, useRef, useState } from "react";
import { Play } from "lucide-react";
import { COPY } from "../../lib/cardCopy";

interface Props {
  clipUrl?: string | null;
  poster?: string | null;
}

// 逐幕视频片段播放器。状态机:
//   POSTER(海报+▶) → 点按 → LOADING(海报+转圈) → canplay → PLAYING(原生 inline)
//   无 clip 有海报 → POSTER_ONLY(纯海报,不可点)
//   无 clip 无海报 → 不渲染(return null),卡片回退到现状布局
// 桌面 hover ≥150ms → 静音 loop 预览(reduced-motion / 无 hover 设备禁用)。
export function SceneClip({ clipUrl, poster }: Props) {
  const [playing, setPlaying] = useState(false);
  const [loading, setLoading] = useState(false);
  const [hoverPreview, setHoverPreview] = useState(false);
  // 媒体加载失败(如旧分析的 clip/poster 已被清理 → 404)。优雅降级:不显破图/破框。
  const [posterFailed, setPosterFailed] = useState(false);
  const [clipFailed, setClipFailed] = useState(false);
  const hoverTimer = useRef<number | null>(null);

  // 卸载时清掉 hover 防抖计时器。必须在任何条件 return 之前声明所有 hook
  // (React rules of hooks)——否则「无媒体 → return null」会少调一个 hook 致崩溃。
  useEffect(
    () => () => {
      if (hoverTimer.current !== null) window.clearTimeout(hoverTimer.current);
    },
    [],
  );

  const canPlay = !!clipUrl;
  const hasPoster = !!poster;

  // 无任何媒体 → 不占位
  if (!canPlay && !hasPoster) return null;
  // 媒体已失效(404):海报挂了且没在播 → 整槽隐藏;clip 挂了且无海报 → 隐藏。
  if (posterFailed && !playing) return null;
  if (clipFailed && !hasPoster) return null;

  const reduceMotion =
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const hoverCapable =
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(hover: hover) and (pointer: fine)").matches;
  const allowHoverPreview = canPlay && hoverCapable && !reduceMotion;

  const clearHoverTimer = () => {
    if (hoverTimer.current !== null) {
      window.clearTimeout(hoverTimer.current);
      hoverTimer.current = null;
    }
  };

  const onEnter = () => {
    if (!allowHoverPreview || playing) return;
    clearHoverTimer();
    hoverTimer.current = window.setTimeout(() => setHoverPreview(true), 150);
  };
  const onLeave = () => {
    clearHoverTimer();
    setHoverPreview(false);
  };

  const startPlay = () => {
    if (!canPlay) return;
    setHoverPreview(false);
    setLoading(true);
    setPlaying(true);
  };

  return (
    <div
      className="relative mb-3 h-56 w-full overflow-hidden rounded-xl bg-stone-950"
      onMouseEnter={onEnter}
      onMouseLeave={onLeave}
      data-testid="scene-clip"
    >
      {/* PLAYING — 原生 inline 播放,占满 */}
      {playing && clipUrl && (
        <video
          src={clipUrl}
          poster={poster ?? undefined}
          controls
          autoPlay
          playsInline
          preload="none"
          onWaiting={() => setLoading(true)}
          onPlaying={() => setLoading(false)}
          onCanPlay={() => setLoading(false)}
          onError={() => {
            setClipFailed(true);
            setPlaying(false);
            setLoading(false);
          }}
          className="h-full w-full object-contain"
        />
      )}

      {/* hover 静音预览(桌面),覆盖在海报上;点按播放后不显 */}
      {!playing && hoverPreview && clipUrl && (
        <video
          src={clipUrl}
          muted
          loop
          autoPlay
          playsInline
          preload="none"
          className="h-full w-full object-cover"
        />
      )}

      {/* POSTER / POSTER_ONLY */}
      {!playing && !hoverPreview && (
        <>
          {hasPoster ? (
            <img
              src={poster ?? undefined}
              alt=""
              loading="lazy"
              onError={() => setPosterFailed(true)}
              className="h-full w-full object-cover"
            />
          ) : (
            <div className="h-full w-full bg-gradient-to-br from-stone-800 to-stone-950" />
          )}
        </>
      )}

      {/* ▶ 播放按钮 / 加载转圈 —— 仅可播放时 */}
      {!playing && canPlay && (
        <button
          type="button"
          onClick={startPlay}
          aria-label={COPY.clip_play_label}
          className="group absolute inset-0 flex items-center justify-center"
        >
          <span className="relative flex h-14 w-14 items-center justify-center">
            <span className="absolute inset-0 rounded-full bg-[#7c2d12]/80 transition-transform duration-200 group-hover:scale-105 group-active:scale-95 group-hover:anim-pulse-ring" />
            <Play className="relative h-6 w-6 translate-x-[1px] fill-white text-white" />
          </span>
        </button>
      )}

      {/* 仅首帧角标(POSTER_ONLY) */}
      {!canPlay && hasPoster && (
        <span className="absolute bottom-2 right-2 rounded-md bg-black/45 px-2 py-0.5 text-[11px] text-white/90">
          {COPY.clip_poster_only}
        </span>
      )}

      {/* 缓冲转圈 */}
      {loading && playing && (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center bg-black/20">
          <span className="h-8 w-8 rounded-full border-2 border-white/30 border-t-white anim-spin-slow" />
        </div>
      )}
    </div>
  );
}
