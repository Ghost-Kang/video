import { COPY } from "../../lib/cardCopy";

interface Props {
  currentStep: 1 | 2;
}

const STEPS: Array<{ n: 1 | 2; titleKey: "onboarding_step1_title" | "onboarding_step2_title"; descKey: "onboarding_step1_desc" | "onboarding_step2_desc"; emoji: string }> = [
  { n: 1, titleKey: "onboarding_step1_title", descKey: "onboarding_step1_desc", emoji: "🔗" },
  { n: 2, titleKey: "onboarding_step2_title", descKey: "onboarding_step2_desc", emoji: "✨" },
];

export function OnboardingSteps({ currentStep }: Props) {
  return (
    <section
      aria-label="开始步骤"
      className="anim-fade-up"
    >
      <header className="text-center mb-8">
        <h1 className="font-serif-cn text-2xl md:text-3xl text-stone-900 dark:text-stone-50 tracking-[-0.02em]">
          {COPY.onboarding_title}
        </h1>
        <p className="mt-3 text-sm text-stone-500 dark:text-stone-400">
          {COPY.onboarding_subtitle}
        </p>
      </header>

      <ol className="grid grid-cols-1 md:grid-cols-2 gap-3 md:gap-4">
        {STEPS.map((s) => {
          const isActive = s.n === currentStep;
          const isDone = s.n < currentStep;
          const isFuture = s.n > currentStep;

          const base =
            "relative overflow-hidden rounded-2xl border p-5 backdrop-blur-md transition-all duration-300";
          const tone = isActive
            ? "border-[#7c2d12]/40 dark:border-[#ea580c]/50 bg-white/80 dark:bg-stone-900/70 glow-warm hover-glow"
            : isDone
              ? "border-emerald-500/30 bg-white/55 dark:bg-stone-900/55"
              : "border-stone-200/60 dark:border-stone-800/60 bg-white/40 dark:bg-stone-900/40 opacity-60";

          return (
            <li
              key={s.n}
              className={`${base} ${tone}`}
              aria-current={isActive ? "step" : undefined}
            >
              {isActive && (
                <span className="tech-topline pointer-events-none absolute inset-x-0 top-0 h-[3px]" aria-hidden />
              )}
              <div className="flex items-center gap-2 mb-2">
                <span
                  className={
                    "inline-flex h-6 w-6 items-center justify-center rounded-full text-[11px] font-medium " +
                    (isDone
                      ? "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400"
                      : isActive
                        ? "bg-[#7c2d12] dark:bg-[#ea580c] text-[#faf8f3]"
                        : "bg-stone-200 dark:bg-stone-800 text-stone-500 dark:text-stone-400")
                  }
                  aria-hidden
                >
                  {isDone ? "✓" : s.n}
                </span>
                <span
                  className="text-xl"
                  aria-hidden
                >
                  {s.emoji}
                </span>
              </div>
              <h2 className="font-serif-cn text-base text-stone-900 dark:text-stone-50">
                {COPY[s.titleKey]}
              </h2>
              <p className="mt-1 text-xs leading-[1.6] text-stone-500 dark:text-stone-400">
                {COPY[s.descKey]}
              </p>
              {isFuture && (
                <span className="sr-only">未开始</span>
              )}
            </li>
          );
        })}
      </ol>
    </section>
  );
}
