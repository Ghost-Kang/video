import { create } from "zustand";
import type { SessionMeta } from "../lib/sessionTitle";

function lsKey(key: string, userId: string) {
  return `openrhtv_${userId}_${key}`;
}

function loadJSON<T>(key: string, fallback: T): T {
  try {
    const data = localStorage.getItem(key);
    return data ? JSON.parse(data) : fallback;
  } catch {
    return fallback;
  }
}

function saveJSON(key: string, val: unknown) {
  localStorage.setItem(key, JSON.stringify(val));
}

interface SessionStore {
  userId: string;
  sessions: string[];
  names: Record<string, string>;
  meta: Record<string, SessionMeta>;
  setUserId: (userId: string) => void;
  hydrate: (userId?: string) => void;
  setSessions: (sessions: string[]) => void;
  setNames: (names: Record<string, string>) => void;
  setMeta: (threadId: string, meta: SessionMeta) => void;
  addSession: (threadId: string) => void;
  deleteSession: (threadId: string) => void;
  rename: (threadId: string, name: string) => void;
  reset: () => void;
}

export const useSessionStore = create<SessionStore>((set, get) => ({
  userId: "default",
  sessions: [],
  names: {},
  meta: {},

  setUserId: (userId) => {
    set({ userId });
    get().hydrate(userId);
  },

  hydrate: (userId = get().userId) =>
    set({
      userId,
      sessions: loadJSON<string[]>(lsKey("sessions", userId), []),
      names: loadJSON<Record<string, string>>(lsKey("names", userId), {}),
      meta: loadJSON<Record<string, SessionMeta>>(lsKey("meta", userId), {}),
    }),

  setSessions: (sessions) => {
    saveJSON(lsKey("sessions", get().userId), sessions);
    set({ sessions });
  },

  setNames: (names) => {
    saveJSON(lsKey("names", get().userId), names);
    set({ names });
  },

  setMeta: (threadId, m) =>
    set((state) => {
      const meta = { ...state.meta, [threadId]: m };
      saveJSON(lsKey("meta", state.userId), meta);
      return { meta };
    }),

  addSession: (threadId) =>
    set((state) => {
      if (state.sessions.includes(threadId)) return state;
      const sessions = [threadId, ...state.sessions];
      saveJSON(lsKey("sessions", state.userId), sessions);
      return { sessions };
    }),

  deleteSession: (threadId) =>
    set((state) => {
      const sessions = state.sessions.filter((id) => id !== threadId);
      // rest 解构会触发 no-unused-vars(_deletedName/_deletedMeta);显式拷贝+delete 等价。
      const names = { ...state.names };
      delete names[threadId];
      const meta = { ...state.meta };
      delete meta[threadId];
      saveJSON(lsKey("sessions", state.userId), sessions);
      saveJSON(lsKey("names", state.userId), names);
      saveJSON(lsKey("meta", state.userId), meta);
      return { sessions, names, meta };
    }),

  rename: (threadId, name) =>
    set((state) => {
      const names = { ...state.names, [threadId]: name };
      saveJSON(lsKey("names", state.userId), names);
      return { names };
    }),

  reset: () => set({ sessions: [], names: {}, meta: {} }),
}));
