import { useEffect, useState } from "react";
import { ImageIcon } from "lucide-react";
import type { Scene } from "../../types/cascade";
import { COPY } from "../../lib/cardCopy";
import { CARD_CLASS, BTN_SECONDARY } from "../../lib/cardStyles";
import { reuseAnchor, type Anchor, type AnchorKind } from "../../lib/anchorApi";
import { AnchorPickerModal } from "../anchors/AnchorPickerModal";
import { WarningChips } from "../feedback/WarningChip";

interface Props {
  scene: Scene;
  onGenerateFirstFrame?: (sceneIndex: number) => void;
}

export function ShotCard({ scene, onGenerateFirstFrame }: Props) {
  const [pickerKind, setPickerKind] = useState<AnchorKind | null>(null);
  const [picked, setPicked] = useState<Anchor | null>(null);
  const [generating, setGenerating] = useState(false);
  const dialogue = scene.dialogue_and_narration?.trim();
  const sceneWarnings = scene.warnings.filter((warning) =>
    warning.field.startsWith(`scenes[${scene.scene_index - 1}].`)
  );

  // Reset the local spinner once the WS frame patches the URL in.
  useEffect(() => {
    if (scene.first_frame_url) setGenerating(false);
  }, [scene.first_frame_url]);

  const handlePick = (anchor: Anchor) => {
    setPicked(anchor);
    setPickerKind(null);
    void reuseAnchor(anchor.id, {
      user_id: "default",
      reused_in_run_id: "local",
      reused_in_shot_index: scene.scene_index,
    });
  };

  const handleGenerate = () => {
    if (!onGenerateFirstFrame || generating) return;
    setGenerating(true);
    onGenerateFirstFrame(scene.scene_index);
  };

  return (
    <section className={CARD_CLASS} data-testid={`shot-card-${scene.scene_index}`}>
      <div className="aspect-video w-full overflow-hidden rounded-xl bg-stone-100 mb-4 flex items-center justify-center">
        {scene.first_frame_url ? (
          <img
            src={scene.first_frame_url}
            alt=""
            className="h-full w-full object-cover"
          />
        ) : generating ? (
          <div className="flex flex-col items-center gap-2 text-stone-500">
            <div
              className="h-6 w-6 animate-spin rounded-full border-2 border-stone-300 border-t-stone-600"
              aria-hidden
            />
            <span className="text-sm">{COPY.shot_generating_first_frame}</span>
          </div>
        ) : (
          <button
            type="button"
            onClick={handleGenerate}
            disabled={!onGenerateFirstFrame}
            className="flex items-center gap-2 rounded-lg bg-white/80 hover:bg-white px-4 py-2 text-sm font-medium text-stone-700 hover:text-stone-900 shadow-sm border border-stone-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            data-testid={`shot-card-${scene.scene_index}-generate`}
          >
            <ImageIcon className="h-4 w-4" aria-hidden />
            {COPY.shot_generate_first_frame}
          </button>
        )}
      </div>

      <h3 className="text-lg font-medium text-stone-900 mb-2">
        {COPY.shot_label_prefix}
        {scene.scene_index}
        {COPY.shot_label_suffix}
      </h3>

      <p className="text-base text-stone-800 mb-2">
        {dialogue || COPY.shot_dialogue_placeholder}
      </p>

      <p className="text-sm text-stone-500 mb-4">{scene.visual_content}</p>

      <div className="mb-4">
        <WarningChips warnings={sceneWarnings} />
      </div>

      {picked && <p className="mb-3 text-sm text-stone-600">已选：{picked.label}</p>}

      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          className={BTN_SECONDARY}
          onClick={() => setPickerKind("character")}
        >
          {COPY.change_character}
        </button>
        <button
          type="button"
          className={BTN_SECONDARY}
          onClick={() => setPickerKind("scene")}
        >
          {COPY.reuse_scene}
        </button>
      </div>
      {pickerKind && (
        <AnchorPickerModal
          kind={pickerKind}
          onClose={() => setPickerKind(null)}
          onPick={handlePick}
        />
      )}
    </section>
  );
}
