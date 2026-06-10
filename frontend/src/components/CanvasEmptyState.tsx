/**
 * 画布空态引导卡(P2 画布 polish)。?view=pro 是画布「解封」给普通用户的入口,
 * 新会话进来画布是空的 —— 没有引导,用户面对一张空白会懵。这张卡告诉用户:
 * 「这是无限画布,告诉导演你想做什么,它会帮你搭好 策划书→角色→场景→分镜→视频→合成」。
 *
 * 「告诉导演」按钮 dispatch open_canvas_chat 事件 → App 打开底部对话 dock(聚焦输入),
 * 把「下一步该干啥」直接变成一次点击。仅在画布 0 节点时由 Canvas 渲染(absolute 居中覆盖)。
 */

const STEPS = ["策划书", "角色", "场景", "分镜", "视频", "合成"];

export function CanvasEmptyState() {
  const askDirector = () => window.dispatchEvent(new CustomEvent("open_canvas_chat"));

  return (
    <div style={S.overlay} className="nodrag nopan" data-testid="canvas-empty-state">
      <div style={S.card} className="anim-fade-up">
        <div style={S.spark}>✦</div>
        <h2 style={S.title} className="font-serif-cn">这是你的创作画布</h2>
        <p style={S.sub}>
          告诉导演你想做什么 —— 比如「做一支 30 秒赛博朋克短片,主角是男侦探」。
          导演会在画布上帮你一步步搭好:
        </p>
        <div style={S.flow}>
          {STEPS.map((s, i) => (
            <span key={s} style={S.flowItem}>
              <span style={S.flowDot}>{i + 1}</span>
              <span style={S.flowLabel}>{s}</span>
              {i < STEPS.length - 1 && <span style={S.arrow}>→</span>}
            </span>
          ))}
        </div>
        <button style={S.cta} className="anim-cta-breathe" onClick={askDirector} data-testid="empty-ask-director">
          告诉导演你想做什么
        </button>
        <div style={S.hint}>每一步你都可以审核、修改、重生,导演只在你确认后才往下走。</div>
        {/* P3(2026-06-10 审计):匿名身份存于本浏览器,换设备/清缓存后旧画布会「静默
            变空白」—— 用户以为数据丢了。空态里给一句解释,把静默坑变成已知行为。 */}
        <div style={S.identityNote} data-testid="empty-identity-note">
          之前在这条链接创作过却看到空白?创作记录跟随本浏览器的匿名身份,换设备或清浏览器数据后,旧会话暂时无法在这里找回。
        </div>
      </div>
    </div>
  );
}

const CLAY = "#7c2d12";
const AMBER = "#b45309";

const S: Record<string, React.CSSProperties> = {
  overlay: {
    position: "absolute",
    inset: 0,
    zIndex: 5,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    pointerEvents: "none",
    padding: 24,
  },
  card: {
    pointerEvents: "auto",
    maxWidth: 520,
    width: "100%",
    background: "rgba(250,248,243,0.92)",
    backdropFilter: "blur(10px)",
    WebkitBackdropFilter: "blur(10px)",
    border: "1px solid rgba(124,45,18,0.16)",
    borderRadius: 20,
    padding: "28px 30px",
    textAlign: "center",
    boxShadow: "0 20px 60px -20px rgba(124,45,18,0.30)",
  },
  spark: { fontSize: 26, color: AMBER, marginBottom: 6 },
  title: { fontSize: 22, color: "#1c1917", margin: "0 0 10px" },
  sub: { fontSize: 13.5, lineHeight: 1.65, color: "#57534e", margin: "0 0 18px" },
  flow: {
    display: "flex",
    flexWrap: "wrap",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    marginBottom: 22,
  },
  flowItem: { display: "inline-flex", alignItems: "center", gap: 6 },
  flowDot: {
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    width: 20,
    height: 20,
    borderRadius: 999,
    fontSize: 11,
    fontWeight: 600,
    color: "#fff",
    background: CLAY,
  },
  flowLabel: { fontSize: 12.5, color: CLAY, fontWeight: 500 },
  arrow: { color: "rgba(124,45,18,0.4)", fontSize: 12, margin: "0 2px" },
  cta: {
    display: "inline-block",
    padding: "11px 26px",
    borderRadius: 999,
    border: "none",
    cursor: "pointer",
    background: CLAY,
    color: "#faf8f3",
    fontSize: 14,
    fontWeight: 600,
    boxShadow: "0 8px 24px -8px rgba(124,45,18,0.5)",
  },
  hint: { fontSize: 11.5, color: "#a8a29e", marginTop: 14, lineHeight: 1.5 },
  identityNote: {
    fontSize: 11,
    color: "#a8a29e",
    marginTop: 8,
    lineHeight: 1.5,
    paddingTop: 8,
    borderTop: "1px dashed rgba(124,45,18,0.12)",
  },
};
