import type { Branch, HostRecord, Metric, NotificationSettings, PredictiveRisk, Snapshot, SystemLog, Threshold, User, VM } from "../types";

const configuredApiBase = import.meta.env.VITE_API_BASE_URL as string | undefined;
const configuredWsBase = import.meta.env.VITE_WS_BASE_URL as string | undefined;
const wsProtocol = window.location.protocol === "https:" ? "wss" : "ws";

export const API_BASE = configuredApiBase?.length ? configuredApiBase : `${window.location.origin}/api`;
export const WS_BASE = configuredWsBase?.length ? configuredWsBase : `${wsProtocol}://${window.location.host}/ws`;

type Options = RequestInit & {
  token?: string | null;
};

export async function apiFetch<T>(path: string, options: Options = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.token) headers.set("Authorization", `Bearer ${options.token}`);
  if (options.body && !(options.body instanceof URLSearchParams) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(body.detail ?? response.statusText);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export async function login(username: string, password: string): Promise<string> {
  const form = new URLSearchParams();
  form.set("username", username);
  form.set("password", password);
  const response = await apiFetch<{ access_token: string }>("/auth/login", {
    method: "POST",
    body: form
  });
  return response.access_token;
}

export const getMe = (token: string) => apiFetch<User>("/auth/me", { token });
export const getHosts = (token: string) => apiFetch<HostRecord[]>("/hosts", { token });
export const getSnapshot = (token: string) => apiFetch<Snapshot>("/metrics/current", { token });
export const getPredictiveRisks = (token: string) => apiFetch<PredictiveRisk[]>("/metrics/risks", { token });
export const getBranches = (token: string) => apiFetch<Branch[]>("/admin/branches", { token });
export const createBranch = (token: string, payload: Partial<Branch>) =>
  apiFetch<Branch>("/admin/branches", { method: "POST", token, body: JSON.stringify(payload) });
export const updateBranch = (token: string, id: number, payload: Partial<Branch>) =>
  apiFetch<Branch>(`/admin/branches/${id}`, { method: "PUT", token, body: JSON.stringify(payload) });
export const getThresholds = (token: string) => apiFetch<Threshold[]>("/admin/thresholds", { token });
export const getAdminVMs = (token: string) => apiFetch<VM[]>("/admin/vms", { token });
export const getUsers = (token: string) => apiFetch<User[]>("/admin/users", { token });
export const getSystemLogs = (token: string) => apiFetch<SystemLog[]>("/admin/logs", { token });
export const updateSystemLog = (token: string, id: number, patch: Partial<Pick<SystemLog, "status" | "admin_note">>) =>
  apiFetch<SystemLog>(`/admin/logs/${id}`, { method: "PUT", token, body: JSON.stringify(patch) });
export const getNotificationSettings = (token: string) =>
  apiFetch<NotificationSettings>("/admin/notification-settings", { token });
export const getHistory = (token: string, type: "host" | "vm", id: number, range: string) =>
  apiFetch<Metric[]>(`/metrics/history?entity_type=${type}&entity_id=${id}&range=${range}`, { token });
