"""Thread-safe execution progress for live QA runs."""
from __future__ import annotations

import threading
from typing import Any, Dict, Optional

_lock = threading.Lock()
_state: Dict[int, Dict[str, Any]] = {}


def set_progress(
    run_id: int,
    *,
    status: str = "running",
    phase: str = "",
    current: int = 0,
    total: int = 0,
    test_id: str = "",
    message: str = "",
    error: Optional[str] = None,
    visited: Optional[int] = None,
    discovered: Optional[int] = None,
    failed: Optional[int] = None,
    skipped: Optional[int] = None,
    tested: Optional[int] = None,
    remaining: Optional[int] = None,
    log_line: str = "",
) -> None:
    with _lock:
        pct = (100.0 * current / total) if total else 0.0
        prev = _state.get(run_id, {})
        logs = list(prev.get("crawl_logs", []))
        if log_line:
            logs.append(str(log_line)[:300])
            logs = logs[-120:]
        _state[run_id] = {
            "run_id": run_id,
            "status": status,
            "phase": phase,
            "current": current,
            "total": total,
            "percent": round(min(100.0, pct), 2),
            "test_id": test_id,
            "message": message,
            "error": error,
            "visited": int(visited if visited is not None else prev.get("visited", 0)),
            "discovered": int(discovered if discovered is not None else prev.get("discovered", 0)),
            "failed": int(failed if failed is not None else prev.get("failed", 0)),
            "skipped": int(skipped if skipped is not None else prev.get("skipped", 0)),
            "tested": int(tested if tested is not None else prev.get("tested", 0)),
            "remaining": int(remaining if remaining is not None else prev.get("remaining", 0)),
            "crawl_logs": logs,
        }


def get_progress(run_id: int) -> Optional[Dict[str, Any]]:
    with _lock:
        return dict(_state.get(run_id, {})) if run_id in _state else None


def clear_progress(run_id: int) -> None:
    with _lock:
        _state.pop(run_id, None)
