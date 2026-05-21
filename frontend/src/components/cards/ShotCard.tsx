import { useState } from "react";
import { ImageIcon } from "lucide-react";
import type { Scene } from "../../types/cascade";
import { COPY } from "../../lib/cardCopy";
import { CARD_CLASS, BTN_SECONDARY } from "../../lib/cardStyles";
import { reuseAnchor, type Anchor, type AnchorKind } from "../../lib/anchorApi";
import { AnchorPickerModal } from "../anchors/AnchorPickerModal";
import { WarningChips } from "../feedback/WarningChip";

interface Props {
  scene: Scene;
}

export function ShotCard({ scene }: Props) {
  const [pickerKind, setPickerKind] = useState<AnchorKind | null>(null);
  const [picked, setPicked] = useState<Anchor | null>(null);
  const dialogue = scene.dialogue_and_narration?.trim();
  const sceneWarnings = scene.warnings.filter((warning) =>
    warning.field.startsWith(`scenes[${scene.scene_index - 1}].`)
  );

  const handlePick = (anchor: Anchor) => {
    setPicked(anchor);
    setPickerKind(null);
    void reuseAnchor(anchor.id, {
      user_id: "default",
      reused_in_run_id: "local",
      reused_in_shot_index: scene.scene_index,
    });
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
        ) : (
          <ImageIcon className="h-10 w-10 text-stone-300" aria-hidden />
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
