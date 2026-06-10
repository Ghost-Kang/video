import { useCallback, useEffect, useState } from "react";
import { apiFetch } from "../lib/apiClient";

export const CONSENT_STORAGE_KEY = "openrhtv_consent_v0";
export const CONSENT_VERSION = "v0";
export const CONSENT_DOCS = ["user_agreement_v0", "privacy_v0"] as const;

export interface ConsentRecord {
  version: string;
  acceptedAt: string;
}

export interface UseConsentResult {
  accepted: boolean;
  acceptedAt: string | null;
  accept: () => Promise<void>;
}

function readStored(): ConsentRecord | null {
  try {
    const raw = window.localStorage.getItem(CONSENT_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (typeof parsed !== "object" || parsed === null) return null;
    if (parsed.version !== CONSENT_VERSION) return null;
    if (typeof parsed.acceptedAt !== "string") return null;
    return parsed as ConsentRecord;
  } catch {
    return null;
  }
}

const ANON_COOKIE_MAX_AGE_S = 60 * 60 * 24 * 365; // 1 年

function readAnonCookie(key: string): string | null {
  try {
    const m = document.cookie.match(new RegExp(`(?:^|;\\s*)${key}=([^;]+)`));
    return m ? decodeURIComponent(m[1]) : null;
  } catch {
    return null;
  }
}

function writeAnonCookie(key: string, value: string): void {
  try {
    document.cookie = `${key}=${encodeURIComponent(value)}; max-age=${ANON_COOKIE_MAX_AGE_S}; path=/; SameSite=Lax`;
  } catch {
    /* cookie 不可用(隐私模式等)→ 仍有 localStorage */
  }
}

function anonId(): string {
  // P3 加固(2026-06-10 审计):匿名身份此前仅存 localStorage —— 清浏览器数据 =
  // 身份永久丢失 = 所有画布/会话静默变空白(数据按 user+thread 双键存在后端,
  // 前端却再也指不到)。双写 cookie(1 年):清 localStorage(最常见丢失方式)
  // 后可从 cookie 恢复同一身份。仍是同浏览器方案;换设备要靠未来的账号体系。
  const KEY = "openrhtv_anon_id";
  let id = window.localStorage.getItem(KEY);
  if (!id) {
    id = readAnonCookie(KEY);
    if (id) window.localStorage.setItem(KEY, id); // cookie → localStorage 回填
  }
  if (!id) {
    id = `anon-${Math.random().toString(36).slice(2, 10)}${Date.now().toString(36)}`;
    window.localStorage.setItem(KEY, id);
  }
  writeAnonCookie(KEY, id); // 每次访问续期
  return id;
}

export function useConsent(): UseConsentResult {
  const [record, setRecord] = useState<ConsentRecord | null>(() => readStored());

  useEffect(() => {
    const onStorage = (e: StorageEvent) => {
      if (e.key === CONSENT_STORAGE_KEY) setRecord(readStored());
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const accept = useCallback(async () => {
    const now = new Date().toISOString();
    const next: ConsentRecord = { version: CONSENT_VERSION, acceptedAt: now };
    window.localStorage.setItem(CONSENT_STORAGE_KEY, JSON.stringify(next));
    setRecord(next);

    // Phase 1 anon flow bridge: upstream's auth gate (66758bd) requires
    // `rhtv_user` in localStorage to grant /chat access. Auto-write our
    // stable anon ID as the user so consent acceptance doubles as anon
    // login. No explicit /login screen needed for trial creators.
    // Dispatch a custom event so AppRoutes' user state re-reads
    // localStorage (same-tab storage events don't fire in browsers).
    const uid = anonId();
    if (!window.localStorage.getItem("rhtv_user")) {
      window.localStorage.setItem("rhtv_user", uid);
    }
    window.dispatchEvent(new Event("rhtv-auth-changed"));

    try {
      await apiFetch("/api/events", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          event_name: "consent_accepted",
          user_id: uid,
          payload: {
            version: CONSENT_VERSION,
            accepted_at: now,
            documents: [...CONSENT_DOCS],
          },
        }),
      });
    } catch {
      const QUEUE_KEY = "openrhtv_event_retry_queue";
      try {
        const queued = JSON.parse(window.localStorage.getItem(QUEUE_KEY) || "[]");
        queued.push({
          event_name: "consent_accepted",
          ts: now,
          payload: { version: CONSENT_VERSION, accepted_at: now, documents: [...CONSENT_DOCS] },
        });
        window.localStorage.setItem(QUEUE_KEY, JSON.stringify(queued));
      } catch {
        // localStorage saturated; consent record itself is the source of truth
      }
    }
  }, []);

  return {
    accepted: record !== null,
    acceptedAt: record?.acceptedAt ?? null,
    accept,
  };
}
