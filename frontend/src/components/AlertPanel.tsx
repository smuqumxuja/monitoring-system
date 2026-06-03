import { Check, TriangleAlert } from "lucide-react";

import { apiFetch } from "../services/api";
import type { Alert } from "../types";

type Props = {
  token: string;
  alerts: Alert[];
};

export default function AlertPanel({ token, alerts }: Props) {
  const ack = async (id: number) => {
    await apiFetch(`/alerts/${id}/ack`, { method: "PATCH", token });
  };

  return (
    <aside className="rounded-lg border border-zinc-200 bg-white">
      <div className="flex items-center justify-between border-b border-zinc-200 px-4 py-3">
        <div className="font-semibold">Alertlar</div>
        <span className="rounded-full bg-zinc-100 px-2 py-1 text-xs text-zinc-600">{alerts.length}</span>
      </div>
      <div className="max-h-[520px] overflow-y-auto p-3">
        {alerts.map((alert) => (
          <div key={alert.id} className="mb-3 rounded-md border border-zinc-200 p-3 last:mb-0">
            <div className="flex gap-2">
              <TriangleAlert size={18} className={alert.level === "critical" ? "text-rose-600" : "text-amber-600"} />
              <div className="min-w-0 flex-1">
                <div className="truncate font-medium">{alert.title}</div>
                <p className="mt-1 text-sm text-zinc-600">{alert.message}</p>
                <div className="mt-2 text-xs text-zinc-500">{new Date(alert.created_at).toLocaleString()}</div>
              </div>
              <button className="rounded-md p-1 text-zinc-500 hover:bg-zinc-100" onClick={() => ack(alert.id)} title="Acknowledge">
                <Check size={16} />
              </button>
            </div>
          </div>
        ))}
        {!alerts.length && <div className="p-4 text-sm text-zinc-500">Aktiv alert yo'q.</div>}
      </div>
    </aside>
  );
}

