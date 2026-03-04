import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = Path(os.getenv("RUN_LOG_DIR", str(BASE_DIR / "logs")))
LOG_DIR.mkdir(parents=True, exist_ok=True)

RUN_LOG_FILE = Path(os.getenv("RUN_LOG_FILE", str(LOG_DIR / "run_logs.json")))
RUN_LOG_MAX_ENTRIES = int(os.getenv("RUN_LOG_MAX_ENTRIES", "300"))
RUN_LOG_TITLE_LIMIT = int(os.getenv("RUN_LOG_TITLE_LIMIT", "100"))

_LOCK = threading.Lock()


def _load_run_logs() -> list[dict[str, Any]]:
    if not RUN_LOG_FILE.exists():
        return []
    try:
        with open(RUN_LOG_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_run_logs(entries: list[dict[str, Any]]) -> None:
    with open(RUN_LOG_FILE, "w", encoding="utf-8") as file:
        json.dump(entries, file, indent=2, ensure_ascii=True)


def summarize_tests(tests: dict | None) -> dict[str, Any]:
    positive = tests.get("positive_tests", []) if isinstance(tests, dict) else []
    negative = tests.get("negative_tests", []) if isinstance(tests, dict) else []

    positive_titles = [
        str(case.get("scenario", "")).strip()
        for case in positive
        if isinstance(case, dict) and str(case.get("scenario", "")).strip()
    ][:RUN_LOG_TITLE_LIMIT]

    negative_titles = [
        str(case.get("scenario", "")).strip()
        for case in negative
        if isinstance(case, dict) and str(case.get("scenario", "")).strip()
    ][:RUN_LOG_TITLE_LIMIT]

    return {
        "positive_count": len(positive),
        "negative_count": len(negative),
        "total_count": len(positive) + len(negative),
        "positive_titles": positive_titles,
        "negative_titles": negative_titles,
    }


def log_generation_run(
    endpoint: str,
    status: str,
    request_payload: dict[str, Any],
    result_payload: dict[str, Any] | None = None,
    error: str | None = None,
    duration_ms: int | None = None,
) -> str:
    entry = {
        "run_id": str(uuid4()),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "endpoint": endpoint,
        "status": status,
        "duration_ms": duration_ms,
        "request": request_payload or {},
        "result": result_payload or {},
        "error": error,
    }

    with _LOCK:
        logs = _load_run_logs()
        logs.append(entry)
        if len(logs) > RUN_LOG_MAX_ENTRIES:
            logs = logs[-RUN_LOG_MAX_ENTRIES:]
        _save_run_logs(logs)

    return entry["run_id"]


def list_run_logs(limit: int = 20) -> list[dict[str, Any]]:
    safe_limit = max(1, min(limit, 200))
    with _LOCK:
        logs = _load_run_logs()
    return list(reversed(logs[-safe_limit:]))


def get_latest_run_log() -> dict[str, Any] | None:
    with _LOCK:
        logs = _load_run_logs()
    if not logs:
        return None
    return logs[-1]
