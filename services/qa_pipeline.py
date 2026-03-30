"""Full QA run: crawl → parallel extract+profile → generate → execute → persist (single module for sync + async)."""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

import config
from models.database import Database
from performance.scorer import score_run
from services.ai_insights import enrich_failed_results_with_ai, maybe_enhance_insights
from services.crawler import PageSnapshot, crawl_site
from services.data_generator import single_profile
from services.defect_analyzer import enrich_results
from services.element_extractor import extract_elements
from services.run_metrics import (
    build_advanced_analytics,
    build_insights,
    build_performance_breakdown,
    category_pass_rate,
    compute_coverage,
    compute_health_score,
    critical_path_coverage_pct,
    failure_severity_quality_score,
    flows_tested_summary,
    performance_score_from_load_times_ms,
    risk_label_from_results,
    severity_distribution,
)
from services.test_executor import execute_tests
from services.test_generator import generate_test_cases
from services.visual_regression import compare_page_screenshot
from services.webhook_notifier import send_run_completed_webhook

ProgressFn = Optional[Callable[[str, int, int, str, Optional[Dict[str, Any]]], None]]


def _page_class_lookup(crawl: Dict[str, Any], page_url: str) -> str:
    pu = (page_url or "").split("#")[0].rstrip("/")
    for p in crawl.get("pages") or []:
        u = getattr(p, "url", None)
        if u is None and isinstance(p, dict):
            u = p.get("url")
        if not u:
            continue
        if str(u).split("#")[0].rstrip("/") == pu:
            pc = getattr(p, "page_class", None)
            if pc is None and isinstance(p, dict):
                pc = p.get("page_class")
            return str(pc or "")
    return ""


def run_qa_pipeline(
    *,
    url: str,
    depth: str,
    max_pages: Optional[int],
    max_depth: Optional[int],
    run_id: int,
    batch_id: str,
    db: Database,
    progress: ProgressFn = None,
    webhook_url: Optional[str] = None,
    public_base_url: str = "",
) -> Dict[str, Any]:
    """
    Assumes run row already inserted (placeholder). Updates run and inserts test_cases.
    progress(phase, current, total, test_id) — phases: crawl, extract, generate, execute, persist
    """
    if progress:
        progress("crawl", 0, 1, "", {"visited": 0, "discovered": 1, "failed": 0})
    pipeline_logs: List[str] = []

    def crawl_progress(meta: Dict[str, Any]) -> None:
        if progress:
            vis = int(meta.get("visited") or 0)
            disc = int(meta.get("discovered") or 0)
            progress("crawl", vis, max(vis, disc, 1), "", meta)

    mode = (depth or "standard").lower()
    effective_max_depth = int(max_depth) if max_depth is not None else (
        config.MAX_DEPTH_QUICK
        if mode == "quick"
        else config.MAX_DEPTH_DEEP
        if mode == "deep"
        else config.MAX_DEPTH_FULL
        if mode == "full"
        else config.MAX_DEPTH_STANDARD
    )
    crawl = crawl_site(url, max_pages=max_pages, max_depth=effective_max_depth, on_progress=crawl_progress)
    pages = list(crawl.get("pages") or [])
    if not pages:
        # Crawl fallback keeps the rest of the pipeline alive even if the site blocks bots.
        pipeline_logs.append("Crawler returned no pages; injecting homepage fallback.")
        crawl = dict(crawl)
        crawl["pages"] = [
            PageSnapshot(
                url=url,
                depth=0,
                priority=0,
                title=url,
                page_class="FALLBACK",
                load_status="fallback",
                error="Crawler fallback page injected",
                error_type="fallback",
                error_message="Crawler fallback page injected",
            )
        ]
        crawl["visited_urls"] = [url]
        crawl["valid_urls"] = [url]
        crawl["total_pages_discovered"] = max(int(crawl.get("total_pages_discovered") or 0), 1)
        crawl["total_pages_visited"] = max(int(crawl.get("total_pages_visited") or 0), 1)
        crawl["errors"] = list(crawl.get("errors") or []) + ["Crawler fallback page injected"]
        crawl["crawl_logs"] = list(crawl.get("crawl_logs") or []) + [f"fallback injected: {url}"]
    if progress:
        progress(
            "crawl",
            int(crawl.get("total_pages_visited") or 0),
            max(int(crawl.get("total_pages_discovered") or 1), 1),
            "",
            {
                "visited": int(crawl.get("total_pages_visited") or 0),
                "discovered": int(crawl.get("total_pages_discovered") or 0),
                "failed": int(crawl.get("failed_pages") or 0),
            },
        )

    if progress:
        progress("extract", 0, 2, "", None)
    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_el = pool.submit(extract_elements, crawl)
        fut_pr = pool.submit(single_profile)
        try:
            elements = fut_el.result()
        except Exception as e:
            # Extraction should never stop the run; fall back to an empty element set.
            pipeline_logs.append(f"extract_elements failed: {e}")
            elements = []
        try:
            profile = fut_pr.result()
        except Exception as e:
            # Synthetic profile generation is a convenience, so fall back to a fresh profile.
            pipeline_logs.append(f"single_profile failed: {e}")
            profile = single_profile()
    if progress:
        progress("extract", 2, 2, "", None)

    dataset_snapshot = {
        "synthetic_profile": asdict(profile),
        "parallel_phases": ["extract_elements", "single_profile"],
        "note": "Post-crawl element extraction and synthetic profile generation run in parallel threads.",
    }

    if progress:
        progress("generate", 0, 1, "", None)
    tests = generate_test_cases(url, elements, crawl, depth_mode=depth)
    pipeline_logs.append(f"Generated {len(tests)} test case(s) from {len(crawl.get('pages') or [])} crawled page(s).")
    # Quick mode = critical-only execution for faster feedback.
    if mode == "quick":
        tests = [t for t in tests if str(t.get("priority") or "") == "Critical"]
        pipeline_logs.append(f"Quick mode kept {len(tests)} critical test case(s).")
    if progress:
        progress("generate", 1, 1, "", None)

    def exec_progress(cur: int, tot: int, tid: str) -> None:
        if progress:
            progress(
                "execute",
                cur,
                tot,
                tid,
                {
                    "tested": int(cur),
                    "remaining": max(int(tot) - int(cur), 0),
                },
            )

    # Incremental skip logic using page cache (content hash unchanged => skip test).
    page_hash: Dict[str, str] = {}
    page_urls: List[str] = []
    for p in crawl.get("pages") or []:
        pu = str(getattr(p, "url", "") or "")
        if not pu:
            continue
        page_urls.append(pu)
        page_hash[pu] = str(getattr(p, "content_hash", "") or "")
    cached = db.get_page_cache_bulk(page_urls)
    unchanged_pages = {
        u
        for u in page_urls
        if u in cached and str(cached[u].get("content_hash") or "") == str(page_hash.get(u) or "")
    }
    run_tests: List[Dict[str, Any]] = []
    skipped_results: List[Dict[str, Any]] = []
    for t in tests:
        pu = str(t.get("page") or t.get("action", {}).get("url") or "")
        if pu and pu in unchanged_pages:
            skipped_results.append(
                {
                    "test_id": t.get("id", ""),
                    "name": t.get("name", ""),
                    "title": t.get("title") or t.get("name", ""),
                    "user_story": t.get("user_story", ""),
                    "scenario": t.get("scenario", ""),
                    "test_type": t.get("test_type", "Positive"),
                    "component": t.get("component") or "",
                    "page": pu,
                    "category": t.get("category", ""),
                    "priority": t.get("priority", ""),
                    "status": "skipped",
                    "expected": t.get("expected_result", ""),
                    "expected_result": t.get("expected_result", ""),
                    "actual": "Skipped: page unchanged since last run",
                    "actual_result": "Skipped: page unchanged since last run",
                    "error_kind": "",
                    "element_selector": "",
                    "issue_type": t.get("category", ""),
                    "message": "incremental-skip",
                    "screenshot": "",
                    "screenshot_path": "",
                    "steps": t.get("steps", []),
                    "action_kind": (t.get("action") or {}).get("kind"),
                    "flow_type": (t.get("action") or {}).get("flow_type"),
                    "retry_count": 0,
                    "logs": [],
                }
            )
            continue
        run_tests.append(t)

    raw_results = execute_tests(run_tests, profile, batch_id, run_id, progress=exec_progress)
    raw_results = raw_results + skipped_results
    results = enrich_results(raw_results)
    results = enrich_failed_results_with_ai(results)
    pipeline_logs.append(
        f"Execution finished: passed={sum(1 for r in results if r.get('status') == 'passed')}, "
        f"failed={sum(1 for r in results if r.get('status') == 'failed')}, "
        f"skipped={sum(1 for r in results if r.get('status') == 'skipped')}."
    )

    passed = sum(1 for r in results if r.get("status") == "passed")
    failed = sum(1 for r in results if r.get("status") == "failed")
    skipped = sum(1 for r in results if r.get("status") == "skipped")
    total = len(results)
    executed_total = max(1, passed + failed)
    running = 0

    pass_rate = (passed / executed_total * 100.0) if executed_total else 0.0
    page_perf_rows = [p.performance for p in (crawl.get("pages") or []) if getattr(p, "performance", None)]
    perf_score, perf_grade = score_run(page_perf_rows)
    if not page_perf_rows:
        perf_score = performance_score_from_load_times_ms(crawl.get("load_times_ms") or [])
        perf_grade = "Avg" if perf_score >= 55 else "Poor"
    cov_pct, tested_el, total_el, untested = compute_coverage(elements, tests)
    sev_quality = failure_severity_quality_score(results)
    sec_score_metric = round(category_pass_rate(results, "security"), 2)
    a11y_score = round(category_pass_rate(results, "accessibility"), 2)
    health = compute_health_score(pass_rate, sev_quality, perf_score)
    insights = build_insights(results)
    insights = maybe_enhance_insights(insights, results)
    perf_breakdown = build_performance_breakdown(crawl.get("load_times_ms") or [], perf_score, results)
    flows_summary = flows_tested_summary(results)
    security_warnings = [
        {"test": r.get("name", ""), "detail": (r.get("actual") or "")[:240]}
        for r in results
        if r.get("status") == "failed" and (r.get("category") or "").lower() == "security"
    ][:12]
    sev_chart = severity_distribution(results)

    category_failures: Dict[str, int] = {}
    for r in results:
        if r.get("status") == "failed":
            cat = r.get("category") or "Unknown"
            category_failures[cat] = category_failures.get(cat, 0) + 1

    critical_failures = sum(
        1 for r in results if r.get("status") == "failed" and (r.get("severity") == "Critical")
    )

    timeline_before = db.timeline_data(30)
    prev_rate: Optional[float] = None
    # timeline_data is chronological; last row is this run (placeholder). Use prior row for trend.
    if len(timeline_before) >= 2:
        try:
            prev_rate = float(timeline_before[-2].get("success_rate") or 0)
        except Exception:
            prev_rate = None
    analytics = build_advanced_analytics(results, crawl, previous_success_rate=prev_rate)
    risk_label = risk_label_from_results(results)
    crit_cov = critical_path_coverage_pct(crawl, results)

    summary = {
        "url": url,
        "depth": depth,
        "max_pages": max_pages,
        "risk_score_label": risk_label,
        "critical_path_coverage_percent": crit_cov,
        "advanced_analytics": analytics,
        "mode": mode,
        "max_depth": effective_max_depth,
        "pages_crawled": len(crawl.get("visited_urls") or []),
        "total_pages_discovered": int(crawl.get("total_pages_discovered") or 0),
        "total_pages_visited": int(crawl.get("total_pages_visited") or len(crawl.get("visited_urls") or [])),
        "failed_pages": int(crawl.get("failed_pages") or 0),
        "skipped_pages": int(crawl.get("skipped_pages") or 0),
        "tests_skipped": int(skipped),
        "tests_executed": int(passed + failed),
        "crawl_errors": crawl.get("errors") or [],
        "crawl_logs": crawl.get("crawl_logs") or [],
        "pipeline_logs": pipeline_logs,
        "critical_failures": critical_failures,
        "pass_rate": round(pass_rate, 2),
        "performance_score": round(perf_score, 2),
        "performance_grade": perf_grade,
        "severity_quality_score": round(sev_quality, 2),
        "coverage_score": cov_pct,
        "tested_elements": tested_el,
        "total_elements": total_el,
        "untested_elements": untested,
        "coverage": cov_pct,
        "user_flows_tested": flows_summary,
        "accessibility_score": a11y_score,
        "security_score_metric": sec_score_metric,
        "security_warnings": security_warnings,
        "performance_breakdown": perf_breakdown,
        "synthetic_dataset": dataset_snapshot,
        "pipeline": {
            "parallel_after_crawl": True,
            "phases": ["crawl", "extract_elements+profile (parallel)", "generate_tests", "execute", "persist"],
            "logs": pipeline_logs,
        },
        "release_readiness": "Ready"
        if critical_failures == 0 and pass_rate >= 80.0
        else "Not Ready",
    }

    labels = list(category_failures.keys())
    data = [category_failures[k] for k in labels]
    if not labels:
        labels = [
            "Functional",
            "UI/UX",
            "Navigation",
            "Validation",
            "Security",
            "Performance",
            "Accessibility",
        ]
        data = [0.0] * len(labels)
    tl_labels = [r.get("timestamp", "")[:19] for r in timeline_before]
    tl_data = [float(r.get("success_rate", 0) or 0) for r in timeline_before]
    cat_run = Counter((r.get("category") or "functional").lower() for r in results)
    cat_keys = sorted(cat_run.keys())
    charts = {
        "pass_fail": {
            "labels": ["Passed", "Failed", "Running"],
            "data": [float(passed), float(failed), float(running)],
        },
        "category_failures": {"labels": labels, "data": [float(x) for x in data]},
        "tests_by_category": {
            "labels": cat_keys if cat_keys else ["functional"],
            "data": [float(cat_run[k]) for k in cat_keys] if cat_keys else [float(total)],
        },
        "timeline": {"labels": tl_labels, "data": tl_data},
        "severity_distribution": sev_chart,
        "coverage": {
            "labels": ["Covered", "Gap"],
            "data": [float(cov_pct), float(max(0.0, 100.0 - cov_pct))],
        },
        "performance_trend": {
            "labels": [r.get("timestamp", "")[:19] for r in timeline_before] + [datetime.now(timezone.utc).isoformat()[:19]],
            "data": [float(r.get("performance_score") or 0) for r in timeline_before] + [float(perf_score)],
        },
    }

    if progress:
        progress("persist", 0, 1, "", None)

    db.update_run_completion(
        run_id=run_id,
        total=total,
        passed=passed,
        failed=failed,
        summary=summary,
        charts=charts,
        health_score=health,
        coverage=cov_pct,
        performance_score=perf_score,
        insights=insights,
        accessibility_score=a11y_score,
        security_score=sec_score_metric,
        synthetic_dataset_json=json.dumps(dataset_snapshot, ensure_ascii=False),
    )

    for r in results:
        shot = r.get("screenshot_path") or r.get("screenshot")
        pg = r.get("page") or ""
        db.insert_test_case(
            run_id=run_id,
            test_id=r.get("test_id", ""),
            name=r.get("name", ""),
            category=r.get("category", ""),
            priority=r.get("priority", ""),
            status=r.get("status", ""),
            expected=r.get("expected_result") or r.get("expected", ""),
            actual=r.get("actual_result") or r.get("actual", ""),
            suggestion=r.get("suggestion", ""),
            screenshot=shot,
            steps=r.get("steps") or [],
            severity=r.get("severity", ""),
            retry_count=int(r.get("retry_count") or 0),
            screenshot_path=shot,
            page=pg,
            root_cause=r.get("root_cause") or "",
            user_story=r.get("user_story", "") or "",
            scenario=r.get("scenario", "") or "",
            test_type=r.get("test_type", "") or "",
            logs=list(r.get("logs") or []),
            component=r.get("component", "") or "",
            page_class=_page_class_lookup(crawl, pg),
            element_selector=r.get("element_selector", "") or "",
            issue_type=r.get("issue_type", "") or "",
            message=r.get("message", "") or "",
        )

    db.clear_page_audits(run_id)
    db.clear_visual_tests(run_id)
    visual_failures = 0
    for p in crawl.get("pages") or []:
        db.insert_page_audit(
            run_id=run_id,
            page_url=p.url,
            load_status=p.load_status,
            response_time_ms=float(p.load_time_ms or 0),
            error_type=p.error_type,
            error_message=p.error_message or p.error or "",
            js_errors=p.js_errors,
            performance=p.performance,
            performance_score=p.performance_score,
            issues=p.perf_issues,
            suggestions=p.suggestions,
        )
        # Update cache only for successfully crawled pages with known hash.
        if str(getattr(p, "load_status", "")) != "failed":
            db.upsert_page_cache(
                page_url=str(getattr(p, "url", "") or ""),
                content_hash=str(getattr(p, "content_hash", "") or ""),
                run_id=run_id,
                last_result={"load_status": getattr(p, "load_status", "success")},
            )
        shot = p.performance.get("screenshot_path") if isinstance(p.performance, dict) else None
        if shot:
            diff = compare_page_screenshot(
                page_key=p.url,
                run_id=run_id,
                src_path=shot,
                screenshots_root=config.VISUAL_BASE_DIR,
                mismatch_threshold=config.VISUAL_DIFF_THRESHOLD_PERCENT,
            )
            visual_failed = bool(diff.get("failed"))
            if visual_failed:
                visual_failures += 1
            db.insert_visual_test(
                run_id=run_id,
                page_url=p.url,
                baseline_path=str(diff.get("baseline_path") or ""),
                current_path=str(diff.get("current_path") or ""),
                diff_path=str(diff.get("diff_path") or ""),
                mismatch_percent=float(diff.get("mismatch_percent") or 0),
                status=str(diff.get("status") or ""),
                failed=visual_failed,
            )

    response_tests = [
        {
            "test_id": r.get("test_id"),
            "id": r.get("test_id"),
            "title": r.get("title") or r.get("name"),
            "name": r.get("name"),
            "user_story": r.get("user_story", ""),
            "scenario": r.get("scenario", ""),
            "test_type": r.get("test_type", "Positive"),
            "category": r.get("category"),
            "priority": r.get("priority"),
            "status": r.get("status"),
            "steps": r.get("steps"),
            "expected_result": r.get("expected_result") or r.get("expected"),
            "actual_result": r.get("actual_result") or r.get("actual"),
            "expected": r.get("expected_result") or r.get("expected"),
            "actual": r.get("actual_result") or r.get("actual"),
            "severity": r.get("severity"),
            "page": r.get("page") or "",
            "page_class": _page_class_lookup(crawl, r.get("page") or ""),
            "component": r.get("component", ""),
            "root_cause": r.get("root_cause") or "",
            "suggestion": r.get("suggestion"),
            "screenshot": r.get("screenshot_path") or r.get("screenshot"),
            "screenshot_path": r.get("screenshot_path") or r.get("screenshot"),
            "retry_count": r.get("retry_count", 0),
            "logs": r.get("logs") or [],
        }
        for r in results
    ]

    success_rate = (passed / total * 100.0) if total else 0.0
    response_body: Dict[str, Any] = {
        "run_id": run_id,
        "total": total,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "running": running,
        "health_score": health,
        "severity_quality_score": round(sev_quality, 2),
        "pass_rate": round(pass_rate, 2),
        "performance_score": round(perf_score, 2),
        "performance_grade": perf_grade,
        "coverage_score": cov_pct,
        "coverage": cov_pct,
        "accessibility_score": a11y_score,
        "security_score": sec_score_metric,
        "critical_failures": critical_failures,
        "pages_discovered": int(crawl.get("total_pages_discovered") or 0),
        "pages_visited": int(crawl.get("total_pages_visited") or 0),
        "failed_pages": int(crawl.get("failed_pages") or 0),
        "skipped_pages": int(crawl.get("skipped_pages") or 0),
        "visual_failures": visual_failures,
        "user_flows_tested": flows_summary,
        "security_warnings": security_warnings,
        "performance_breakdown": perf_breakdown,
        "insights": insights,
        "test_cases": response_tests,
        "summary": summary,
        "charts": charts,
        "integrations": {
            "webhook": {
                "attempted": False,
                "success": False,
                "http_status": None,
                "error": None,
            }
        },
    }

    if webhook_url:
        ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        base = public_base_url.rstrip("/")
        wh_payload = {
            "event": "autoqa.run.completed",
            "schema_version": 1,
            "timestamp": ts,
            "run_id": run_id,
            "target_url": url,
            "results": {
                "total": total,
                "passed": passed,
                "failed": failed,
                "success_rate_percent": round(success_rate, 2),
                "critical_failures": critical_failures,
                "health_score": health,
                "coverage": cov_pct,
                "total_pages": int(crawl.get("total_pages_discovered") or 0),
                "success_pages": max(0, int(crawl.get("total_pages_visited") or 0) - int(crawl.get("failed_pages") or 0)),
                "failed_pages": int(crawl.get("failed_pages") or 0),
                "accessibility_score": a11y_score,
                "security_score": sec_score_metric,
                "performance_score": round(perf_score, 2),
            },
            "summary": summary,
            "links": {
                "api_run": f"{base}/api/runs/{run_id}",
                "api_tests": f"{base}/api/runs/{run_id}/tests",
                "api_report_json": f"{base}/api/runs/{run_id}/report",
                "api_compare": f"{base}/api/compare-runs/{run_id}",
                "api_heatmap": f"{base}/api/heatmap/{run_id}",
                "report_pdf": f"{base}/api/download-report/{run_id}",
                "report_html": f"{base}/report/{run_id}",
                "dashboard": f"{base}/dashboard",
            },
        }
        ok_wh, code, err_wh = send_run_completed_webhook(
            webhook_url,
            wh_payload,
            timeout_sec=config.WEBHOOK_TIMEOUT_SEC,
        )
        response_body["integrations"]["webhook"] = {
            "attempted": True,
            "success": ok_wh,
            "http_status": code,
            "error": err_wh or None,
        }

    if progress:
        progress("persist", 1, 1, "", None)

    return response_body
