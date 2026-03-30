"""Heuristic user-flow and enterprise test definitions from crawl data."""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from services.crawler import PageSnapshot


def _page_pairs(crawl: Dict[str, Any]) -> Tuple[List[str], List[float]]:
    urls: List[str] = []
    times: List[float] = []
    for p in crawl.get("pages") or []:
        if isinstance(p, PageSnapshot):
            if p.error:
                continue
            urls.append(p.url)
            times.append(float(p.load_time_ms or 0))
        elif isinstance(p, dict):
            if p.get("error"):
                continue
            urls.append(str(p.get("url", "")))
            times.append(float(p.get("load_time_ms", 0) or 0))
    return urls, times


def build_enterprise_tests(url: str, crawl: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Industry-practice tests: flows, navigation, validation, security, responsiveness, performance."""
    base = url.split("#")[0].rstrip("/")
    urls, load_times = _page_pairs(crawl)

    tests: List[Dict[str, Any]] = []

    # User flows (E2E-style single test case each; executor runs full sequence)
    tests.append(
        {
            "name": "User flow: Login journey (discover → credentials → submit)",
            "title": "User flow: Login journey",
            "category": "Functional",
            "priority": "Critical",
            "page": base,
            "steps": [
                f"Open {base}",
                "Find login/sign-in entry point",
                "Enter synthetic credentials where fields exist",
                "Submit and verify navigation or inline validation (no hard crash)",
            ],
            "expected_result": "Flow progresses without fatal error; URL or DOM reflects auth attempt",
            "action": {"kind": "user_flow", "url": base, "start_url": base, "flow_type": "login"},
        }
    )
    tests.append(
        {
            "name": "User flow: Signup / register journey",
            "title": "User flow: Signup journey",
            "category": "Functional",
            "priority": "High",
            "page": base,
            "steps": [
                f"Open {base}",
                "Open register/sign-up path",
                "Fill minimal safe fields and observe validation",
            ],
            "expected_result": "Signup path reachable; validation or confirmation without crash",
            "action": {"kind": "user_flow", "url": base, "start_url": base, "flow_type": "signup"},
        }
    )
    tests.append(
        {
            "name": "User flow: Search → results",
            "title": "User flow: Search",
            "category": "Functional",
            "priority": "High",
            "page": base,
            "steps": ["Locate search control", "Enter query", "Trigger search (enter or button)", "Verify DOM change or navigation"],
            "expected_result": "Search executes without error; results area or URL updates",
            "action": {"kind": "user_flow", "url": base, "start_url": base, "flow_type": "search"},
        }
    )
    tests.append(
        {
            "name": "User flow: Primary form submission with retained data",
            "title": "User flow: Form submission",
            "category": "Functional",
            "priority": "High",
            "page": base,
            "steps": [
                "Fill first visible text/email fields",
                "Submit form",
                "Verify values were sent (navigation or message)",
            ],
            "expected_result": "Form accepts input and submit does not hard-fail",
            "action": {"kind": "user_flow", "url": base, "start_url": base, "flow_type": "generic_form"},
        }
    )

    # Navigation
    tests.append(
        {
            "name": "Navigation: primary menu / header internal links",
            "title": "Navigation: menu links",
            "category": "Navigation",
            "priority": "High",
            "page": base,
            "steps": ["Sample links inside header/nav", "Follow up to 6 internal URLs", "Assert each loads body"],
            "expected_result": "No broken internal navigation from menu sample",
            "action": {"kind": "nav_menu_internal_links_probe", "url": base, "max_links": 6},
        }
    )
    tests.append(
        {
            "name": "Navigation: footer links integrity",
            "title": "Navigation: footer links",
            "category": "Navigation",
            "priority": "Medium",
            "page": base,
            "steps": ["Collect footer / contentinfo links", "Visit internal targets"],
            "expected_result": "Footer internal links load without transport failure",
            "action": {"kind": "nav_footer_links_probe", "url": base, "max_links": 5},
        }
    )
    tests.append(
        {
            "name": "Navigation: breadcrumb controls",
            "title": "Navigation: breadcrumbs",
            "category": "Navigation",
            "priority": "Low",
            "page": base,
            "steps": ["Detect breadcrumb trail if present", "Interact first navigable crumb"],
            "expected_result": "Breadcrumb interaction does not error or is N/A",
            "action": {"kind": "nav_breadcrumb_probe", "url": base},
        }
    )
    tests.append(
        {
            "name": "Navigation: browser back + refresh stability",
            "title": "Navigation: back & refresh",
            "category": "Navigation",
            "priority": "High",
            "page": base,
            "steps": ["Load page", "Navigate internally", "history.back()", "refresh()", "check body"],
            "expected_result": "Back and refresh leave page usable",
            "action": {"kind": "browser_back_refresh_probe", "url": base},
        }
    )

    # Validation
    tests.append(
        {
            "name": "Validation: empty required-style form submit",
            "title": "Validation: empty submit",
            "category": "Validation",
            "priority": "High",
            "page": base,
            "steps": ["Focus first form", "Submit without filling"],
            "expected_result": "Browser or app blocks or warns; no uncaught exception",
            "action": {"kind": "form_empty_submit_probe", "url": base},
        }
    )
    tests.append(
        {
            "name": "Validation: invalid phone pattern",
            "title": "Validation: phone format",
            "category": "Validation",
            "priority": "Medium",
            "page": base,
            "steps": ["Find tel input if any", "Enter invalid pattern"],
            "expected_result": "Invalid tel flagged or rejected",
            "action": {"kind": "form_invalid_phone_probe", "url": base},
        }
    )
    tests.append(
        {
            "name": "Validation: min/max length boundary on first text field",
            "title": "Validation: length boundary",
            "category": "Validation",
            "priority": "Medium",
            "page": base,
            "steps": ["Type very long string into first text input", "Observe truncation or validity"],
            "expected_result": "Excessive length handled without crash",
            "action": {"kind": "form_boundary_length_probe", "url": base},
        }
    )
    tests.append(
        {
            "name": "Validation: special characters in input",
            "title": "Validation: special chars",
            "category": "Validation",
            "priority": "Medium",
            "page": base,
            "steps": ["Enter unicode/symbol string"],
            "expected_result": "Value accepted or safely rejected",
            "action": {"kind": "form_special_chars_probe", "url": base},
        }
    )

    # Edge / negative
    tests.append(
        {
            "name": "Edge: oversized payload in first text field",
            "title": "Edge: long string",
            "category": "Functional",
            "priority": "Medium",
            "page": base,
            "steps": ["Send 4000+ character string"],
            "expected_result": "Page remains responsive",
            "action": {"kind": "edge_long_string_probe", "url": base},
        }
    )
    tests.append(
        {
            "name": "Security: XSS-like string neutralization in DOM",
            "title": "Security: XSS probe",
            "category": "Security",
            "priority": "Critical",
            "page": base,
            "steps": ["Inject script tag string into first text input", "Submit or blur", "Inspect DOM safety"],
            "expected_result": "No script execution indicator; page stable",
            "action": {"kind": "edge_xss_string_probe", "url": base},
        }
    )
    tests.append(
        {
            "name": "Security: SQLi pattern in search/input",
            "title": "Security: SQLi probe",
            "category": "Security",
            "priority": "High",
            "page": base,
            "steps": ["Enter classic SQLi test string"],
            "expected_result": "Application does not white-screen; error handled",
            "action": {"kind": "edge_sqli_string_probe", "url": base},
        }
    )
    tests.append(
        {
            "name": "Security: HTTPS in address bar",
            "title": "Security: HTTPS",
            "category": "Security",
            "priority": "Critical",
            "page": base,
            "steps": [f"Open {base}", "Assert scheme"],
            "expected_result": "Page served over https",
            "action": {"kind": "security_https_check", "url": base},
        }
    )
    tests.append(
        {
            "name": "Security: baseline security headers (meta/CSP hint)",
            "title": "Security: headers hint",
            "category": "Security",
            "priority": "Medium",
            "page": base,
            "steps": ["Check meta CSP / X-UA / referrer-policy hints in HTML"],
            "expected_result": "At least one hardening signal or informational pass",
            "action": {"kind": "security_headers_meta_probe", "url": base},
        }
    )

    # Accessibility aggregate
    tests.append(
        {
            "name": "Accessibility: WCAG-style composite score",
            "title": "Accessibility: composite score",
            "category": "Accessibility",
            "priority": "High",
            "page": base,
            "steps": ["Images alt ratio", "input names", "focusables", "sample contrast"],
            "expected_result": "Composite a11y score ≥ threshold",
            "action": {"kind": "a11y_wcag_aggregate_score", "url": base, "min_score": 55.0},
        }
    )

    # Responsiveness
    tests.append(
        {
            "name": "Responsiveness: mobile / tablet / desktop layout",
            "title": "Responsiveness: viewports",
            "category": "UI/UX",
            "priority": "High",
            "page": base,
            "steps": ["375×812", "768×1024", "1280×720", "check horizontal overflow"],
            "expected_result": "No severe horizontal scroll break at sampled sizes",
            "action": {"kind": "responsive_multi_viewport_probe", "url": base},
        }
    )

    # Performance
    tests.append(
        {
            "name": "Performance: navigation timing (TTFB proxy)",
            "title": "Performance: TTFB proxy",
            "category": "Performance",
            "priority": "High",
            "page": base,
            "steps": ["Navigation Timing API responseStart - fetchStart"],
            "expected_result": "TTFB under generous SLA or documented",
            "action": {"kind": "performance_navigation_timing", "url": base, "max_ttfb_ms": 3500},
        }
    )
    tests.append(
        {
            "name": "Performance: repeated load stability (light load)",
            "title": "Performance: multi-visit",
            "category": "Performance",
            "priority": "Medium",
            "page": base,
            "steps": ["Sequential GET ×3", "Compare durations"],
            "expected_result": "All loads complete; variance bounded",
            "action": {"kind": "performance_multi_load_probe", "url": base, "visits": 3},
        }
    )
    if urls and load_times:
        tests.append(
            {
                "name": "Performance: slowest crawled page re-validation",
                "title": "Performance: slowest page",
                "category": "Performance",
                "priority": "Medium",
                "page": urls[load_times.index(max(load_times))] if load_times else base,
                "steps": ["Re-open slowest URL from crawl", "Measure fresh navigation"],
                "expected_result": "Page still reachable; timing recorded",
                "action": {
                    "kind": "performance_slowest_page_revalidate",
                    "url": base,
                    "urls": urls,
                    "load_times_ms": load_times,
                },
            }
        )

    return tests
