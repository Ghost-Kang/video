// Pro view (Canvas + node editor) 默认对所有用户隐藏。
// 仅当 VITE_ADMIN_USER_IDS 显式列出当前 userId 时才显示。
// 用法:.env.local 加 VITE_ADMIN_USER_IDS=xukang.wang@gmail.com,admin

const ADMIN_USER_IDS = new Set(
  (import.meta.env.VITE_ADMIN_USER_IDS ?? "")
    .split(",")
    .map((id: string) => id.trim())
    .filter(Boolean)
);

// 兼容旧 API:接收 userId(原 sessionId 调用点已切换)。
export function shouldHideProToggle(userId: string): boolean {
  return !ADMIN_USER_IDS.has(userId);
}

export function isAdminUser(userId: string): boolean {
  return ADMIN_USER_IDS.has(userId);
}
