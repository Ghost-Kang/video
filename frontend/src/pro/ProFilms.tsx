import { useState } from "react";
import { deleteFilm, listFilms, type ProFilm } from "./proExecution";

/** 「我的成片」库:列出用户存过的成片,可播放/下载/删除(成片发布出口 = 产品内库)。 */
export function ProFilms() {
  const [open, setOpen] = useState(false);
  const [films, setFilms] = useState<ProFilm[]>([]);

  const refresh = async () => setFilms(await listFilms());
  const toggle = () => {
    const next = !open;
    setOpen(next);
    if (next) void refresh();
  };
  const onDelete = async (id: string) => {
    await deleteFilm(id);
    await refresh();
  };

  return (
    <div style={{ position: "relative", pointerEvents: "all" }} onPointerDown={(e) => e.stopPropagation()}>
      <button
        type="button"
        onClick={toggle}
        data-testid="pro-films-toggle"
        className="rounded-lg border border-[var(--color-ink)]/15 px-2.5 py-1.5 text-xs font-medium text-[var(--color-ink-soft)] transition hover:bg-[var(--color-paper-deeper)]"
      >
        🎞 我的成片
      </button>
      {open && (
        <div className="absolute right-0 top-9 z-40 max-h-[60vh] w-72 overflow-y-auto rounded-xl border border-[var(--color-clay)]/20 bg-[var(--color-paper)] p-2 shadow-xl">
          {films.length === 0 ? (
            <div className="px-2 py-3 text-xs text-[var(--color-ink-soft)]/60">还没有成片 —— 运行后点「💾 存入我的成片」。</div>
          ) : (
            films.map((f) => (
              <div key={f.film_id} className="mb-2 rounded-lg border border-[var(--color-ink)]/10 p-1.5">
                <video src={f.video_url} controls muted playsInline className="h-24 w-full rounded bg-black object-cover" />
                <div className="mt-1 flex items-center justify-between text-[10px]">
                  <span className="truncate text-[var(--color-ink-soft)]">{f.title || f.created_at.slice(0, 16).replace("T", " ")}</span>
                  <span className="flex shrink-0 gap-2">
                    <a href={f.video_url} download target="_blank" rel="noreferrer" className="text-[var(--color-clay)] hover:underline">
                      下载
                    </a>
                    <button type="button" onClick={() => onDelete(f.film_id)} className="text-[var(--color-ink-soft)]/50 hover:text-red-500">
                      删除
                    </button>
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
