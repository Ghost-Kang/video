import { useRef, useCallback } from "react";

/**
 * Click ripple — 在元素上点击位置生成 ripple 圆,扩散并淡出。
 * 通过附加 absolute child 到 ref 容器,容器需 relative + overflow-hidden。
 */
export function useRipple<T extends HTMLElement = HTMLElement>() {
  const ref = useRef<T>(null);

  const spawn = useCallback((e: React.MouseEvent) => {
    const el = ref.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const size = 8;
    const x = e.clientX - rect.left - size / 2;
    const y = e.clientY - rect.top - size / 2;
    const dot = document.createElement("span");
    dot.className = "ripple-dot";
    dot.style.width = `${size}px`;
    dot.style.height = `${size}px`;
    dot.style.left = `${x}px`;
    dot.style.top = `${y}px`;
    el.appendChild(dot);
    setTimeout(() => dot.remove(), 750);
  }, []);

  return { ref, spawn };
}
