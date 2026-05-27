import { create } from "zustand";

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
  setUserId: (userId: string) => void;
  hydrate: (userId?: string) => void;
  setSessions: (sessions: string[]) => void;
  setNames: (names: Record<string, string>) => void;
  addSession: (threadId: string) => void;
  deleteSession: (threadId: string) => void;
  rename: (threadId: string, name: string) => void;
  reset: () => void;
}

export const useSessionStore = create<SessionStore>((set, get) => ({
  userId: "default",
  sessions: [],
  names: {},

  setUserId: (userId) => {
    set({ userId });
    get().hydrate(userId);
  },

  hydrate: (userId = get().userId) =>
    set({
      userId,
      sessions: loadJSON<string[]>(lsKey("sessions", userId), []),
      names: loadJSON<Record<string, string>>(lsKey("names", userId), {}),
    }),

  setSessions: (sessions) => {
    saveJSON(lsKey("sessions", get().userId), sessions);
    set({ sessions });
  },

  setNames: (names) => {
    saveJSON(lsKey("names", get().userId), names);
    set({ names });
  },

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
      const { [threadId]: _deleted, ...names } = state.names;
      saveJSON(lsKey("sessions", state.userId), sessions);
      saveJSON(lsKey("names", state.userId), names);
      return { sessions, names };
    }),

  rename: (threadId, name) =>
    set((state) => {
      const names = { ...state.names, [threadId]: name };
      saveJSON(lsKey("names", state.userId), names);
      return { names };
    }),

  reset: () => set({ sessions: [], names: {} }),
}));
