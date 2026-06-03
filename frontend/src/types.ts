export type Role = "superadmin" | "admin" | "kuzatuvchi" | "viewer";

export type User = {
  id: number;
  username: string;
  role: Role;
  branch_id: number | null;
  branch_name: string | null;
  is_active: boolean;
};

export type Branch = {
  id: number;
  name: string;
  code: string;
  address: string | null;
  active: boolean;
  created_at: string;
  updated_at: string;
};

export type Metric = {
  id: number;
  entity_type: "host" | "vm";
  host_id: number | null;
  vm_id: number | null;
  cpu_total_mhz: number | null;
  cpu_used_mhz: number | null;
  cpu_usage_percent: number | null;
  ram_total_mb: number | null;
  ram_used_mb: number | null;
  ram_usage_percent: number | null;
  disk_size_bytes: number | null;
  disk_usage_percent: number | null;
  datastore_total_bytes: number | null;
  datastore_free_bytes: number | null;
  datastore_usage_percent: number | null;
  nic_status: Array<Record<string, unknown>> | null;
  network_rx_kbps: number | null;
  network_tx_kbps: number | null;
  uptime_seconds: number | null;
  power_state: string | null;
  ping_up: boolean | null;
  latency_ms: number | null;
  packet_loss_percent: number | null;
  datastore_details: Array<Record<string, unknown>> | null;
  extra: Record<string, unknown> | null;
  collected_at: string;
};

export type NetworkStatus = {
  id: number;
  entity_key: string;
  entity_type: "host" | "vm";
  entity_id: number;
  target_ip: string;
  status: "unknown" | "online" | "warning" | "probable_outage" | "offline" | "disabled";
  online: boolean;
  latency_ms: number | null;
  packet_loss_percent: number | null;
  consecutive_failures: number;
  last_success_at: string | null;
  last_checked_at: string | null;
  updated_at: string;
};

export type VM = {
  id: number;
  host_id: number;
  moid: string;
  name: string;
  guest_os: string | null;
  ip_address: string | null;
  power_state: string | null;
  uptime_seconds: number | null;
  monitoring_enabled: boolean;
  last_seen_at: string | null;
  latest_metric: Metric | null;
  network_status: NetworkStatus | null;
};

export type Host = {
  id: number;
  branch_id: number | null;
  branch_name: string | null;
  name: string;
  hostname: string;
  username: string;
  port: number;
  verify_ssl: boolean;
  active: boolean;
  snmp_enabled: boolean;
  snmp_community: string | null;
  snmp_port: number;
  latest_metric: Metric | null;
  network_status: NetworkStatus | null;
  vms: VM[];
};

export type HostRecord = {
  id: number;
  branch_id: number | null;
  branch_name: string | null;
  name: string;
  hostname: string;
  username: string;
  port: number;
  verify_ssl: boolean;
  active: boolean;
  snmp_enabled: boolean;
  snmp_community: string | null;
  snmp_port: number;
};

export type Alert = {
  id: number;
  source_type: string;
  source_id: number | null;
  metric: string;
  level: "warning" | "critical";
  title: string;
  message: string;
  is_active: boolean;
  acknowledged_at: string | null;
  resolved_at: string | null;
  last_notified_at: string | null;
  notification_count: number;
  created_at: string;
  updated_at: string;
};

export type PredictiveRisk = {
  id: string;
  source_type: "host" | "vm";
  source_id: number;
  source_name: string;
  host_id: number | null;
  host_name: string | null;
  metric: string;
  level: "warning" | "critical";
  title: string;
  message: string;
  recommendations: string[];
  current_value: number | null;
  average_7d: number | null;
  trend_per_day: number | null;
  forecast_7d: number | null;
  days_to_limit: number | null;
  sample_count: number;
  confidence: number;
};

export type Snapshot = {
  generated_at: string;
  hosts: Host[];
  active_alerts: Alert[];
  predictive_risks: PredictiveRisk[];
};

export type Threshold = {
  id: number;
  metric: string;
  warning_value: number | null;
  critical_value: number | null;
  operator: "gte" | "lte";
  enabled: boolean;
  updated_at: string;
};

export type NotificationSettings = {
  telegram_bot_token_configured: boolean;
  telegram_chat_id: string | null;
  smtp_host: string | null;
  smtp_port: number;
  smtp_username: string | null;
  smtp_password_configured: boolean;
  smtp_from: string | null;
  smtp_to: string | null;
  smtp_use_tls: boolean;
};

export type SystemLog = {
  id: number;
  branch_id: number | null;
  level: "info" | "warning" | "error" | "critical" | string;
  category: string;
  source: string | null;
  message: string;
  details: Record<string, unknown> | null;
  status: "open" | "reviewed" | "resolved";
  admin_note: string | null;
  created_at: string;
  updated_at: string;
};

export type EntityRef = {
  type: "host" | "vm";
  id: number;
  label: string;
};
