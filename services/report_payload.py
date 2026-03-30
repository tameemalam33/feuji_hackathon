"""Canonical structured report payload for PDF, HTML, and JSON exports."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        if v is None:
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def _parse_summary(run: Dict[str, Any]) -> Dict[str, Any]:
    raw = run.get("summary_json") or "{}"
    try:
        return json.loads(raw) if isinstance(raw, str) else dict(raw or {})
    except Exception:
        return {}


def _parse_insights(run: Dict[str, Any]) -> List[str]:
    raw = run.get("insights_json") or "[]"
    try:
        if isinstance(raw, str):
            arr = json.loads(raw)
        else:
            arr = list(raw or [])
        return [str(x) for x in arr if str(x).strip()]
    except Exception:
        return []


def _severity_rank(s: Optional[str]) -> int:
    order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3, "None": 9}
    return order.get(str(s or ""), 4)


def build_report_payload(
    run: Dict[str, Any],
    tests: List[Dict[str, Any]],
    charts: Dict[str, Any],
    pages: Optional[List[Dict[str, Any]]] = None,
    *,
    include_tests: bool = True,
) -> Dict[str, Any]:
    """
    Structured report matching product contract:
    summary, tests, failures, suggestions, performance, recommendation (+ charts snapshot).
    """
    pages = pages or []
    summ = _parse_summary(run)
    ai_insights = _parse_insights(run)

    total = int(run.get("total") or 0)
    passed = int(run.get("passed") or 0)
    failed = int(run.get("failed") or 0)
    coverage = _safe_float(run.get("coverage"), 0.0)
    health_score = round((passed / total * 100.0) if total else 0.0, 2)

    critical_issues = sum(
        1
        for t in tests
        if t.get("status") == "failed" and str(t.get("severity") or "") == "Critical"
    )

    normalized_tests: List[Dict[str, Any]] = []
    for t in tests:
        normalized_tests.append(
            {
                "id": t.get("test_id") or t.get("id"),
                "userStory": t.get("user_story") or "",
                "scenario": t.get("scenario") or t.get("title") or t.get("name") or "",
                "type": t.get("test_type") or "Positive",
                "status": t.get("status") or "pending",
                "severity": t.get("severity") or "",
                "category": (t.get("category") or "").lower() or "functional",
                "name": t.get("name") or "",
                "page": t.get("page") or "",
                "pageClass": t.get("page_class") or "",
                "component": t.get("component") or "",
                "steps": t.get("steps") or [],
                "expected": t.get("expected_result") or t.get("expected") or "",
                "actual": t.get("actual_result") or t.get("actual") or "",
                "rootCause": t.get("root_cause") or "",
                "suggestedFix": t.get("suggestion") or "",
                "elementSelector": t.get("element_selector") or "",
                "issueType": t.get("issue_type") or "",
                "message": t.get("message") or "",
                "logs": t.get("logs") or [],
                "screenshotUrl": t.get("screenshot") or t.get("screenshot_path") or "",
            }
        )

    failed_tests = [t for t in tests if t.get("status") == "failed"]
    failures: List[Dict[str, Any]] = []
    for t in sorted(failed_tests, key=lambda x: (_severity_rank(x.get("severity")), x.get("name") or "")):
        failures.append(
            {
                "id": t.get("test_id") or t.get("id"),
                "runId": run.get("id"),
                "testId": t.get("test_id") or t.get("id"),
                "name": t.get("name") or "",
                "scenario": t.get("scenario") or t.get("title") or "",
                "steps": t.get("steps") or [],
                "expected": t.get("expected_result") or t.get("expected") or "",
                "actual": t.get("actual_result") or t.get("actual") or "",
                "errorMessage": (t.get("actual_result") or t.get("actual") or "")[:2000],
                "logs": t.get("logs") or [],
                "screenshotUrl": t.get("screenshot") or t.get("screenshot_path") or "",
                "severity": t.get("severity") or "Medium",
                "category": t.get("category") or "",
                "rootCause": t.get("root_cause") or "",
                "aiSuggestion": t.get("suggestion") or "",
                "suggestedFix": t.get("suggestion") or "",
                "elementSelector": t.get("element_selector") or "",
                "issueType": t.get("issue_type") or "",
                "message": t.get("message") or "",
                "page": t.get("page") or "",
            }
        )

    suggestions: List[Dict[str, Any]] = [
        {
            "testId": f.get("testId"),
            "title": f.get("name"),
            "rootCause": f.get("rootCause") or "See actual result.",
            "suggestedFix": f.get("suggestedFix") or "Reproduce locally and verify DOM/network state.",
        }
        for f in failures
    ]

    sev_counts: Dict[str, int] = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    for t in failed_tests:
        s = str(t.get("severity") or "Medium")
        if s in sev_counts:
            sev_counts[s] += 1
        elif s == "None":
            pass
        else:
            sev_counts["Medium"] += 1

    pb = summ.get("performance_breakdown") or {}
    slow_pages: List[Dict[str, Any]] = []
    max_lcp = 0.0
    for p in pages:
        perf = p.get("performance") or {}
        if isinstance(perf, dict):
            lcp = _safe_float(perf.get("lcp_ms"), 0.0)
            max_lcp = max(max_lcp, lcp)
        slow_pages.append(
            {
                "url": p.get("page_url") or "",
                "responseTimeMs": _safe_float(p.get("response_time_ms"), 0.0),
                "lcpMs": _safe_float((perf or {}).get("lcp_ms"), 0.0) if isinstance(perf, dict) else 0.0,
                "loadStatus": p.get("load_status") or "",
            }
        )
    slow_pages.sort(key=lambda x: -x["responseTimeMs"])
    slow_pages = slow_pages[:15]

    performance = {
        "loadTime": _safe_float(pb.get("crawl_avg_load_ms"), 0.0),
        "slowestPageMs": _safe_float(pb.get("crawl_slowest_ms"), 0.0),
        "slowApis": [],
        "largestContentfulPaintMs": round(max_lcp, 2) if max_lcp else None,
        "avgTtfbMs": pb.get("measured_avg_ttfb_ms"),
        "slowPages": slow_pages,
        "performanceScore": _safe_float(pb.get("performance_score"), _safe_float(run.get("performance_score"), 0.0)),
    }

    pass_rate = _safe_float(run.get("success_rate"), health_score)
    verdict, verdict_detail, blocking, improvements = _compute_verdict(
        critical_issues=critical_issues,
        failed=failed,
        passed=passed,
        total=total,
        pass_rate=pass_rate,
        summ=summ,
    )

    tests_out: List[Dict[str, Any]] = normalized_tests if include_tests else []
    payload: Dict[str, Any] = {
        "meta": {
            "runId": run.get("id"),
            "url": run.get("url") or summ.get("url") or "",
            "timestamp": run.get("timestamp") or "",
            "depth": summ.get("depth") or "",
        },
        "summary": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "coverage": round(coverage, 2),
            "critical": critical_issues,
            "healthScore": health_score,
        },
        "charts": charts or {},
        "issuePrioritization": {
            "countsBySeverity": sev_counts,
            "orderedSeverities": ["Critical", "High", "Medium", "Low"],
        },
        "tests": tests_out,
        "testsTotal": len(normalized_tests),
        "failures": failures,
        "suggestions": suggestions,
        "performance": performance,
        "recommendation": verdict,
        "recommendationDetail": {
            "verdict": verdict_detail,
            "label": verdict,
            "blockingIssues": blocking,
            "keyImprovements": improvements,
        },
        "aiInsights": ai_insights,
    }
    return payload


def _compute_verdict(
    *,
    critical_issues: int,
    failed: int,
    passed: int,
    total: int,
    pass_rate: float,
    summ: Dict[str, Any],
) -> Tuple[str, str, List[str], List[str]]:
    blocking: List[str] = []
    improvements: List[str] = []

    if critical_issues > 0:
        blocking.append(f"{critical_issues} critical test failure(s) require immediate attention.")
    fp = summ.get("failed_pages")
    if fp is not None and int(fp) > 0:
        blocking.append(f"{int(fp)} page(s) failed during crawl.")

    if failed > 0:
        improvements.append("Triage failed tests by severity (Critical → High first).")
        improvements.append("Use root-cause and suggested fix for each failure.")
    if (summ.get("coverage_score") or 0) and float(summ.get("coverage_score") or 0) < 60:
        improvements.append("Increase element coverage on high-traffic flows.")

    if critical_issues == 0 and failed == 0 and total > 0:
        return (
            "✅ Ready for Production",
            "All executed tests passed. No critical or failing checks in this run.",
            blocking,
            ["Keep running regression suites in CI.", "Monitor performance and Core Web Vitals in production."],
        )

    if critical_issues > 0:
        return (
            "❌ Not Ready",
            "Critical failures detected — do not ship until resolved.",
            blocking,
            improvements,
        )

    if failed > 0 or (pass_rate < 85.0 and total > 0):
        return (
            "⚠️ Needs Fixes",
            "Non-critical failures or pass rate below target — address before production.",
            blocking,
            improvements,
        )

    return (
        "✅ Ready for Production",
        "Acceptable pass rate with no critical failures.",
        blocking,
        improvements,
    )
