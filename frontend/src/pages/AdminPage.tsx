import { useEffect, useMemo, useState } from "react";
import type { Dispatch, FormEvent, ReactNode, SetStateAction } from "react";
import { Bell, Building2, ClipboardList, HardDrive, ListChecks, RefreshCw, Save, Server, Trash2, Users } from "lucide-react";

import {
  apiFetch,
  createBranch,
  getAdminVMs,
  getBranches,
  getHosts,
  getNotificationSettings,
  getSystemLogs,
  getThresholds,
  getUsers,
  updateBranch,
  updateSystemLog
} from "../services/api";
import type { Branch, HostRecord, NotificationSettings, SystemLog, Threshold, User, VM } from "../types";

type Props = { token: string; currentUser: User };
type Tab = "hosts" | "vms" | "thresholds" | "notifications" | "users" | "branches" | "logs";
type Draft = Record<string, string | number | boolean | null | undefined>;
type HostDraft = { branch_id: number | null; name: string; hostname: string; username: string; password: string; port: number; verify_ssl: boolean; active: boolean; snmp_enabled: boolean; snmp_community: string; snmp_port: number };
type VMDraft = { host_id: number | null; moid: string; name: string; guest_os: string; ip_address: string; power_state: string; uptime_seconds: string; monitoring_enabled: boolean };
type UserDraft = { username: string; password: string; role: User["role"]; branch_id: number | null; is_active: boolean };
type BranchDraft = { name: string; code: string; address: string; active: boolean };
type NotificationDraft = { telegram_bot_token: string; telegram_chat_id: string; smtp_host: string; smtp_port: number; smtp_username: string; smtp_password: string; smtp_from: string; smtp_to: string; smtp_use_tls: boolean };

const hostBlank: HostDraft = { branch_id: null, name: "", hostname: "", username: "root", password: "", port: 443, verify_ssl: false, active: true, snmp_enabled: false, snmp_community: "public", snmp_port: 161 };
const vmBlank: VMDraft = { host_id: null, moid: "", name: "", guest_os: "", ip_address: "", power_state: "manual", uptime_seconds: "", monitoring_enabled: true };
const userBlank: UserDraft = { username: "", password: "", role: "kuzatuvchi", branch_id: null, is_active: true };
const branchBlank: BranchDraft = { name: "", code: "", address: "", active: true };
const notificationBlank: NotificationDraft = { telegram_bot_token: "", telegram_chat_id: "", smtp_host: "", smtp_port: 587, smtp_username: "", smtp_password: "", smtp_from: "", smtp_to: "", smtp_use_tls: true };

export default function AdminPage({ token, currentUser }: Props) {
  const [tab, setTab] = useState<Tab>("hosts");
  const [hosts, setHosts] = useState<HostRecord[]>([]);
  const [vms, setVms] = useState<VM[]>([]);
  const [thresholds, setThresholds] = useState<Threshold[]>([]);
  const [branches, setBranches] = useState<Branch[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [logs, setLogs] = useState<SystemLog[]>([]);
  const [host, setHost] = useState({ ...hostBlank });
  const [vm, setVm] = useState({ ...vmBlank });
  const [newUser, setNewUser] = useState({ ...userBlank });
  const [branch, setBranch] = useState({ ...branchBlank });
  const [notification, setNotification] = useState({ ...notificationBlank });
  const [editingHost, setEditingHost] = useState<number | null>(null);
  const [editingVM, setEditingVM] = useState<number | null>(null);
  const [editingBranch, setEditingBranch] = useState<number | null>(null);
  const [thresholdDrafts, setThresholdDrafts] = useState<Record<string, Draft>>({});
  const [userDrafts, setUserDrafts] = useState<Record<number, Draft>>({});
  const [logDrafts, setLogDrafts] = useState<Record<number, Draft>>({});
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("Tizim tayyor.");

  const isSuperadmin = currentUser.role === "superadmin";
  const firstBranch = branches[0]?.id ?? null;
  const hostName = useMemo(() => new Map(hosts.map((row) => [row.id, row.name])), [hosts]);

  async function refresh() {
    setLoading(true);
    try {
      const [h, vmRows, th, br, us, lg, settings] = await Promise.all([
        getHosts(token),
        getAdminVMs(token),
        getThresholds(token),
        getBranches(token),
        getUsers(token),
        getSystemLogs(token),
        getNotificationSettings(token)
      ]);
      setHosts(h);
      setVms(vmRows);
      setThresholds(th);
      setBranches(br);
      setUsers(us);
      setLogs(lg);
      setNotification(toNotificationForm(settings));
      setThresholdDrafts(Object.fromEntries(th.map((row) => [row.metric, pick(row, ["warning_value", "critical_value", "operator", "enabled"])])));
      setUserDrafts(Object.fromEntries(us.map((row) => [row.id, pick(row, ["role", "branch_id", "is_active"])])));
      setLogDrafts(Object.fromEntries(lg.map((row) => [row.id, { status: row.status, admin_note: row.admin_note ?? "" }])));
      setMessage("Ma'lumotlar yangilandi.");
    } catch (error) {
      setMessage(err(error));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, [token]);

  useEffect(() => {
    if (host.branch_id === null && firstBranch) setHost((old) => ({ ...old, branch_id: firstBranch }));
    if (newUser.branch_id === null && firstBranch) setNewUser((old) => ({ ...old, branch_id: firstBranch }));
    if (vm.host_id === null && hosts[0]?.id) setVm((old) => ({ ...old, host_id: hosts[0].id }));
  }, [firstBranch, hosts]);

  async function save(action: () => Promise<unknown>, ok: string) {
    try {
      setLoading(true);
      await action();
      setMessage(ok);
      await refresh();
    } catch (error) {
      setMessage(err(error));
    } finally {
      setLoading(false);
    }
  }

  async function submitHost(event: FormEvent) {
    event.preventDefault();
    const body: Draft = { ...host, snmp_community: host.snmp_enabled ? host.snmp_community : null };
    if (editingHost && !body.password) delete body.password;
    await save(
      () => apiFetch(editingHost ? `/hosts/${editingHost}` : "/hosts", { method: editingHost ? "PUT" : "POST", token, body: JSON.stringify(body) }),
      "ESXi host saqlandi."
    );
    setHost({ ...hostBlank, branch_id: firstBranch });
    setEditingHost(null);
  }

  async function submitVM(event: FormEvent) {
    event.preventDefault();
    const body = { ...vm, moid: vm.moid || null, guest_os: vm.guest_os || null, ip_address: vm.ip_address || null, uptime_seconds: vm.uptime_seconds ? Number(vm.uptime_seconds) : null };
    await save(
      () => apiFetch(editingVM ? `/admin/vms/${editingVM}` : "/admin/vms", { method: editingVM ? "PUT" : "POST", token, body: JSON.stringify(body) }),
      "VM ma'lumoti saqlandi."
    );
    setVm({ ...vmBlank, host_id: hosts[0]?.id ?? null });
    setEditingVM(null);
  }

  async function submitUser(event: FormEvent) {
    event.preventDefault();
    await save(
      () => apiFetch("/admin/users", { method: "POST", token, body: JSON.stringify({ ...newUser, branch_id: newUser.role === "superadmin" ? null : newUser.branch_id }) }),
      "Foydalanuvchi yaratildi."
    );
    setNewUser({ ...userBlank, branch_id: firstBranch });
  }

  async function submitBranch(event: FormEvent) {
    event.preventDefault();
    await save(() => (editingBranch ? updateBranch(token, editingBranch, branch) : createBranch(token, branch)), "Filial saqlandi.");
    setBranch({ ...branchBlank });
    setEditingBranch(null);
  }

  async function submitNotifications(event: FormEvent) {
    event.preventDefault();
    const body = {
      telegram_bot_token: notification.telegram_bot_token || undefined,
      telegram_chat_id: notification.telegram_chat_id || null,
      smtp_host: notification.smtp_host || null,
      smtp_port: notification.smtp_port,
      smtp_username: notification.smtp_username || null,
      smtp_password: notification.smtp_password || undefined,
      smtp_from: notification.smtp_from || null,
      smtp_to: notification.smtp_to || null,
      smtp_use_tls: notification.smtp_use_tls
    };
    await save(() => apiFetch("/admin/notification-settings", { method: "PUT", token, body: JSON.stringify(body) }), "Alert sozlamalari saqlandi.");
    setNotification((old) => ({ ...old, telegram_bot_token: "", smtp_password: "" }));
  }

  function startHostEdit(row: HostRecord) {
    setEditingHost(row.id);
    setHost({ branch_id: row.branch_id, name: row.name, hostname: row.hostname, username: row.username, password: "", port: row.port, verify_ssl: row.verify_ssl, active: row.active, snmp_enabled: row.snmp_enabled, snmp_community: row.snmp_community ?? "public", snmp_port: row.snmp_port });
    setTab("hosts");
  }

  function startVMEdit(row: VM) {
    setEditingVM(row.id);
    setVm({ host_id: row.host_id, moid: row.moid, name: row.name, guest_os: row.guest_os ?? "", ip_address: row.ip_address ?? "", power_state: row.power_state ?? "manual", uptime_seconds: row.uptime_seconds ? String(row.uptime_seconds) : "", monitoring_enabled: row.monitoring_enabled });
    setTab("vms");
  }

  const tabs: Array<{ id: Tab; label: string; icon: ReactNode; superOnly?: boolean }> = [
    { id: "hosts", label: "ESXi hostlar", icon: <Server size={16} /> },
    { id: "vms", label: "VM lar", icon: <HardDrive size={16} /> },
    { id: "thresholds", label: "Threshold", icon: <ListChecks size={16} /> },
    { id: "notifications", label: "Alert sozlamalari", icon: <Bell size={16} /> },
    { id: "users", label: "Foydalanuvchilar", icon: <Users size={16} /> },
    { id: "branches", label: "Filiallar", icon: <Building2 size={16} />, superOnly: true },
    { id: "logs", label: "Log jurnallar", icon: <ClipboardList size={16} /> }
  ];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div><h2 className="text-xl font-semibold">Admin panel</h2><p className="text-sm text-zinc-500">Role: {currentUser.role} {currentUser.branch_name ? `/ ${currentUser.branch_name}` : ""}</p></div>
        <button className="flex items-center gap-2 rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm" onClick={() => void refresh()} disabled={loading}><RefreshCw size={16} /> Yangilash</button>
      </div>
      <div className="rounded-lg border border-zinc-200 bg-white p-2"><div className="flex flex-wrap gap-2">{tabs.filter((item) => !item.superOnly || isSuperadmin).map((item) => <button key={item.id} className={`nav-item flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium ${tab === item.id ? "nav-item-active" : "nav-item-inactive hover:bg-zinc-100"}`} aria-current={tab === item.id ? "page" : undefined} onClick={() => setTab(item.id)}>{item.icon}{item.label}</button>)}</div></div>
      <div className="rounded-lg border border-zinc-200 bg-white px-4 py-3 text-sm text-zinc-700">{loading ? "Bajarilmoqda..." : message}</div>

      {tab === "hosts" && <Section title={editingHost ? "ESXi hostni tahrirlash" : "Yangi ESXi host qo'shish"}>
        <form className="grid gap-3 lg:grid-cols-4" onSubmit={submitHost}>
          <BranchSelect value={host.branch_id} branches={branches} disabled={!isSuperadmin} onChange={(branch_id) => setHost({ ...host, branch_id })} />
          <Input label="Nomi" value={host.name} onChange={(name) => setHost({ ...host, name })} />
          <Input label="IP/hostname" value={host.hostname} onChange={(hostname) => setHost({ ...host, hostname })} />
          <Input label="Username" value={host.username} onChange={(username) => setHost({ ...host, username })} />
          <Input label={editingHost ? "Yangi parol" : "Parol"} type="password" value={host.password} onChange={(password) => setHost({ ...host, password })} />
          <NumberInput label="Port" value={host.port} onChange={(port) => setHost({ ...host, port })} />
          <NumberInput label="SNMP port" value={host.snmp_port} onChange={(snmp_port) => setHost({ ...host, snmp_port })} />
          <Input label="SNMP community" value={host.snmp_community} onChange={(snmp_community) => setHost({ ...host, snmp_community })} />
          <Check label="SSL verify" checked={host.verify_ssl} onChange={(verify_ssl) => setHost({ ...host, verify_ssl })} />
          <Check label="Active" checked={host.active} onChange={(active) => setHost({ ...host, active })} />
          <Check label="SNMP monitoring" checked={host.snmp_enabled} onChange={(snmp_enabled) => setHost({ ...host, snmp_enabled })} />
          <Actions primary={editingHost ? "O'zgarishlarni saqlash" : "Host qo'shish"} onCancel={editingHost ? () => { setEditingHost(null); setHost({ ...hostBlank, branch_id: firstBranch }); } : undefined} />
        </form>
        <Table headers={["Nomi", "Filial", "IP", "User", "Holat", "Amal"]}>{hosts.map((row) => <tr key={row.id}><Td>{row.name}</Td><Td>{row.branch_name ?? "-"}</Td><Td>{row.hostname}:{row.port}</Td><Td>{row.username}</Td><Td>{row.active ? "active" : "disabled"}</Td><Td><Small onClick={() => startHostEdit(row)}>Tahrirlash</Small><Danger onClick={() => void save(() => apiFetch(`/hosts/${row.id}`, { method: "DELETE", token }), "Host o'chirildi.")}>O'chirish</Danger></Td></tr>)}</Table>
      </Section>}

      {tab === "vms" && <Section title={editingVM ? "VMni tahrirlash" : "Yangi VM qo'shish"}>
        <form className="grid gap-3 lg:grid-cols-4" onSubmit={submitVM}>
          <label className="text-sm font-medium text-zinc-700">ESXi host<select className="mt-1 w-full rounded-md border border-zinc-300 px-3 py-2" value={vm.host_id ?? ""} onChange={(e) => setVm({ ...vm, host_id: Number(e.target.value) || null })}>{hosts.map((row) => <option key={row.id} value={row.id}>{row.name}</option>)}</select></label>
          <Input label="VM nomi" value={vm.name} onChange={(name) => setVm({ ...vm, name })} />
          <Input label="MOID" value={vm.moid} onChange={(moid) => setVm({ ...vm, moid })} />
          <Input label="IP address" value={vm.ip_address} onChange={(ip_address) => setVm({ ...vm, ip_address })} />
          <Input label="Guest OS" value={vm.guest_os} onChange={(guest_os) => setVm({ ...vm, guest_os })} />
          <Input label="Power status" value={vm.power_state} onChange={(power_state) => setVm({ ...vm, power_state })} />
          <Input label="Uptime seconds" value={vm.uptime_seconds} onChange={(uptime_seconds) => setVm({ ...vm, uptime_seconds })} />
          <Check label="Monitoring yoqilgan" checked={vm.monitoring_enabled} onChange={(monitoring_enabled) => setVm({ ...vm, monitoring_enabled })} />
          <Actions primary={editingVM ? "VM o'zgarishini saqlash" : "VM qo'shish"} onCancel={editingVM ? () => { setEditingVM(null); setVm({ ...vmBlank, host_id: hosts[0]?.id ?? null }); } : undefined} />
        </form>
        <Table headers={["VM", "Host", "IP", "Power", "Monitoring", "Amal"]}>{vms.map((row) => <tr key={row.id}><Td>{row.name}</Td><Td>{hostName.get(row.host_id) ?? row.host_id}</Td><Td>{row.ip_address ?? "-"}</Td><Td>{row.power_state ?? "-"}</Td><Td>{row.monitoring_enabled ? "on" : "off"}</Td><Td><Small onClick={() => startVMEdit(row)}>Tahrirlash</Small><Small onClick={() => void save(() => apiFetch(`/admin/vms/${row.id}/monitoring`, { method: "PUT", token, body: JSON.stringify({ monitoring_enabled: !row.monitoring_enabled }) }), "VM monitoring holati o'zgardi.")}>{row.monitoring_enabled ? "O'chirish" : "Yoqish"}</Small><Danger onClick={() => void save(() => apiFetch(`/admin/vms/${row.id}`, { method: "DELETE", token }), "VM o'chirildi.")}>O'chirish</Danger></Td></tr>)}</Table>
      </Section>}

      {tab === "thresholds" && <Section title="Threshold sozlamalari"><Table headers={["Metric", "Warning", "Critical", "Operator", "Enabled", "Amal"]}>{thresholds.map((row) => {
        const d = thresholdDrafts[row.metric] ?? {};
        return <tr key={row.metric}><Td>{row.metric}</Td><Td><Mini value={String(d.warning_value ?? "")} onChange={(warning_value) => setDraft(setThresholdDrafts, row.metric, d, { warning_value: Number(warning_value) })} /></Td><Td><Mini value={String(d.critical_value ?? "")} onChange={(critical_value) => setDraft(setThresholdDrafts, row.metric, d, { critical_value: Number(critical_value) })} /></Td><Td><select className="rounded-md border border-zinc-300 px-2 py-1" value={String(d.operator ?? row.operator)} onChange={(e) => setDraft(setThresholdDrafts, row.metric, d, { operator: e.target.value })}><option value="gte">gte</option><option value="lte">lte</option></select></Td><Td><input type="checkbox" checked={Boolean(d.enabled)} onChange={(e) => setDraft(setThresholdDrafts, row.metric, d, { enabled: e.target.checked })} /></Td><Td><Small onClick={() => void save(() => apiFetch(`/admin/thresholds/${row.metric}`, { method: "PUT", token, body: JSON.stringify(d) }), "Threshold saqlandi.")}>Saqlash</Small></Td></tr>;
      })}</Table></Section>}

      {tab === "notifications" && <Section title="Telegram va email alert sozlamalari"><form className="grid gap-3 lg:grid-cols-3" onSubmit={submitNotifications}>
        {["telegram_bot_token", "telegram_chat_id", "smtp_host", "smtp_username", "smtp_password", "smtp_from", "smtp_to"].map((key) => <Input key={key} label={key} type={key.includes("token") || key.includes("password") ? "password" : "text"} value={String(notification[key as keyof typeof notification] ?? "")} onChange={(value) => setNotification({ ...notification, [key]: value })} />)}
        <NumberInput label="smtp_port" value={notification.smtp_port} onChange={(smtp_port) => setNotification({ ...notification, smtp_port })} />
        <Check label="SMTP TLS" checked={notification.smtp_use_tls} onChange={(smtp_use_tls) => setNotification({ ...notification, smtp_use_tls })} />
        <Actions primary="Alert sozlamalarini saqlash" />
      </form></Section>}

      {tab === "users" && <Section title="Yangi foydalanuvchi yaratish va rol berish">
        <form className="grid gap-3 lg:grid-cols-5" onSubmit={submitUser}>
          <Input label="Username" value={newUser.username} onChange={(username) => setNewUser({ ...newUser, username })} />
          <Input label="Password" type="password" value={newUser.password} onChange={(password) => setNewUser({ ...newUser, password })} />
          <RoleSelect value={newUser.role} superadmin={isSuperadmin} onChange={(role) => setNewUser({ ...newUser, role })} />
          <BranchSelect value={newUser.branch_id} branches={branches} disabled={!isSuperadmin || newUser.role === "superadmin"} onChange={(branch_id) => setNewUser({ ...newUser, branch_id })} />
          <Check label="Active" checked={newUser.is_active} onChange={(is_active) => setNewUser({ ...newUser, is_active })} />
          <Actions primary="Foydalanuvchi qo'shish" />
        </form>
        <Table headers={["Username", "Role", "Filial", "Active", "Amal"]}>{users.map((row) => {
          const d = userDrafts[row.id] ?? {};
          return <tr key={row.id}><Td>{row.username}</Td><Td><RoleSelect value={(d.role as User["role"]) ?? row.role} superadmin={isSuperadmin} onChange={(role) => setDraft(setUserDrafts, row.id, d, { role })} /></Td><Td><BranchSelect compact value={(d.branch_id as number | null) ?? null} branches={branches} disabled={!isSuperadmin || d.role === "superadmin"} onChange={(branch_id) => setDraft(setUserDrafts, row.id, d, { branch_id })} /></Td><Td><input type="checkbox" checked={Boolean(d.is_active)} onChange={(e) => setDraft(setUserDrafts, row.id, d, { is_active: e.target.checked })} /></Td><Td><Small onClick={() => void save(() => apiFetch(`/admin/users/${row.id}`, { method: "PUT", token, body: JSON.stringify(d) }), "Foydalanuvchi o'zgartirildi.")}>Saqlash</Small></Td></tr>;
        })}</Table>
      </Section>}

      {tab === "branches" && isSuperadmin && <Section title={editingBranch ? "Filialni tahrirlash" : "Filial qo'shish"}>
        <form className="grid gap-3 lg:grid-cols-4" onSubmit={submitBranch}>
          <Input label="Nomi" value={branch.name} onChange={(name) => setBranch({ ...branch, name })} />
          <Input label="Kodi" value={branch.code} onChange={(code) => setBranch({ ...branch, code })} />
          <Input label="Manzil" value={branch.address} onChange={(address) => setBranch({ ...branch, address })} />
          <Check label="Active" checked={branch.active} onChange={(active) => setBranch({ ...branch, active })} />
          <Actions primary={editingBranch ? "Filialni saqlash" : "Filial qo'shish"} onCancel={editingBranch ? () => { setEditingBranch(null); setBranch({ ...branchBlank }); } : undefined} />
        </form>
        <Table headers={["Nomi", "Kod", "Manzil", "Active", "Amal"]}>{branches.map((row) => <tr key={row.id}><Td>{row.name}</Td><Td>{row.code}</Td><Td>{row.address ?? "-"}</Td><Td>{row.active ? "active" : "disabled"}</Td><Td><Small onClick={() => { setEditingBranch(row.id); setBranch({ name: row.name, code: row.code, address: row.address ?? "", active: row.active }); }}>Tahrirlash</Small></Td></tr>)}</Table>
      </Section>}

      {tab === "logs" && <Section title="Log jurnallar"><Table headers={["Vaqt", "Level", "Category", "Source", "Message", "Status", "Admin izoh", "Amal"]}>{logs.map((row) => {
        const d = logDrafts[row.id] ?? { status: row.status, admin_note: row.admin_note ?? "" };
        return <tr key={row.id}><Td>{new Date(row.created_at).toLocaleString()}</Td><Td>{row.level}</Td><Td>{row.category}</Td><Td>{row.source ?? "-"}</Td><Td>{row.message}</Td><Td><select className="rounded-md border border-zinc-300 px-2 py-1" value={String(d.status)} onChange={(e) => setDraft(setLogDrafts, row.id, d, { status: e.target.value })}><option value="open">open</option><option value="reviewed">reviewed</option><option value="resolved">resolved</option></select></Td><Td><Mini value={String(d.admin_note ?? "")} onChange={(admin_note) => setDraft(setLogDrafts, row.id, d, { admin_note })} /></Td><Td><Small onClick={() => void save(() => updateSystemLog(token, row.id, d as Pick<SystemLog, "status" | "admin_note">), "Log yozuvi yangilandi.")}>Saqlash</Small></Td></tr>;
      })}</Table></Section>}
    </div>
  );
}

function pick(source: object, keys: string[]): Draft {
  const row = source as unknown as Draft;
  return Object.fromEntries(keys.map((key) => [key, row[key]]));
}

function setDraft<K extends string | number>(setter: Dispatch<SetStateAction<Record<K, Draft>>>, id: K, current: Draft, patch: Draft) {
  setter((all) => ({ ...all, [id]: { ...current, ...patch } }));
}

function toNotificationForm(settings: NotificationSettings) {
  return { ...notificationBlank, telegram_chat_id: settings.telegram_chat_id ?? "", smtp_host: settings.smtp_host ?? "", smtp_port: settings.smtp_port, smtp_username: settings.smtp_username ?? "", smtp_from: settings.smtp_from ?? "", smtp_to: settings.smtp_to ?? "", smtp_use_tls: settings.smtp_use_tls };
}

function err(error: unknown) {
  return error instanceof Error ? error.message : "Noma'lum xatolik.";
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return <section className="space-y-4 rounded-lg border border-zinc-200 bg-white p-4"><h3 className="font-semibold">{title}</h3>{children}</section>;
}

function Input({ label, value, onChange, type = "text" }: { label: string; value: string; onChange: (value: string) => void; type?: string }) {
  return <label className="text-sm font-medium text-zinc-700">{label}<input className="mt-1 w-full rounded-md border border-zinc-300 px-3 py-2" type={type} value={value} onChange={(e) => onChange(e.target.value)} /></label>;
}

function NumberInput({ label, value, onChange }: { label: string; value: number; onChange: (value: number) => void }) {
  return <Input label={label} value={String(value)} onChange={(next) => onChange(Number(next) || 0)} />;
}

function Mini({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  return <input className="w-32 rounded-md border border-zinc-300 px-2 py-1" value={value} onChange={(e) => onChange(e.target.value)} />;
}

function Check({ label, checked, onChange }: { label: string; checked: boolean; onChange: (checked: boolean) => void }) {
  return <label className="flex items-center gap-2 rounded-md border border-zinc-200 px-3 py-2 text-sm font-medium text-zinc-700"><input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />{label}</label>;
}

function BranchSelect({ value, branches, disabled, compact, onChange }: { value: number | null; branches: Branch[]; disabled?: boolean; compact?: boolean; onChange: (id: number | null) => void }) {
  return <label className="text-sm font-medium text-zinc-700">{compact ? "" : "Filial"}<select className={`${compact ? "w-40" : "mt-1 w-full"} rounded-md border border-zinc-300 px-3 py-2`} value={value ?? ""} disabled={disabled} onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)}><option value="">Tanlang</option>{branches.map((row) => <option key={row.id} value={row.id}>{row.name}</option>)}</select></label>;
}

function RoleSelect({ value, superadmin, onChange }: { value: User["role"]; superadmin: boolean; onChange: (role: User["role"]) => void }) {
  const roles: User["role"][] = superadmin ? ["superadmin", "admin", "kuzatuvchi"] : ["admin", "kuzatuvchi"];
  return <label className="text-sm font-medium text-zinc-700">Role<select className="mt-1 w-full rounded-md border border-zinc-300 px-3 py-2" value={value} onChange={(e) => onChange(e.target.value as User["role"])}>{roles.map((role) => <option key={role} value={role}>{role}</option>)}</select></label>;
}

function Actions({ primary, onCancel }: { primary: string; onCancel?: () => void }) {
  return <div className="flex items-end gap-2"><button className="flex items-center gap-2 rounded-md bg-zinc-900 px-4 py-2 text-sm font-medium text-white" type="submit"><Save size={16} />{primary}</button>{onCancel && <button className="rounded-md border border-zinc-300 px-4 py-2 text-sm" type="button" onClick={onCancel}>Bekor qilish</button>}</div>;
}

function Table({ headers, children }: { headers: string[]; children: ReactNode }) {
  return <div className="overflow-x-auto rounded-lg border border-zinc-200"><table className="min-w-full divide-y divide-zinc-200 text-sm"><thead className="bg-zinc-50"><tr>{headers.map((h) => <th key={h} className="px-3 py-2 text-left font-semibold text-zinc-600">{h}</th>)}</tr></thead><tbody className="divide-y divide-zinc-100">{children}</tbody></table></div>;
}

function Td({ children }: { children: ReactNode }) {
  return <td className="max-w-sm px-3 py-2 align-top text-zinc-700">{children}</td>;
}

function Small({ children, onClick }: { children: ReactNode; onClick: () => void }) {
  return <button className="mr-2 rounded-md border border-zinc-300 px-2 py-1 text-xs font-medium text-zinc-700" type="button" onClick={onClick}>{children}</button>;
}

function Danger({ children, onClick }: { children: ReactNode; onClick: () => void }) {
  return <button className="rounded-md border border-rose-200 px-2 py-1 text-xs font-medium text-rose-700" type="button" onClick={onClick}><Trash2 className="mr-1 inline" size={12} />{children}</button>;
}
