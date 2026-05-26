import { useRef, useState } from "react";
import { ArrowUpRight } from "lucide-react";
import { FushiScene, YuerScene, ChufangScene } from "./NicheIllustration";

export interface FeaturedCard {
  id: string;
  niche: string;
  thumbnail_url: string;
  title_three_lines: string[];
  fixture_analysis_id: string;
}

const NICHE_META: Record<
  string,
  {
    label: string;
    Scene: typeof FushiScene;
    gradient: string;
  }
> = {
  baomam_fushi: {
    label: "宝妈辅食",
    Scene: FushiScene,
    gradient: "bg-[radial-gradient(120%_120%_at_30%_20%,#fff8e7_0%,#fbd8a5_45%,#d4945a_100%)]",
  },
  yuer_richang: {
    label: "育儿日常",
    Scene: YuerScene,
    gradient: "bg-[radial-gradient(120%_120%_at_70%_30%,#ffeaef_0%,#fbc4cf_45%,#d68fa0_100%)]",
  },
  jiating_chufang: {
    label: "家庭厨房",
    Scene: ChufangScene,
    gradient: "bg-[radial-gradient(120%_120%_at_50%_30%,#fff9d6_0%,#fbe085_45%,#d4a83c_100%)]",
  },
};

export function HotCard({ card, onPick }: { card: FeaturedCard; onPick: (card: FeaturedCard) => void }) {
  const meta = NICHE_META[card.niche] || NICHE_META.baomam_fushi;
  const { Scene } = meta;
  const imgRef = useRef<HTMLDivElement>(null);
  const wrapRef = useRef<HTMLElement>(null);
  const [tilt, setTilt] = useState({ rx: 0, ry: 0, glareX: 50, glareY: 50, tx: 0, ty: 0 });
  const [hovered, setHovered] = useState(false);

  const handleMove = (e: React.MouseEvent) => {
    const el = imgRef.current;
    const wrap = wrapRef.current;
    if (!el || !wrap) return;
    const rect = el.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width;
    const y = (e.clientY - rect.top) / rect.height;
    const ry = (x - 0.5) * 8;
    const rx = (0.5 - y) * 8;
    const wrapRect = wrap.getBoundingClientRect();
    const cx = wrapRect.left + wrapRect.width / 2;
    const cy = wrapRect.top + wrapRect.height / 2;
    const tx = (e.clientX - cx) * 0.04;
    const ty = (e.clientY - cy) * 0.04;
    setTilt({ rx, ry, glareX: x * 100, glareY: y * 100, tx, ty });
  };

  const handleLeave = () => {
    setTilt({ rx: 0, ry: 0, glareX: 50, glareY: 50, tx: 0, ty: 0 });
    setHovered(false);
  };

  const handleClick = (e: React.MouseEvent) => {
    const el = imgRef.current;
    if (el) {
      const rect = el.getBoundingClientRect();
      const size = 12;
      const dot = document.createElement("span");
      dot.className = "ripple-dot";
      dot.style.width = `${size}px`;
      dot.style.height = `${size}px`;
      dot.style.left = `${e.clientX - rect.left - size / 2}px`;
      dot.style.top = `${e.clientY - rect.top - size / 2}px`;
      el.appendChild(dot);
      setTimeout(() => dot.remove(), 750);
    }
    setTimeout(() => onPick(card), 180);
  };

  return (
    <article
      ref={wrapRef}
      className="group relative cursor-pointer text-left"
      onClick={handleClick}
      onMouseMove={handleMove}
      onMouseLeave={handleLeave}
      onMouseEnter={() => setHovered(true)}
      style={{
        perspective: "800px",
        transform: `translate(${tilt.tx}px, ${tilt.ty}px)`,
        transition:
          tilt.tx === 0 && tilt.ty === 0
            ? "transform 0.4s cubic-bezier(0.16, 1, 0.3, 1)"
            : "transform 0.15s cubic-bezier(0.16, 1, 0.3, 1)",
      }}
    >
      <div
        ref={imgRef}
        className={`relative aspect-[4/3] rounded-xl overflow-hidden ${meta.gradient} mb-3 will-change-transform`}
        style={{
          transform: `rotateX(${tilt.rx}deg) rotateY(${tilt.ry}deg) scale(${tilt.rx === 0 && tilt.ry === 0 ? 1 : 1.025})`,
          transition: "transform 0.25s cubic-bezier(0.16, 1, 0.3, 1)",
          transformStyle: "preserve-3d",
          boxShadow:
            tilt.rx === 0 && tilt.ry === 0
              ? "0 1px 2px rgba(28,25,23,0.04), 0 4px 12px -2px rgba(28,25,23,0.06)"
              : "0 8px 32px -8px rgba(28,25,23,0.18)",
        }}
      >
        {card.thumbnail_url ? (
          <img src={card.thumbnail_url} alt="" className="h-full w-full object-cover" />
        ) : (
          <>
            {/* SVG 场景插画 — 居中,响应 currentColor,占满 80% */}
            <div className="absolute inset-0 flex items-center justify-center p-4">
              <Scene
                className="h-full w-auto max-w-[85%] transition-all duration-[600ms] ease-out"
                style={{
                  transform: hovered ? "rotate(-3deg) scale(1.06)" : "rotate(0deg) scale(1)",
                  filter: "drop-shadow(0 6px 14px rgba(0,0,0,0.15))",
                }}
              />
            </div>

            {/* niche label — 左下 chip,毛玻璃 */}
            <span className="absolute bottom-3 left-3 rounded-full bg-white/75 dark:bg-stone-950/65 backdrop-blur-sm px-2.5 py-0.5 text-[10px] font-medium uppercase tracking-[0.15em] text-stone-800 dark:text-stone-100 shadow-sm">
              {meta.label}
            </span>
          </>
        )}

        {/* glare 高光 */}
        <div
          aria-hidden
          className="absolute inset-0 pointer-events-none"
          style={{
            background: `radial-gradient(circle at ${tilt.glareX}% ${tilt.glareY}%, rgba(255,255,255,0.45) 0%, transparent 45%)`,
            opacity: tilt.rx === 0 && tilt.ry === 0 ? 0 : 1,
            transition: "opacity 0.3s ease-out",
          }}
        />
      </div>

      <h2 className="font-serif-cn text-sm text-stone-900 dark:text-stone-100 leading-snug mb-2 group-hover:text-[#7c2d12] dark:group-hover:text-[#ea580c] transition-colors">
        {card.title_three_lines[0]}
        <ArrowUpRight
          className="inline h-3.5 w-3.5 ml-1 -translate-y-0.5 opacity-0 group-hover:opacity-100 group-hover:translate-x-0.5 transition-all duration-300"
          aria-hidden
        />
      </h2>
    </article>
  );
}
