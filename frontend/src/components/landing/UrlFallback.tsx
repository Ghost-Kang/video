import { useState, useEffect, useRef } from "react";
import { ArrowRight, Link as LinkIcon, Check, HelpCircle } from "lucide-react";
import { useMagnetic } from "../../hooks/useMagnetic";
import { COPY } from "../../lib/cardCopy";
import { checkLink } from "../../lib/linkValidator";
import { DurationSweetSpot } from "./DurationSweetSpot";

// 只承诺我们真能解析的(抖音);不再写「小红书」。
const PLACEHOLDERS = [COPY.url_placeholder_a, COPY.url_placeholder_b];

function useTypewriterPlaceholder(phrases: string[], paused: boolean): string {
  const [text, setText] = useState("");

  useEffect(() => {
    // paused 时不动状态(显示值在 return 处派生为 ""),避免 effect 里同步 setState
    // (react-hooks/set-state-in-effect)。
    if (paused) return;
    let timer: ReturnType<typeof setTimeout> | undefined;
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

    // 重启动画前先清上一轮残留(异步回调内 setState,规则允许),再 400ms 起打。
    timer = setTimeout(() => {
      setText("");
      timer = setTimeout(tick, 400);
    }, 0);
    return () => clearTimeout(timer);
  }, [phrases, paused]);

  // paused → 派生空串(用户聚焦/已输入时不打字机);恢复时 effect 重启动画。
  return paused ? "" : text;
}

export function UrlFallback({ onSubmit }: { onSubmit: (url: string) => void }) {
  const [url, setUrl] = useState("");
  const [focused, setFocused] = useState(false);
  const [submitErr, setSubmitErr] = useState<string | null>(null);
  const [showHelp, setShowHelp] = useState(false);
  const placeholder = useTypewriterPlaceholder(PLACEHOLDERS, focused || url.length > 0);
  const canSubmit = url.trim().length > 0;
  const check = checkLink(url);
  // 即时反馈:认出的(✓)/ 别的平台(立刻提示);「没认出」不打字时不唠叨,提交时才报。
  const livePlatformErr =
    !check.ok && check.reason === "platform"
      ? `${COPY.link_err_platform_prefix}${check.platform}${COPY.link_err_platform_suffix}`
      : null;
  const errorMsg = submitErr || livePlatformErr;
  const btnRef = useMagnetic<HTMLButtonElement>(0.4, 110);
  const formRef = useRef<HTMLFormElement>(null);
  const submittedRef = useRef(false);

  const submit = (e: React.FormEvent | React.MouseEvent) => {
    e.preventDefault();
    if (!canSubmit || submittedRef.current) return;
    const verdict = checkLink(url);
    if (!verdict.ok) {
      setSubmitErr(
        verdict.reason === "platform"
          ? `${COPY.link_err_platform_prefix}${verdict.platform}${COPY.link_err_platform_suffix}`
          : COPY.link_err_unknown,
      );
      setShowHelp(true);
      return;
    }
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
        className={`group relative overflow-hidden flex items-center gap-3 rounded-2xl border-2 px-5 py-2 backdrop-blur-md transition-all duration-300 ${
          canSubmit
            ? "border-[#7c2d12]/40 bg-white/90 dark:bg-stone-900/85 shadow-[0_8px_32px_-8px_rgba(124,45,18,0.25)] anim-input-glow"
            : focused
              ? "border-stone-900 dark:border-stone-100 bg-white/90 dark:bg-stone-900/85 shadow-soft-lg"
              : "border-stone-300/70 dark:border-stone-700/70 bg-white/55 dark:bg-stone-900/40 hover:border-[#7c2d12]/30 dark:hover:border-[#ea580c]/30 hover:shadow-[0_0_22px_-6px_rgba(234,88,12,0.35)]"
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
          onChange={(event) => {
            setUrl(event.target.value);
            if (submitErr) setSubmitErr(null);
          }}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          className="min-w-0 flex-1 bg-transparent text-base md:text-lg text-stone-900 dark:text-stone-100 outline-none placeholder:text-stone-500 dark:placeholder:text-stone-500 py-3 text-left font-medium"
          placeholder={placeholder + (placeholder ? " │" : COPY.url_placeholder_a)}
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

      {/* 即时反馈 / 引导 */}
      <div className="mt-2 min-h-[20px] text-[12px]">
        {errorMsg ? (
          <p className="anim-fade-in flex items-start gap-1.5 text-rose-500 dark:text-rose-400">
            <span>{errorMsg}</span>
          </p>
        ) : check.ok && url.trim() ? (
          <p className="anim-fade-in flex items-center gap-1 text-emerald-600 dark:text-emerald-400">
            <Check className="h-3.5 w-3.5" />
            {check.kind === "short" ? COPY.link_ok_short : COPY.link_ok_full}
          </p>
        ) : (
          <button
            type="button"
            onClick={() => setShowHelp((v) => !v)}
            className="inline-flex items-center gap-1 text-stone-400 transition-colors hover:text-[#7c2d12] dark:text-stone-500 dark:hover:text-[#ea580c]"
          >
            <HelpCircle className="h-3.5 w-3.5" />
            {COPY.link_help_toggle}
          </button>
        )}
      </div>

      {/* 怎么复制链接 —— 引导 */}
      {showHelp && (
        <div className="anim-fade-in mt-2 space-y-2.5 rounded-xl border border-stone-200/60 bg-white/60 p-3.5 text-left backdrop-blur-sm dark:border-stone-700/50 dark:bg-stone-900/40">
          <div className="flex items-start gap-2">
            <span className="mt-0.5 shrink-0 rounded-md bg-[#7c2d12]/[0.08] px-1.5 py-0.5 text-[11px] font-medium text-[#7c2d12] dark:bg-[#ea580c]/15 dark:text-[#ea580c]">
              {COPY.link_help_desktop_t}
            </span>
            <p className="text-[12.5px] leading-[1.6] text-stone-600 dark:text-stone-300">
              {COPY.link_help_desktop_d}
            </p>
          </div>
          <div className="flex items-start gap-2">
            <span className="mt-0.5 shrink-0 rounded-md bg-stone-100 px-1.5 py-0.5 text-[11px] font-medium text-stone-500 dark:bg-stone-800 dark:text-stone-400">
              {COPY.link_help_app_t}
            </span>
            <p className="text-[12.5px] leading-[1.6] text-stone-600 dark:text-stone-300">
              {COPY.link_help_app_d}
            </p>
          </div>
        </div>
      )}

      {/* 时长甜蜜点 */}
      <DurationSweetSpot />
    </div>
  );
}
