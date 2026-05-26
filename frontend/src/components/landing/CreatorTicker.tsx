import { useEffect, useRef, useState } from "react";

const ACTIVITIES = [
  "宝宝妈正在改写一条 8 万赞辅食视频",
  "@朵朵妈 7 分钟前完成了第一条",
  "本周 12 位创作者拿到 publish_pack",
  "@芒果 刚刚拆解了《一周不重样辅食》",
  "@单单妈 把「开头三秒」改了 3 版",
  "@诗小馒 在调「卡通馒头」的封面",
  "Cascade 今天分析了 47 条爆款",
  "平均拆解耗时 26 秒",
];

export function CreatorTicker() {
  const items = [...ACTIVITIES, ...ACTIVITIES];
  const ref = useRef<HTMLDivElement>(null);
  const [offsetY, setOffsetY] = useState(0);

  // 反向滚动视差 — 下滚时 ticker 区域略微向上漂移
  useEffect(() => {
    let raf = 0;
    const update = () => {
      const el = ref.current;
      if (!el) return;
      const rect = el.getBoundingClientRect();
      const vh = window.innerHeight;
      // 当 ticker 进入视口 → 0..1
      const enter = Math.min(1, Math.max(0, (vh - rect.top) / (vh + rect.height)));
      setOffsetY((1 - enter) * 20);  // 最多上漂 20px
    };
    const onScroll = () => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(update);
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    update();
    return () => {
      window.removeEventListener("scroll", onScroll);
      cancelAnimationFrame(raf);
    };
  }, []);

  return (
    <div
      ref={ref}
      className="pointer-events-none select-none overflow-hidden border-t border-stone-200/60 dark:border-stone-800/60 py-3 transition-transform duration-300"
      style={{ transform: `translateY(${offsetY}px)` }}
    >
      <div className="anim-marquee flex gap-12 whitespace-nowrap">
        {items.map((text, i) => (
          <span
            key={i}
            className="text-[11px] uppercase tracking-[0.15em] text-stone-400 dark:text-stone-600 inline-flex items-center gap-3"
          >
            <span className="h-1 w-1 rounded-full bg-[#7c2d12]/40 dark:bg-[#ea580c]/50" aria-hidden />
            {text}
          </span>
        ))}
      </div>
    </div>
  );
}
