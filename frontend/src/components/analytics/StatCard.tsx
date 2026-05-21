interface StatCardProps {
  label: string;
  value: string | number;
  hint?: string;
}

export function StatCard({ label, value, hint }: StatCardProps) {
  return (
    <div className="rounded-2xl bg-white border border-stone-200 p-5 shadow-sm">
      <div className="text-xs uppercase tracking-wider text-stone-500">{label}</div>
      <div className="mt-2 text-3xl font-medium text-stone-900 tabular-nums">{value}</div>
      {hint && <div className="mt-1 text-xs text-stone-500">{hint}</div>}
    </div>
  );
}
