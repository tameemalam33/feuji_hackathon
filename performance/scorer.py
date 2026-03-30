"""Score page and run performance."""
from __future__ import annotations

from typing import Any, Dict, List, Tuple


def score_page(perf: Dict[str, Any]) -> float:
    load = float(perf.get("load_time_ms") or 0)
    fcp = float(perf.get("fcp_ms") or 0)
    lcp = float(perf.get("lcp_ms") or 0)
    cls = float(perf.get("cls") or 0)
    tbt = float(perf.get("tbt_ms") or 0)

    score = 100.0
    score -= min(45.0, max(0.0, (load - 1800.0) / 120.0))
    score -= min(20.0, max(0.0, (fcp - 1200.0) / 120.0))
    score -= min(20.0, max(0.0, (lcp - 2200.0) / 140.0))
    score -= min(10.0, max(0.0, (cls - 0.1) * 80.0))
    score -= min(10.0, max(0.0, (tbt - 200.0) / 40.0))
    return max(0.0, min(100.0, round(score, 2)))


def score_run(perf_rows: List[Dict[str, Any]]) -> Tuple[float, str]:
    if not perf_rows:
        return 70.0, "Avg"
    vals = [score_page(p) for p in perf_rows]
    score = round(sum(vals) / len(vals), 2)
    if score >= 80:
        return score, "Good"
    if score >= 55:
        return score, "Avg"
    return score, "Poor"
