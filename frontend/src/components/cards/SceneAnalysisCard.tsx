import type { Scene } from "../../types/cascade";
import { COPY, scrubUiForbidden } from "../../lib/cardCopy";
import { CARD_CLASS } from "../../lib/cardStyles";
import { useInView } from "../../hooks/useInView";
import { SceneClip } from "./SceneClip";

interface Props {
  scene: Scene;
}

function fmtTime(sec: number): string {
  const s = Math.max(0, Math.round(sec));
  const m = Math.floor(s / 60);
  return `${String(m).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
}

// 视频分析(逐幕)— 对齐 toprador image 2:
//   头部:序号 + 时间 + 分镜主题 + 说明/描述 + 片段和口播 + 情感
//   突出双栏:视觉内容 / 听觉内容
//   下方网格:摄影 / 机位 / 演员 / 画面文字 / 画面表现形式 / 场景 / 道具 / 服装 / 光影色彩
export function SceneAnalysisCard({ scene }: Props) {
  const c = (s: string | undefined) => scrubUiForbidden(s ?? "").trim();
  const grid: { label: string; text: string }[] = [
    { label: COPY.sc_cinematography, text: c(scene.cinematography) },
    { label: COPY.sc_camera_position, text: c(scene.camera_position) },
    { label: COPY.sc_actors, text: c(scene.actors) },
    { label: COPY.sc_on_screen_text, text: c(scene.on_screen_text) },
    { label: COPY.sc_presentation, text: c(scene.visual_presentation_style) },
    { label: COPY.sc_scene, text: c(scene.scene) },
    { label: COPY.sc_props, text: c(scene.props_list) },
    { label: COPY.sc_costume, text: c(scene.costume) },
    { label: COPY.sc_lighting, text: c(scene.lighting_and_color) },
  ].filter((g) => g.text && g.text !== "无");

  const visual = c(scene.visual_content);
  const audio = c(scene.audio_content);
  const { ref, inView } = useInView<HTMLElement>();

  return (
    <section
      ref={ref}
      className={`${CARD_CLASS} hover-glow ${inView ? "anim-tech-in" : "opacity-0"}`}
      data-testid="scene-analysis-card"
    >
      {/* 逐幕视频片段 */}
      <SceneClip clipUrl={scene.clip_url} poster={scene.clip_poster_url ?? scene.first_frame_url} />

      {/* 头部 */}
      <div className="flex items-baseline gap-2 mb-1.5">
        <span className="num-tech rounded-md bg-[#7c2d12]/[0.06] px-1.5 py-0.5 text-[12px] text-[#7c2d12]/80 dark:bg-[#ea580c]/10 dark:text-[#ea580c]/80">
          {fmtTime(scene.timestamp_start)}–{fmtTime(scene.timestamp_end)}
        </span>
        <h3 className="font-serif-cn text-[16px] text-stone-900 dark:text-stone-50">
          {c(scene.theme) || `镜头 ${scene.scene_index}`}
        </h3>
        {c(scene.emotion) && (
          <span className="ml-auto text-[12px] text-[#7c2d12] dark:text-[#ea580c]">
            {c(scene.emotion)}
          </span>
        )}
      </div>
      {c(scene.segment_description) && (
        <p className="mb-1 text-[14px] leading-[1.6] text-stone-700 dark:text-stone-300">
          {c(scene.segment_description)}
        </p>
      )}
      {c(scene.dialogue_and_narration) && (
        <p className="mb-3 text-[13px] leading-[1.6] text-stone-500 dark:text-stone-400">
          <span className="text-stone-400 dark:text-stone-500">{COPY.sc_dialogue}：</span>
          {c(scene.dialogue_and_narration)}
        </p>
      )}

      {/* 视觉 / 听觉 双栏突出 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
        {visual && (
          <div className="rounded-xl bg-[#fef7f0] dark:bg-stone-800/50 border-l-2 border-[#7c2d12]/50 dark:border-[#ea580c]/50 px-3.5 py-3">
            <div className="text-[12px] font-medium text-[#7c2d12] dark:text-[#ea580c] mb-1">
              {COPY.sc_visual}
            </div>
            <p className="text-[14px] leading-[1.6] text-stone-800 dark:text-stone-200">{visual}</p>
          </div>
        )}
        {audio && audio !== "无" && (
          <div className="rounded-xl bg-emerald-50/60 dark:bg-stone-800/50 border-l-2 border-emerald-600/40 px-3.5 py-3">
            <div className="text-[12px] font-medium text-emerald-700 dark:text-emerald-400 mb-1">
              {COPY.sc_audio}
            </div>
            <p className="text-[14px] leading-[1.6] text-stone-800 dark:text-stone-200">{audio}</p>
          </div>
        )}
      </div>

      {/* 拍摄/美术网格 */}
      {grid.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-x-4 gap-y-3">
          {grid.map((g) => (
            <div key={g.label}>
              <div className="text-[11px] text-stone-400 dark:text-stone-500 mb-0.5">{g.label}</div>
              <p className="text-[13px] leading-[1.5] text-stone-700 dark:text-stone-300">{g.text}</p>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
