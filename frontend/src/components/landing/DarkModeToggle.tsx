import { Sun, Moon } from "lucide-react";
import { useDarkMode } from "../../hooks/useDarkMode";

export function DarkModeToggle() {
  const { isDark, toggle } = useDarkMode();
  return (
    <button
      type="button"
      onClick={toggle}
      className="fixed top-5 right-5 z-50 inline-flex h-9 w-9 items-center justify-center rounded-full border border-stone-200/70 dark:border-stone-700/70 bg-white/60 dark:bg-stone-900/60 backdrop-blur text-stone-600 dark:text-stone-300 hover:text-[#7c2d12] dark:hover:text-[#ea580c] hover:border-stone-300 dark:hover:border-stone-600 transition-all duration-300 hover:scale-110 active:scale-95"
      title={isDark ? "切到 light" : "切到 dark"}
      aria-label="切换主题"
    >
      {isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
    </button>
  );
}
