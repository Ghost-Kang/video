import { useEffect, useState } from "react";

export function WaitlistCta() {
  const [visible, setVisible] = useState(false);
  const [open, setOpen] = useState(false);
  const [contact, setContact] = useState("");
  const [toast, setToast] = useState("");

  useEffect(() => {
    const onScroll = () => setVisible(window.scrollY > window.innerHeight * 0.5);
    onScroll();
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <>
      {visible && (
        <div className="fixed inset-x-0 bottom-0 z-30 border-t border-stone-200 bg-white/95 p-3">
          <div className="mx-auto flex max-w-[720px] items-center justify-between gap-3">
            <span className="text-sm text-stone-700">内测 10 人 · 6 周免费 · 我陪你做完第一条</span>
            <button type="button" className="bg-orange-500 hover:bg-orange-600 text-white rounded-xl py-3 px-5 font-medium" onClick={() => setOpen(true)}>
              私信我加入
            </button>
          </div>
        </div>
      )}
      {open && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/20 p-4">
          <form
            className="w-full max-w-sm rounded-2xl bg-white p-5 shadow-lg"
            onSubmit={(event) => {
              event.preventDefault();
              console.log("waitlist", contact);
              setToast("我们收到了");
              setOpen(false);
            }}
          >
            <label className="mb-2 block text-sm text-stone-600">微信号或私信链接</label>
            <input value={contact} onChange={(event) => setContact(event.target.value)} className="mb-4 w-full rounded-xl border border-stone-200 px-3 py-2" />
            <button type="submit" className="w-full bg-orange-500 hover:bg-orange-600 text-white rounded-xl py-3 px-5 font-medium">提交</button>
          </form>
        </div>
      )}
      {toast && <div className="fixed bottom-20 left-1/2 z-50 -translate-x-1/2 rounded-xl bg-stone-900 px-4 py-2 text-sm text-white">{toast}</div>}
    </>
  );
}
