import { useState, useEffect, useRef } from "react";
import { ArrowRight, Link as LinkIcon } from "lucide-react";
import { useMagnetic } from "../../hooks/useMagnetic";
import { COPY } from "../../lib/cardCopy";

const PLACEHOLDERS = [
  "粘一条小红书链接",
  "粘一条抖音链接",
  "粘一条视频号链接",
];

function useTypewriterPlaceholder(phrases: string[], paused: boolean): string {
  const [text, setText] = useState("");

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | undefined;
    if (paused) {
      setText("");
      return () => {
        if (timer) clearTimeout(timer);
      };
    }
    let phraseIdx = 0;
    let charIdx = 0;
    let mode: "typing" | "holding" | "deleting" = "typing";

    const tick = () => {
      const target = phrases[phraseIdx];
      if (mode === "typing") {
        charIdx += 1;
        setText(target.slice(0, charIdx));
        if (charIdx >= target.length) {
          mode = "holding";
          timer = setTimeout(tick, 1600);
          return;
        }
        timer = setTimeout(tick, 60);
      } else if (mode === "holding") {
        mode = "deleting";
        timer = setTimeout(tick, 30);
      } else {
        charIdx -= 1;
        setText(target.slice(0, charIdx));
        if (charIdx <= 0) {
          phraseIdx = (phraseIdx + 1) % phrases.length;
          mode = "typing";
          timer = setTimeout(tick, 200);
          return;
        }
        timer = setTimeout(tick, 25);
      }
    };

    timer = setTimeout(tick, 400);
    return () => clearTimeout(timer);
  }, [phrases, paused]);

  return text;
}

export function UrlFallback({ onSubmit }: { onSubmit: (url: string) => void }) {
  const [url, setUrl] = useState("");
  const [focused, setFocused] = useState(false);
  const placeholder = useTypewriterPlaceholder(PLACEHOLDERS, focused || url.length > 0);
  const canSubmit = url.trim().length > 0;
  const btnRef = useMagnetic<HTMLButtonElement>(0.4, 110);
  const formRef = useRef<HTMLFormElement>(null);
  const submittedRef = useRef(false);

  const submit = (e: React.FormEvent | React.MouseEvent) => {
    e.preventDefault();
    if (!canSubmit || submittedRef.current) return;
    submittedRef.current = true;
    const el = formRef.current;
    if (el && "clientX" in e) {
      const rect = el.getBoundingClientRect();
      const dot = document.createElement("span");
      dot.className = "ripple-dot";
      dot.style.width = "10px";
      dot.style.height = "10px";
      dot.style.left = `${(e as React.MouseEvent).clientX - rect.left - 5}px`;
      dot.style.top = `${(e as React.MouseEvent).clientY - rect.top - 5}px`;
      el.appendChild(dot);
      setTimeout(() => dot.remove(), 750);
    }
    setTimeout(() => onSubmit(url.trim()), 180);
  };

  return (
    <div>
      <form
        ref={formRef}
        className={`group relative overflow-hidden flex items-center gap-3 rounded-2xl border-2 px-5 py-2 transition-all duration-300 ${
          canSubmit
            ? "border-[#7c2d12]/40 bg-white dark:bg-stone-900 shadow-[0_8px_32px_-8px_rgba(124,45,18,0.25)] anim-input-glow"
            : focused
              ? "border-stone-900 dark:border-stone-100 bg-white dark:bg-stone-900 shadow-soft-lg"
              : "border-stone-300/80 dark:border-stone-700/80 bg-white/50 dark:bg-stone-900/40 hover:border-stone-400 dark:hover:border-stone-600"
        }`}
        onSubmit={submit}
      >
        {/* paste indicator icon (左侧) */}
        <LinkIcon
          className={`h-5 w-5 shrink-0 transition-colors duration-300 ${
            canSubmit
              ? "text-[#7c2d12] dark:text-[#ea580c]"
              : focused
                ? "text-stone-900 dark:text-stone-100"
                : "text-stone-400 dark:text-stone-500"
          }`}
          aria-hidden
        />

        <input
          value={url}
          onChange={(event) => setUrl(event.target.value)}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          className="min-w-0 flex-1 bg-transparent text-base md:text-lg text-stone-900 dark:text-stone-100 outline-none placeholder:text-stone-500 dark:placeholder:text-stone-500 py-3 text-left font-medium"
          placeholder={placeholder + (placeholder ? " │" : "粘一条小红书 / 抖音链接")}
          aria-label="爆款视频链接"
          autoFocus
        />

        {/* CTA 按钮 — 主焦点 */}
        <button
          ref={btnRef}
          type="submit"
          onClick={submit}
          disabled={!canSubmit}
          className={`inline-flex items-center gap-2 rounded-full px-5 py-2.5 text-sm font-semibold whitespace-nowrap shrink-0 transition-colors duration-300 ${
            canSubmit
              ? "bg-[#7c2d12] hover:bg-[#9a3412] text-white anim-cta-glow"
              : "bg-stone-100 dark:bg-stone-800 text-stone-500 dark:text-stone-400 border border-stone-200 dark:border-stone-700 anim-cta-breathe cursor-default"
          }`}
        >
          拆解
          <ArrowRight
            className={`h-4 w-4 ${canSubmit ? "anim-arrow-nudge" : ""}`}
            aria-hidden
          />
        </button>
      </form>
      <p className="mt-2 text-center text-[11px] text-stone-500 dark:text-stone-400">
        {COPY.duration_hint}
      </p>
    </div>
  );
}
