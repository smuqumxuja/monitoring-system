import { useEffect, useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { getHistory } from "../services/api";
import type { EntityRef, Metric } from "../types";

const ranges = ["1h", "24h", "7d", "30d"] as const;

type Props = {
  token: string;
  entity: EntityRef;
  entityOptions?: EntityRef[];
  onEntityChange?: (entity: EntityRef) => void;
};

export default function HistoryChart({ token, entity, entityOptions = [], onEntityChange }: Props) {
  const [range, setRange] = useState<(typeof ranges)[number]>("1h");
  const [rows, setRows] = useState<Metric[]>([]);

  useEffect(() => {
    getHistory(token, entity.type, entity.id, range).then(setRows).catch(() => setRows([]));
  }, [token, entity.type, entity.id, range]);

  const data = rows.map((row) => ({
    time: new Date(row.collected_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    cpu: row.cpu_usage_percent,
    ram: row.ram_usage_percent,
    disk: row.disk_usage_percent ?? row.datastore_usage_percent,
    latency: row.latency_ms,
    loss: row.packet_loss_percent
  }));
  const selectedEntityKey = `${entity.type}:${entity.id}`;

  function changeEntity(value: string) {
    const next = entityOptions.find((item) => `${item.type}:${item.id}` === value);
    if (next) onEntityChange?.(next);
  }

  return (
    <section className="rounded-lg border border-zinc-200 bg-white p-4">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="font-semibold">Tarixiy grafik</div>
          <div className="text-sm text-zinc-500">{entity.label}</div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {entityOptions.length > 1 && (
            <label className="flex items-center gap-2 text-sm text-zinc-600">
              <span>Host/VM tanlash</span>
              <select className="rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-700" value={selectedEntityKey} onChange={(event) => changeEntity(event.target.value)}>
                {entityOptions.map((item) => (
                  <option key={`${item.type}:${item.id}`} value={`${item.type}:${item.id}`}>
                    {item.type === "host" ? "Host: " : "VM: "}
                    {item.label}
                  </option>
                ))}
              </select>
            </label>
          )}
          <div className="flex rounded-md border border-zinc-200 bg-zinc-50 p-1">
            {ranges.map((item) => (
              <button key={item} className={`rounded px-3 py-1 text-sm ${range === item ? "bg-white text-emerald-700 shadow-sm" : "text-zinc-600"}`} onClick={() => setRange(item)}>
                {item}
              </button>
            ))}
          </div>
        </div>
      </div>
      <div className="h-72">
        {data.length ? (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" />
              <XAxis dataKey="time" stroke="#71717a" />
              <YAxis stroke="#71717a" />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="cpu" name="CPU %" stroke="#059669" dot={false} />
              <Line type="monotone" dataKey="ram" name="RAM %" stroke="#0891b2" dot={false} />
              <Line type="monotone" dataKey="disk" name="Disk/Datastore %" stroke="#d97706" dot={false} />
              <Line type="monotone" dataKey="latency" name="Latency ms" stroke="#52525b" dot={false} />
              <Line type="monotone" dataKey="loss" name="Packet loss %" stroke="#e11d48" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex h-full items-center justify-center text-sm text-zinc-500">Bu interval uchun metric yo'q.</div>
        )}
      </div>
    </section>
  );
}
