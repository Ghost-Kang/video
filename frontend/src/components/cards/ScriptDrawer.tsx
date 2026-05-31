import { useEffect, useRef, useState } from "react";
import { X, Copy, Check } from "lucide-react";
import type { CascadeAnalysisContract, Scene } from "../../types/cascade";
import { COPY, scrubUiForbidden } from "../../lib/cardCopy";
import { transcriptLines } from "../../lib/scriptText";

interface Props {
  analysis: CascadeAnalysisContract;
  onClose: () => void;
}

function fmtTime(sec: number): string {
  const s = Math.max(0, Math.round(sec));
  return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
}

const clean = (s: string | undefined | null) => scrubUiForbidden(s ?? "").trim();
const notNone = (s: string) => (s && s !== "无" ? s : "");

interface ShotData {
  lead: string;
  visual: string;
  dialogue: string;
  grid: { label: string; text: string }[];
}

// 「照着复刻」用:画面取详细 visual_content(景别/构图/动作/色调),不是简略说明;
// 补全场景/出镜/道具服装/光影/听觉等复刻有用字段。
function shotData(scene: Scene): ShotData {
  const grid = [
    {
      label: COPY.script_shot_field_shot,
      text: [clean(scene.cinematography), clean(scene.camera_position)].filter(Boolean).join(" / "),
    },
    { label: COPY.script_shot_field_scene, text: notNone(clean(scene.scene)) },
    { label: COPY.script_shot_field_actors, text: notNone(clean(scene.actors)) },
    {
      label: COPY.script_shot_field_props,
      text: [clean(scene.props_list), clean(scene.costume)].filter((v) => v && v !== "无").join(" / "),
    },
    { label: COPY.script_shot_field_light, text: notNone(clean(scene.lighting_and_color)) },
    { label: COPY.script_shot_field_audio, text: notNone(clean(scene.audio_content)) },
  ].filter((g) => g.text);
  return {
    lead: clean(scene.segment_description),
    visual: clean(scene.visual_content),
    dialogue: clean(scene.dialogue_and_narration),
    grid,
  };
}

function buildShotsCopy(scenes: Scene[]): string {
  return scenes
    .map((s, i) => {
      const d = shotData(s);
      const head = `${i + 1}. ${fmtTime(s.timestamp_start)}–${fmtTime(s.timestamp_end)}${
        clean(s.theme) ? ` · ${clean(s.theme)}` : ""
      }`;
      const lines = [head];
      if (d.lead) lines.push(`   ${d.lead}`);
      if (d.visual) lines.push(`   ${COPY.script_shot_field_visual}: ${d.visual}`);
      if (d.dialogue) lines.push(`   ${COPY.script_shot_field_dialogue}: ${d.dialogue.replace(/\n/g, " / ")}`);
      d.grid.forEach((g) => lines.push(`   ${g.label}: ${g.text}`));
      return lines.join("\n");
    })
    .join("\n\n");
}

export function ScriptDrawer({ analysis, onClose }: Props) {
  const [tab, setTab] = useState<"shots" | "transcript">("shots");
  const [copied, setCopied] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const [isDesktop] = useState(
    () =>
      typeof window !== "undefined" &&
      typeof window.matchMedia === "function" &&
      window.matchMedia("(min-width: 768px)").matches,
  );

  const scenes = [...analysis.scenes].sort((a, b) => a.scene_index - b.scene_index);
  const lines = transcriptLines(analysis.full_transcript);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    panelRef.current?.focus();
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const copy = async () => {
    const text = tab === "shots" ? buildShotsCopy(scenes) : lines.join("\n");
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      /* clipboard blocked — silently no-op */
    }
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  };

  const animClass = isDesktop ? "anim-slide-in-right" : "anim-slide-in-up";

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/30 anim-fade-in backdrop-blur-[2px] md:items-stretch md:justify-end"
      onMouseDown={onClose}
      data-testid="script-drawer"
    >
      <div
        ref={panelRef}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-label={COPY.script_drawer_title}
        onMouseDown={(e) => e.stopPropagation()}
        className={`relative flex w-full max-h-[88vh] flex-col overflow-hidden rounded-t-2xl border-stone-200/50 bg-[var(--color-paper)]/95 outline-none backdrop-blur-xl dark:border-stone-800/50 dark:bg-stone-950/92 md:h-full md:max-h-none md:w-[470px] md:max-w-full md:rounded-t-none md:border-l ${animClass}`}
      >
        {/* 顶部流光描边 */}
        <span className="tech-topline pointer-events-none absolute inset-x-0 top-0 h-[3px]" aria-hidden />

        {/* grabber(手机) */}
        <div className="flex justify-center pt-2.5 md:hidden">
          <span className="h-1 w-10 rounded-full bg-stone-300 dark:bg-stone-700" />
        </div>

        {/* header */}
        <div className="flex items-start justify-between px-5 pt-3.5 pb-2">
          <div>
            <h3 className="font-serif-cn text-[17px] text-stone-900 dark:text-stone-50">
              {COPY.script_drawer_title}
            </h3>
            <p className="mt-0.5 text-[12px] text-stone-500 dark:text-stone-400">
              {COPY.script_drawer_subtitle}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label={COPY.script_close}
            className="-mr-1 flex h-9 w-9 items-center justify-center rounded-full text-stone-500 transition-colors hover:bg-stone-100 hover:text-stone-900 dark:text-stone-400 dark:hover:bg-stone-800 dark:hover:text-stone-100"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* tabs */}
        <div role="tablist" className="flex gap-5 border-b border-stone-200/60 px-5 dark:border-stone-800/60">
          {(["shots", "transcript"] as const).map((key) => {
            const selected = tab === key;
            return (
              <button
                key={key}
                role="tab"
                aria-selected={selected}
                type="button"
                onClick={() => setTab(key)}
                className={`relative -mb-px py-2.5 text-[14px] transition-colors ${
                  selected
                    ? "font-medium text-[#7c2d12] dark:text-[#ea580c]"
                    : "text-stone-500 hover:text-stone-800 dark:text-stone-400 dark:hover:text-stone-200"
                }`}
              >
                {key === "shots" ? COPY.script_tab_shots : COPY.script_tab_transcript}
                {key === "shots" && (
                  <span aria-hidden className="num-tech ml-1 text-[11px] text-stone-400 dark:text-stone-500">
                    {scenes.length}
                    {COPY.script_shots_count_suffix}
                  </span>
                )}
                {selected && (
                  <span className="absolute inset-x-0 -bottom-px h-[2px] origin-left bg-[#7c2d12] anim-draw-line dark:bg-[#ea580c]" />
                )}
              </button>
            );
          })}
        </div>

        {/* content */}
        <div className="flex-1 overflow-y-auto px-5 py-4" role="tabpanel">
          {tab === "shots" ? (
            <ol className="relative">
              {/* 时间线竖轴(科技/结构感) */}
              <span
                className="pointer-events-none absolute bottom-2 left-[11px] top-2 w-px bg-gradient-to-b from-[#7c2d12]/40 via-stone-200 to-transparent dark:via-stone-700"
                aria-hidden
              />
              {scenes.map((s, i) => {
                const d = shotData(s);
                const emotion = clean(s.emotion);
                return (
                  <li
                    key={s.scene_index}
                    className="anim-fade-up relative pb-5 pl-9 last:pb-0"
                    style={{ animationDelay: `${i * 60}ms` }}
                  >
                    {/* 时间线节点 */}
                    <span className="num-tech absolute left-0 top-0 flex h-6 w-6 items-center justify-center rounded-full bg-[#7c2d12] text-[11px] font-semibold text-white shadow-[0_0_12px_-2px_rgba(234,88,12,0.65)] dark:bg-[#ea580c]">
                      {i + 1}
                    </span>

                    {/* 头部:时间 + 主题 + 情感 */}
                    <div className="mb-1.5 flex items-baseline gap-2">
                      <span className="num-tech rounded-md bg-[#7c2d12]/[0.06] px-1.5 py-0.5 text-[11px] text-[#7c2d12]/80 dark:bg-[#ea580c]/10 dark:text-[#ea580c]/80">
                        {fmtTime(s.timestamp_start)}–{fmtTime(s.timestamp_end)}
                      </span>
                      {clean(s.theme) && (
                        <span className="font-serif-cn text-[14px] text-stone-900 dark:text-stone-100">
                          {clean(s.theme)}
                        </span>
                      )}
                      {emotion && (
                        <span className="ml-auto shrink-0 text-[11px] text-[#7c2d12]/70 dark:text-[#ea580c]/70">
                          {emotion}
                        </span>
                      )}
                    </div>

                    {d.lead && (
                      <p className="mb-2 text-[12.5px] leading-[1.6] text-stone-500 dark:text-stone-400">
                        {d.lead}
                      </p>
                    )}

                    {/* 重点:画面(照着复刻的核心)—— accent 玻璃框突出 */}
                    {d.visual && (
                      <div className="mb-2 rounded-xl border-l-2 border-[#7c2d12]/50 bg-[#fef7f0]/70 px-3 py-2 dark:border-[#ea580c]/50 dark:bg-stone-800/40">
                        <div className="mb-0.5 text-[11px] font-semibold text-[#7c2d12] dark:text-[#ea580c]">
                          {COPY.script_shot_field_visual}
                        </div>
                        <p className="text-[13px] leading-[1.6] text-stone-800 dark:text-stone-200">{d.visual}</p>
                      </div>
                    )}

                    {/* 重点:台词 —— 引用式突出 */}
                    {d.dialogue && (
                      <div className="mb-2 rounded-xl border-l-2 border-emerald-500/40 bg-emerald-50/50 px-3 py-2 dark:bg-stone-800/40">
                        <div className="mb-0.5 text-[11px] font-semibold text-emerald-700 dark:text-emerald-400">
                          {COPY.script_shot_field_dialogue}
                        </div>
                        <p className="whitespace-pre-line text-[13px] leading-[1.6] text-stone-700 dark:text-stone-300">
                          {d.dialogue}
                        </p>
                      </div>
                    )}

                    {/* 拍摄参数(次级,2 列紧凑) */}
                    {d.grid.length > 0 && (
                      <div className="grid grid-cols-1 gap-x-4 gap-y-1 sm:grid-cols-2">
                        {d.grid.map((g) => (
                          <p key={g.label} className="text-[12px] leading-[1.5] text-stone-600 dark:text-stone-400">
                            <span className="text-stone-400 dark:text-stone-500">{g.label} </span>
                            {g.text}
                          </p>
                        ))}
                      </div>
                    )}
                  </li>
                );
              })}
            </ol>
          ) : lines.length > 0 ? (
            <div className="space-y-1.5">
              {lines.map((line, i) => (
                <p
                  key={i}
                  className="anim-fade-up flex gap-2.5 text-[13.5px] leading-[1.7] text-stone-700 dark:text-stone-300"
                  style={{ animationDelay: `${Math.min(i, 12) * 35}ms` }}
                >
                  <span className="num-tech mt-0.5 shrink-0 text-[11px] text-stone-300 dark:text-stone-600">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <span>{line}</span>
                </p>
              ))}
            </div>
          ) : (
            <p className="py-8 text-center text-[13px] text-stone-400 dark:text-stone-500">
              {COPY.script_transcript_empty}
            </p>
          )}
        </div>

        {/* sticky footer — copy */}
        <div className="border-t border-stone-200/60 px-5 py-3 dark:border-stone-800/60">
          <button
            type="button"
            onClick={copy}
            aria-live="polite"
            className="hover-glow flex w-full items-center justify-center gap-2 rounded-xl bg-[#7c2d12] py-2.5 text-[14px] font-medium text-white transition-all hover:bg-[#9a3412] active:scale-[0.99] dark:bg-[#ea580c] dark:hover:bg-[#c2410c]"
          >
            {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
            {copied ? COPY.script_copied : COPY.script_copy}
          </button>
        </div>
      </div>
    </div>
  );
}
