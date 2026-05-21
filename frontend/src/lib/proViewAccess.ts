const TRIAL_SESSION_IDS = new Set(
  (import.meta.env.VITE_TRIAL_SESSION_IDS ?? "")
    .split(",")
    .map((sessionId: string) => sessionId.trim())
    .filter(Boolean)
);

export function shouldHideProToggle(sessionId: string): boolean {
  return TRIAL_SESSION_IDS.has(sessionId);
}
