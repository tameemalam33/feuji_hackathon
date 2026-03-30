"""Health score, coverage, insights, and chart helpers for QA runs."""
from __future__ import annotations

import re
from collections import Counter
from typing import Any, Dict, List, Optional, Set, Tuple

import config


def _clamp01(x: float) -> float:
    return max(0.0, min(100.0, x))


def performance_score_from_load_times_ms(load_times: List[float]) -> float:
    """Map average page load (ms) to 0–100 (faster is better)."""
    if not load_times:
        return 70.0
    avg = sum(load_times) / len(load_times)
    good, bad = float(config.PERF_SCORE_GOOD_MS), float(config.PERF_SCORE_BAD_MS)
    if avg <= good:
        return 100.0
    if avg >= bad:
        return 0.0
    return _clamp01(100.0 - ((avg - good) / (bad - good)) * 100.0)


def category_pass_rate(results: List[Dict[str, Any]], category: str) -> float:
    cat_l = (category or "").lower()
    rows = [r for r in results if (r.get("category") or "").lower() == cat_l]
    if not rows:
        return 0.0
    passed = sum(1 for r in rows if r.get("status") == "passed")
    return 100.0 * passed / len(rows)


def failure_severity_quality_score(results: List[Dict[str, Any]]) -> float:
    """
    0–100 quality score from failure severities (higher = less damaging failures).
    Used as 30% weight in health_score.
    """
    failed = [r for r in results if r.get("status") == "failed"]
    if not failed:
        return 100.0
    weights = {"Critical": 18, "High": 11, "Medium": 6, "Low": 3, "None": 4}
    raw = sum(weights.get(str(r.get("severity") or "Medium"), 7) for r in failed)
    norm = raw / max(len(failed) ** 0.85, 1.0)
    penalty = min(100.0, norm * 2.15)
    return max(0.0, 100.0 - penalty)


def compute_health_score(
    pass_rate: float,
    severity_quality_score: float,
    performance_score: float,
) -> float:
    """health = pass_rate*0.5 + severity_quality*0.3 + performance*0.2"""
    h = pass_rate * 0.5 + severity_quality_score * 0.3 + performance_score * 0.2
    return round(_clamp01(h), 2)


def heatmap_failures_by_page(test_cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Failures per page with severity band for UI heatmap."""
    counts: Dict[str, int] = {}
    weights: Dict[str, float] = {}
    sev_map = {"Critical": 4.0, "High": 3.0, "Medium": 2.0, "Low": 1.0, "None": 1.0}
    for t in test_cases:
        if t.get("status") != "failed":
            continue
        p = (t.get("page") or "").strip() or "unknown"
        counts[p] = counts.get(p, 0) + 1
        sr = str(t.get("severity") or "Medium")
        weights[p] = weights.get(p, 0.0) + sev_map.get(sr, 2.0)
    rows: List[Dict[str, Any]] = []
    for page, n in sorted(counts.items(), key=lambda x: (-x[1], x[0])):
        w = weights.get(page, 0.0)
        band = "high" if w >= 8 else "medium" if w >= 4 else "low"
        rows.append(
            {
                "page": page,
                "failures": n,
                "severity_weight": round(w, 2),
                "band": band,
            }
        )
    return rows


def compare_runs_extended(
    prev_run: Dict[str, Any],
    cur_run: Dict[str, Any],
    prev_tests: List[Dict[str, Any]],
    cur_tests: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Rich regression payload: deltas for pass rate, coverage, performance + improvements/regressions."""
    prev_id = prev_run.get("id")
    prev_failed = int(prev_run.get("failed") or 0)
    cur_failed = int(cur_run.get("failed") or 0)
    delta = cur_failed - prev_failed

    def _sig(t: Dict[str, Any]) -> str:
        return compare_runs_issue_signature(t)

    prev_s = {_sig(t) for t in prev_tests if t.get("status") == "failed"}
    cur_s = {_sig(t) for t in cur_tests if t.get("status") == "failed"}

    def _detail(sig: str, pool: List[Dict[str, Any]]) -> Dict[str, Any]:
        for t in pool:
            if t.get("status") == "failed" and _sig(t) == sig:
                return {
                    "test_id": t.get("test_id"),
                    "name": t.get("name"),
                    "category": t.get("category"),
                    "severity": t.get("severity"),
                }
        return {"test_id": "", "name": sig, "category": "", "severity": ""}

    new_sigs = cur_s - prev_s
    fixed_sigs = prev_s - cur_s
    regressions = [_detail(s, cur_tests) for s in sorted(new_sigs)]
    improvements = [_detail(s, prev_tests) for s in sorted(fixed_sigs)]

    pt = float(prev_run.get("success_rate") or 0)
    ct = float(cur_run.get("success_rate") or 0)
    pcov = float(prev_run.get("coverage") or 0) if prev_run.get("coverage") is not None else None
    ccov = float(cur_run.get("coverage") or 0) if cur_run.get("coverage") is not None else None
    pperf = float(prev_run.get("performance_score") or 0) if prev_run.get("performance_score") is not None else None
    cperf = float(cur_run.get("performance_score") or 0) if cur_run.get("performance_score") is not None else None

    return {
        "previous_run_id": prev_id,
        "previous_failed": prev_failed,
        "current_failed": cur_failed,
        "delta": delta,
        "new_issues": regressions,
        "fixed_issues": improvements,
        "regressions": regressions,
        "improvements": improvements,
        "pass_rate": {"previous": round(pt, 2), "current": round(ct, 2), "delta": round(ct - pt, 2)},
        "coverage": {
            "previous": round(pcov, 2) if pcov is not None else None,
            "current": round(ccov, 2) if ccov is not None else None,
            "delta": round(ccov - pcov, 2) if pcov is not None and ccov is not None else None,
        },
        "performance_score": {
            "previous": round(pperf, 2) if pperf is not None else None,
            "current": round(cperf, 2) if cperf is not None else None,
            "delta": round(cperf - pperf, 2) if pperf is not None and cperf is not None else None,
        },
    }


def element_action_key(action: Dict[str, Any]) -> Optional[Tuple[str, str, int]]:
    kind = action.get("kind")
    url = (action.get("url") or "").split("#")[0].rstrip("/")
    if kind == "link_click_probe":
        return (url, "link", int(action.get("index", 0)))
    if kind == "button_click_probe":
        return (url, "button", int(action.get("index", 0)))
    if kind in ("input_type_probe", "input_validation_probe"):
        return (url, "input", int(action.get("index", 0)))
    if kind == "form_present":
        return (url, "form", int(action.get("index", 0)))
    return None


def discovered_element_keys(elements: List[Dict[str, Any]]) -> Set[Tuple[str, str, int]]:
    keys: Set[Tuple[str, str, int]] = set()
    for el in elements:
        t = el.get("type")
        meta = el.get("meta") or {}
        if meta.get("broken"):
            continue
        if t not in ("link", "button", "input", "form"):
            continue
        if meta.get("strategy") != "tag_index":
            continue
        pu = (el.get("page_url") or "").split("#")[0].rstrip("/")
        idx = int(meta.get("index", 0))
        keys.add((pu, str(t), idx))
    return keys


def covered_keys_from_tests(test_cases: List[Dict[str, Any]]) -> Set[Tuple[str, str, int]]:
    covered: Set[Tuple[str, str, int]] = set()
    for tc in test_cases:
        action = tc.get("action") or {}
        k = element_action_key(action)
        if k:
            covered.add(k)
    return covered


def compute_coverage(
    elements: List[Dict[str, Any]],
    test_cases: List[Dict[str, Any]],
) -> Tuple[float, int, int, List[str]]:
    discovered = discovered_element_keys(elements)
    covered = covered_keys_from_tests(test_cases)
    total = len(discovered)
    tested = len(discovered & covered)
    if total <= 0:
        return 100.0, 0, 0, []
    pct = round((tested / total) * 100.0, 2)
    untested_keys = discovered - covered
    samples: List[str] = []
    for el in elements:
        meta = el.get("meta") or {}
        if meta.get("broken"):
            continue
        t = el.get("type")
        if t not in ("link", "button", "input", "form") or meta.get("strategy") != "tag_index":
            continue
        pu = (el.get("page_url") or "").split("#")[0].rstrip("/")
        idx = int(meta.get("index", 0))
        if (pu, str(t), idx) in untested_keys:
            label = (el.get("text") or t)[:80]
            samples.append(f"{t}[{idx}] on {pu} — {label}")
            if len(samples) >= 25:
                break
    return pct, tested, total, samples


def severity_distribution(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    failed = [r for r in results if r.get("status") == "failed"]
    c = Counter((r.get("severity") or "Medium") for r in failed)
    order = ["Critical", "High", "Medium", "Low"]
    labels = order + [k for k in sorted(c.keys()) if k not in order and k != "None"]
    data = [float(c.get(lbl, 0)) for lbl in labels]
    return {"labels": labels, "data": data}


def _parse_missing_alt_count(actual: str) -> Optional[int]:
    m = re.search(r"missing_alt[~=]*(\d+)", (actual or "").lower())
    if m:
        return int(m.group(1))
    return None


def build_insights(results: List[Dict[str, Any]]) -> List[str]:
    failed = [r for r in results if r.get("status") == "failed"]
    if not failed:
        return ["All executed checks passed for this run."]

    lines: List[str] = []
    by_sev = Counter((r.get("severity") or "Medium") for r in failed)
    for sev in ("Critical", "High", "Medium", "Low"):
        n = by_sev.get(sev, 0)
        if n:
            lines.append(f"{n} {sev} issue(s) detected.")

    flow_fails = [
        r
        for r in failed
        if (r.get("action_kind") == "user_flow")
        or ("user flow" in (r.get("name") or "").lower())
        or ("flow:" in (r.get("name") or "").lower())
    ]
    if len(flow_fails) >= 2:
        lines.append("Multiple failures in user flows (e.g. login, signup, search, or checkout-style forms).")
    elif len(flow_fails) == 1:
        lines.append(f"User flow regression: {flow_fails[0].get('name', 'flow test')}.")

    nav_fails = [r for r in failed if "nav_" in str(r.get("action_kind") or "")]
    if len(nav_fails) >= 3:
        lines.append("Navigation quality degraded: several menu, footer, or history checks failed.")

    val_fails = [r for r in failed if (r.get("category") or "").lower() == "validation"]
    if len(val_fails) >= 2:
        lines.append("Form validation appears weak: multiple validation or edge-case checks failed.")

    sec_fails = [r for r in failed if (r.get("category") or "").lower() == "security"]
    for r in sec_fails[:3]:
        lines.append(f"Security concern: {r.get('name', 'check')} — {(r.get('actual') or '')[:100]}")

    a11y_fails = [r for r in failed if (r.get("category") or "").lower() == "accessibility"]
    alt_miss_total = 0
    for r in a11y_fails:
        n = _parse_missing_alt_count(r.get("actual") or "")
        if n is not None:
            alt_miss_total = max(alt_miss_total, n)
    if alt_miss_total >= 5:
        lines.append(f"Many images may lack usable alt text (approx. {alt_miss_total}+ flagged in probes).")
    elif a11y_fails and any("a11y" in (r.get("action_kind") or "") for r in a11y_fails):
        lines.append("Accessibility composite or WCAG-style checks fell below threshold.")

    top = sorted(failed, key=lambda r: (_sev_rank(r.get("severity")), r.get("name", "")))[:5]
    for r in top:
        name = (r.get("name") or "Unnamed test").strip()
        act = (r.get("actual") or "")[:120]
        lines.append(f"- {name}" + (f": {act}" if act else ""))
    return lines


def build_performance_breakdown(
    crawl_load_times: List[float],
    perf_score: float,
    results: List[Dict[str, Any]],
) -> Dict[str, Any]:
    slowest_ms = max(crawl_load_times) if crawl_load_times else 0.0
    avg_ms = sum(crawl_load_times) / len(crawl_load_times) if crawl_load_times else 0.0
    ttfb_samples: List[float] = []
    for r in results:
        if r.get("action_kind") != "performance_navigation_timing":
            continue
        m = re.search(r"ttfb_ms=(\d+)", r.get("actual") or "")
        if m:
            ttfb_samples.append(float(m.group(1)))
    avg_ttfb = sum(ttfb_samples) / len(ttfb_samples) if ttfb_samples else None
    return {
        "crawl_avg_load_ms": round(avg_ms, 2),
        "crawl_slowest_ms": round(slowest_ms, 2),
        "performance_score": round(perf_score, 2),
        "measured_avg_ttfb_ms": round(avg_ttfb, 2) if avg_ttfb is not None else None,
    }


def flows_tested_summary(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for r in results:
        if r.get("action_kind") != "user_flow":
            continue
        name = r.get("name") or "Flow"
        flow_type = r.get("flow_type")
        if not flow_type:
            nl = (name or "").lower()
            if "login" in nl:
                flow_type = "login"
            elif "signup" in nl or "register" in nl:
                flow_type = "signup"
            elif "search" in nl:
                flow_type = "search"
            elif "form" in nl:
                flow_type = "generic_form"
            else:
                flow_type = "unknown"
        out.append(
            {
                "name": name,
                "flow_type": flow_type,
                "status": r.get("status"),
                "page": r.get("page") or "",
            }
        )
    return out


def _sev_rank(s: Optional[str]) -> int:
    order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3, "None": 9}
    return order.get(s or "", 4)


def compare_runs_issue_signature(test_row: Dict[str, Any]) -> str:
    tid = test_row.get("test_id") or test_row.get("id") or ""
    name = test_row.get("name") or ""
    cat = test_row.get("category") or ""
    return f"{tid}|{name}|{cat}"


def risk_label_from_results(results: List[Dict[str, Any]]) -> str:
    failed = [r for r in results if r.get("status") == "failed"]
    if any((r.get("severity") or "") == "Critical" for r in failed):
        return "High"
    if sum(1 for r in failed if (r.get("severity") or "") == "High") >= 2:
        return "Medium"
    if failed:
        return "Medium"
    return "Low"


def critical_path_coverage_pct(crawl: Dict[str, Any], results: List[Dict[str, Any]]) -> float:
    """Share of AUTH/FORM/DASHBOARD URLs with at least one passing test."""
    pages = crawl.get("pages") or []
    critical_urls: List[str] = []
    for p in pages:
        pc = getattr(p, "page_class", None) if not isinstance(p, dict) else p.get("page_class")
        u = getattr(p, "url", None) if not isinstance(p, dict) else p.get("url")
        if not u:
            continue
        if (pc or "") in ("AUTH", "FORM", "DASHBOARD"):
            critical_urls.append(str(u).split("#")[0].rstrip("/"))
    if not critical_urls:
        return round(
            100.0
            * sum(1 for r in results if r.get("status") == "passed")
            / max(len(results), 1),
            2,
        )
    ok = 0
    for cu in set(critical_urls):
        base = cu.split("#")[0].rstrip("/")
        if any(
            (r.get("status") == "passed")
            and str(r.get("page") or "").split("#")[0].rstrip("/") == base
            for r in results
        ):
            ok += 1
    return round(100.0 * ok / max(len(set(critical_urls)), 1), 2)


def build_advanced_analytics(
    results: List[Dict[str, Any]],
    crawl: Dict[str, Any],
    previous_success_rate: Optional[float] = None,
) -> Dict[str, Any]:
    fail_pages: Counter[str] = Counter()
    fail_comp: Counter[str] = Counter()
    cat_totals: Counter[str] = Counter()
    for r in results:
        cat = (r.get("category") or "functional").lower()
        cat_totals[cat] += 1
        if r.get("status") != "failed":
            continue
        pu = (r.get("page") or "unknown").split("#")[0].rstrip("/")
        fail_pages[pu] += 1
        comp = (r.get("component") or "").strip()
        if comp:
            fail_comp[comp] += 1

    mfp = fail_pages.most_common(1)[0][0] if fail_pages else ""
    mpc = fail_comp.most_common(1)[0][0] if fail_comp else ""

    pages = crawl.get("pages") or []
    visited = len(pages)
    discovered = int(crawl.get("total_pages_discovered") or 0)
    load_times = list(crawl.get("load_times_ms") or [])
    urls: List[str] = []
    for p in pages:
        urls.append(str(getattr(p, "url", "") or (p.get("url") if isinstance(p, dict) else "") or ""))
    slowest = ""
    if load_times and urls:
        n = min(len(load_times), len(urls))
        if n > 0:
            imax = max(range(n), key=lambda j: load_times[j])
            slowest = urls[imax] or ""

    passed = sum(1 for r in results if r.get("status") == "passed")
    total = max(len(results), 1)
    cur_rate = 100.0 * passed / total

    return {
        "most_failing_page": mfp,
        "most_problematic_component": mpc,
        "slowest_page_url": slowest,
        "pages_tested": visited,
        "pages_discovered": max(discovered, visited),
        "tests_per_category": {k: int(cat_totals[k]) for k in sorted(cat_totals.keys())},
        "trend_comparison": {
            "previous_pass_rate_percent": round(previous_success_rate, 2)
            if previous_success_rate is not None
            else None,
            "current_pass_rate_percent": round(cur_rate, 2),
            "delta_percent_points": round(cur_rate - previous_success_rate, 2)
            if previous_success_rate is not None
            else None,
        },
    }
