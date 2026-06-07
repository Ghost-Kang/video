import { useProCanvasStore } from "../store/proCanvasStore";

/** 运行产物 / 失败原因条(底部)。pro_run_node_done/done 累积 outputs;failed 显错误。 */
export function RunOutputs() {
  const run = useProCanvasStore((s) => s.run);
  const show = run.status === "done" || run.status === "failed" || run.outputs.length > 0;
  if (!show) return null;

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
          <span className="shrink-0 text-xs font-medium text-[var(--color-ink-soft)]">
            产物 {run.outputs.length}
          </span>
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
                <a
                  href={url}
                  download
                  target="_blank"
                  rel="noreferrer"
                  className="text-[10px] font-medium text-[var(--color-clay)] hover:underline"
                >
                  ⬇ 下载{isVid ? "成片" : ""}
                </a>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
