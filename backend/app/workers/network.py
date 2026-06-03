import logging
import time

from app.config import get_settings
from app.database import SessionLocal
from app.services.network_monitor_service import NetworkMonitor
from app.utils.bootstrap import init_database


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("network-worker")


def main() -> None:
    settings = get_settings()
    with SessionLocal() as db:
        init_database(db)
    monitor = NetworkMonitor()
    logger.info("Network worker started, interval=%s seconds", settings.network_check_interval_seconds)
    while True:
        started = time.monotonic()
        try:
            with SessionLocal() as db:
                monitor.check_once(db)
        except Exception:
            logger.exception("Network monitor cycle failed")
        elapsed = time.monotonic() - started
        time.sleep(max(1, settings.network_check_interval_seconds - elapsed))


if __name__ == "__main__":
    main()
