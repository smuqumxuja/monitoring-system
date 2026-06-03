type Props = {
  label: string;
  value: string | number;
  tone?: "neutral" | "ok" | "warn" | "bad";
};

export default function MetricCard({ label, value, tone = "neutral" }: Props) {
  const color = {
    neutral: "text-zinc-950",
    ok: "text-emerald-700",
    warn: "text-amber-700",
    bad: "text-rose-700"
  }[tone];

  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-4">
      <div className="text-xs font-medium uppercase text-zinc-500">{label}</div>
      <div className={`mt-2 text-xl font-semibold ${color}`}>{value}</div>
    </div>
  );
}

