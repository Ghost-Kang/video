import { useEffect, useRef, useState } from "react";
import { X } from "lucide-react";
import type { CascadeAnalysisContract, Scene } from "../../types/cascade";
import { COPY, scrubUiForbidden } from "../../lib/cardCopy";

interface Props {
  analysis: CascadeAnalysisContract;
  onClose: () => void;
}

function fmtTime(sec: number): string {
  const s = Math.max(0, Math.round(sec));
  return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
}

const clean = (s: string | undefined | null) => scrubUiForbidden(s ?? "").trim();

function shotLines(scene: Scene): { label: string; text: string }[] {
  const shot = [clean(scene.cinematography), clean(scene.camera_position)]
    .filter(Boolean)
    .join(" / ");
  const visual = clean(scene.segment_description) || clean(scene.visual_content);
  const propsCostume = [clean(scene.props_list), clean(scene.costume)]
    .filter((v) => v && v !== "无")
    .join(" / ");
  return [
    { label: COPY.script_shot_field_shot, text: shot },
    { label: COPY.script_shot_field_visual, text: visual },
    { label: COPY.script_shot_field_dialogue, text: clean(scene.dialogue_and_narration) },
    { label: COPY.script_shot_field_props, text: propsCostume },
  ].filter((r) => r.text);
}

function buildShotsCopy(scenes: Scene[]): string {
  return scenes
    .map((s, i) => {
      const head = `${i + 1}. ${fmtTime(s.timestamp_start)}–${fmtTime(s.timestamp_end)}${
        clean(s.theme) ? ` · ${clean(s.theme)}` : ""
      }`;
      const body = shotLines(s).map((r) => `   ${r.label}: ${r.text}`);
      return [head, ...body].join("\n");
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
  const transcript = clean(analysis.full_transcript);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    panelRef.current?.focus();
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const copy = async () => {
    const text = tab === "shots" ? buildShotsCopy(scenes) : transcript;
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      /* clipboard blocked — silently no-op; user can still read the panel */
    }
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  };

  const animClass = isDesktop ? "anim-slide-in-right" : "anim-slide-in-up";

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/25 anim-fade-in md:items-stretch md:justify-end"
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
        className={`flex w-full max-h-[85vh] flex-col rounded-t-2xl bg-white outline-none dark:bg-stone-900 md:h-full md:max-h-none md:w-[420px] md:max-w-full md:rounded-t-none ${animClass}`}
      >
        {/* grabber(手机) */}
        <div className="flex justify-center pt-2 md:hidden">
          <span className="h-1 w-10 rounded-full bg-stone-300 dark:bg-stone-700" />
        </div>

        {/* header */}
        <div className="flex items-start justify-between px-5 pt-3 pb-2">
          <div>
            <h3 className="font-serif-cn text-base text-stone-900 dark:text-stone-50">
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
            className="-mr-1 flex h-9 w-9 items-center justify-center rounded-full text-stone-500 hover:bg-stone-100 hover:text-stone-900 dark:text-stone-400 dark:hover:bg-stone-800 dark:hover:text-stone-100"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* tabs */}
        <div role="tablist" className="flex gap-5 border-b border-stone-100 px-5 dark:border-stone-800">
          {(
            [
              ["shots", COPY.script_tab_shots],
              ["transcript", COPY.script_tab_transcript],
            ] as const
          ).map(([key, label]) => (
            <button
              key={key}
              role="tab"
              aria-selected={tab === key}
              type="button"
              onClick={() => setTab(key)}
              className={`relative -mb-px py-2.5 text-[14px] transition-colors ${
                tab === key
                  ? "font-medium text-[#7c2d12] dark:text-[#ea580c]"
                  : "text-stone-500 hover:text-stone-800 dark:text-stone-400 dark:hover:text-stone-200"
              }`}
            >
              {label}
              {tab === key && (
                <span className="absolute inset-x-0 -bottom-px h-[2px] origin-left bg-[#7c2d12] anim-draw-line dark:bg-[#ea580c]" />
              )}
            </button>
          ))}
        </div>

        {/* content */}
        <div className="flex-1 overflow-y-auto px-5 py-4" role="tabpanel">
          {tab === "shots" ? (
            <ol className="divide-y divide-stone-100 dark:divide-stone-800">
              {scenes.map((s, i) => (
                <li key={s.scene_index} className="py-3 first:pt-0">
                  <div className="mb-1.5 flex items-baseline gap-2">
                    <span className="text-[12px] tabular-nums text-stone-400 dark:text-stone-500">
                      {i + 1}. {fmtTime(s.timestamp_start)}–{fmtTime(s.timestamp_end)}
                    </span>
                    {clean(s.theme) && (
                      <span className="font-serif-cn text-[14px] text-stone-900 dark:text-stone-100">
                        {clean(s.theme)}
                      </span>
                    )}
                  </div>
                  <div className="space-y-1">
                    {shotLines(s).map((r) => (
                      <p key={r.label} className="text-[13px] leading-[1.6] text-stone-700 dark:text-stone-300">
                        <span className="text-stone-400 dark:text-stone-500">{r.label}：</span>
                        {r.text}
                      </p>
                    ))}
                  </div>
                </li>
              ))}
            </ol>
          ) : transcript ? (
            <p className="whitespace-pre-wrap text-[14px] leading-[1.8] text-stone-700 dark:text-stone-300">
              {transcript}
            </p>
          ) : (
            <p className="py-8 text-center text-[13px] text-stone-400 dark:text-stone-500">
              {COPY.script_transcript_empty}
            </p>
          )}
        </div>

        {/* sticky footer — copy */}
        <div className="border-t border-stone-100 px-5 py-3 dark:border-stone-800">
          <button
            type="button"
            onClick={copy}
            aria-live="polite"
            className="w-full rounded-xl bg-[#7c2d12] py-2.5 text-[14px] font-medium text-white transition-transform hover:bg-[#9a3412] active:scale-[0.99] dark:bg-[#ea580c] dark:hover:bg-[#c2410c]"
          >
            {copied ? COPY.script_copied : COPY.script_copy}
          </button>
        </div>
      </div>
    </div>
  );
}
