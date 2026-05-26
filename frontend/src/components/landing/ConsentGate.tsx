import { type ReactNode } from "react";
import { useConsent } from "../../hooks/useConsent";

// Phase C 改造:ConsentGate 不阻塞 children。
// 未同意时仅在底部显示极小法律链接,首次交互自动同意。
export function ConsentGate({ children }: { children: ReactNode }) {
  const { accepted, accept } = useConsent();

  const handleAutoAccept = () => {
    if (!accepted) void accept();
  };

  return (
    <>
      <div onClickCapture={handleAutoAccept}>{children}</div>
      {!accepted && (
        <p className="mt-14 text-[10px] uppercase tracking-[0.18em] text-stone-400">
          继续使用即同意{" "}
          <a
            href="/legal/user-agreement"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-stone-700 underline-offset-2 hover:underline"
          >
            用户协议
          </a>
          {" · "}
          <a
            href="/legal/privacy"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-stone-700 underline-offset-2 hover:underline"
          >
            隐私政策
          </a>
        </p>
      )}
    </>
  );
}
