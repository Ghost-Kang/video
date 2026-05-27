import { useId } from "react";

/**
 * 3 个 niche 的 SVG 场景插画 v3 — 显式深色 palette + useId() 解决 defs id 冲突
 * 之前 bowl-grad / mom-grad 是全局 id,3 张同 niche 卡共用导致 fill="url(#X)" 引用错乱
 * 现在用 useId() 给每个 instance 唯一 suffix,完全隔离
 */

interface SceneProps {
  className?: string;
  style?: React.CSSProperties;
}

export function FushiScene({ className = "", style }: SceneProps) {
  const uid = useId();
  const bowlId = `bowl-${uid}`;
  const foodId = `food-${uid}`;
  const spoonId = `spoon-${uid}`;
  return (
    <svg viewBox="0 0 120 120" className={className} style={style} fill="none" aria-hidden>
      <defs>
        <linearGradient id={bowlId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#7c2d12" />
          <stop offset="100%" stopColor="#431407" />
        </linearGradient>
        <linearGradient id={foodId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#fb923c" />
          <stop offset="100%" stopColor="#c2410c" />
        </linearGradient>
        <linearGradient id={spoonId} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#a16207" />
          <stop offset="100%" stopColor="#713f12" />
        </linearGradient>
      </defs>

      {/* 3 道蒸汽 — 深 stone 色,粗描边 */}
      <g strokeLinecap="round" strokeWidth="2.5" stroke="#57534e" fill="none">
        <path d="M45 32 Q49 24 45 16 Q41 10 45 4" className="anim-steam" style={{ animationDelay: "0s" }} />
        <path d="M60 32 Q64 24 60 16 Q56 10 60 4" className="anim-steam" style={{ animationDelay: "0.4s" }} />
        <path d="M75 32 Q79 24 75 16 Q71 10 75 4" className="anim-steam" style={{ animationDelay: "0.8s" }} />
      </g>

      {/* 桌面阴影 */}
      <ellipse cx="60" cy="100" rx="42" ry="3.5" fill="#1c1917" opacity="0.22" />

      {/* 木勺 — wobble 摇动 */}
      <g className="anim-wobble" style={{ transformOrigin: "85px 50px" }}>
        <line x1="86" y1="50" x2="112" y2="20" stroke={`url(#${spoonId})`} strokeWidth="4" strokeLinecap="round" />
        <ellipse cx="83" cy="53" rx="8" ry="5" fill={`url(#${spoonId})`} transform="rotate(-35 83 53)" />
        {/* 勺心高光 */}
        <ellipse cx="81" cy="51" rx="3.5" ry="2" fill="#fef3c7" opacity="0.5" transform="rotate(-35 81 51)" />
      </g>

      {/* 碗体 */}
      <path d="M22 52 Q22 92 60 96 Q98 92 98 52 Z" fill={`url(#${bowlId})`} />

      {/* 碗内食物 */}
      <ellipse cx="60" cy="54" rx="36" ry="5" fill={`url(#${foodId})`} />
      {/* 食物粒子 — 几颗深一点的点装饰 */}
      <circle cx="48" cy="53" r="1.5" fill="#7c2d12" opacity="0.6" />
      <circle cx="68" cy="55" r="1.2" fill="#7c2d12" opacity="0.5" />
      <circle cx="74" cy="52" r="1" fill="#7c2d12" opacity="0.5" />

      {/* 碗口高光 */}
      <path d="M22 52 Q60 56 98 52" stroke="#fef3c7" strokeWidth="1.5" fill="none" opacity="0.45" />

      {/* 碗腰带装饰 */}
      <path d="M28 75 Q60 80 92 75" stroke="#fde68a" strokeWidth="1" fill="none" opacity="0.4" />
    </svg>
  );
}

export function YuerScene({ className = "", style }: SceneProps) {
  const uid = useId();
  const momId = `mom-${uid}`;
  const babyId = `baby-${uid}`;
  const heartId = `heart-${uid}`;
  return (
    <svg viewBox="0 0 120 120" className={className} style={style} fill="none" aria-hidden>
      <defs>
        <linearGradient id={momId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#9f1239" />
          <stop offset="100%" stopColor="#500724" />
        </linearGradient>
        <linearGradient id={babyId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#fef3c7" />
          <stop offset="100%" stopColor="#fcd34d" />
        </linearGradient>
        <linearGradient id={heartId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#ef4444" />
          <stop offset="100%" stopColor="#b91c1c" />
        </linearGradient>
      </defs>

      {/* Sparkles 装饰 */}
      <g fill="#eab308">
        <text x="16" y="32" fontSize="16" className="anim-float-a">✦</text>
        <text x="98" y="38" fontSize="13" className="anim-float-b">✦</text>
        <text x="100" y="98" fontSize="11" className="anim-float-c">✦</text>
        <text x="14" y="92" fontSize="10" className="anim-float-b" style={{ animationDelay: "0.5s" }}>✦</text>
      </g>

      {/* 妈妈身体 */}
      <path
        d="M28 112 Q28 75 54 70 Q54 50 65 50 Q76 50 76 70 Q102 75 102 112 Z"
        fill={`url(#${momId})`}
      />
      {/* 妈妈头 */}
      <circle cx="65" cy="38" r="14" fill="#7f1d1d" />
      {/* 妈妈发髻 */}
      <ellipse cx="65" cy="26" rx="10" ry="6" fill="#450a0a" />
      {/* 妈妈脸高光 */}
      <ellipse cx="61" cy="36" rx="2" ry="2.5" fill="#fef3c7" opacity="0.35" />

      {/* 宝宝 */}
      <g>
        <circle cx="48" cy="84" r="14" fill={`url(#${babyId})`} />
        <circle cx="48" cy="66" r="11" fill={`url(#${babyId})`} />
        <path d="M44 55 Q48 49 52 55" stroke="#7c2d12" strokeWidth="2.2" fill="none" strokeLinecap="round" />
        <g className="anim-blink" style={{ transformOrigin: "44px 67px" }}>
          <ellipse cx="44" cy="67" rx="2" ry="2.5" fill="#1c1917" />
        </g>
        <g className="anim-blink" style={{ transformOrigin: "52px 67px", animationDelay: "0.05s" }}>
          <ellipse cx="52" cy="67" rx="2" ry="2.5" fill="#1c1917" />
        </g>
        <path d="M45 72 Q48 75 51 72" stroke="#9f1239" strokeWidth="1.6" fill="none" strokeLinecap="round" />
        <circle cx="40" cy="71" r="2.2" fill="#fb7185" opacity="0.6" />
        <circle cx="56" cy="71" r="2.2" fill="#fb7185" opacity="0.6" />
      </g>

      {/* 心 */}
      <g className="anim-heart-beat" style={{ transformOrigin: "85px 55px" }}>
        <path
          d="M85 67
             C 79 62, 73 56, 76 50
             C 78 47, 82 47, 85 51
             C 88 47, 92 47, 94 50
             C 97 56, 91 62, 85 67 Z"
          fill={`url(#${heartId})`}
          stroke="#7f1d1d"
          strokeWidth="0.5"
        />
        <ellipse cx="81" cy="54" rx="2" ry="3" fill="white" opacity="0.5" transform="rotate(-20 81 54)" />
      </g>
    </svg>
  );
}

export function ChufangScene({ className = "", style }: SceneProps) {
  const uid = useId();
  const potId = `pot-${uid}`;
  const lidId = `lid-${uid}`;
  const flameId = `flame-${uid}`;
  return (
    <svg viewBox="0 0 120 120" className={className} style={style} fill="none" aria-hidden>
      <defs>
        <linearGradient id={potId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#44403c" />
          <stop offset="100%" stopColor="#1c1917" />
        </linearGradient>
        <linearGradient id={lidId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#57534e" />
          <stop offset="100%" stopColor="#292524" />
        </linearGradient>
        <radialGradient id={flameId} cx="50%" cy="80%" r="60%">
          <stop offset="0%" stopColor="#fef08a" />
          <stop offset="40%" stopColor="#f97316" />
          <stop offset="100%" stopColor="#b91c1c" />
        </radialGradient>
      </defs>

      <g strokeLinecap="round" strokeWidth="2.5" stroke="#78716c" fill="none">
        <path d="M45 30 Q49 22 45 14 Q41 8 45 2" className="anim-steam" style={{ animationDelay: "0s" }} />
        <path d="M60 28 Q64 20 60 12 Q56 6 60 0" className="anim-steam" style={{ animationDelay: "0.35s" }} />
        <path d="M75 30 Q79 22 75 14 Q71 8 75 2" className="anim-steam" style={{ animationDelay: "0.7s" }} />
      </g>

      <rect x="54" y="32" width="12" height="7" rx="2.5" fill={`url(#${lidId})`} />
      <path d="M20 50 Q20 38 60 38 Q100 38 100 50 Z" fill={`url(#${lidId})`} />
      <line x1="18" y1="51" x2="102" y2="51" stroke="#1c1917" strokeWidth="2" />

      <path d="M18 52 L18 84 Q18 94 28 94 L92 94 Q102 94 102 84 L102 52 Z" fill={`url(#${potId})`} />

      <ellipse cx="13" cy="65" rx="5" ry="4" fill={`url(#${potId})`} />
      <ellipse cx="107" cy="65" rx="5" ry="4" fill={`url(#${potId})`} />

      <line x1="22" y1="60" x2="98" y2="60" stroke="#a8a29e" strokeWidth="0.6" opacity="0.4" />
      <line x1="8" y1="98" x2="112" y2="98" stroke="#44403c" strokeWidth="2" />

      <g>
        <path
          d="M40 114 Q36 102 44 98 Q42 105 47 105 Q45 100 51 102 Q48 108 43 114 Z"
          fill={`url(#${flameId})`}
          className="anim-flame"
          style={{ transformOrigin: "46px 114px", animationDelay: "0s" }}
        />
        <path
          d="M55 116 Q51 104 60 100 Q57 107 63 107 Q60 101 67 103 Q62 110 58 116 Z"
          fill={`url(#${flameId})`}
          className="anim-flame"
          style={{ transformOrigin: "60px 116px", animationDelay: "0.12s" }}
        />
        <path
          d="M72 114 Q68 102 76 98 Q74 105 79 105 Q77 100 83 102 Q80 108 75 114 Z"
          fill={`url(#${flameId})`}
          className="anim-flame"
          style={{ transformOrigin: "77px 114px", animationDelay: "0.24s" }}
        />
        <circle cx="46" cy="100" r="1.5" fill="#fef3c7" opacity="0.7" className="anim-flame" style={{ animationDelay: "0s" }} />
        <circle cx="60" cy="102" r="1.5" fill="#fef3c7" opacity="0.7" className="anim-flame" style={{ animationDelay: "0.12s" }} />
        <circle cx="77" cy="100" r="1.5" fill="#fef3c7" opacity="0.7" className="anim-flame" style={{ animationDelay: "0.24s" }} />
      </g>
    </svg>
  );
}
