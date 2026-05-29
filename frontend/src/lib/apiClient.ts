/**
 * Single chokepoint for all `/api` calls so every request carries the right
 * auth header. Backend (agent/transport/http_router.py) gates:
 *   - cohort endpoints (analysis/rewrite/anchors/events POST/cost) on a valid
 *     X-Invite-Code — enforced only when the server has INVITE_CODES set;
 *   - admin reads (events GET / creators / health summary) on X-Admin-Token.
 *
 * The invite code is written by the InviteCode gate; the admin token is entered
 * by the founder via the admin pages' token bar. Both live in localStorage
 * (sessionStorage fallback for private mode). Open endpoints (/api/health,
 * /api/stats/public, /api/client_error) ignore these headers.
 */

const INVITE_CODE_KEY = "openrhtv_invite_code";
export const ADMIN_TOKEN_KEY = "openrhtv_admin_token";

function readStored(key: string): string | null {
  try {
    return localStorage.getItem(key) || sessionStorage.getItem(key) || null;
  } catch {
    return null; // private mode / storage disabled
  }
}

export function readAdminToken(): string | null {
  return readStored(ADMIN_TOKEN_KEY);
}

export function writeAdminToken(token: string): void {
  try {
    localStorage.setItem(ADMIN_TOKEN_KEY, token.trim());
  } catch {
    try {
      sessionStorage.setItem(ADMIN_TOKEN_KEY, token.trim());
    } catch {
      /* in-memory only — nothing we can do */
    }
  }
}

/** fetch() wrapper that injects X-Invite-Code and (when present) X-Admin-Token. */
export function apiFetch(input: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers);
  const code = readStored(INVITE_CODE_KEY);
  if (code && !headers.has("X-Invite-Code")) headers.set("X-Invite-Code", code);
  const adminToken = readStored(ADMIN_TOKEN_KEY);
  if (adminToken && !headers.has("X-Admin-Token")) headers.set("X-Admin-Token", adminToken);
  return fetch(input, { ...init, headers });
}
