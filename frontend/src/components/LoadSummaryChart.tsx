import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { Host } from "../types";

type Props = {
  hosts: Host[];
};

export default function LoadSummaryChart({ hosts }: Props) {
  const data = hosts.map((host) => ({
    name: host.name,
    cpu: round(host.latest_metric?.cpu_usage_percent),
    ram: round(host.latest_metric?.ram_usage_percent),
    disk: round(host.latest_metric?.datastore_usage_percent)
  }));

  return (
    <section className="rounded-lg border border-zinc-200 bg-white p-4">
      <div className="mb-4">
        <div className="font-semibold">Hostlar bo'yicha yuklama</div>
        <div className="text-sm text-zinc-500">CPU, RAM va datastore foizlarda</div>
      </div>
      <div className="h-72">
        {data.length ? (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" />
              <XAxis dataKey="name" stroke="#71717a" />
              <YAxis stroke="#71717a" domain={[0, 100]} />
              <Tooltip />
              <Legend />
              <Bar dataKey="cpu" name="CPU %" fill="#059669" radius={[3, 3, 0, 0]} />
              <Bar dataKey="ram" name="RAM %" fill="#0891b2" radius={[3, 3, 0, 0]} />
              <Bar dataKey="disk" name="Disk %" fill="#d97706" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex h-full items-center justify-center text-sm text-zinc-500">Hostlar yo'q.</div>
        )}
      </div>
    </section>
  );
}

function round(value?: number | null) {
  return value === null || value === undefined ? 0 : Number(value.toFixed(1));
}

