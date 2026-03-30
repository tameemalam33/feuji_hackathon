"""REST API for AutoQA Pro."""
from __future__ import annotations

import csv
import io
import json
import os
import threading
import uuid
from typing import Any, Dict, List, Optional

from flask import Blueprint, Response, jsonify, request, send_file

import config
from models.database import Database
from services.qa_pipeline import run_qa_pipeline
from services.report_generator import build_pdf
from services.report_payload import build_report_payload
from services.issue_highlight import highlight_element_screenshot
from services.run_metrics import compare_runs_extended, heatmap_failures_by_page
from services.run_progress import get_progress, set_progress
from utils.helpers import validate_url
from utils.integrations import api_key_authorized

api_bp = Blueprint("api", __name__, url_prefix="/api")

_db = Database()


def _public_base_url() -> str:
    if config.PUBLIC_BASE_URL:
        return config.PUBLIC_BASE_URL.rstrip("/")
    return (request.url_root or "").rstrip("/")


def _clamp_max_pages(raw: Any) -> int:
    try:
        n = int(raw)
    except (TypeError, ValueError):
        n = config.MAX_PAGES_STANDARD
    return max(1, min(config.MAX_CRAWL_PAGES_MAX, n))


def _mode_to_pages(mode: str) -> Optional[int]:
    m = (mode or "standard").lower()
    if m == "quick":
        return config.MAX_PAGES_QUICK
    if m == "deep":
        return config.MAX_PAGES_DEEP
    if m == "full":
        return None
    return config.MAX_PAGES_STANDARD


def _serialize_run_row(run: dict) -> dict:
    if run.get("summary_json"):
        try:
            run["summary"] = json.loads(run["summary_json"])
        except Exception:
            run["summary"] = {}
    if run.get("charts_json"):
        try:
            run["charts"] = json.loads(run["charts_json"])
        except Exception:
            run["charts"] = {}
    if run.get("insights_json"):
        try:
            run["insights"] = json.loads(run["insights_json"])
        except Exception:
            run["insights"] = []
    summ = run.get("summary") or {}
    if isinstance(summ, dict):
        run["critical_failures"] = int(summ.get("critical_failures") or 0)
        run["user_flows_tested"] = summ.get("user_flows_tested") or []
        run["security_warnings"] = summ.get("security_warnings") or []
        run["performance_breakdown"] = summ.get("performance_breakdown") or {}
    else:
        run["critical_failures"] = 0
        run["user_flows_tested"] = []
        run["security_warnings"] = []
        run["performance_breakdown"] = {}
    return run


def _empty_run_row(run_id: int) -> dict:
    # Safe fallback keeps the UI alive when the backing row is missing or incomplete.
    return {
        "id": run_id,
        "run_id": run_id,
        "url": "",
        "total": 0,
        "passed": 0,
        "failed": 0,
        "success_rate": 0.0,
        "health_score": 0.0,
        "coverage": 0.0,
        "performance_score": 0.0,
        "accessibility_score": 0.0,
        "security_score": 0.0,
        "critical_failures": 0,
        "user_flows_tested": [],
        "security_warnings": [],
        "performance_breakdown": {},
        "summary": {
            "status": "fallback",
            "total_pages_discovered": 0,
            "total_pages_visited": 0,
            "failed_pages": 0,
            "skipped_pages": 0,
            "crawl_logs": [],
            "pipeline_logs": [],
        },
        "charts": {},
        "insights": [],
        "fallback": True,
    }


def _mode_to_depth(mode: str) -> int:
    m = (mode or "standard").lower()
    if m == "quick":
        return config.MAX_DEPTH_QUICK
    if m == "deep":
        return config.MAX_DEPTH_DEEP
    if m == "full":
        return config.MAX_DEPTH_FULL
    return config.MAX_DEPTH_STANDARD


def _run_options_from_request() -> tuple[str, str, Optional[int], int, Optional[str]]:
    body = request.get_json(silent=True) or {}
    raw_url = body.get("url", "")
    crawl_mode = (body.get("crawl_mode") or body.get("depth") or "standard").lower()
    max_pages_raw = body.get("max_pages")
    max_depth_raw = body.get("max_depth")
    raw_webhook = (body.get("webhook_url") or "").strip()
    webhook_url: Optional[str] = None
    if raw_webhook:
        wok, wmsg = validate_url(raw_webhook)
        if not wok:
            raise ValueError(f"Invalid webhook_url: {wmsg}")
        webhook_url = wmsg

    ok, msg = validate_url(raw_url)
    if not ok:
        raise ValueError(msg)

    url = msg
    if max_pages_raw is not None and max_pages_raw != "":
        max_pages = _clamp_max_pages(max_pages_raw)
    else:
        max_pages = _mode_to_pages(crawl_mode)
    if max_depth_raw is not None and str(max_depth_raw).strip() != "":
        try:
            max_depth = max(0, min(6, int(max_depth_raw)))
        except (TypeError, ValueError):
            max_depth = _mode_to_depth(crawl_mode)
    else:
        max_depth = _mode_to_depth(crawl_mode)
    return url, crawl_mode, max_pages, max_depth, webhook_url


@api_bp.route("/run-full-test", methods=["POST"])
def run_full_test():
    if not api_key_authorized(request):
        return (
            jsonify(
                {
                    "error": "Unauthorized. Provide Authorization: Bearer <AUTOQA_API_KEY> or header X-API-Key when the server sets AUTOQA_API_KEY.",
                }
            ),
            401,
        )

    try:
        url, crawl_mode, max_pages, max_depth, webhook_url = _run_options_from_request()
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    batch_id = uuid.uuid4().hex[:16]
    run_id = _db.insert_run(
        url=url,
        total=0,
        passed=0,
        failed=0,
        summary={"status": "running", "url": url, "crawl_mode": crawl_mode, "max_pages": max_pages, "max_depth": max_depth},
        charts={},
        batch_id=batch_id,
        accessibility_score=None,
        security_score=None,
        synthetic_dataset_json=None,
    )

    try:
        body = run_qa_pipeline(
            url=url,
            depth=crawl_mode,
            max_pages=max_pages,
            max_depth=max_depth,
            run_id=run_id,
            batch_id=batch_id,
            db=_db,
            progress=None,
            webhook_url=webhook_url,
            public_base_url=_public_base_url(),
        )
    except Exception as e:
        return jsonify({"error": f"QA run failed: {e}", "run_id": run_id}), 500

    return jsonify(body)


@api_bp.route("/run-full-test-async", methods=["POST"])
def run_full_test_async():
    """Start QA in a background thread; poll GET /api/runs/<id>/execution-status until completed."""
    if not api_key_authorized(request):
        return (
            jsonify(
                {
                    "error": "Unauthorized. Provide Authorization: Bearer <AUTOQA_API_KEY> or header X-API-Key when the server sets AUTOQA_API_KEY.",
                }
            ),
            401,
        )

    try:
        url, crawl_mode, max_pages, max_depth, webhook_url = _run_options_from_request()
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    batch_id = uuid.uuid4().hex[:16]
    run_id = _db.insert_run(
        url=url,
        total=0,
        passed=0,
        failed=0,
        summary={"status": "running", "url": url, "crawl_mode": crawl_mode, "max_pages": max_pages, "max_depth": max_depth},
        charts={},
        batch_id=batch_id,
        accessibility_score=None,
        security_score=None,
        synthetic_dataset_json=None,
    )

    base = _public_base_url()

    def _worker() -> None:
        try:
            set_progress(run_id, status="running", phase="starting", current=0, total=1, message="Starting…")

            def hook(phase: str, cur: int, tot: int, tid: str, meta: Optional[Dict[str, Any]] = None) -> None:
                meta = meta or {}
                set_progress(
                    run_id,
                    status="running",
                    phase=phase,
                    current=cur,
                    total=max(tot, 1),
                    test_id=tid,
                    message=f"{phase} {cur}/{max(tot, 1)}",
                    visited=meta.get("visited"),
                    discovered=meta.get("discovered"),
                    failed=meta.get("failed"),
                    skipped=meta.get("skipped"),
                    tested=meta.get("tested"),
                    remaining=meta.get("remaining"),
                    log_line=str(meta.get("log_line") or ""),
                )

            run_qa_pipeline(
                url=url,
                depth=crawl_mode,
                max_pages=max_pages,
                max_depth=max_depth,
                run_id=run_id,
                batch_id=batch_id,
                db=_db,
                progress=hook,
                webhook_url=webhook_url,
                public_base_url=base,
            )
            set_progress(
                run_id,
                status="completed",
                phase="done",
                current=1,
                total=1,
                message="Complete",
            )
        except Exception as e:
            set_progress(run_id, status="failed", phase="error", current=0, total=1, error=str(e)[:500])

    threading.Thread(target=_worker, daemon=True).start()

    return (
        jsonify(
            {
                "run_id": run_id,
                "status": "started",
                "poll_execution": f"{base}/api/runs/{run_id}/execution-status",
                "poll_run": f"{base}/api/runs/{run_id}",
            }
        ),
        202,
    )


@api_bp.route("/runs/<int:run_id>/execution-status", methods=["GET"])
def execution_status(run_id: int):
    if not _db.get_run(run_id):
        return jsonify({"error": "Not found"}), 404
    st = get_progress(run_id)
    if not st:
        run = _db.get_run(run_id)
        done = int(run.get("total") or 0) > 0
        return jsonify(
            {
                "run_id": run_id,
                "status": "completed" if done else "unknown",
                "phase": "done" if done else "",
                "current": int(run.get("passed", 0) or 0) + int(run.get("failed", 0) or 0),
                "total": int(run.get("total") or 0),
                "percent": 100.0 if done else 0.0,
                "test_id": "",
                "message": "",
                "error": None,
            }
        )
    return jsonify(st)


@api_bp.route("/run-status/<int:run_id>", methods=["GET"])
def run_status(run_id: int):
    """Lightweight status endpoint for global page polling."""
    if not _db.get_run(run_id):
        return jsonify({"error": "Not found"}), 404
    st = get_progress(run_id) or {}
    run = _db.get_run(run_id) or {}
    done = int(run.get("total") or 0) > 0
    status = st.get("status") or ("completed" if done else "running")
    progress = float(st.get("percent") or (100.0 if done else 0.0))
    return jsonify({"run_id": run_id, "status": status, "progress": round(progress, 2)})


@api_bp.route("/progress/<int:run_id>", methods=["GET"])
def crawl_progress(run_id: int):
    if not _db.get_run(run_id):
        return jsonify({"error": "Not found"}), 404
    st = get_progress(run_id) or {}
    visited = int(st.get("visited") or 0)
    discovered = int(st.get("discovered") or 0)
    failed = int(st.get("failed") or 0)
    skipped = int(st.get("skipped") or 0)
    tested = int(st.get("tested") or 0)
    remaining = int(st.get("remaining") or max(discovered - visited, 0))
    progress = round((100.0 * visited / discovered), 2) if discovered > 0 else float(st.get("percent") or 0.0)
    return jsonify(
        {
            "run_id": run_id,
            "progress": progress,
            "visited": visited,
            "discovered": discovered,
            "failed": failed,
            "skipped": skipped,
            "tested": tested,
            "remaining": remaining,
            "status": st.get("status") or "unknown",
            "phase": st.get("phase") or "",
            "logs": st.get("crawl_logs") or [],
        }
    )


@api_bp.route("/runs/latest", methods=["GET"])
def latest_run():
    rows = _db.list_runs(1)
    if not rows:
        return jsonify({"run": None})
    run = rows[0]
    _serialize_run_row(run)
    return jsonify({"run": run})


@api_bp.route("/alerts/latest", methods=["GET"])
def alerts_latest():
    runs = _db.list_runs(1)
    if not runs:
        return jsonify({"alert": False, "message": "", "critical_failures": 0, "run_id": None})
    r = runs[0]
    summary = {}
    if r.get("summary_json"):
        try:
            summary = json.loads(r["summary_json"])
        except Exception:
            summary = {}
    crit = int(summary.get("critical_failures") or 0)
    thr = config.CRITICAL_ALERT_THRESHOLD
    alert = crit >= thr
    msg = (
        f"Critical issues detected in latest run (≥{thr} critical failures)."
        if alert
        else ""
    )
    return jsonify(
        {
            "alert": alert,
            "message": msg,
            "critical_failures": crit,
            "run_id": r.get("id"),
            "threshold": thr,
        }
    )


@api_bp.route("/heatmap/<int:run_id>", methods=["GET"])
def heatmap_run(run_id: int):
    if not _db.get_run(run_id):
        return jsonify({"run_id": run_id, "pages": [], "fallback": True})
    tests = _db.get_test_cases_for_run(run_id)
    return jsonify({"run_id": run_id, "pages": heatmap_failures_by_page(tests)})


@api_bp.route("/compare-runs/<int:run_id>", methods=["GET"])
def compare_runs(run_id: int):
    cur = _db.get_run(run_id)
    if not cur:
        return jsonify(
            {
                "previous_run_id": None,
                "previous_failed": 0,
                "current_failed": 0,
                "delta": 0,
                "new_issues": [],
                "fixed_issues": [],
                "regressions": [],
                "improvements": [],
                "pass_rate": {"previous": None, "current": 0.0, "delta": None},
                "coverage": {"previous": None, "current": 0.0, "delta": None},
                "performance_score": {"previous": None, "current": 0.0, "delta": None},
                "visual_changes": {"previous_failed": None, "current_failed": 0, "delta": None},
                "fallback": True,
            }
        )
    prev_id = _db.get_previous_run_id(run_id)
    cur_failed_ct = int(cur.get("failed") or 0)
    if not prev_id:
        sr = float(cur.get("success_rate") or 0)
        ccov = cur.get("coverage")
        cperf = cur.get("performance_score")
        return jsonify(
            {
                "previous_run_id": None,
                "previous_failed": 0,
                "current_failed": cur_failed_ct,
                "delta": 0,
                "new_issues": [],
                "fixed_issues": [],
                "regressions": [],
                "improvements": [],
                "pass_rate": {"previous": None, "current": round(sr, 2), "delta": None},
                "coverage": {
                    "previous": None,
                    "current": round(float(ccov), 2) if ccov is not None else None,
                    "delta": None,
                },
                "performance_score": {
                    "previous": None,
                    "current": round(float(cperf), 2) if cperf is not None else None,
                    "delta": None,
                },
                "visual_changes": {"previous_failed": None, "current_failed": 0, "delta": None},
            }
        )

    prev = _db.get_run(prev_id)
    pt = _db.get_test_cases_for_run(prev_id)
    ct = _db.get_test_cases_for_run(run_id)
    payload = compare_runs_extended(prev, cur, pt, ct)
    prev_v = _db.get_visual_tests_for_run(prev_id)
    cur_v = _db.get_visual_tests_for_run(run_id)
    prev_v_fail = sum(1 for r in prev_v if int(r.get("failed") or 0) == 1)
    cur_v_fail = sum(1 for r in cur_v if int(r.get("failed") or 0) == 1)
    payload["visual_changes"] = {
        "previous_failed": prev_v_fail,
        "current_failed": cur_v_fail,
        "delta": cur_v_fail - prev_v_fail,
    }
    return jsonify(payload)


@api_bp.route("/integrations", methods=["GET"])
def integrations_info():
    """Discover integration options (CI, webhooks, auth)."""
    return jsonify(
        {
            "service": "autoqa-pro",
            "endpoints": {
                "run_full_test": {
                    "method": "POST",
                    "path": "/api/run-full-test",
                    "content_type": "application/json",
                    "body": {
                        "url": "string (required) — target site to test",
                        "crawl_mode": "quick | standard | deep | full (optional; default standard)",
                        "depth": "legacy alias of crawl_mode (backward compatible)",
                        "max_pages": f"integer optional — manual crawl cap (1–{config.MAX_CRAWL_PAGES_MAX})",
                        "test_type": "all (optional, reserved)",
                        "webhook_url": "string (optional) — HTTPS URL to receive JSON when run completes",
                    },
                    "headers": {
                        "Authorization": "Bearer <AUTOQA_API_KEY> — required if server sets AUTOQA_API_KEY",
                        "X-API-Key": "<AUTOQA_API_KEY> — alternative to Bearer",
                    },
                },
                "run_full_test_async": {
                    "method": "POST",
                    "path": "/api/run-full-test-async",
                    "note": "Returns 202 with run_id; poll execution-status until completed, then GET /api/runs/<id> for full metrics.",
                    "body": "same as run_full_test",
                    "headers": "same as run_full_test",
                },
                "execution_status": {"method": "GET", "path": "/api/runs/<run_id>/execution-status"},
                "run_status": {"method": "GET", "path": "/api/run-status/<run_id>"},
                "crawl_progress": {"method": "GET", "path": "/api/progress/<run_id>"},
                "latest_run": {"method": "GET", "path": "/api/runs/latest"},
                "run_by_id": {"method": "GET", "path": "/api/run/<run_id>"},
                "pages_by_run": {"method": "GET", "path": "/api/pages/<run_id>"},
                "performance_by_run": {"method": "GET", "path": "/api/performance/<run_id>"},
                "visual_by_run": {"method": "GET", "path": "/api/visual/<run_id>"},
                "alerts_latest": {
                    "method": "GET",
                    "path": "/api/alerts/latest",
                    "note": "Critical-failure banner payload for latest stored run (threshold from AUTOQA_CRITICAL_ALERT_THRESHOLD).",
                },
                "heatmap": {"method": "GET", "path": "/api/heatmap/<run_id>"},
                "health": {"method": "GET", "path": "/api/health"},
                "compare_runs": {
                    "method": "GET",
                    "path": "/api/compare-runs/<run_id>",
                    "note": "Compares to previous run: regressions/improvements, pass_rate/coverage/performance_score deltas.",
                },
                "export_json": {"method": "GET", "path": "/api/runs/<run_id>/export.json"},
                "export_csv": {"method": "GET", "path": "/api/runs/<run_id>/export.csv"},
                "structured_report_json": {
                    "method": "GET",
                    "path": "/api/runs/<run_id>/report",
                    "note": "Canonical report payload (summary, failures, suggestions, performance, verdict). Use ?compact=1 to omit full tests array for faster loads.",
                },
                "bug_reports": {"method": "GET", "path": "/api/runs/<run_id>/bug-reports"},
                "enterprise": {"method": "GET", "path": "/api/runs/<run_id>/enterprise"},
            },
            "webhook_event": {
                "name": "autoqa.run.completed",
                "payload": "JSON POST with run_id, results, summary, links (api_run, pdf, dashboard)",
            },
            "ci_example": "examples/github-actions-autoqa.yml",
        }
    )


@api_bp.route("/runs", methods=["GET"])
def list_runs():
    runs = _db.list_runs(200)
    for r in runs:
        _serialize_run_row(r)
    return jsonify({"runs": runs})


@api_bp.route("/runs", methods=["DELETE"])
def delete_all_runs():
    if not api_key_authorized(request):
        return jsonify({"error": "Unauthorized"}), 401
    _db.clear_runs()
    return jsonify({"ok": True})


@api_bp.route("/runs/<int:run_id>", methods=["DELETE"])
def delete_run(run_id: int):
    if not api_key_authorized(request):
        return jsonify({"error": "Unauthorized"}), 401
    if not _db.get_run(run_id):
        return jsonify({"error": "Not found"}), 404
    _db.delete_run(run_id)
    return jsonify({"ok": True, "run_id": run_id})


@api_bp.route("/runs/<int:run_id>", methods=["GET"])
def get_run(run_id: int):
    run = _db.get_run(run_id)
    if not run:
        return jsonify(_empty_run_row(run_id))
    _serialize_run_row(run)
    run["health_score"] = run.get("health_score")
    run["coverage"] = run.get("coverage")
    run["performance_score"] = run.get("performance_score")
    run["accessibility_score"] = run.get("accessibility_score")
    run["security_score"] = run.get("security_score")
    return jsonify(run)


@api_bp.route("/run/<int:run_id>", methods=["GET"])
def get_run_alias(run_id: int):
    """Alias for single-run fetch."""
    return get_run(run_id)


@api_bp.route("/runs/<int:run_id>/enterprise", methods=["GET"])
def get_run_enterprise(run_id: int):
    """Enterprise QA slice: flows, a11y, security warnings, performance breakdown (from stored summary)."""
    run = _db.get_run(run_id)
    if not run:
        return jsonify(
            {
                "run_id": run_id,
                "user_flows_tested": [],
                "accessibility_score": 0.0,
                "security_score": 0.0,
                "security_warnings": [],
                "performance_breakdown": {},
                "fallback": True,
            }
        )
    summary = {}
    if run.get("summary_json"):
        try:
            summary = json.loads(run["summary_json"])
        except Exception:
            summary = {}
    return jsonify(
        {
            "run_id": run_id,
            "user_flows_tested": summary.get("user_flows_tested") or [],
            "accessibility_score": run.get("accessibility_score"),
            "security_score": run.get("security_score"),
            "security_warnings": summary.get("security_warnings") or [],
            "performance_breakdown": summary.get("performance_breakdown") or {},
        }
    )


@api_bp.route("/runs/<int:run_id>/tests", methods=["GET"])
def get_run_tests(run_id: int):
    if not _db.get_run(run_id):
        return jsonify({"test_cases": [], "total": 0, "offset": 0, "limit": 0, "hasMore": False, "fallback": True})
    tests = _db.get_test_cases_for_run(run_id)
    try:
        offset = max(0, int(request.args.get("offset", 0) or 0))
    except (TypeError, ValueError):
        offset = 0
    limit_raw = request.args.get("limit")
    try:
        if limit_raw is None:
            slice_tests = tests[offset:]
            lim = len(slice_tests)
        else:
            lim = max(1, min(500, int(limit_raw)))
            slice_tests = tests[offset : offset + lim]
    except (TypeError, ValueError):
        slice_tests = tests[offset:]
        lim = len(slice_tests)
    return jsonify(
        {
            "test_cases": slice_tests,
            "total": len(tests),
            "offset": offset,
            "limit": lim,
            "hasMore": offset + len(slice_tests) < len(tests),
        }
    )


@api_bp.route("/runs/<int:run_id>/report", methods=["GET"])
def get_run_report(run_id: int):
    """Structured report JSON (summary, failures, suggestions, performance, recommendation)."""
    run = _db.get_run(run_id)
    if not run:
        return jsonify(build_report_payload(_empty_run_row(run_id), [], {}, [], include_tests=False))
    tests = _db.get_test_cases_for_run(run_id)
    charts = {}
    if run.get("charts_json"):
        try:
            charts = json.loads(run["charts_json"])
        except Exception:
            charts = {}
    pages = _db.get_pages_for_run(run_id)
    compact = request.args.get("compact") == "1"
    payload = build_report_payload(run, tests, charts, pages, include_tests=not compact)
    return jsonify(payload)


@api_bp.route("/runs/<int:run_id>/issues", methods=["GET"])
def get_run_issues(run_id: int):
    """Actionable issues derived from failed tests, scoped to a single run."""
    if not _db.get_run(run_id):
        return jsonify({"criticalIssues": [], "warningIssues": [], "passedTests": [], "fallback": True})
    tests = _db.get_test_cases_for_run(run_id)
    charts = {}
    run = _db.get_run(run_id) or {}
    if run.get("charts_json"):
        try:
            charts = json.loads(run["charts_json"])
        except Exception:
            charts = {}

    report_payload = build_report_payload(
        run=run,
        tests=tests,
        charts=charts,
        pages=None,
        include_tests=False,
    )
    failures = report_payload.get("failures") or []

    critical = [f for f in failures if (f.get("severity") or "") == "Critical"]
    warnings = [
        f
        for f in failures
        if (f.get("severity") or "") in ("High", "Medium")
    ]

    # For dashboard UX we also show a green section with a small number of passes.
    passed = [t for t in tests if (t.get("status") or "") == "passed"]
    # Sort by priority (Critical->High->Medium->Low) for relevance.
    pr_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
    passed.sort(key=lambda x: pr_order.get(str(x.get("priority") or "Low"), 9))
    passed_cards = []
    for t in passed[:12]:
        passed_cards.append(
            {
                "id": t.get("test_id") or t.get("id"),
                "runId": run_id,
                "testId": t.get("test_id") or t.get("id"),
                "scenario": t.get("scenario") or t.get("title") or t.get("name") or "",
                "severity": "Passed",
                "pageUrl": t.get("page") or "",
                "elementSelector": t.get("element_selector") or "",
                "issueType": t.get("issue_type") or "",
                "message": "",
                "steps": t.get("steps") or [],
                "expected": t.get("expected_result") or t.get("expected") or "",
                "actual": t.get("actual_result") or t.get("actual") or "",
                "aiSuggestion": "",
            }
        )

    return jsonify(
        {
            "run_id": run_id,
            "counts": {
                "critical": len(critical),
                "warnings": len(warnings),
                "passed": len(passed_cards),
            },
            "criticalIssues": critical,
            "warningIssues": warnings,
            "passedTests": passed_cards,
        }
    )


@api_bp.route("/issues/highlight", methods=["POST"])
def preview_issue_highlight():
    """
    Generate a screenshot with a red highlight around the selector.
    Request body: { run_id, pageUrl, elementSelector, testId }
    """
    if not request.is_json:
        return jsonify({"error": "Expected JSON body"}), 400
    body = request.get_json(silent=True) or {}
    run_id = body.get("run_id")
    page_url = body.get("pageUrl") or body.get("page_url") or ""
    selector = body.get("elementSelector") or body.get("selector") or ""
    test_id = body.get("testId") or body.get("test_id") or ""

    try:
        run_id = int(run_id)
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid run_id"}), 400

    if not page_url or not selector:
        return jsonify({"error": "Missing pageUrl or elementSelector"}), 400

    try:
        res = highlight_element_screenshot(
            page_url=page_url,
            element_selector=selector,
            run_id=run_id,
            test_id=str(test_id),
        )
    except Exception as e:
        return jsonify({"error": f"Highlight failed: {e}"}), 500

    return jsonify(res)


@api_bp.route("/pages/<int:run_id>", methods=["GET"])
def get_run_pages(run_id: int):
    if not _db.get_run(run_id):
        return jsonify({"error": "Not found"}), 404
    pages = _db.get_pages_for_run(run_id)
    for p in pages:
        perf = p.get("performance") or {}
        raw = str(perf.get("screenshot_path") or "")
        web = ""
        if raw:
            n = raw.replace("\\", "/")
            idx = n.lower().find("/static/")
            web = n[idx:] if idx >= 0 else ""
        p["screenshot"] = web
    return jsonify({"run_id": run_id, "pages": pages})


@api_bp.route("/performance/<int:run_id>", methods=["GET"])
def get_run_performance(run_id: int):
    run = _db.get_run(run_id)
    if not run:
        return jsonify({"error": "Not found"}), 404
    _serialize_run_row(run)
    pages = _db.get_pages_for_run(run_id)
    perf_rows = [
        {
            "page_url": p.get("page_url"),
            "load_status": p.get("load_status"),
            "response_time_ms": p.get("response_time_ms"),
            "performance_score": p.get("performance_score"),
            "performance": p.get("performance"),
            "issues": p.get("issues"),
            "suggestions": p.get("suggestions"),
        }
        for p in pages
    ]
    return jsonify(
        {
            "run_id": run_id,
            "performance_score": run.get("performance_score"),
            "performance_grade": (run.get("summary") or {}).get("performance_grade"),
            "rows": perf_rows,
        }
    )


@api_bp.route("/visual/<int:run_id>", methods=["GET"])
def get_run_visual(run_id: int):
    if not _db.get_run(run_id):
        return jsonify({"error": "Not found"}), 404
    rows = _db.get_visual_tests_for_run(run_id)
    return jsonify({"run_id": run_id, "visual_tests": rows})


@api_bp.route("/timeline", methods=["GET"])
def timeline():
    rows = _db.timeline_data(25)
    return jsonify({"timeline": rows})


@api_bp.route("/runs/<int:run_id>/export.json", methods=["GET"])
def export_run_json(run_id: int):
    run = _db.get_run(run_id)
    if not run:
        return jsonify({"error": "Not found"}), 404
    _serialize_run_row(run)
    tests = _db.get_test_cases_for_run(run_id)
    return jsonify({"run": run, "test_cases": tests})


@api_bp.route("/runs/<int:run_id>/export.csv", methods=["GET"])
def export_run_csv(run_id: int):
    run = _db.get_run(run_id)
    if not run:
        return jsonify({"error": "Not found"}), 404
    tests = _db.get_test_cases_for_run(run_id)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(
        [
            "test_id",
            "user_story",
            "scenario",
            "test_type",
            "category",
            "priority",
            "severity",
            "status",
            "page",
            "page_class",
            "component",
        ]
    )
    for t in tests:
        w.writerow(
            [
                t.get("test_id", ""),
                t.get("user_story", ""),
                t.get("scenario", ""),
                t.get("test_type", ""),
                t.get("category", ""),
                t.get("priority", ""),
                t.get("severity", ""),
                t.get("status", ""),
                t.get("page", ""),
                t.get("page_class", ""),
                t.get("component", ""),
            ]
        )
    return Response(
        buf.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename=autoqa_run_{run_id}.csv"},
    )


@api_bp.route("/runs/<int:run_id>/bug-reports", methods=["GET"])
def bug_reports(run_id: int):
    if not _db.get_run(run_id):
        return jsonify({"error": "Not found"}), 404
    tests = _db.get_test_cases_for_run(run_id)
    bugs: List[Dict[str, Any]] = []
    for t in tests:
        if t.get("status") != "failed":
            continue
        bugs.append(
            {
                "title": t.get("name") or t.get("test_id"),
                "severity": t.get("severity"),
                "category": t.get("category"),
                "page": t.get("page"),
                "steps": t.get("steps") or [],
                "expected": t.get("expected_result") or t.get("expected"),
                "actual": t.get("actual_result") or t.get("actual"),
                "root_cause": t.get("root_cause"),
                "suggestion": t.get("suggestion"),
                "logs": t.get("logs") or [],
            }
        )
    return jsonify({"run_id": run_id, "bug_reports": bugs, "count": len(bugs)})


@api_bp.route("/download-report/<int:run_id>", methods=["GET"])
def download_report(run_id: int):
    run = _db.get_run(run_id)
    if not run:
        return jsonify({"error": "Not found"}), 404
    tests = _db.get_test_cases_for_run(run_id)
    charts = {}
    if run.get("charts_json"):
        try:
            charts = json.loads(run["charts_json"])
        except Exception:
            charts = {}
    pages = _db.get_pages_for_run(run_id)

    reports_dir = os.path.join(config.INSTANCE_DIR, "reports")
    os.makedirs(reports_dir, exist_ok=True)
    out_path = os.path.join(reports_dir, f"autoqa_report_{run_id}.pdf")
    build_pdf(run, tests, charts, out_path, pages_audit=pages)
    return send_file(out_path, as_attachment=True, download_name=f"AutoQA_Report_{run_id}.pdf")


@api_bp.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "autoqa-pro"})
