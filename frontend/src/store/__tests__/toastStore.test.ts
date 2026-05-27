import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useToastStore } from "../toastStore";

describe("toastStore", () => {
  beforeEach(() => {
    useToastStore.getState().clear();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("push appends a toast and returns its id", () => {
    const id = useToastStore.getState().push({ title: "hi" });
    const toasts = useToastStore.getState().toasts;
    expect(toasts).toHaveLength(1);
    expect(toasts[0].id).toBe(id);
    expect(toasts[0].kind).toBe("info"); // default
    expect(toasts[0].title).toBe("hi");
  });

  it("respects explicit kind + body", () => {
    useToastStore.getState().push({ kind: "error", title: "bad", body: "details" });
    const t = useToastStore.getState().toasts[0];
    expect(t.kind).toBe("error");
    expect(t.body).toBe("details");
  });

  it("auto-dismisses after ttlMs", () => {
    useToastStore.getState().push({ title: "fade", ttlMs: 200 });
    expect(useToastStore.getState().toasts).toHaveLength(1);
    vi.advanceTimersByTime(199);
    expect(useToastStore.getState().toasts).toHaveLength(1);
    vi.advanceTimersByTime(2);
    expect(useToastStore.getState().toasts).toHaveLength(0);
  });

  it("ttlMs=0 disables auto-dismiss", () => {
    useToastStore.getState().push({ title: "sticky", ttlMs: 0 });
    vi.advanceTimersByTime(60_000);
    expect(useToastStore.getState().toasts).toHaveLength(1);
  });

  it("manual dismiss by id removes the toast", () => {
    const id1 = useToastStore.getState().push({ title: "a" });
    const id2 = useToastStore.getState().push({ title: "b" });
    useToastStore.getState().dismiss(id1);
    const toasts = useToastStore.getState().toasts;
    expect(toasts).toHaveLength(1);
    expect(toasts[0].id).toBe(id2);
  });

  it("stacks multiple toasts in push order", () => {
    useToastStore.getState().push({ title: "1" });
    useToastStore.getState().push({ title: "2" });
    useToastStore.getState().push({ title: "3" });
    expect(useToastStore.getState().toasts.map((t) => t.title)).toEqual(["1", "2", "3"]);
  });

  // ---- W4D5-T2: ToastAction 字段 ----

  it("stores ToastAction on the toast when pushed", () => {
    const onClick = vi.fn();
    useToastStore.getState().push({
      title: "with action",
      action: { label: "再试一次", onClick },
    });
    const t = useToastStore.getState().toasts[0];
    expect(t.action).toBeDefined();
    expect(t.action?.label).toBe("再试一次");
    expect(t.action?.onClick).toBe(onClick);
    expect(t.action?.closeOnClick).toBeUndefined(); // default = true at render time
  });

  it("preserves explicit closeOnClick=false on action", () => {
    useToastStore.getState().push({
      title: "sticky action",
      action: { label: "x", onClick: () => {}, closeOnClick: false },
    });
    const t = useToastStore.getState().toasts[0];
    expect(t.action?.closeOnClick).toBe(false);
  });

  it("absent action stays undefined (no surprise mutation)", () => {
    useToastStore.getState().push({ title: "plain" });
    const t = useToastStore.getState().toasts[0];
    expect(t.action).toBeUndefined();
  });
});
