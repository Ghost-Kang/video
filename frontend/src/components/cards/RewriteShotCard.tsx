import type { RewriteShot } from "../../lib/cascadeMapper";
import { COPY } from "../../lib/cardCopy";
import { CARD_CLASS } from "../../lib/cardStyles";

interface Props {
  shot: RewriteShot;
}

// 改写后的镜头 — 不带时间戳/运镜(rewrite 不产生),只显示草稿文案。
// 跟 ShotCard(源视频)的区别:左竖条改用橙色,提示这是用户的版本草稿,不是源数据。
export function RewriteShotCard({ shot }: Props) {
  return (
    <section
      className={`${CARD_CLASS} border-l-4 border-l-[#7c2d12] dark:border-l-[#ea580c]`}
      data-testid={`rewrite-shot-card-${shot.shot_index}`}
    >
      <h3 className="text-base font-medium text-stone-900 dark:text-stone-50 mb-2">
        {COPY.shot_label_prefix}
        {shot.shot_index}
        {COPY.shot_label_suffix}
      </h3>
      <p className="text-[15px] leading-[1.65] text-stone-800 dark:text-stone-200 mb-2">
        {shot.dialogue.trim() || COPY.shot_dialogue_placeholder}
      </p>
      <p className="text-sm text-stone-500 dark:text-stone-400">{shot.visual}</p>
    </section>
  );
}
