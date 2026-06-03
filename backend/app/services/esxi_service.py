from dataclasses import dataclass, field
import logging
import ssl


logger = logging.getLogger(__name__)


@dataclass
class VmMetrics:
    moid: str
    name: str
    guest_os: str | None
    ip_address: str | None
    power_state: str | None
    uptime_seconds: int | None
    cpu_total_mhz: float | None
    cpu_used_mhz: float | None
    cpu_usage_percent: float | None
    ram_total_mb: float | None
    ram_used_mb: float | None
    ram_usage_percent: float | None
    disk_size_bytes: int | None
    disk_usage_percent: float | None
    network_rx_kbps: float | None = None
    network_tx_kbps: float | None = None


@dataclass
class HostMetrics:
    uptime_seconds: int | None
    cpu_total_mhz: float | None
    cpu_used_mhz: float | None
    cpu_usage_percent: float | None
    ram_total_mb: float | None
    ram_used_mb: float | None
    ram_usage_percent: float | None
    datastore_total_bytes: int | None
    datastore_free_bytes: int | None
    datastore_usage_percent: float | None
    datastore_details: list[dict] = field(default_factory=list)
    nic_status: list[dict] = field(default_factory=list)
    network_rx_kbps: float | None = None
    network_tx_kbps: float | None = None


@dataclass
class EsxiSample:
    host: HostMetrics
    vms: list[VmMetrics]


def collect_esxi(hostname: str, username: str, password: str, port: int = 443, verify_ssl: bool = False) -> EsxiSample:
    from pyVim import connect
    from pyVmomi import vim

    context = None if verify_ssl else ssl._create_unverified_context()
    logger.info("Connecting to ESXi host %s:%s", hostname, port)
    service_instance = None
    try:
        service_instance = connect.SmartConnect(host=hostname, user=username, pwd=password, port=port, sslContext=context)
        content = service_instance.RetrieveContent()
        host_system = _first_host(content, vim)
        quick = host_system.summary.quickStats
        hardware = host_system.summary.hardware
        datastore_total, datastore_free, datastore_usage, datastore_details = _datastore_usage(host_system)

        cpu_total_mhz = _float_or_none((hardware.cpuMhz or 0) * (hardware.numCpuCores or 0))
        cpu_used_mhz = _float_or_none(getattr(quick, "overallCpuUsage", None))
        ram_total_mb = _float_or_none((hardware.memorySize or 0) / 1024 / 1024)
        ram_used_mb = _float_or_none(getattr(quick, "overallMemoryUsage", None))

        host_metrics = HostMetrics(
            uptime_seconds=getattr(quick, "uptime", None),
            cpu_total_mhz=cpu_total_mhz,
            cpu_used_mhz=cpu_used_mhz,
            cpu_usage_percent=_percent(cpu_used_mhz, cpu_total_mhz),
            ram_total_mb=ram_total_mb,
            ram_used_mb=ram_used_mb,
            ram_usage_percent=_percent(ram_used_mb, ram_total_mb),
            datastore_total_bytes=datastore_total,
            datastore_free_bytes=datastore_free,
            datastore_usage_percent=datastore_usage,
            datastore_details=datastore_details,
            nic_status=_nic_status(host_system),
        )

        vms: list[VmMetrics] = []
        for vm in getattr(host_system, "vm", []) or []:
            try:
                vms.append(_vm_metrics(vm, vim, hardware))
            except Exception:
                logger.exception("Failed to parse VM metrics from host %s; vm=%s", hostname, getattr(vm, "name", "unknown"))
        return EsxiSample(host=host_metrics, vms=vms)
    except Exception:
        logger.exception("Failed to collect ESXi metrics from %s:%s", hostname, port)
        raise
    finally:
        if service_instance:
            try:
                connect.Disconnect(service_instance)
            except Exception:
                logger.exception("Failed to disconnect from ESXi host %s:%s", hostname, port)


def _first_host(content, vim):
    view = content.viewManager.CreateContainerView(content.rootFolder, [vim.HostSystem], True)
    try:
        if not view.view:
            raise RuntimeError("No ESXi HostSystem found")
        return view.view[0]
    finally:
        view.Destroy()


def _float_or_none(value: object) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _percent(used: float | None, total: float | None) -> float | None:
    if used is None or not total:
        return None
    return round(max(0.0, min(100.0, (used / total) * 100)), 2)


def _datastore_usage(host_system) -> tuple[int | None, int | None, float | None, list[dict]]:
    total = 0
    free = 0
    details = []
    for datastore in getattr(host_system, "datastore", []) or []:
        summary = datastore.summary
        capacity = int(getattr(summary, "capacity", 0) or 0)
        free_space = int(getattr(summary, "freeSpace", 0) or 0)
        if capacity <= 0:
            continue
        total += capacity
        free += free_space
        details.append(
            {
                "name": summary.name,
                "capacity_bytes": capacity,
                "free_bytes": free_space,
                "usage_percent": _percent(capacity - free_space, capacity),
            }
        )
    if not total:
        return None, None, None, details
    return total, free, _percent(total - free, total), details


def _nic_status(host_system) -> list[dict]:
    network = getattr(getattr(host_system, "config", None), "network", None)
    pnics = getattr(network, "pnic", None) or []
    result = []
    for pnic in pnics:
        link_speed = getattr(pnic, "linkSpeed", None)
        result.append(
            {
                "device": getattr(pnic, "device", None),
                "mac": getattr(pnic, "mac", None),
                "status": "up" if link_speed else "down",
                "speed_mb": getattr(link_speed, "speedMb", None) if link_speed else None,
                "duplex": getattr(link_speed, "duplex", None) if link_speed else None,
            }
        )
    return result


def _vm_metrics(vm, vim, hardware) -> VmMetrics:
    summary = vm.summary
    config = summary.config
    runtime = summary.runtime
    stats = summary.quickStats
    guest = getattr(summary, "guest", None)
    cpu_total = _float_or_none((config.numCpu or 0) * (hardware.cpuMhz or 0))
    cpu_used = _float_or_none(getattr(stats, "overallCpuUsage", None))
    ram_total = _float_or_none(config.memorySizeMB or 0)
    ram_used = _float_or_none(getattr(stats, "guestMemoryUsage", None))
    return VmMetrics(
        moid=vm._moId,
        name=config.name or vm.name,
        guest_os=getattr(config, "guestFullName", None),
        ip_address=getattr(guest, "ipAddress", None) or getattr(getattr(vm, "guest", None), "ipAddress", None),
        power_state=str(getattr(runtime, "powerState", None)),
        uptime_seconds=getattr(stats, "uptimeSeconds", None),
        cpu_total_mhz=cpu_total,
        cpu_used_mhz=cpu_used,
        cpu_usage_percent=_percent(cpu_used, cpu_total),
        ram_total_mb=ram_total,
        ram_used_mb=ram_used,
        ram_usage_percent=_percent(ram_used, ram_total),
        disk_size_bytes=_vm_disk_size(vm, vim),
        disk_usage_percent=_vm_disk_usage(vm),
    )


def _vm_disk_size(vm, vim) -> int | None:
    total = 0
    devices = getattr(getattr(getattr(vm, "config", None), "hardware", None), "device", None) or []
    for device in devices:
        if isinstance(device, vim.vm.device.VirtualDisk):
            total += int(getattr(device, "capacityInKB", 0) or 0) * 1024
    return total or None


def _vm_disk_usage(vm) -> float | None:
    guest_disks = getattr(getattr(vm, "guest", None), "disk", None) or []
    capacity = 0
    free = 0
    for disk in guest_disks:
        capacity += int(getattr(disk, "capacity", 0) or 0)
        free += int(getattr(disk, "freeSpace", 0) or 0)
    return _percent(capacity - free, capacity) if capacity else None
