import { type ReactNode } from "react";
import { useConsent } from "../../hooks/useConsent";

export function ConsentGate({ children }: { children: ReactNode }) {
  const { accepted, accept } = useConsent();

  if (accepted) {
    return (
      <>
        <div className="mb-4 inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-1 text-xs text-emerald-700">
          <span aria-hidden>✓</span>
          <span>已同意 v0 协议</span>
        </div>
        {children}
      </>
    );
  }

  return (
    <>
      <div
        data-testid="consent-block"
        className="mb-6 rounded-2xl border border-amber-200 bg-amber-50/60 p-4"
      >
        <p className="mb-2 text-sm text-amber-900">先勾选同意才能开始 ↓</p>
        <label className="flex cursor-pointer items-start gap-2 text-sm text-stone-800">
          <input
            type="checkbox"
            data-testid="consent-checkbox"
            className="mt-1 h-4 w-4 cursor-pointer accent-orange-500"
            checked={false}
            onChange={() => {
              void accept();
            }}
          />
          <span>
            我已阅读并同意{" "}
            <a
              href="/legal/user-agreement"
              target="_blank"
              rel="noopener noreferrer"
              className="text-orange-600 underline underline-offset-2 hover:text-orange-700"
            >
              《用户协议 v0》
            </a>{" "}
            和{" "}
            <a
              href="/legal/privacy"
              target="_blank"
              rel="noopener noreferrer"
              className="text-orange-600 underline underline-offset-2 hover:text-orange-700"
            >
              《隐私政策 v0》
            </a>
            <span className="ml-1 text-stone-500">
              (本服务为 Phase 1 内测,公测前协议将完整重写)
            </span>
          </span>
        </label>
      </div>
      <div
        data-testid="consent-gated"
        aria-disabled="true"
        className="pointer-events-none opacity-50"
      >
        {children}
      </div>
    </>
  );
}
