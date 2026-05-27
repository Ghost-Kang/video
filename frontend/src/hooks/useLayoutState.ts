import { useEffect, useState } from "react";

export function useLayoutState() {
  const isMobileInitial = typeof window !== "undefined" && window.matchMedia("(max-width: 768px)").matches;
  const [sidebarOpen, setSidebarOpen] = useState(!isMobileInitial);
  const [chatOpen, setChatOpen] = useState(!isMobileInitial);

  useEffect(() => {
    const mql = window.matchMedia("(max-width: 768px)");
    const onChange = (event: MediaQueryListEvent) => {
      setSidebarOpen(!event.matches);
      setChatOpen(!event.matches);
    };
    mql.addEventListener("change", onChange);
    return () => mql.removeEventListener("change", onChange);
  }, []);

  return { sidebarOpen, chatOpen, setSidebarOpen, setChatOpen };
}
