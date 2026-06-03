from dataclasses import dataclass, field
import logging


logger = logging.getLogger(__name__)


@dataclass
class SnmpMetrics:
    uptime_seconds: int | None = None
    network_rx_octets: int | None = None
    network_tx_octets: int | None = None
    raw: dict = field(default_factory=dict)


async def collect_snmp_metrics(hostname: str, community: str | None, port: int = 161) -> SnmpMetrics:
    if not community:
        return SnmpMetrics()
    try:
        import pysnmp.hlapi.asyncio as hlapi
    except ImportError:
        logger.exception("pysnmp import failed")
        return SnmpMetrics(raw={"error": "pysnmp is not installed"})

    sample = SnmpMetrics()
    try:
        sample.uptime_seconds = await _get_uptime(hlapi, hostname, community, port)
        sample.network_rx_octets = await _get_int(hlapi, hostname, community, port, "1.3.6.1.2.1.31.1.1.1.6.1")
        sample.network_tx_octets = await _get_int(hlapi, hostname, community, port, "1.3.6.1.2.1.31.1.1.1.10.1")
        sample.raw = {"if_index": 1}
    except Exception as exc:
        logger.exception("SNMP collection failed for %s:%s", hostname, port)
        sample.raw = {"error": str(exc)}
    return sample


async def _target(hlapi, hostname: str, port: int):
    create = getattr(hlapi.UdpTransportTarget, "create", None)
    if create:
        return await create((hostname, port), timeout=2, retries=0)
    return hlapi.UdpTransportTarget((hostname, port), timeout=2, retries=0)


async def _get_value(hlapi, hostname: str, community: str, port: int, oid: str):
    command = getattr(hlapi, "getCmd", None) or getattr(hlapi, "get_cmd")
    result = await command(
        hlapi.SnmpEngine(),
        hlapi.CommunityData(community, mpModel=1),
        await _target(hlapi, hostname, port),
        hlapi.ContextData(),
        hlapi.ObjectType(hlapi.ObjectIdentity(oid)),
    )
    error_indication, error_status, _error_index, var_binds = result
    if error_indication or error_status or not var_binds:
        return None
    return var_binds[0][1]


async def _get_int(hlapi, hostname: str, community: str, port: int, oid: str) -> int | None:
    value = await _get_value(hlapi, hostname, community, port, oid)
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


async def _get_uptime(hlapi, hostname: str, community: str, port: int) -> int | None:
    ticks = await _get_int(hlapi, hostname, community, port, "1.3.6.1.2.1.1.3.0")
    return int(ticks / 100) if ticks is not None else None
