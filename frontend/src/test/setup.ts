import "@testing-library/jest-dom/vitest";
import { beforeEach } from "vitest";

// jsdom in this project exposes `window.localStorage` as a plain `{}` (no
// Storage methods). Polyfill with a Map-backed implementation so any code or
// test that relies on the standard Storage API works.
class MemoryStorage implements Storage {
  private store = new Map<string, string>();
  get length(): number {
    return this.store.size;
  }
  clear(): void {
    this.store.clear();
  }
  getItem(key: string): string | null {
    return this.store.has(key) ? (this.store.get(key) as string) : null;
  }
  key(index: number): string | null {
    return Array.from(this.store.keys())[index] ?? null;
  }
  removeItem(key: string): void {
    this.store.delete(key);
  }
  setItem(key: string, value: string): void {
    this.store.set(key, String(value));
  }
}

Object.defineProperty(window, "localStorage", {
  value: new MemoryStorage(),
  configurable: true,
  writable: true,
});

beforeEach(() => {
  window.localStorage.clear();
});
