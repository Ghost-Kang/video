import type { ProductionDim, CostTier } from "../../types/cascade";
import { COPY } from "../../lib/cardCopy";
import { CARD_CLASS } from "../../lib/cardStyles";

interface Props {
  production: ProductionDim;
}

const COST_TIER_LABEL: Record<CostTier, string> = {
  solo_phone: COPY.production_cost_solo,
  small_team: COPY.production_cost_team,
  post_heavy: COPY.production_cost_heavy,
};

const CHIP_CLASS =
  "inline-flex items-center rounded-full border border-stone-300 dark:border-stone-700 bg-white/70 dark:bg-stone-900/70 px-3 py-1 text-[12px] text-stone-700 dark:text-stone-300";

// 拍这条要花多少 + 能换成你自己的元素。chip 给"成本档+小时数",
// 列表给可替换 anchors(可能为空)。
export function ProductionCard({ production }: Props) {
  return (
    <section className={CARD_CLASS} data-testid="production-card">
      <h2 className="font-serif-cn text-lg font-medium text-stone-900 dark:text-stone-50 mb-4 tracking-[-0.01em]">
        {COPY.production_header}
      </h2>
      <div className="flex flex-wrap gap-2 mb-4">
        <span className={CHIP_CLASS}>{COST_TIER_LABEL[production.cost_tier]}</span>
        <span className={CHIP_CLASS}>
          {production.estimated_hours}
          {COPY.production_hours_suffix}
        </span>
      </div>
      {production.replaceable_anchors.length > 0 && (
        <>
          <h3 className="text-[11px] uppercase tracking-[0.14em] font-medium text-[#7c2d12] dark:text-[#ea580c] mb-2">
            {COPY.production_replaceable_header}
          </h3>
          <ul className="space-y-1.5">
            {production.replaceable_anchors.map((anchor, i) => (
              <li
                key={i}
                className="text-[14px] leading-[1.6] text-stone-700 dark:text-stone-300 pl-3 border-l-2 border-stone-200 dark:border-stone-700"
              >
                {anchor}
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
