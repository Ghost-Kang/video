import type { AudioDim } from "../../types/cascade";
import { COPY } from "../../lib/cardCopy";
import { CARD_CLASS } from "../../lib/cardStyles";

interface Props {
  audio: AudioDim;
}

// 音频三维: BGM / 口播 / 音效。样式跟 ScriptCard 的 bullet 风格保持一致
// (border-l-2 + 陶土橙 label),给视觉一致性。
export function AudioCard({ audio }: Props) {
  const bullets = [
    { label: COPY.audio_bgm_label, text: audio.bgm },
    { label: COPY.audio_pace_label, text: audio.voice_pace },
    { label: COPY.audio_sfx_label, text: audio.sound_effects },
  ];

  return (
    <section className={CARD_CLASS} data-testid="audio-card">
      <h2 className="font-serif-cn text-lg font-medium text-stone-900 dark:text-stone-50 mb-5 tracking-[-0.01em]">
        {COPY.audio_header}
      </h2>
      <ul className="space-y-4">
        {bullets.map((b) => (
          <li key={b.label} className="border-l-2 border-stone-200 dark:border-stone-700 pl-3.5">
            <div className="text-[11px] uppercase tracking-[0.14em] font-medium text-[#7c2d12] dark:text-[#ea580c] mb-1">
              {b.label}
            </div>
            <p className="text-[15px] leading-[1.65] text-stone-800 dark:text-stone-200">
              {b.text}
            </p>
          </li>
        ))}
      </ul>
    </section>
  );
}
