import { useProCanvasStore } from "../store/proCanvasStore";
import { useToastStore } from "../store/toastStore";
import { saveFilm } from "./proExecution";

/** 运行产物 / 失败原因条(底部)。pro_run_node_done/done 累积 outputs;failed 显错误。
 *  视频产物可播放 + 下载 + 「存入我的成片」(成片发布出口 = 产品内库)。 */
export function RunOutputs({ threadId }: { threadId: string }) {
  const run = useProCanvasStore((s) => s.run);
  const show = run.status === "done" || run.status === "failed" || run.outputs.length > 0;
  if (!show) return null;

  const onSave = async (url: string) => {
    try {
      await saveFilm(url, threadId);
      useToastStore.getState().push({ kind: "info", title: "已存入我的成片", ttlMs: 2000 });
    } catch {
      useToastStore.getState().push({ kind: "error", title: "保存失败" });
    }
  };

  return (
    <div
      style={{ position: "absolute", left: 12, right: 12, bottom: 12, zIndex: 25, pointerEvents: "all" }}
      className="rounded-2xl border border-[var(--color-clay)]/15 bg-[var(--color-paper)]/95 px-4 py-3 shadow-lg backdrop-blur"
      onPointerDown={(e) => e.stopPropagation()}
      data-testid="pro-run-outputs"
    >
      {run.status === "failed" ? (
        <p className="text-sm text-red-600">运行失败:{run.error || "未知错误"}</p>
      ) : (
        <div className="flex items-center gap-3 overflow-x-auto">
          <span className="shrink-0 text-xs font-medium text-[var(--color-ink-soft)]">产物 {run.outputs.length}</span>
          {run.outputs.map((url, i) => {
            const isVid = /\.(mp4|webm|mov)(\?|$)/i.test(url);
            return (
              <div key={i} className="flex shrink-0 flex-col items-center gap-1">
                {isVid ? (
                  <video
                    src={url}
                    controls
                    muted
                    playsInline
                    className="h-20 w-32 rounded-lg border border-[var(--color-clay)]/15 bg-black object-cover"
                  />
                ) : (
                  <a href={url} target="_blank" rel="noreferrer">
                    <img
                      src={url}
                      alt={`output ${i + 1}`}
                      className="h-16 w-16 rounded-lg border border-[var(--color-clay)]/15 object-cover"
                    />
                  </a>
                )}
                <div className="flex items-center gap-2">
                  <a
                    href={url}
                    download
                    target="_blank"
                    rel="noreferrer"
                    className="text-[10px] font-medium text-[var(--color-clay)] hover:underline"
                  >
                    ⬇ 下载{isVid ? "成片" : ""}
                  </a>
                  {isVid && (
                    <button
                      type="button"
                      onClick={() => onSave(url)}
                      className="text-[10px] font-medium text-[var(--color-clay)] hover:underline"
                    >
                      💾 存入我的成片
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
