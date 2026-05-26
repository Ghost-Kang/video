import { useState, useCallback } from "react";
import { ArrowRight } from "lucide-react";
import { PageShell } from "./PageShell";
import { useMagnetic } from "../hooks/useMagnetic";

interface Props {
  onLogin: (userId: string) => void;
}

export function Login({ onLogin }: Props) {
  const [id, setId] = useState("");
  const [error, setError] = useState("");
  const canSubmit = id.trim().length > 0;
  const btnRef = useMagnetic<HTMLButtonElement>(0.4, 110);

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      const uid = id.trim();
      if (!uid) {
        setError("请输入工号");
        return;
      }
      setError("");
      localStorage.setItem("rhtv_user", uid);
      onLogin(uid);
    },
    [id, onLogin],
  );

  return (
    <PageShell showProgress={false}>
      <div className="flex-1 flex items-center justify-center px-6 py-16">
        <form
          onSubmit={handleSubmit}
          className="anim-fade-up w-full max-w-md"
          style={{ animationDelay: "100ms" }}
        >
          {/* eyebrow */}
          <p className="mb-8 text-[11px] uppercase tracking-[0.22em] text-stone-500 dark:text-stone-400 text-center">
            <span className="inline-flex items-center gap-2">
              <span className="relative inline-flex h-1.5 w-1.5">
                <span className="absolute inset-0 rounded-full bg-emerald-500 anim-pulse-ring" />
                <span className="relative h-1.5 w-1.5 rounded-full bg-emerald-500" />
              </span>
              Cascade · 内测中
            </span>
          </p>

          {/* hero */}
          <h1 className="font-serif-cn text-4xl md:text-5xl text-stone-900 dark:text-stone-50 leading-[1.3] mb-3 text-center">
            欢迎{" "}
            <span className="text-shimmer-clay italic inline-block px-1.5">回来</span>
          </h1>

          <p className="text-base text-stone-500 dark:text-stone-400 leading-relaxed mb-12 text-center">
            输入你的工号继续创作。
          </p>

          {/* input card */}
          <div
            className={`group relative overflow-hidden flex items-center gap-3 rounded-2xl border-2 px-5 py-2 transition-all duration-300 ${
              canSubmit
                ? "border-[#7c2d12]/40 bg-white dark:bg-stone-900 shadow-[0_8px_32px_-8px_rgba(124,45,18,0.25)] anim-input-glow"
                : "border-stone-300/80 dark:border-stone-700/80 bg-white/60 dark:bg-stone-900/40 focus-within:border-stone-900 dark:focus-within:border-stone-100 focus-within:bg-white dark:focus-within:bg-stone-900"
            }`}
          >
            <input
              value={id}
              onChange={(e) => setId(e.target.value)}
              placeholder="输入工号"
              className="min-w-0 flex-1 bg-transparent text-base md:text-lg text-stone-900 dark:text-stone-100 outline-none placeholder:text-stone-500 dark:placeholder:text-stone-500 py-3 text-left font-medium"
              autoFocus
              aria-label="工号"
            />
            <button
              ref={btnRef}
              type="submit"
              disabled={!canSubmit}
              className={`inline-flex items-center gap-2 rounded-full px-5 py-2.5 text-sm font-semibold whitespace-nowrap shrink-0 transition-colors duration-300 ${
                canSubmit
                  ? "bg-[#7c2d12] hover:bg-[#9a3412] text-white anim-cta-glow"
                  : "bg-stone-100 dark:bg-stone-800 text-stone-500 dark:text-stone-400 border border-stone-200 dark:border-stone-700 anim-cta-breathe cursor-default"
              }`}
            >
              登录
              <ArrowRight
                className={`h-4 w-4 ${canSubmit ? "anim-arrow-nudge" : ""}`}
                aria-hidden
              />
            </button>
          </div>

          {error && (
            <p
              className="mt-4 text-center text-sm text-rose-600 dark:text-rose-400"
              role="alert"
            >
              {error}
            </p>
          )}

          <p className="mt-12 text-center text-[11px] uppercase tracking-[0.22em] text-stone-400 dark:text-stone-600">
            没有工号?{" "}
            <a
              href="/"
              className="text-stone-700 dark:text-stone-300 hover:text-[#7c2d12] dark:hover:text-[#ea580c] underline underline-offset-4 transition-colors"
            >
              先看 demo
            </a>
          </p>
        </form>
      </div>
    </PageShell>
  );
}
