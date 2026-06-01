import { useState } from "react";
import { COPY } from "../../lib/cardCopy";
import { BTN_PRIMARY } from "../../lib/cardStyles";

interface Props {
  /** 触发改写。topic 为用户填的一句话主题(可选,留空 = 纯按源片骨架通用改写)。 */
  onPick: (topic?: string) => void;
}

// 去 niche 后的通用改写 CTA(取代旧的 3 赛道 NicheCTA)。不再让用户在写死的
// 宝妈/育儿/厨房里选,而是:套用这条爆款的骨架四要素,可选填一句话主题,直接
// 把分析接到「你的版本」。analysis 落地、还没改写、且没有改写在途时出现。
export function RewriteCTA({ onPick }: Props) {
  const [topic, setTopic] = useState("");
  const fire = () => onPick(topic.trim() || undefined);

  return (
    <section
      className="mt-8 rounded-2xl border border-[#7c2d12]/20 dark:border-[#ea580c]/30 bg-[#fef7f0]/40 dark:bg-stone-800/40 p-5"
      data-testid="rewrite-cta"
      aria-label="改写成你的版本"
    >
      <h2 className="font-serif-cn text-lg font-medium text-stone-900 dark:text-stone-50 mb-2 tracking-[-0.01em]">
        {COPY.rewrite_cta_header}
      </h2>
      <p className="text-sm text-stone-600 dark:text-stone-400 mb-4">
        {COPY.rewrite_cta_hint}
      </p>
      <input
        type="text"
        value={topic}
        onChange={(e) => setTopic(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") fire();
        }}
        placeholder={COPY.rewrite_topic_placeholder}
        maxLength={60}
        aria-label={COPY.rewrite_topic_placeholder}
        className="mb-3 w-full rounded-xl border border-stone-200 dark:border-stone-700 bg-white dark:bg-stone-900 px-4 py-2.5 text-[15px] text-stone-800 dark:text-stone-100 placeholder:text-stone-400 focus:outline-none focus:ring-2 focus:ring-orange-400"
      />
      <button type="button" onClick={fire} className={`${BTN_PRIMARY} w-full`}>
        {COPY.rewrite_cta_button}
      </button>
    </section>
  );
}
