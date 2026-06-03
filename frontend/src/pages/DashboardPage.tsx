import { useMemo, useState } from "react";

import AlertPanel from "../components/AlertPanel";
import HistoryChart from "../components/HistoryChart";
import HostBlock from "../components/HostBlock";
import LoadSummaryChart from "../components/LoadSummaryChart";
import MetricCard from "../components/MetricCard";
import RiskPanel from "../components/RiskPanel";
import { useRealtimeMetrics } from "../hooks/useRealtimeMetrics";
import type { EntityRef } from "../types";

type Props = {
  token: string;
};

export default function DashboardPage({ token }: Props) {
  const { snapshot, status } = useRealtimeMetrics(token);
  const [selected, setSelected] = useState<EntityRef | null>(null);
  const vms = useMemo(() => snapshot?.hosts.flatMap((host) => host.vms) ?? [], [snapshot]);
  const hostCount = snapshot?.hosts.length ?? 0;
  const onlineHosts = snapshot?.hosts.filter((host) => host.network_status?.online).length ?? 0;
  const offlineHosts = Math.max(hostCount - onlineHosts, 0);
  const avgCpu = average(snapshot?.hosts.map((host) => host.latest_metric?.cpu_usage_percent));
  const avgRam = average(snapshot?.hosts.map((host) => host.latest_metric?.ram_usage_percent));
  const avgDisk = average(snapshot?.hosts.map((host) => host.latest_metric?.datastore_usage_percent));
  const critical = snapshot?.active_alerts.filter((alert) => alert.level === "critical").length ?? 0;
  const warning = snapshot?.active_alerts.filter((alert) => alert.level === "warning").length ?? 0;
  const risks = snapshot?.predictive_risks ?? [];
  const criticalRisks = risks.filter((risk) => risk.level === "critical").length;
  const firstHost = snapshot?.hosts[0];
  const selectedEntity = selected ?? (firstHost ? { type: "host" as const, id: firstHost.id, label: firstHost.name } : null);

  return (
    <div className="space-y-5">
      <section className="grid gap-3 md:grid-cols-4">
        <MetricCard label="ESXi hostlar" value={hostCount} />
        <MetricCard label="VM lar" value={vms.length} />
        <MetricCard label="Online hostlar" value={`${onlineHosts} online`} tone={onlineHosts === hostCount && hostCount > 0 ? "ok" : "warn"} />
        <MetricCard label="Offline hostlar" value={`${offlineHosts} offline`} tone={offlineHosts ? "bad" : "ok"} />
      </section>

      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <MetricCard label="CPU yuklama" value={pct(avgCpu)} tone={loadTone(avgCpu)} />
        <MetricCard label="RAM yuklama" value={pct(avgRam)} tone={loadTone(avgRam)} />
        <MetricCard label="Disk yuklama" value={pct(avgDisk)} tone={loadTone(avgDisk)} />
        <MetricCard label="Alertlar" value={`${critical} critical / ${warning} warning`} tone={critical ? "bad" : warning ? "warn" : "ok"} />
        <MetricCard label="Risklar" value={`${criticalRisks} critical / ${risks.length - criticalRisks} warning`} tone={criticalRisks ? "bad" : risks.length ? "warn" : "ok"} />
      </section>

      <div className="flex items-center justify-between rounded-lg border border-zinc-200 bg-white px-4 py-3 text-sm">
        <span className="text-zinc-600">Real-time yangilanish WebSocket orqali ishlaydi.</span>
        <span className={status === "live" ? "font-medium text-emerald-700" : "font-medium text-amber-700"}>{status}</span>
      </div>

      {!snapshot && <div className="rounded-lg border border-zinc-200 bg-white p-4 text-sm text-zinc-600">Ma'lumotlar yuklanmoqda...</div>}
      {snapshot && !snapshot.hosts.length && <div className="rounded-lg border border-zinc-200 bg-white p-4 text-sm text-zinc-600">Admin panel orqali ESXi host qo'shing.</div>}

      {snapshot && (
        <>
          <LoadSummaryChart hosts={snapshot.hosts} />
          <RiskPanel risks={risks} />
          <section className="grid gap-4 lg:grid-cols-3">
            <div className="space-y-4 lg:col-span-2">
              {snapshot.hosts.map((host) => (
                <HostBlock key={host.id} host={host} selected={selectedEntity} onSelect={setSelected} />
              ))}
            </div>
            <AlertPanel token={token} alerts={snapshot.active_alerts} />
          </section>
          {selectedEntity && <HistoryChart token={token} entity={selectedEntity} />}
        </>
      )}
    </div>
  );
}

function average(values?: Array<number | null | undefined>) {
  const actual = (values ?? []).filter((value): value is number => typeof value === "number");
  if (!actual.length) return null;
  return actual.reduce((sum, value) => sum + value, 0) / actual.length;
}

function pct(value?: number | null) {
  return value === null || value === undefined ? "-" : `${value.toFixed(1)}%`;
}

function loadTone(value?: number | null) {
  if (value === null || value === undefined) return "neutral";
  if (value >= 90) return "bad";
  if (value >= 75) return "warn";
  return "ok";
}
