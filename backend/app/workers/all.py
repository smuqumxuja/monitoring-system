import logging
import queue
import threading
import time

from app.workers.collector import main as collector_main
from app.workers.network import main as network_main


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("worker")


def run_worker(name: str, target, failures: queue.Queue[str]) -> None:
    try:
        logger.info("Starting %s", name)
        target()
    except Exception:
        logger.exception("%s stopped unexpectedly", name)
        failures.put(name)
        raise


def main() -> None:
    failures: queue.Queue[str] = queue.Queue()
    threads = [
        threading.Thread(target=run_worker, args=("collector-worker", collector_main, failures), daemon=True),
        threading.Thread(target=run_worker, args=("network-worker", network_main, failures), daemon=True),
    ]
    for thread in threads:
        thread.start()
    while True:
        try:
            failed = failures.get(timeout=5)
            logger.error("%s failed; stopping worker process so Docker can restart it", failed)
            raise SystemExit(1)
        except queue.Empty:
            for thread in threads:
                if not thread.is_alive():
                    logger.error("A worker thread exited without reporting failure; stopping process")
                    raise SystemExit(1)
            time.sleep(1)


if __name__ == "__main__":
    main()
