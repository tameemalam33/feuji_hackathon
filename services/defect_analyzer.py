"""Rule-based defect classification, root cause, and remediation hints."""
from __future__ import annotations

from typing import Any, Dict, List


def analyze_result(row: Dict[str, Any]) -> Dict[str, Any]:
    """Return severity, root_cause, and ai_suggestion for a single test result."""
    status = row.get("status", "")
    actual = (row.get("actual") or "").lower()
    err = (row.get("error_kind") or "").lower()
    name = (row.get("name") or "").lower()
    kind = (row.get("action_kind") or "").lower()
    cat = (row.get("category") or "").lower()

    if status == "passed":
        return {
            "severity": "None",
            "root_cause": "N/A",
            "ai_suggestion": "No action required.",
        }

    def rc_interaction() -> str:
        return "Element overlapped or hidden"

    def rc_network() -> str:
        return "Slow page load or JS delay"

    def rc_validation() -> str:
        return "Missing input validation"

    def rc_security() -> str:
        return "Security control or safe-handling gap (HTTPS, headers, injection handling)."

    def rc_a11y() -> str:
        return "Accessibility markup or keyboard support insufficient."

    def rc_nav() -> str:
        return "Navigation, routing, or history behavior."

    def rc_layout() -> str:
        return "Layout / responsive / viewport rendering."

    if kind == "api_ui_network_probe" and status == "failed":
        return {
            "severity": "High",
            "root_cause": "Backend API returned HTTP 5xx or network failure after UI action.",
            "ai_suggestion": "Open DevTools Network: identify failing XHR/fetch, verify auth/session, and check service logs.",
        }

    if kind == "assert_password_field" and status == "failed":
        return {
            "severity": "Medium",
            "root_cause": "Expected password field not visible on auth-style page.",
            "ai_suggestion": "Confirm login route markup; check for SSO overlay hiding fields or conditional rendering.",
        }

    if kind == "user_flow":
        return {
            "severity": "High",
            "root_cause": "End-to-end user journey blocked or incomplete.",
            "ai_suggestion": "Trace the full journey in staging: entry link, form fields, submit, and post-submit URL/DOM.",
        }

    if kind == "button_click_probe" and (
        "not clickable" in actual or "intercepted" in actual or "not interactable" in actual
    ):
        return {
            "severity": "Critical",
            "root_cause": rc_interaction(),
            "ai_suggestion": "Button is blocked or not interactable — check overlays, z-index, disabled state, "
            "and scroll the element into view before interaction.",
        }

    if kind == "link_click_probe" and ("not clickable" in actual or "intercepted" in actual):
        return {
            "severity": "Critical",
            "root_cause": rc_interaction(),
            "ai_suggestion": "Primary navigation control failed — inspect overlapping UI, cookie banners, and "
            "pointer-events on ancestors.",
        }

    if err == "timeout" or "timeout" in actual:
        return {
            "severity": "High",
            "root_cause": rc_network(),
            "ai_suggestion": "Investigate slow resources, third-party scripts, or network latency. "
            "Consider lazy-loading assets and reducing render-blocking JavaScript.",
        }

    if kind in (
        "input_validation_probe",
        "form_empty_submit_probe",
        "form_invalid_phone_probe",
        "form_boundary_length_probe",
        "form_special_chars_probe",
    ) and status == "failed":
        return {
            "severity": "High",
            "root_cause": rc_validation(),
            "ai_suggestion": "Align HTML5 constraints, visible error copy, and server-side validation rules.",
        }

    if "validation" in name or (kind == "input_type_probe" and "email" in actual and "invalid" in actual):
        return {
            "severity": "High",
            "root_cause": rc_validation(),
            "ai_suggestion": "Tighten client-side and server-side validation for user inputs; "
            "align input type, pattern, and API contracts.",
        }

    if kind in (
        "edge_xss_string_probe",
        "edge_sqli_string_probe",
        "security_https_check",
        "security_headers_meta_probe",
    ):
        return {
            "severity": "Critical" if "https" in kind or "xss" in kind else "High",
            "root_cause": rc_security(),
            "ai_suggestion": "Review CSP, encoding, HTTPS redirects, ORM/query usage, and output escaping.",
        }

    if kind in (
        "nav_menu_internal_links_probe",
        "nav_footer_links_probe",
        "nav_breadcrumb_probe",
        "browser_back_refresh_probe",
    ):
        return {
            "severity": "High",
            "root_cause": rc_nav(),
            "ai_suggestion": "Verify internal routes, SPA history integration, and link href integrity.",
        }

    if kind in ("assert_viewport_content", "responsive_multi_viewport_probe", "resize", "scroll_bottom", "scroll_top", "assert_body"):
        return {
            "severity": "Medium",
            "root_cause": rc_layout(),
            "ai_suggestion": "Verify CSS breakpoints, overflow, stacking context, and mobile-first layout.",
        }

    if kind in ("performance_navigation", "performance_navigation_timing", "performance_multi_load_probe") or "navigation_ms" in actual:
        return {
            "severity": "High",
            "root_cause": rc_network(),
            "ai_suggestion": "Page load exceeded threshold — profile network waterfall, caching, and bundle size.",
        }

    if kind in ("a11y_images_alt", "a11y_input_names", "a11y_headings", "a11y_wcag_aggregate_score", "a11y_tab_focus"):
        return {
            "severity": "Medium",
            "root_cause": rc_a11y(),
            "ai_suggestion": "Improve ARIA, labels, alt text, focus order, and contrast per WCAG guidance.",
        }

    if cat == "accessibility":
        return {
            "severity": "Medium",
            "root_cause": rc_a11y(),
            "ai_suggestion": "Run dedicated axe/WAVE audit and fix reported violations.",
        }

    if "no link at index" in actual or "no button at index" in actual or "no input at index" in actual:
        return {
            "severity": "Low",
            "root_cause": "DOM drift vs crawl snapshot.",
            "ai_suggestion": "DOM changed vs crawl snapshot or dynamic list rendering. "
            "Re-run crawl or stabilize selectors with data-testid attributes.",
        }

    if "images" in name or "alt" in actual:
        return {
            "severity": "Low",
            "root_cause": rc_a11y(),
            "ai_suggestion": "Add descriptive alt text for informative images; use alt=\"\" for decorative images.",
        }

    return {
        "severity": "Medium",
        "root_cause": "Unclassified failure — requires manual reproduction.",
        "ai_suggestion": "Review failing step, reproduce manually, and capture network/console logs for the affected page.",
    }


def enrich_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for r in results:
        a = analyze_result(r)
        x = dict(r)
        x["severity"] = a["severity"]
        x["suggestion"] = a["ai_suggestion"]
        x["root_cause"] = a["root_cause"]
        out.append(x)
    return out
