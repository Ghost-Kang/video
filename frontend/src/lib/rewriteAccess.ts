// 改写功能（「你的版本」自动改写）解封灰度开关。
//
// founder D2(phase2_kickoff_synthesis_2026-05-31.md §3):改写先 rewrite-beta
// cohort 灰度一周，再全量。因此 REWRITE_ENABLED 不能再是源码硬常量 —— 必须可在
// 运行时按 cohort 控制。优先级（高 → 低):
//
//   1. 后端下发的 per-cohort flag(若存在)
//   2. 构建期 env：import.meta.env.VITE_REWRITE_ENABLED === "true"
//   3. 默认 false(灰度未开 = 当前线上行为，完全不变)
//
// TODO(后端下发 cohort flag 后切到按 cohort):目前 WS auth 握手只把 invite_code
// 当作「单一共享 cohort 准入码」(ws_server.py:71 校验 config.INVITE_CODES 成员),
// session_list / session_state 帧(ws_messages.py:173-189)均**未下发** cohort 名
// 或 feature flag。一旦后端在握手/session_state 加上 per-cohort 的
// rewrite_enabled(例如 rewrite-beta cohort = true),把它解析出来传给本函数的
// `cohortFlag` 形参即可——优先级链已就位,无需改调用点逻辑。
//
// 铁律:本轮**保持改写实际关闭**。不传 cohortFlag 且不设 VITE_REWRITE_ENABLED 时,
// 解析结果恒为 false,行为与硬常量 false 完全一致。

/**
 * 解析改写功能是否启用。
 *
 * @param cohortFlag 后端下发的 per-cohort 开关。`undefined` = 后端未下发
 *   (当前状态)；`true`/`false` = 后端显式按 cohort 决定(将来接上)。
 * @returns 改写是否启用。优先级:cohortFlag > VITE_REWRITE_ENABLED > false。
 */
export function resolveRewriteEnabled(cohortFlag?: boolean): boolean {
  // 1. 后端 per-cohort flag 优先(显式 true/false 都尊重，只有 undefined 才下探)。
  if (cohortFlag !== undefined) return cohortFlag;

  // 2. 构建期 env。只有显式字符串 "true" 才算开;其余(含 undefined / "false" / "0")= 关。
  //    懒读 import.meta.env 让 vitest 的 vi.stubEnv 能逐用例覆盖。
  const envFlag = import.meta.env.VITE_REWRITE_ENABLED;
  if (envFlag === "true") return true;

  // 3. 默认关闭(灰度未开)。
  return false;
}
