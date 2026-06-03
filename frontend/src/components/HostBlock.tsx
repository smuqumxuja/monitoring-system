import type { EntityRef, Host, VM } from "../types";

type Props = {
  host: Host;
  selected: EntityRef | null;
  onSelect: (entity: EntityRef) => void;
};

export default function HostBlock({ host, selected, onSelect }: Props) {
  const metric = host.latest_metric;
  const hostOnline = host.network_status?.online ?? false;
  const hostTone = host.network_status ? (hostOnline ? "normal" : "critical") : "warning";

  return (
    <section className={`rounded-lg border bg-white shadow-sm ${hostOnline ? "border-zinc-200" : "border-rose-200"}`}>
      <button
        className={`flex w-full flex-wrap items-start justify-between gap-3 border-b px-4 py-4 text-left ${
          selected?.type === "host" && selected.id === host.id ? "bg-emerald-50" : ""
        }`}
        onClick={() => onSelect({ type: "host", id: host.id, label: host.name })}
      >
        <div>
          <div className="flex items-center gap-2">
            <h2 className="font-semibold">{host.name}</h2>
            <StatusBadge tone={hostTone} label={host.network_status?.status ?? "unknown"} />
          </div>
          <div className="mt-1 text-sm text-zinc-500">
            {host.hostname}:{host.port} / VM: {host.vms.length}
          </div>
        </div>
        <div className="grid min-w-full grid-cols-2 gap-2 text-sm sm:min-w-[420px] sm:grid-cols-4">
          <LoadCell label="CPU" value={pct(metric?.cpu_usage_percent)} />
          <LoadCell label="RAM" value={pct(metric?.ram_usage_percent)} />
          <LoadCell label="Disk" value={pct(metric?.datastore_usage_percent)} />
          <LoadCell label="Latency" value={latency(host.network_status?.latency_ms)} />
        </div>
      </button>

      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-zinc-50 text-xs uppercase text-zinc-500">
            <tr>
              <th className="px-4 py-3">VM</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Power</th>
              <th className="px-4 py-3">IP</th>
              <th className="px-4 py-3">CPU</th>
              <th className="px-4 py-3">RAM</th>
              <th className="px-4 py-3">Disk</th>
              <th className="px-4 py-3">Ping</th>
            </tr>
          </thead>
          <tbody>
            {host.vms.map((vm) => {
              const health = vmHealth(vm);
              return (
                <tr
                  key={vm.id}
                  className={`cursor-pointer border-t border-zinc-100 hover:bg-zinc-50 ${rowTone(health)} ${
                    selected?.type === "vm" && selected.id === vm.id ? "outline outline-2 outline-emerald-200" : ""
                  }`}
                  onClick={() => onSelect({ type: "vm", id: vm.id, label: vm.name })}
                >
                  <td className="px-4 py-3">
                    <div className="font-medium">{vm.name}</div>
                    <div className="text-xs text-zinc-500">{vm.guest_os ?? "guest OS unknown"}</div>
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge tone={health} label={healthLabel(health)} />
                  </td>
                  <td className="px-4 py-3">{vm.power_state ?? "-"}</td>
                  <td className="px-4 py-3 text-zinc-600">{vm.ip_address ?? "-"}</td>
                  <td className="px-4 py-3">{pct(vm.latest_metric?.cpu_usage_percent)}</td>
                  <td className="px-4 py-3">{pct(vm.latest_metric?.ram_usage_percent)}</td>
                  <td className="px-4 py-3">{size(vm.latest_metric?.disk_size_bytes)}</td>
                  <td className="px-4 py-3">
                    {vm.network_status?.online
                      ? latency(vm.network_status.latency_ms)
                      : vm.network_status?.status ?? "unknown"}
                  </td>
                </tr>
              );
            })}
            {!host.vms.length && (
              <tr>
                <td className="px-4 py-5 text-zinc-500" colSpan={8}>
                  Bu host ichida VM topilmadi.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function LoadCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-zinc-50 px-3 py-2">
      <div className="text-xs text-zinc-500">{label}</div>
      <div className="font-semibold">{value}</div>
    </div>
  );
}

function StatusBadge({ tone, label }: { tone: "normal" | "warning" | "critical"; label: string }) {
  const klass = {
    normal: "bg-emerald-100 text-emerald-700",
    warning: "bg-amber-100 text-amber-700",
    critical: "bg-rose-100 text-rose-700"
  }[tone];
  return <span className={`rounded-full px-2 py-1 text-xs font-medium ${klass}`}>{label}</span>;
}

function vmHealth(vm: VM): "normal" | "warning" | "critical" {
  if (vm.network_status?.status === "offline" || vm.network_status?.online === false) return "critical";
  if (vm.power_state && !vm.power_state.includes("poweredOn")) return "critical";
  const metric = vm.latest_metric;
  if ((metric?.cpu_usage_percent ?? 0) >= 90 || (metric?.ram_usage_percent ?? 0) >= 90 || (metric?.disk_usage_percent ?? 0) >= 92) {
    return "critical";
  }
  if (vm.network_status?.status === "probable_outage" || vm.network_status?.status === "warning") return "warning";
  if ((metric?.cpu_usage_percent ?? 0) >= 75 || (metric?.ram_usage_percent ?? 0) >= 75 || (metric?.disk_usage_percent ?? 0) >= 80) {
    return "warning";
  }
  return "normal";
}

function healthLabel(health: "normal" | "warning" | "critical") {
  if (health === "critical") return "critical/offline";
  return health;
}

function rowTone(health: "normal" | "warning" | "critical") {
  if (health === "critical") return "bg-rose-50/60";
  if (health === "warning") return "bg-amber-50/60";
  return "bg-emerald-50/40";
}

function pct(value?: number | null) {
  return value === null || value === undefined ? "-" : `${value.toFixed(1)}%`;
}

function latency(value?: number | null) {
  return value === null || value === undefined ? "-" : `${Math.round(value)} ms`;
}

function size(value?: number | null) {
  if (value === null || value === undefined) return "-";
  const gb = value / 1024 / 1024 / 1024;
  return `${gb.toFixed(gb >= 10 ? 0 : 1)} GB`;
}
