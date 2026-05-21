import { useState } from "react";

export function UrlFallback({ onSubmit }: { onSubmit: (url: string) => void }) {
  const [url, setUrl] = useState("");
  return (
    <form
      className="mt-6 flex flex-col gap-2 sm:flex-row sm:items-center"
      onSubmit={(event) => {
        event.preventDefault();
        if (url.trim()) onSubmit(url.trim());
      }}
    >
      <label className="text-stone-500 text-sm whitespace-nowrap">或者粘贴你看到的爆款链接 →</label>
      <input
        value={url}
        onChange={(event) => setUrl(event.target.value)}
        className="min-w-0 flex-1 rounded-xl border border-stone-200 bg-white px-3 py-2 text-base outline-none focus:ring-2 focus:ring-orange-400"
        placeholder="https://"
      />
    </form>
  );
}
