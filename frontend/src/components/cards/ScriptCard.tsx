import { useState } from "react";
import type { CascadeAnalysisContract } from "../../types/cascade";
import { COPY } from "../../lib/cardCopy";
import { CARD_CLASS, BTN_PRIMARY, BTN_SECONDARY } from "../../lib/cardStyles";
import { WarningChips } from "../feedback/WarningChip";

interface Props {
  analysis: CascadeAnalysisContract;
  script: string;
  onScriptChange: (script: string) => void;
}

export function ScriptCard({ analysis, script, onScriptChange }: Props) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(script);
  const va = analysis.viral_analysis;
  const warnings = analysis.warnings.filter((w) => w.field.startsWith("viral_analysis."));

  const bullets = [
    { label: COPY.hook_label, text: va.hook },
    { label: COPY.pacing_label, text: va.pacing },
    { label: COPY.climax_label, text: va.climax },
  ];

  const save = () => {
    onScriptChange(draft);
    setEditing(false);
  };

  return (
    <section className={CARD_CLASS} data-testid="script-card">
      <h2 className="text-lg font-medium text-stone-900 mb-4">
        {COPY.why_viral_header}
      </h2>
      <ul className="space-y-3 mb-6">
        {bullets.map((b) => (
          <li key={b.label} className="text-base text-stone-700">
            <span className="font-medium text-stone-900">{b.label}</span>
            <span className="text-stone-500"> — </span>
            {b.text}
          </li>
        ))}
      </ul>
      <WarningChips warnings={warnings} />

      <h2 className="text-lg font-medium text-stone-900 mt-6 mb-3">
        {COPY.script_header}
      </h2>
      {editing ? (
        <div className="space-y-3">
          <textarea
            className="w-full min-h-[140px] rounded-xl border border-stone-200 p-3 text-base text-stone-800 focus:outline-none focus:ring-2 focus:ring-orange-400"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
          />
          <div className="flex gap-3">
            <button type="button" className={BTN_PRIMARY} onClick={save}>
              {COPY.save_script}
            </button>
            <button
              type="button"
              className={BTN_SECONDARY}
              onClick={() => {
                setDraft(script);
                setEditing(false);
              }}
            >
              取消
            </button>
          </div>
        </div>
      ) : (
        <>
          <p className="text-base text-stone-700 whitespace-pre-wrap">{script}</p>
          <button
            type="button"
            className={`${BTN_SECONDARY} mt-3`}
            onClick={() => {
              setDraft(script);
              setEditing(true);
            }}
          >
            {COPY.edit_script}
          </button>
        </>
      )}
    </section>
  );
}
