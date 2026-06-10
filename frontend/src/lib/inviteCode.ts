/**
 * 邀请码存取(从 pages/InviteCode.tsx 拆出,lint 清理 2026-06-10)。
 * react-refresh/only-export-components:组件文件导出非组件函数会破坏 fast refresh。
 */

export const INVITE_CODE_STORAGE_KEY = "openrhtv_invite_code";

export function readInviteCode(): string | null {
  try {
    return (
      localStorage.getItem(INVITE_CODE_STORAGE_KEY) ||
      sessionStorage.getItem(INVITE_CODE_STORAGE_KEY) ||
      null
    );
  } catch {
    return null;
  }
}
