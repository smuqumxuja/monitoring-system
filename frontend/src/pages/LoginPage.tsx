import { FormEvent, useState } from "react";
import { Activity } from "lucide-react";

import { login } from "../services/api";

type Props = {
  onLogin: (token: string) => void;
};

export default function LoginPage({ onLogin }: Props) {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      onLogin(await login(username, password));
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="app-shell flex min-h-screen items-center justify-center px-4">
      <form className="app-content w-full max-w-sm rounded-lg border border-zinc-200 bg-white/95 p-6 shadow-sm backdrop-blur" onSubmit={submit}>
        <div className="mb-6 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-600 text-white">
            <Activity size={22} />
          </div>
          <div>
            <h1 className="text-lg font-semibold">Monitoring System</h1>
            <p className="text-sm text-zinc-500">ESXi va VM monitoring</p>
          </div>
        </div>
        <label className="mb-3 block">
          <span className="mb-1 block text-sm font-medium text-zinc-700">Login</span>
          <input className="w-full rounded-md border border-zinc-300 px-3 py-2 outline-none focus:border-emerald-600" value={username} onChange={(event) => setUsername(event.target.value)} />
        </label>
        <label className="mb-4 block">
          <span className="mb-1 block text-sm font-medium text-zinc-700">Parol</span>
          <input className="w-full rounded-md border border-zinc-300 px-3 py-2 outline-none focus:border-emerald-600" type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
        </label>
        {error && <div className="mb-4 rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</div>}
        <button className="w-full rounded-md bg-emerald-600 px-4 py-2 font-medium text-white hover:bg-emerald-700 disabled:opacity-60" disabled={loading}>
          {loading ? "Kirilmoqda..." : "Kirish"}
        </button>
      </form>
    </main>
  );
}
