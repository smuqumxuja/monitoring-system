import { FormEvent, useEffect, useState } from "react";
import { Activity, RefreshCw } from "lucide-react";

import { getCaptcha, login } from "../services/api";
import type { CaptchaChallenge } from "../services/api";

type Props = {
  onLogin: (token: string) => void;
};

export default function LoginPage({ onLogin }: Props) {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [captcha, setCaptcha] = useState<CaptchaChallenge | null>(null);
  const [captchaAnswer, setCaptchaAnswer] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [captchaLoading, setCaptchaLoading] = useState(false);

  const loadCaptcha = async () => {
    setCaptchaLoading(true);
    setCaptchaAnswer("");
    try {
      setCaptcha(await getCaptcha());
    } catch (exc) {
      setCaptcha(null);
      setError(exc instanceof Error ? exc.message : "Captcha yuklanmadi");
    } finally {
      setCaptchaLoading(false);
    }
  };

  useEffect(() => {
    void loadCaptcha();
  }, []);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!captcha) {
      setError("Captcha hali yuklanmagan");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      onLogin(await login(username, password, captcha.captcha_token, captchaAnswer));
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Login failed");
      void loadCaptcha();
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
        <div className="mb-4 rounded-md border border-zinc-200 bg-zinc-50 p-3">
          <div className="mb-2 flex items-center justify-between gap-2">
            <span className="text-sm font-medium text-zinc-700">Captcha</span>
            <button className="rounded-md border border-zinc-300 bg-white p-2 text-zinc-600" type="button" onClick={() => void loadCaptcha()} disabled={captchaLoading || loading} title="Captchani yangilash">
              <RefreshCw size={16} />
            </button>
          </div>
          <div className="mb-2 rounded-md bg-white px-3 py-2 text-center text-lg font-semibold text-zinc-900">
            {captchaLoading ? "Yuklanmoqda..." : captcha?.question ?? "Captcha yo'q"}
          </div>
          <input
            className="w-full rounded-md border border-zinc-300 px-3 py-2 outline-none focus:border-emerald-600"
            inputMode="numeric"
            placeholder="Javobni kiriting"
            value={captchaAnswer}
            onChange={(event) => setCaptchaAnswer(event.target.value)}
          />
        </div>
        {error && <div className="mb-4 rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</div>}
        <button className="w-full rounded-md bg-emerald-600 px-4 py-2 font-medium text-white hover:bg-emerald-700 disabled:opacity-60" disabled={loading || captchaLoading || !captcha || !captchaAnswer.trim()}>
          {loading ? "Kirilmoqda..." : "Kirish"}
        </button>
      </form>
    </main>
  );
}
