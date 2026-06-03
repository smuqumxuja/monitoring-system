import logging
import time

from app.config import get_settings
from app.database import SessionLocal
from app.services.collector_service import MonitoringCollector
from app.utils.bootstrap import init_database


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("collector-worker")


def main() -> None:
    settings = get_settings()
    with SessionLocal() as db:
        init_database(db)
    collector = MonitoringCollector()
    logger.info("Collector worker started, interval=%s seconds", settings.collect_interval_seconds)
    while True:
        started = time.monotonic()
        try:
            with SessionLocal() as db:
                collector.collect_once(db)
        except Exception:
            logger.exception("Collector cycle failed")
        elapsed = time.monotonic() - started
        time.sleep(max(5, settings.collect_interval_seconds - elapsed))


if __name__ == "__main__":
    main()

