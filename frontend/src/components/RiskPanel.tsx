import { Lightbulb, TrendingUp, TriangleAlert } from "lucide-react";

import type { PredictiveRisk } from "../types";

type Props = {
  risks: PredictiveRisk[];
};

export default function RiskPanel({ risks }: Props) {
  const critical = risks.filter((risk) => risk.level === "critical").length;

  return (
    <section className="rounded-lg border border-zinc-200 bg-white">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-zinc-200 px-4 py-3">
        <div>
          <div className="font-semibold">Risklar</div>
          <p className="text-sm text-zinc-500">So'nggi 7 kunlik CPU/RAM/disk trendi asosidagi predictive monitoring.</p>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <span className="rounded-full bg-rose-100 px-2 py-1 font-medium text-rose-700">{critical} critical</span>
          <span className="rounded-full bg-amber-100 px-2 py-1 font-medium text-amber-700">{risks.length - critical} warning</span>
        </div>
      </div>

      <div className="p-4">
        {!risks.length && (
          <div className="rounded-md border border-dashed border-zinc-300 bg-zinc-50 p-4 text-sm text-zinc-600">
            Hozircha predictive risk aniqlanmadi. 7 kunlik tarixiy metriclar yig'ilgani sari prognoz ishonchliligi oshadi.
          </div>
        )}

        {!!risks.length && (
          <div className="grid gap-3 lg:grid-cols-2">
            {risks.map((risk) => (
              <RiskItem key={risk.id} risk={risk} />
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

function RiskItem({ risk }: { risk: PredictiveRisk }) {
  const isCritical = risk.level === "critical";
  const border = isCritical ? "border-rose-200 bg-rose-50/40" : "border-amber-200 bg-amber-50/40";
  const iconColor = isCritical ? "text-rose-600" : "text-amber-600";

  return (
    <article className={`rounded-lg border p-4 ${border}`}>
      <div className="flex gap-3">
        <TriangleAlert size={20} className={iconColor} />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-semibold">{risk.title}</h3>
            <span className={`rounded-full px-2 py-1 text-xs font-medium ${isCritical ? "bg-rose-100 text-rose-700" : "bg-amber-100 text-amber-700"}`}>
              {risk.level}
            </span>
          </div>
          <div className="mt-1 text-xs text-zinc-500">
            {risk.source_type.toUpperCase()}: {risk.source_name}
            {risk.host_name && risk.source_type === "vm" ? ` / Host: ${risk.host_name}` : ""}
          </div>
          <p className="mt-3 text-sm text-zinc-700">{risk.message}</p>

          <div className="mt-3 grid gap-2 text-xs text-zinc-600 sm:grid-cols-4">
            <RiskStat label="Current" value={pct(risk.current_value)} />
            <RiskStat label="Avg 7d" value={pct(risk.average_7d)} />
            <RiskStat label="Trend" value={trend(risk.trend_per_day)} />
            <RiskStat label="Forecast 7d" value={pct(risk.forecast_7d)} />
          </div>

          <div className="mt-3 flex items-start gap-2 rounded-md bg-white/70 p-3 text-sm">
            <Lightbulb size={16} className="mt-0.5 text-emerald-700" />
            <div>
              <div className="font-medium text-zinc-800">Tavsiya</div>
              <div className="mt-1 flex flex-wrap gap-2">
                {risk.recommendations.map((item) => (
                  <span key={item} className="rounded-full bg-emerald-100 px-2 py-1 text-xs font-medium text-emerald-700">
                    {item}
                  </span>
                ))}
              </div>
            </div>
          </div>

          <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-zinc-500">
            <span className="flex items-center gap-1">
              <TrendingUp size={14} /> Confidence {(risk.confidence * 100).toFixed(0)}%
            </span>
            <span>Samples: {risk.sample_count}</span>
            {risk.days_to_limit !== null && <span>Limitgacha: {risk.days_to_limit.toFixed(1)} kun</span>}
          </div>
        </div>
      </div>
    </article>
  );
}

function RiskStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-white/70 px-3 py-2">
      <div className="text-[11px] uppercase text-zinc-500">{label}</div>
      <div className="mt-1 font-semibold text-zinc-900">{value}</div>
    </div>
  );
}

function pct(value?: number | null) {
  return value === null || value === undefined ? "-" : `${value.toFixed(1)}%`;
}

function trend(value?: number | null) {
  if (value === null || value === undefined) return "-";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}%/kun`;
}
