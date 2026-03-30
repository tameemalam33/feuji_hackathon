"""DOM- and URL-based page classification for category-driven test selection."""
from __future__ import annotations

from typing import Any, Dict
from urllib.parse import urlparse

from services.crawler import PageSnapshot

def _lower_url_path(url: str) -> str:
    try:
        p = urlparse(url)
        return f"{(p.path or '/').lower()} {p.query.lower()}"
    except Exception:
        return (url or "").lower()


def classify_page(snap: PageSnapshot) -> str:
    """
    Heuristic classification from crawl snapshot (DOM counts + URL signals).
    """
    if snap.error or snap.load_status == "failed":
        return "ERROR"

    path = _lower_url_path(snap.url or "")
    title = (snap.title or "").lower()

    auth_kw = (
        "login",
        "signin",
        "sign-in",
        "signup",
        "sign-up",
        "register",
        "auth",
        "oauth",
        "password",
        "account/create",
        "forgot-password",
        "reset-password",
    )
    if any(k in path for k in auth_kw) or any(k in title for k in ("login", "sign in", "sign up", "register")):
        return "AUTH"

    err_kw = ("404", "500", "error", "not-found", "unauthorized", "forbidden")
    if any(k in path for k in err_kw) or any(k in title for k in ("404", "not found", "error", "forbidden")):
        return "ERROR"

    search_kw = ("search", "query", "find", "results")
    if any(k in path for k in search_kw) or "search" in title:
        return "SEARCH"

    product_kw = ("/product", "/item", "/p/", "/shop", "/cart", "/checkout", "/pricing", "buy")
    if any(k in path for k in product_kw):
        return "PRODUCT"

    n_inputs = len(snap.inputs or [])
    n_forms = len(snap.forms or [])
    n_links = len(snap.links or [])
    n_btns = len(snap.buttons or [])

    has_password = any(
        (inp.get("type") or "").lower() == "password" for inp in (snap.inputs or [])
    )

    if has_password or (n_forms >= 1 and n_inputs >= 2 and n_links <= 25):
        return "AUTH"

    if n_forms >= 2 or n_inputs >= 6:
        return "FORM"

    # Dashboard: many interactive nodes + tables/charts hints in link text
    table_like = sum(
        1
        for ln in (snap.links or [])[:80]
        if any(
            w in (ln.get("text") or "").lower()
            for w in ("dashboard", "analytics", "report", "chart", "admin", "settings")
        )
    )
    if (n_links >= 18 or n_btns >= 12) and (table_like >= 1 or n_inputs >= 4):
        return "DASHBOARD"

    if n_links >= 35 and n_inputs <= 3 and n_forms <= 1:
        return "STATIC"

    if n_forms >= 1 or n_inputs >= 3:
        return "FORM"

    return "STATIC"


def classify_from_signals(signals: Dict[str, Any]) -> str:
    """Classify from a plain dict (for tests or JSON round-trips)."""
    snap = PageSnapshot(
        url=str(signals.get("url") or ""),
        title=str(signals.get("title") or ""),
        links=list(signals.get("links") or []),
        buttons=list(signals.get("buttons") or []),
        inputs=list(signals.get("inputs") or []),
        forms=list(signals.get("forms") or []),
        error=signals.get("error"),
        load_status=str(signals.get("load_status") or "success"),
    )
    return classify_page(snap)


def page_signals_summary(snap: PageSnapshot) -> Dict[str, Any]:
    return {
        "url": snap.url,
        "title": snap.title,
        "counts": {
            "links": len(snap.links or []),
            "buttons": len(snap.buttons or []),
            "inputs": len(snap.inputs or []),
            "forms": len(snap.forms or []),
        },
        "page_class": getattr(snap, "page_class", None) or classify_page(snap),
    }
