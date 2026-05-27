interface StatCardProps {
  label: string;
  value: string | number;
  hint?: string;
}

export function StatCard({ label, value, hint }: StatCardProps) {
  return (
    <div className="rounded-2xl bg-white dark:bg-stone-900 border border-stone-200/70 dark:border-stone-800/70 p-5 shadow-soft hover:shadow-soft-lg hover:-translate-y-0.5 transition-all duration-300">
      <div className="text-[11px] uppercase tracking-[0.18em] text-stone-500 dark:text-stone-400">{label}</div>
      <div className="mt-2 font-serif-cn text-3xl text-stone-900 dark:text-stone-50 tabular">{value}</div>
      {hint && <div className="mt-1 text-xs text-stone-500 dark:text-stone-400">{hint}</div>}
    </div>
  );
}
