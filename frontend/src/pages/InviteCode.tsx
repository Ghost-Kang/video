import { useState } from "react";

const STORAGE_KEY = "openrhtv_invite_code";

interface Props {
  onAccept: (code: string) => void;
}

// 内测准入门 — 在 Landing 之前。Founder 发邀请码,创作者输入后写
// localStorage,后续 WS auth 自动带上。Backend 在 INVITE_CODES 非空
// 时校验,空集则接受任意串 (dev 默认行为)。
export function InviteCode({ onAccept }: Props) {
  const [input, setInput] = useState("");
  const [submitting, setSubmitting] = useState(false);
  // W5D4 — true when we landed here because the backend rejected the stored
  // invite code (WS close 4003). useWebSocket cleared the bad code and fired
  // `rhtv-invite-rejected`, which dropped AppRoutes back to this gate. Show a
  // clear "码不对" hint instead of the old "填错也能进" lie.
  const [rejected] = useState(() => {
    try {
      return sessionStorage.getItem("openrhtv_invite_rejected") === "1";
    } catch {
      return false;
    }
  });

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const code = input.trim();
    if (!code || submitting) return;
    setSubmitting(true);
    try {
      sessionStorage.removeItem("openrhtv_invite_rejected");
    } catch {
      // ignore
    }
    try {
      localStorage.setItem(STORAGE_KEY, code);
    } catch {
      // private mode / cookie 关闭 — 用 sessionStorage fallback
      try {
        sessionStorage.setItem(STORAGE_KEY, code);
      } catch {
        // 都不行就给 in-memory pass
      }
    }
    onAccept(code);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--color-paper)] dark:bg-stone-950 px-6">
      <div className="w-full max-w-sm anim-fade-up">
        <p className="mb-3 text-[11px] uppercase tracking-[0.22em] text-stone-500 dark:text-stone-400 text-center">
          Cascade · 内测中
        </p>
        <h1 className="font-serif-cn text-3xl text-stone-900 dark:text-stone-50 text-center mb-3 tracking-[-0.02em]">
          输入邀请码
        </h1>
        <p className={`text-center text-sm mb-8 ${rejected ? "text-[#9a3412] dark:text-[#ea580c]" : "text-stone-500 dark:text-stone-400"}`}>
          {rejected
            ? "刚才那个邀请码后台没认出来,换一个有效的再试。"
            : "内测期间,需要邀请码才能开始。没有? 找朋友要一个。"}
        </p>

        <form onSubmit={submit} className="space-y-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="粘到这里"
            autoFocus
            disabled={submitting}
            aria-label="邀请码"
            className="w-full rounded-xl border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900 px-4 py-3 text-base text-stone-900 dark:text-stone-100 outline-none placeholder:text-stone-400 dark:placeholder:text-stone-500 focus:border-[#7c2d12] dark:focus:border-[#ea580c] transition-colors font-inherit text-center tracking-[0.04em]"
          />
          <button
            type="submit"
            disabled={!input.trim() || submitting}
            className="w-full rounded-xl bg-[#7c2d12] dark:bg-[#ea580c] py-3 text-[13px] font-medium tracking-[0.01em] text-[#faf8f3] transition-colors hover:bg-[#9a3412] dark:hover:bg-[#c2410c] disabled:opacity-40 disabled:cursor-not-allowed font-inherit"
          >
            进去看看
          </button>
        </form>

        <p className="mt-6 text-center text-[11px] text-stone-400 dark:text-stone-500">
          码不对会连不上 — 后台校验,填对才能开始
        </p>
      </div>
    </div>
  );
}

export function readInviteCode(): string | null {
  try {
    return (
      localStorage.getItem(STORAGE_KEY) || sessionStorage.getItem(STORAGE_KEY) || null
    );
  } catch {
    return null;
  }
}

export const INVITE_CODE_STORAGE_KEY = STORAGE_KEY;
