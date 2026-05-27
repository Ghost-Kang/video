import { useEffect, useRef, useState } from "react";
import { Sparkles, Zap, TrendingUp, Heart, Clock } from "lucide-react";

interface Activity {
  text: string;
  Icon: typeof Sparkles;
  tone: "clay" | "rose" | "amber" | "emerald";
}

const ACTIVITIES: Activity[] = [
  { text: "宝宝妈正在改写一条 8 万赞辅食视频", Icon: Zap, tone: "clay" },
  { text: "@朵朵妈 7 分钟前完成了第一条", Icon: Sparkles, tone: "rose" },
  { text: "本周 12 位创作者拿到 publish_pack", Icon: TrendingUp, tone: "emerald" },
  { text: "@芒果 刚刚拆解了《一周不重样辅食》", Icon: Zap, tone: "clay" },
  { text: "@单单妈 把「开头三秒」改了 3 版", Icon: Sparkles, tone: "rose" },
  { text: "@诗小馒 在调「卡通馒头」的封面", Icon: Heart, tone: "amber" },
  { text: "Cascade 今天分析了 47 条爆款", Icon: TrendingUp, tone: "emerald" },
  { text: "平均拆解耗时 26 秒", Icon: Clock, tone: "clay" },
];

const TONE_CLS: Record<
  Activity["tone"],
  { dot: string; icon: string; iconDark: string; chipHover: string }
> = {
  clay: {
    dot: "bg-[#7c2d12] dark:bg-[#ea580c]",
    icon: "text-[#7c2d12]",
    iconDark: "dark:text-[#ea580c]",
    chipHover: "hover:bg-[#7c2d12]/10 dark:hover:bg-[#ea580c]/15",
  },
  rose: {
    dot: "bg-rose-600 dark:bg-rose-400",
    icon: "text-rose-700",
    iconDark: "dark:text-rose-400",
    chipHover: "hover:bg-rose-600/10 dark:hover:bg-rose-400/15",
  },
  amber: {
    dot: "bg-amber-600 dark:bg-amber-400",
    icon: "text-amber-700",
    iconDark: "dark:text-amber-400",
    chipHover: "hover:bg-amber-600/10 dark:hover:bg-amber-400/15",
  },
  emerald: {
    dot: "bg-emerald-600 dark:bg-emerald-400",
    icon: "text-emerald-700",
    iconDark: "dark:text-emerald-400",
    chipHover: "hover:bg-emerald-600/10 dark:hover:bg-emerald-400/15",
  },
};

export function CreatorTicker() {
  const items = [...ACTIVITIES, ...ACTIVITIES];
  const ref = useRef<HTMLDivElement>(null);
  const [offsetY, setOffsetY] = useState(0);

  useEffect(() => {
    let raf = 0;
    const update = () => {
      const el = ref.current;
      if (!el) return;
      const rect = el.getBoundingClientRect();
      const vh = window.innerHeight;
      const enter = Math.min(1, Math.max(0, (vh - rect.top) / (vh + rect.height)));
      setOffsetY((1 - enter) * 20);
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
      className="select-none border-t border-b border-stone-200/70 dark:border-stone-800/70 bg-[var(--color-paper-deeper)]/50 dark:bg-stone-900/40 backdrop-blur-sm py-4 transition-transform duration-300 marquee-pause-on-hover"
      style={{ transform: `translateY(${offsetY}px)` }}
    >
      {/* eyebrow */}
      <div className="px-6 mb-3 text-center text-[10px] uppercase tracking-[0.22em] text-stone-500 dark:text-stone-400">
        <span className="inline-flex items-center gap-2">
          <span className="relative inline-flex h-1.5 w-1.5">
            <span className="absolute inset-0 rounded-full bg-emerald-500 anim-pulse-ring" />
            <span className="relative h-1.5 w-1.5 rounded-full bg-emerald-500" />
          </span>
          实时活动
        </span>
      </div>

      {/* ticker row — 边缘 fade,hover 暂停 */}
      <div className="overflow-hidden marquee-fade">
        <div className="anim-marquee-fast flex gap-3 whitespace-nowrap will-change-transform">
          {items.map((act, i) => {
            const t = TONE_CLS[act.tone];
            const { Icon } = act;
            return (
              <span
                key={i}
                className={`group inline-flex items-center gap-2.5 rounded-full border border-stone-200/80 dark:border-stone-700/80 bg-white/70 dark:bg-stone-950/40 px-4 py-2 text-sm text-stone-700 dark:text-stone-200 transition-all duration-300 cursor-default ${t.chipHover} hover:scale-[1.06] hover:border-stone-400 dark:hover:border-stone-500 hover:shadow-soft`}
              >
                <span className={`h-1.5 w-1.5 rounded-full ${t.dot} group-hover:scale-150 transition-transform duration-300`} aria-hidden />
                <Icon
                  className={`h-3.5 w-3.5 ${t.icon} ${t.iconDark} group-hover:rotate-12 transition-transform duration-300`}
                  aria-hidden
                />
                <span className="font-medium">{act.text}</span>
              </span>
            );
          })}
        </div>
      </div>
    </div>
  );
}
