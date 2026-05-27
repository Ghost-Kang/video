import { create } from "zustand";

export type NicheId = "baomam_fushi" | "yuer_richang" | "jiating_chufang";

const LS_KEY = "openrhtv_selected_niche";

function loadNiche(): NicheId | null {
  if (typeof window === "undefined") return null;
  try {
    const v = window.localStorage.getItem(LS_KEY);
    if (v === "baomam_fushi" || v === "yuer_richang" || v === "jiating_chufang") return v;
    return null;
  } catch {
    return null;
  }
}

function saveNiche(v: NicheId | null) {
  if (typeof window === "undefined") return;
  try {
    if (v) window.localStorage.setItem(LS_KEY, v);
    else window.localStorage.removeItem(LS_KEY);
  } catch {
    /* localStorage may be unavailable (private mode) — non-fatal */
  }
}

interface NicheStore {
  niche: NicheId | null;
  setNiche: (v: NicheId | null) => void;
}

export const useNicheStore = create<NicheStore>((set) => ({
  niche: loadNiche(),
  setNiche: (v) => {
    saveNiche(v);
    set({ niche: v });
  },
}));

export const NICHE_LABELS: Record<NicheId, { emoji: string; key: "niche_baomam" | "niche_yuer" | "niche_kitchen" }> = {
  baomam_fushi: { emoji: "🍼", key: "niche_baomam" },
  yuer_richang: { emoji: "👶", key: "niche_yuer" },
  jiating_chufang: { emoji: "🍳", key: "niche_kitchen" },
};
