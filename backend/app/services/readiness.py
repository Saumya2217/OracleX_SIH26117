from __future__ import annotations

import os
import tempfile
from datetime import timedelta
from pathlib import Path
from typing import Any

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.agents.llm_client import llm_client
from app.config import BASE_DIR, settings
from app.services.vector_store import vector_store_service
from app.models.knowledge import ServiceHeartbeat, utcnow


def _migration_head() -> str:
    config = Config(str(BASE_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BASE_DIR / "migrations"))
    return ScriptDirectory.from_config(config).get_current_head() or "unknown"


def _check_directory(path_value: str) -> dict[str, Any]:
    path = Path(path_value)
    try:
        path.mkdir(parents=True, exist_ok=True)
        handle, probe = tempfile.mkstemp(prefix=".oraclex-ready-", dir=path)
        os.close(handle)
        Path(probe).unlink()
        return {"status": "ready", "path": str(path)}
    except Exception as exc:
        return {"status": "unavailable", "path": str(path), "message": str(exc)}


async def collect_readiness(db: Session) -> tuple[dict[str, Any], int]:
    checks: dict[str, dict[str, Any]] = {}

    try:
        db.execute(text("SELECT 1"))
        checks["database"] = {"status": "ready"}
    except Exception as exc:
        checks["database"] = {"status": "unavailable", "message": str(exc)}

    expected_head = _migration_head()
    try:
        current = db.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
        checks["migrations"] = {
            "status": "ready" if current == expected_head else "outdated",
            "current": current,
            "expected": expected_head,
        }
    except Exception as exc:
        checks["migrations"] = {
            "status": "unavailable",
            "current": None,
            "expected": expected_head,
            "message": str(exc),
        }

    upload = _check_directory(settings.UPLOAD_DIR)
    index_storage = _check_directory(settings.CHROMA_PERSIST_DIR)
    checks["storage"] = {
        "status": "ready"
        if upload["status"] == "ready" and index_storage["status"] == "ready"
        else "unavailable",
        "uploads": upload,
        "index": index_storage,
    }

    try:
        vector_store_service.client.heartbeat()
        checks["index"] = {"status": "ready"}
    except Exception as exc:
        checks["index"] = {"status": "unavailable", "message": str(exc)}

    model = await llm_client.check_health()
    checks["model"] = {
        "status": "ready" if model.get("status") == "online" else model.get("status", "unavailable"),
        "configured_model": settings.OLLAMA_DEFAULT_MODEL,
        "active_model": model.get("active_model"),
        "message": model.get("message"),
    }
    try:
        heartbeat = db.get(ServiceHeartbeat, "ingestion-worker")
        if heartbeat is None:
            worker_status = "unavailable" if settings.WORKER_REQUIRED_FOR_READINESS else "not_required"
            worker_message = "No ingestion worker heartbeat has been recorded."
            worker_details: dict[str, Any] = {}
        else:
            age_seconds = max(0.0, (utcnow() - heartbeat.heartbeat_at).total_seconds())
            fresh = heartbeat.heartbeat_at >= utcnow() - timedelta(
                seconds=settings.WORKER_HEARTBEAT_TTL_SECONDS
            )
            worker_status = "ready" if fresh else "unavailable"
            worker_message = None if fresh else "The ingestion worker heartbeat is stale."
            worker_details = {
                "instance_id": heartbeat.instance_id,
                "heartbeat_at": heartbeat.heartbeat_at.isoformat(),
                "age_seconds": round(age_seconds, 1),
            }
        checks["worker"] = {
            "status": worker_status,
            "required": settings.WORKER_REQUIRED_FOR_READINESS,
            "message": worker_message,
            **worker_details,
        }
    except Exception as exc:
        checks["worker"] = {
            "status": "unavailable",
            "required": settings.WORKER_REQUIRED_FOR_READINESS,
            "message": str(exc),
        }

    required = ["database", "migrations", "storage", "index"]
    if settings.MODEL_REQUIRED_FOR_READINESS:
        required.append("model")
    if settings.WORKER_REQUIRED_FOR_READINESS:
        required.append("worker")

    failed = [name for name in required if checks[name]["status"] != "ready"]
    if failed:
        overall = "unavailable"
        status_code = 503
    elif checks["model"]["status"] != "ready":
        overall = "degraded"
        status_code = 200
    else:
        overall = "ready"
        status_code = 200

    return {
        "status": overall,
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "required_checks": required,
        "checks": checks,
    }, status_code
