"""Smart category-based test generation: page classification → focused cases (10–20/page)."""
from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional, Set, Tuple

import config
from services.crawler import PageSnapshot, _normalize_url
from services.flow_test_factory import build_enterprise_tests

PRIORITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}


def _depth_caps(depth: str) -> Tuple[int, bool]:
    """Returns (max_tests_per_page, include_non_critical)."""
    d = (depth or "standard").lower()
    if d == "quick":
        return (config.SMART_TESTS_PER_PAGE_QUICK, False)
    if d == "deep" or d == "full":
        return (config.SMART_TESTS_PER_PAGE_DEEP, True)
    return (config.SMART_TESTS_PER_PAGE_STANDARD, True)


def _dedupe_key(t: Dict[str, Any]) -> str:
    act = t.get("action") or {}
    parts = (
        str(t.get("page") or ""),
        str(act.get("kind") or ""),
        str(act.get("index", "")),
        str(act.get("flow_type") or ""),
        str(act.get("component") or ""),
    )
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:32]


def _wrap(
    *,
    user_story: str,
    scenario: str,
    test_type: str,
    category: str,
    priority: str,
    name: str,
    page: str,
    steps: List[str],
    expected_result: str,
    action: Dict[str, Any],
    component: str = "",
) -> Dict[str, Any]:
    action = dict(action)
    if component:
        action["component"] = component
    return {
        "user_story": user_story,
        "scenario": scenario,
        "test_type": test_type,
        "name": name,
        "title": name,
        "category": category,
        "priority": priority,
        "page": page,
        "steps": steps,
        "expected_result": expected_result,
        "action": action,
        "component": component,
    }


def _site_baseline(url: str, base: str, depth: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    cap_non_crit, include_all = _depth_caps(depth)
    out.append(
        _wrap(
            user_story="As a user, I need the site to load over a secure transport.",
            scenario="Verify HTTPS scheme for the entry URL.",
            test_type="Positive",
            category="security",
            priority="Critical",
            name="HTTPS: entry URL uses TLS",
            page=base,
            steps=[f"Open {base}", "Read window.location.protocol"],
            expected_result="Scheme is https:",
            action={"kind": "security_https_check", "url": base},
        )
    )
    out.append(
        _wrap(
            user_story="As a user, I expect the homepage to render without fatal errors.",
            scenario="Load root URL and confirm document is interactive.",
            test_type="Positive",
            category="functional",
            priority="Critical",
            name="Page load: document becomes available",
            page=base,
            steps=[f"Navigate to {base}"],
            expected_result="Body element present after navigation",
            action={"kind": "load_page", "url": base},
        )
    )
    out.append(
        _wrap(
            user_story="As QA, I want to correlate UI actions with network responses.",
            scenario="Capture XHR/fetch responses after navigation (no 5xx).",
            test_type="Positive",
            category="functional",
            priority="High",
            name="API/UI: network responses after load",
            page=base,
            steps=["Enable performance log", f"GET {base}", "Parse Network.* responses"],
            expected_result="No HTTP 5xx in captured API calls (or none captured)",
            action={"kind": "api_ui_network_probe", "url": base},
        )
    )
    if include_all:
        out.append(
            _wrap(
                user_story="As a user, I need a recognizable page title.",
                scenario="document.title is non-empty.",
                test_type="Positive",
                category="functional",
                priority="High",
                name="Document title is present",
                page=base,
                steps=["Read document.title"],
                expected_result="Title length > 0",
                action={"kind": "assert_title_present", "url": base},
            )
        )
        out.append(
            _wrap(
                user_story="As a user, I need acceptable first paint performance.",
                scenario="Navigation timing within SLA.",
                test_type="Positive",
                category="performance",
                priority="High",
                name="Performance: navigation timing budget",
                page=base,
                steps=["Measure load event duration"],
                expected_result="Load completes within configured SLA",
                action={"kind": "performance_navigation", "url": base, "max_ms": 20000},
            )
        )
        out.append(
            _wrap(
                user_story="As a user with assistive tech, images should expose text alternatives.",
                scenario="Sample img[alt] coverage.",
                test_type="Positive",
                category="accessibility",
                priority="Medium",
                name="Accessibility: image alt sampling",
                page=base,
                steps=["Enumerate first images", "Check alt presence"],
                expected_result="Majority of sampled images have alt",
                action={"kind": "a11y_images_alt", "url": base},
            )
        )
    if include_all and cap_non_crit >= 14:
        out.append(
            _wrap(
                user_story="As QA, I want baseline security hints in HTML.",
                scenario="Meta CSP / referrer-policy hints.",
                test_type="Positive",
                category="security",
                priority="Medium",
                name="Security: HTML hardening hints",
                page=base,
                steps=["Inspect head for CSP/meta hints"],
                expected_result="At least one hardening signal or informational pass",
                action={"kind": "security_headers_meta_probe", "url": base},
            )
        )
    return out


def _component_tests(page: str, base: str) -> List[Dict[str, Any]]:
    if _normalize_url(page) != _normalize_url(base):
        return []
    return [
        _wrap(
            user_story="As a user, I navigate using the primary header.",
            scenario="Header/nav internal links resolve.",
            test_type="Positive",
            category="functional",
            priority="High",
            name="Component: primary navigation links",
            page=page,
            steps=["Find header/nav anchors", "Follow internal samples"],
            expected_result="Sampled internal nav targets load body",
            action={"kind": "nav_menu_internal_links_probe", "url": page, "max_links": 5},
            component="navbar",
        ),
        _wrap(
            user_story="As a user, I use footer links for policies and contact.",
            scenario="Footer internal links resolve.",
            test_type="Positive",
            category="functional",
            priority="Medium",
            name="Component: footer links",
            page=page,
            steps=["Collect footer links", "Visit internal targets"],
            expected_result="Footer internal links load without transport failure",
            action={"kind": "nav_footer_links_probe", "url": page, "max_links": 4},
            component="footer",
        ),
    ]


def _class_tests_auth(page: str) -> List[Dict[str, Any]]:
    return [
        _wrap(
            user_story="As a returning user, I can attempt to sign in.",
            scenario="Discover login path and submit synthetic credentials.",
            test_type="Positive",
            category="functional",
            priority="Critical",
            name="Auth: login journey",
            page=page,
            steps=["Open page", "Locate login", "Enter synthetic credentials", "Submit"],
            expected_result="Flow completes without fatal error",
            action={"kind": "user_flow", "url": page, "start_url": page, "flow_type": "login"},
        ),
        _wrap(
            user_story="As QA, I want validation on empty auth forms.",
            scenario="Submit login form without filling fields.",
            test_type="Negative",
            category="validation",
            priority="High",
            name="Auth: empty submit behavior",
            page=page,
            steps=["Focus first form", "Submit without filling"],
            expected_result="Inline validation or safe rejection",
            action={"kind": "form_empty_submit_probe", "url": page},
        ),
        _wrap(
            user_story="As a user, password fields must be present for sign-in.",
            scenario="Password input exists when auth UI present.",
            test_type="Positive",
            category="functional",
            priority="High",
            name="Auth: password field presence",
            page=page,
            steps=["Query input[type=password]"],
            expected_result="At least one visible password field",
            action={"kind": "assert_password_field", "url": page},
        ),
    ]


def _class_tests_form(page: str) -> List[Dict[str, Any]]:
    return [
        _wrap(
            user_story="As a user, I submit forms with realistic data.",
            scenario="Fill first text fields and submit primary form.",
            test_type="Positive",
            category="functional",
            priority="High",
            name="Form: primary submission path",
            page=page,
            steps=["Fill visible text/email fields", "Submit"],
            expected_result="Submit does not hard-fail",
            action={"kind": "user_flow", "url": page, "start_url": page, "flow_type": "generic_form"},
        ),
        _wrap(
            user_story="As QA, I verify client-side validation.",
            scenario="Invalid email pattern in email field.",
            test_type="Negative",
            category="validation",
            priority="Medium",
            name="Form: email validation probe",
            page=page,
            steps=["Enter invalid email", "Observe validity"],
            expected_result="Invalid email flagged when type=email",
            action={"kind": "input_validation_probe", "url": page, "index": 0, "input_type": "email"},
        ),
        _wrap(
            user_story="As a user, form controls must be discoverable.",
            scenario="First form element exists in DOM.",
            test_type="Positive",
            category="functional",
            priority="Low",
            name="Form: container present",
            page=page,
            steps=["Locate form[0]"],
            expected_result="Form element exists",
            action={"kind": "form_present", "url": page, "index": 0},
        ),
    ]


def _class_tests_dashboard(page: str) -> List[Dict[str, Any]]:
    return [
        _wrap(
            user_story="As a user, I rely on interactive dashboard controls.",
            scenario="Count interactive nodes and ensure primary button responds.",
            test_type="Positive",
            category="functional",
            priority="Medium",
            name="Dashboard: interactive density",
            page=page,
            steps=["Count buttons/links/inputs"],
            expected_result="Reasonable number of interactive elements",
            action={"kind": "count_interactive", "url": page},
        ),
        _wrap(
            user_story="As a user, I scroll long dashboards.",
            scenario="Scroll to bottom and back.",
            test_type="Positive",
            category="performance",
            priority="Low",
            name="Dashboard: scroll stability",
            page=page,
            steps=["Scroll bottom", "Scroll top"],
            expected_result="No script errors during scroll",
            action={"kind": "scroll_bottom", "url": page},
        ),
        _wrap(
            user_story="As QA, I verify SPA history on app shells.",
            scenario="Back navigation after internal click.",
            test_type="Positive",
            category="functional",
            priority="Medium",
            name="Dashboard: history back smoke",
            page=page,
            steps=["Internal nav", "history.back()"],
            expected_result="Page remains usable",
            action={"kind": "browser_back_refresh_probe", "url": page},
        ),
    ]


def _class_tests_search(page: str) -> List[Dict[str, Any]]:
    return [
        _wrap(
            user_story="As a user, I run searches and see results.",
            scenario="Enter query and trigger search.",
            test_type="Positive",
            category="functional",
            priority="High",
            name="Search: query execution",
            page=page,
            steps=["Locate search", "Enter query", "Submit"],
            expected_result="URL or results region updates",
            action={"kind": "user_flow", "url": page, "start_url": page, "flow_type": "search"},
        ),
        _wrap(
            user_story="As QA, I want API health during search.",
            scenario="Network capture after search page load.",
            test_type="Positive",
            category="functional",
            priority="Medium",
            name="Search: API responses",
            page=page,
            steps=["Load page", "Inspect network log"],
            expected_result="No 5xx responses in captured calls",
            action={"kind": "api_ui_network_probe", "url": page},
        ),
    ]


def _class_tests_product(page: str) -> List[Dict[str, Any]]:
    return [
        _wrap(
            user_story="As a shopper, I interact with primary CTAs.",
            scenario="First visible button click probe.",
            test_type="Positive",
            category="functional",
            priority="High",
            name="Product: primary button reachable",
            page=page,
            steps=["Focus button[0]"],
            expected_result="Button exists and is clickable",
            action={"kind": "button_click_probe", "url": page, "index": 0},
        ),
        _wrap(
            user_story="As a shopper, I follow product navigation.",
            scenario="First internal link probe.",
            test_type="Positive",
            category="functional",
            priority="Medium",
            name="Product: primary link navigation",
            page=page,
            steps=["Click first internal anchor"],
            expected_result="Navigation completes",
            action={"kind": "link_click_probe", "url": page, "index": 0},
        ),
    ]


def _class_tests_static(page: str) -> List[Dict[str, Any]]:
    return [
        _wrap(
            user_story="As a user, I see content in the viewport.",
            scenario="Initial viewport has text or structure.",
            test_type="Positive",
            category="functional",
            priority="Medium",
            name="Static: viewport renders content",
            page=page,
            steps=["Measure viewport", "Sample body text length"],
            expected_result="Viewport has meaningful content",
            action={"kind": "assert_viewport_content", "url": page},
        ),
        _wrap(
            user_story="As a user, I can read semantic structure.",
            scenario="Heading outline sample.",
            test_type="Positive",
            category="accessibility",
            priority="Low",
            name="Static: headings outline",
            page=page,
            steps=["Count h1–h6"],
            expected_result="Headings exist or page is minimal",
            action={"kind": "a11y_headings", "url": page},
        ),
    ]


def _class_tests_error(page: str) -> List[Dict[str, Any]]:
    return [
        _wrap(
            user_story="As a user, error pages should still render safely.",
            scenario="Body exists on failed/error route.",
            test_type="Positive",
            category="functional",
            priority="Medium",
            name="Error page: body present",
            page=page,
            steps=["Load URL", "Check body"],
            expected_result="Body element exists",
            action={"kind": "assert_body", "url": page},
        ),
        _wrap(
            user_story="As QA, I verify error routes do not expose stack traces in title.",
            scenario="Title is short and user-facing.",
            test_type="Negative",
            category="security",
            priority="Low",
            name="Error page: title sanity",
            page=page,
            steps=["Read document.title"],
            expected_result="Title present and reasonable length",
            action={"kind": "assert_title_present", "url": page},
        ),
    ]


def _pick_class_templates(pc: str, page: str) -> List[Dict[str, Any]]:
    m = {
        "AUTH": _class_tests_auth,
        "FORM": _class_tests_form,
        "DASHBOARD": _class_tests_dashboard,
        "SEARCH": _class_tests_search,
        "PRODUCT": _class_tests_product,
        "ERROR": _class_tests_error,
        "STATIC": _class_tests_static,
    }
    fn = m.get(pc, _class_tests_static)
    return fn(page)


def _limited_element_tests(elements: List[Dict[str, Any]], per_page_cap: int) -> List[Dict[str, Any]]:
    """Add a small number of element-level probes (deduped by page)."""
    out: List[Dict[str, Any]] = []
    by_page: Dict[str, int] = {}
    for el in elements:
        if el.get("type") not in ("link", "button", "input"):
            continue
        meta = el.get("meta") or {}
        if meta.get("broken"):
            continue
        pu = el.get("page_url") or ""
        if by_page.get(pu, 0) >= per_page_cap:
            continue
        idx = int(meta.get("index", 0))
        et = el.get("type")
        if et == "link":
            out.append(
                _wrap(
                    user_story="As a user, I use in-content links.",
                    scenario=f"Link index {idx} is interactable.",
                    test_type="Positive",
                    category="functional",
                    priority="Medium",
                    name=f"Link probe [{idx}]",
                    page=pu,
                    steps=[f"On {pu}, exercise anchor {idx}"],
                    expected_result="Link exists and responds",
                    action={"kind": "link_click_probe", "url": pu, "index": idx},
                )
            )
        elif et == "button":
            out.append(
                _wrap(
                    user_story="As a user, I activate buttons.",
                    scenario=f"Button index {idx} is reachable.",
                    test_type="Positive",
                    category="functional",
                    priority="Medium",
                    name=f"Button probe [{idx}]",
                    page=pu,
                    steps=[f"Focus button {idx}"],
                    expected_result="Button clickable or safely skipped",
                    action={"kind": "button_click_probe", "url": pu, "index": idx},
                )
            )
        elif et == "input":
            it = (meta.get("input_type") or "text").lower()
            out.append(
                _wrap(
                    user_story="As a user, I enter data in fields.",
                    scenario=f"Input index {idx} accepts text.",
                    test_type="Positive",
                    category="functional",
                    priority="High",
                    name=f"Input probe [{idx}]",
                    page=pu,
                    steps=[f"Type into input {idx}"],
                    expected_result="Value accepted where applicable",
                    action={"kind": "input_type_probe", "url": pu, "index": idx, "input_type": it},
                )
            )
        by_page[pu] = by_page.get(pu, 0) + 1
    return out


def _sort_by_priority(tests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        tests,
        key=lambda t: (
            PRIORITY_ORDER.get(str(t.get("priority") or "Medium"), 2),
            str(t.get("page") or ""),
            str(t.get("name") or ""),
        ),
    )


def generate_test_cases(
    url: str,
    elements: List[Dict[str, Any]],
    crawl: Optional[Dict[str, Any]] = None,
    depth_mode: str = "standard",
) -> List[Dict[str, Any]]:
    crawl = crawl or {}
    base = _normalize_url(url.rstrip("/") or url)
    depth = (depth_mode or "standard").lower()
    max_per_page, include_non_crit = _depth_caps(depth)

    seen_keys: Set[str] = set()
    pool: List[Dict[str, Any]] = []

    for t in _site_baseline(url, base, depth):
        k = _dedupe_key(t)
        if k not in seen_keys:
            seen_keys.add(k)
            pool.append(t)

    pages: List[PageSnapshot] = list(crawl.get("pages") or [])
    visited_urls: Set[str] = set()

    for snap in pages:
        pu = _normalize_url(snap.url or "")
        if not pu or pu in visited_urls:
            continue
        visited_urls.add(pu)
        pc = getattr(snap, "page_class", None) or "STATIC"
        class_tests = _pick_class_templates(pc, pu)
        n = 0
        for t in class_tests:
            if n >= max_per_page:
                break
            if not include_non_crit and str(t.get("priority") or "") not in ("Critical", "High"):
                continue
            k = _dedupe_key(t)
            if k in seen_keys:
                continue
            seen_keys.add(k)
            pool.append(t)
            n += 1

        for ct in _component_tests(pu, base):
            if n >= max_per_page:
                break
            if not include_non_crit and str(ct.get("priority") or "") not in ("Critical", "High"):
                continue
            k = _dedupe_key(ct)
            if k in seen_keys:
                continue
            seen_keys.add(k)
            pool.append(ct)
            n += 1

    elem_cap = 2 if depth == "quick" else 3
    for t in _limited_element_tests(elements, elem_cap):
        k = _dedupe_key(t)
        if k in seen_keys:
            continue
        seen_keys.add(k)
        pool.append(t)

    if include_non_crit and depth != "quick":
        ent = build_enterprise_tests(url, crawl)
        ent_sorted = sorted(
            ent,
            key=lambda x: (PRIORITY_ORDER.get(str(x.get("priority") or "Medium"), 2), str(x.get("name", ""))),
        )
        ent_cap = 10 if depth == "standard" else 18
        for raw in ent_sorted[:ent_cap]:
            if raw.get("category") == "Navigation" and raw["action"].get("kind") == "nav_breadcrumb_probe":
                continue
            cat = raw.get("category") or "functional"
            tax = {
                "Functional": "functional",
                "Navigation": "functional",
                "UI/UX": "functional",
                "Validation": "validation",
                "Performance": "performance",
                "Security": "security",
                "Accessibility": "accessibility",
            }.get(cat, "functional")
            t = _wrap(
                user_story=f"Enterprise coverage: {raw.get('title', raw.get('name', ''))}",
                scenario=raw.get("title") or raw.get("name", ""),
                test_type="Positive",
                category=tax,
                priority=str(raw.get("priority") or "Medium"),
                name=str(raw.get("name", "")),
                page=str(raw.get("page") or base),
                steps=list(raw.get("steps") or []),
                expected_result=str(raw.get("expected_result") or ""),
                action=dict(raw.get("action") or {}),
            )
            if depth == "standard" and t["priority"] in ("Low",):
                continue
            k = _dedupe_key(t)
            if k in seen_keys:
                continue
            seen_keys.add(k)
            pool.append(t)

    pool = _sort_by_priority(pool)

    out: List[Dict[str, Any]] = []
    for idx, t in enumerate(pool, start=1):
        tc = {
            "id": f"TC-{idx:03d}",
            "name": t["name"],
            "title": t.get("title") or t["name"],
            "user_story": t.get("user_story", ""),
            "scenario": t.get("scenario", ""),
            "test_type": t.get("test_type", "Positive"),
            "category": t["category"],
            "priority": t["priority"],
            "page": t.get("page") or url,
            "steps": t["steps"],
            "expected_result": t["expected_result"],
            "action": t["action"],
            "component": t.get("component") or "",
        }
        out.append(tc)
    return out
