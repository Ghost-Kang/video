import { type ReactNode, useRef } from "react";
import { useConsent } from "../../hooks/useConsent";

// Phase C 改造:ConsentGate 不阻塞 children。
// v8 fix:在 onClickCapture 加 in-flight ref guard,防止极快双击触发两次 accept() + 两次 POST。
export function ConsentGate({ children }: { children: ReactNode }) {
  const { accepted, accept } = useConsent();
  const inflightRef = useRef(false);

  const handleAutoAccept = () => {
    if (accepted || inflightRef.current) return;
    inflightRef.current = true;
    void accept().finally(() => {
      // accept 已经写入 localStorage + setRecord,后续 accepted 会变 true
      // 保留 ref true 直到组件卸载,防止 storage 更新延迟期间又一次进入
    });
  };

  return (
    <>
      <div onClickCapture={handleAutoAccept}>{children}</div>
      {!accepted && (
        <p className="mt-14 text-[10px] uppercase tracking-[0.18em] text-stone-400 dark:text-stone-600">
          继续使用即同意{" "}
          <a
            href="/legal/user-agreement"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-stone-700 dark:hover:text-stone-300 underline-offset-2 hover:underline"
          >
            用户协议
          </a>
          {" · "}
          <a
            href="/legal/privacy"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-stone-700 dark:hover:text-stone-300 underline-offset-2 hover:underline"
          >
            隐私政策
          </a>
        </p>
      )}
    </>
  );
}
