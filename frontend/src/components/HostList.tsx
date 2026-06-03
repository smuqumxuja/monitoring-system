import type { EntityRef, Host } from "../types";

type Props = {
  hosts: Host[];
  selected: EntityRef | null;
  onSelect: (entity: EntityRef) => void;
};

export default function HostList({ hosts, selected, onSelect }: Props) {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      {hosts.map((host) => {
        const metric = host.latest_metric;
        const network = host.network_status;
        return (
          <button
            key={host.id}
            className={`rounded-lg border bg-white p-4 text-left shadow-sm hover:border-emerald-500 ${
              selected?.type === "host" && selected.id === host.id ? "border-emerald-500 ring-2 ring-emerald-100" : "border-zinc-200"
            }`}
            onClick={() => onSelect({ type: "host", id: host.id, label: host.name })}
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="font-semibold">{host.name}</div>
                <div className="text-sm text-zinc-500">{host.hostname}</div>
              </div>
              <span className={`rounded-full px-2 py-1 text-xs ${network?.online ? "bg-emerald-100 text-emerald-700" : "bg-rose-100 text-rose-700"}`}>
                {network?.status ?? "unknown"}
              </span>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
              <Cell label="CPU" value={percent(metric?.cpu_usage_percent)} />
              <Cell label="RAM" value={percent(metric?.ram_usage_percent)} />
              <Cell label="Datastore" value={percent(metric?.datastore_usage_percent)} />
              <Cell label="VM" value={host.vms.length.toString()} />
            </div>
            <div className="mt-3 text-sm text-zinc-600">
              RX {rate(metric?.network_rx_kbps)} / TX {rate(metric?.network_tx_kbps)}
              {network?.last_success_at ? ` / last ok ${new Date(network.last_success_at).toLocaleTimeString()}` : ""}
            </div>
          </button>
        );
      })}
    </div>
  );
}

function Cell({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-zinc-50 px-3 py-2">
      <div className="text-xs text-zinc-500">{label}</div>
      <div className="font-semibold">{value}</div>
    </div>
  );
}

function percent(value?: number | null) {
  return value === null || value === undefined ? "-" : `${value.toFixed(1)}%`;
}

function rate(value?: number | null) {
  return value === null || value === undefined ? "-" : `${value.toFixed(1)} Kbps`;
}
