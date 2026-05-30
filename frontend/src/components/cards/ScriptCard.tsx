import { useState } from "react";
import type { CascadeAnalysisContract } from "../../types/cascade";
import { COPY, scrubUiForbidden } from "../../lib/cardCopy";
import { CARD_CLASS, BTN_PRIMARY, BTN_SECONDARY } from "../../lib/cardStyles";
import { WarningChips } from "../feedback/WarningChip";
import { NicheCTA } from "./NicheCTA";
import type { NicheId } from "../../store/nicheStore";

interface Props {
  analysis: CascadeAnalysisContract;
  script: string;
  onScriptChange: (script: string) => void;
  /** Optional — when provided + script is empty, the card shows the niche CTA
   *  instead of an empty "改完的版本" section. */
  onTriggerRewrite?: (niche: NicheId) => void;
}

export function ScriptCard({ analysis, script, onScriptChange, onTriggerRewrite }: Props) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(script);
  const va = analysis.viral_analysis;
  const warnings = analysis.warnings.filter((w) => w.field.startsWith("viral_analysis."));

  const bullets = [
    { label: COPY.hook_label, text: scrubUiForbidden(va.hook) },
    { label: COPY.pacing_label, text: scrubUiForbidden(va.pacing) },
    { label: COPY.climax_label, text: scrubUiForbidden(va.climax) },
  ];

  const save = () => {
    onScriptChange(draft);
    setEditing(false);
  };

  // CTA 显示由父组件 (CardStack) 通过传/不传 `onTriggerRewrite` 决定 — 父组件
  // 知道 rewriteShots 状态,rewrite 真触发了之后才停止传 callback。本卡片
  // 不能用 `!script` 判断,因为分析侧 `loadFromAnalysis` 会自动填一份源台词
  // 拼接当默认 script(buildDefaultScript),那不是改写产物。
  const showCta = Boolean(onTriggerRewrite);
  const showScript = Boolean(script);

  return (
    <section className={CARD_CLASS} data-testid="script-card">
      <h2 className="font-serif-cn text-lg font-medium text-stone-900 dark:text-stone-50 mb-5 tracking-[-0.01em]">
        {COPY.why_viral_header}
      </h2>
      <ul className="space-y-4 mb-6">
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
      {va.replicable_formula && (
        <div className="mb-6 rounded-xl bg-[#fef7f0] dark:bg-stone-800/60 border border-[#7c2d12]/15 dark:border-[#ea580c]/25 px-4 py-3">
          <div className="text-[11px] uppercase tracking-[0.14em] font-medium text-[#7c2d12] dark:text-[#ea580c] mb-1">
            {COPY.formula_label}
          </div>
          <p className="text-[15px] leading-[1.6] text-stone-900 dark:text-stone-100 font-medium">
            {scrubUiForbidden(va.replicable_formula)}
          </p>
        </div>
      )}
      <WarningChips warnings={warnings} />

      {showCta && <NicheCTA onPick={onTriggerRewrite!} />}

      {showScript && (
        <>
          <h2 className="font-serif-cn text-lg font-medium text-stone-900 dark:text-stone-50 mt-8 mb-3 tracking-[-0.01em]">
            {COPY.script_header}
          </h2>
          {editing ? (
            <div className="space-y-3">
              <textarea
                className="w-full min-h-[140px] rounded-xl border border-stone-200 dark:border-stone-700 bg-white dark:bg-stone-900 p-3 text-base text-stone-800 dark:text-stone-100 focus:outline-none focus:ring-2 focus:ring-orange-400"
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
              <p className="text-[15px] leading-[1.75] text-stone-800 dark:text-stone-200 whitespace-pre-wrap">{script}</p>
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
        </>
      )}
    </section>
  );
}
