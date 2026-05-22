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

    try {
      await fetch("/api/events", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          event_name: "consent_accepted",
          user_id: anonId(),
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
