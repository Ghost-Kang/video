import { useCallback, useEffect, useState } from "react";

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

function anonId(): string {
  const KEY = "openrhtv_anon_id";
  let id = window.localStorage.getItem(KEY);
  if (!id) {
    id = `anon-${Math.random().toString(36).slice(2, 10)}${Date.now().toString(36)}`;
    window.localStorage.setItem(KEY, id);
  }
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
      await fetch("/api/events", {
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
