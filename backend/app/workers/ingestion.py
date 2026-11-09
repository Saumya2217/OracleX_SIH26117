from __future__ import annotations

import logging
import os
import signal
import socket
import time

from app.config import settings
from app.database import SessionLocal
from app.services.ingestion import IngestionService


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("oraclex.ingestion-worker")
running = True


def stop_worker(_signum, _frame) -> None:
    global running
    running = False


def run_once(worker_id: str) -> bool:
    if not settings.TESTING and not settings.CHROMA_HOST:
        raise RuntimeError("The ingestion worker requires CHROMA_HOST; do not share embedded Chroma between processes.")
    db = SessionLocal()
    try:
        IngestionService.heartbeat(db, worker_id, {"pid": os.getpid()})
        IngestionService.dispatch_outbox(db, worker_id)
        job_id = IngestionService.claim_next_job(db, worker_id)
        if not job_id:
            return False
        logger.info("Processing ingestion job %s", job_id)
        completed = IngestionService.process_job(db, job_id, worker_id)
        logger.info("Ingestion job %s finished: %s", job_id, completed)
        return True
    finally:
        db.close()


def main() -> None:
    global running
    if not settings.TESTING and not settings.CHROMA_HOST:
        raise RuntimeError("The ingestion worker requires CHROMA_HOST; embedded storage cannot be shared.")
    signal.signal(signal.SIGINT, stop_worker)
    signal.signal(signal.SIGTERM, stop_worker)
    worker_id = f"{socket.gethostname()}-{os.getpid()}"
    logger.info("OracleX ingestion worker started as %s", worker_id)
    while running:
        try:
            processed = run_once(worker_id)
        except Exception:
            logger.exception("Worker loop failed; polling will continue")
            processed = False
        if not processed and running:
            time.sleep(settings.INGESTION_POLL_SECONDS)
    logger.info("OracleX ingestion worker stopped")


if __name__ == "__main__":
    main()
