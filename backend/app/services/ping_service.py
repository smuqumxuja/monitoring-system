from dataclasses import dataclass
import asyncio
import logging


logger = logging.getLogger(__name__)


@dataclass
class PingResult:
    up: bool
    latency_ms: float | None
    packet_loss_percent: float


async def ping_target(target: str | None, count: int, timeout: float) -> PingResult:
    if not target:
        return PingResult(False, None, 100.0)

    try:
        import aioping
    except Exception:
        logger.exception("aioping import failed; target=%s", target)
        return PingResult(False, None, 100.0)

    latencies: list[float] = []
    lost = 0
    for _ in range(count):
        try:
            latency_seconds = await aioping.ping(target, timeout=timeout)
            latencies.append(latency_seconds * 1000)
        except TimeoutError:
            lost += 1
        except OSError:
            logger.warning("Ping OS error; target=%s", target, exc_info=True)
            lost += 1
        except Exception:
            logger.exception("Unexpected ping error; target=%s", target)
            lost += 1
        await asyncio.sleep(0.05)
    packet_loss = (lost / count) * 100 if count else 100.0
    avg_latency = sum(latencies) / len(latencies) if latencies else None
    return PingResult(bool(latencies), avg_latency, packet_loss)
