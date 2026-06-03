import { useEffect, useState } from "react";
import { LayoutDashboard, LogOut, Settings } from "lucide-react";

import AdminPage from "./pages/AdminPage";
import DashboardPage from "./pages/DashboardPage";
import LoginPage from "./pages/LoginPage";
import { getMe } from "./services/api";
import type { User } from "./types";

const TOKEN_KEY = "monitoring_token";
const SESSION_EXPIRES_KEY = "monitoring_session_expires_at";
const SESSION_TTL_MS = 60 * 60 * 1000;

function storedToken() {
  const token = localStorage.getItem(TOKEN_KEY);
  const expiresAt = Number(localStorage.getItem(SESSION_EXPIRES_KEY) ?? "0");
  if (!token || !expiresAt || Date.now() >= expiresAt) {
    clearSession();
    return null;
  }
  return token;
}

function saveSession(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(SESSION_EXPIRES_KEY, String(Date.now() + SESSION_TTL_MS));
}

function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(SESSION_EXPIRES_KEY);
}

export default function App() {
  const [token, setToken] = useState(storedToken);
  const [user, setUser] = useState<User | null>(null);
  const [authLoading, setAuthLoading] = useState(Boolean(token));
  const [page, setPage] = useState<"dashboard" | "admin">("dashboard");

  useEffect(() => {
    if (!token) {
      setUser(null);
      setAuthLoading(false);
      return;
    }
    setAuthLoading(true);
    getMe(token)
      .then((currentUser) => {
        setUser(currentUser);
        saveSession(token);
      })
      .catch(() => {
        clearSession();
        setToken(null);
      })
      .finally(() => {
        setAuthLoading(false);
      });
  }, [token]);

  if (authLoading) {
    return (
      <main className="app-shell flex min-h-screen items-center justify-center px-4">
        <div className="app-content rounded-lg border border-zinc-200 bg-white/95 px-5 py-4 text-sm font-medium text-zinc-700 shadow-sm backdrop-blur">
          Sessiya tekshirilmoqda...
        </div>
      </main>
    );
  }

  if (!token || !user) {
    return <LoginPage onLogin={(nextToken) => { saveSession(nextToken); setToken(nextToken); }} />;
  }

  const logout = () => {
    clearSession();
    setToken(null);
    setUser(null);
  };

  const navClass = (target: "dashboard" | "admin") =>
    `nav-item flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium ${
      page === target ? "nav-item-active" : "nav-item-inactive hover:bg-zinc-100"
    }`;

  return (
    <div className="app-shell min-h-screen">
      <header className="app-content border-b border-zinc-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
          <div>
            <h1 className="font-semibold">Monitoring System</h1>
            <p className="text-xs text-zinc-500">{user.username} / {user.role}</p>
          </div>
          <nav className="flex items-center gap-2">
            <button className={navClass("dashboard")} aria-current={page === "dashboard" ? "page" : undefined} onClick={() => setPage("dashboard")}>
              <LayoutDashboard size={16} /> Dashboard
            </button>
            {(user.role === "admin" || user.role === "superadmin") && (
              <button className={navClass("admin")} aria-current={page === "admin" ? "page" : undefined} onClick={() => setPage("admin")}>
                <Settings size={16} /> Admin
              </button>
            )}
            <button className="rounded-md p-2 text-zinc-600 hover:bg-zinc-100" onClick={logout} title="Logout">
              <LogOut size={18} />
            </button>
          </nav>
        </div>
      </header>
      <main className="app-content mx-auto max-w-7xl px-4 py-5">
        {page === "admin" && (user.role === "admin" || user.role === "superadmin") ? <AdminPage token={token} currentUser={user} /> : <DashboardPage token={token} />}
      </main>
    </div>
  );
}
