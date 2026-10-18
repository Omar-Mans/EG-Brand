"""Worker process: AI jobs + scheduled publishing.  Run with:  python -m app.worker"""

import logging
import threading
import time

from .config import get_settings
from .db import init_db
from .jobs import tick

log = logging.getLogger("worker")


def loop(stop: threading.Event | None = None) -> None:
    interval = get_settings().worker_poll_seconds
    while not (stop and stop.is_set()):
        try:
            tick()
        except Exception:
            log.exception("worker tick failed")
        if stop:
            stop.wait(interval)
        else:
            time.sleep(interval)


def start_background() -> threading.Event:
    stop = threading.Event()
    threading.Thread(target=loop, args=(stop,), daemon=True, name="egbrand-worker").start()
    return stop


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    init_db()
    log.info("worker started")
    loop()
