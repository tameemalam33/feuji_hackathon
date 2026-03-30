"""Multi-page site crawling with Selenium (headless Chrome)."""
from __future__ import annotations

import hashlib
import time
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

import config
from performance.analyzer import collect_window_performance
from performance.issues import detect_issues, map_suggestions
from performance.scorer import score_page


@dataclass
class PageSnapshot:
    url: str
    depth: int = 0
    priority: int = 50
    links: List[Dict[str, Any]] = field(default_factory=list)
    buttons: List[Dict[str, Any]] = field(default_factory=list)
    inputs: List[Dict[str, Any]] = field(default_factory=list)
    forms: List[Dict[str, Any]] = field(default_factory=list)
    page_class: str = "STATIC"
    title: str = ""
    content_hash: str = ""
    load_time_ms: float = 0.0
    error: Optional[str] = None
    load_status: str = "success"
    error_type: str = ""
    error_message: str = ""
    js_errors: List[str] = field(default_factory=list)
    performance: Dict[str, Any] = field(default_factory=dict)
    performance_score: float = 0.0
    perf_issues: List[Dict[str, str]] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


def create_chrome_driver() -> webdriver.Chrome:
    """Public factory for headless Chrome (shared with test executor)."""
    return _build_driver()


def _build_driver() -> webdriver.Chrome:
    opts = Options()
    opts.add_argument("--headless")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    # Make the browser look less like a default automation session.
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--lang=en-US,en")
    opts.add_argument("--blink-settings=imagesEnabled=false")
    opts.add_argument("--window-size=1920,1080")
    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.default_content_setting_values.notifications": 2,
    }
    try:
        opts.add_experimental_option("prefs", prefs)
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option("useAutomationExtension", False)
    except Exception:
        pass
    opts.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    try:
        opts.set_capability("goog:loggingPrefs", {"browser": "ALL", "performance": "ALL"})
    except Exception:
        pass
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    driver.set_page_load_timeout(config.SELENIUM_PAGE_LOAD_TIMEOUT)
    driver.set_script_timeout(config.SELENIUM_SCRIPT_TIMEOUT)
    driver.implicitly_wait(config.SELENIUM_IMPLICIT_WAIT)
    # Hide the most obvious webdriver fingerprint in case the site checks it.
    try:
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                    Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
                    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                """,
            },
        )
    except Exception:
        pass
    return driver


def _same_site(base: str, candidate: str) -> bool:
    try:
        b = urlparse(base)
        c = urlparse(candidate)
        return b.netloc == c.netloc
    except Exception:
        return False


def _is_crawlable_href(href: str) -> bool:
    h = (href or "").strip().lower()
    if not h or h.startswith("#"):
        return False
    if h.startswith("mailto:") or h.startswith("tel:") or h.startswith("javascript:"):
        return False
    blocked_ext = (
        ".pdf",
        ".zip",
        ".rar",
        ".7z",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".ppt",
        ".pptx",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".mp4",
        ".mov",
        ".avi",
        ".mkv",
    )
    if any(h.endswith(ext) for ext in blocked_ext):
        return False
    # We do NOT block login/auth routes (they're high priority),
    # but we do avoid obvious logout routes which can invalidate the session.
    if "logout" in h:
        return False
    if "?" in h:
        # Skip query-heavy links to avoid pagination/session loops.
        q = h.split("?", 1)[1]
        if len(q) > 25 or "&" in q or "id=" in q or "session" in q or "token" in q:
            return False
    return True


def _browser_js_errors(driver: webdriver.Chrome) -> List[str]:
    out: List[str] = []
    try:
        logs = driver.get_log("browser")
        for entry in logs[-30:]:
            lvl = str(entry.get("level") or "").upper()
            msg = str(entry.get("message") or "")
            if lvl in ("SEVERE", "ERROR"):
                out.append(msg[:400])
    except Exception:
        pass
    return out


def _normalize_url(url: str) -> str:
    """Strip fragment and trailing slash for deduplication (except root)."""
    try:
        p = urlparse(url)
        path = p.path or "/"
        if path != "/" and path.endswith("/"):
            path = path.rstrip("/")
        q = f"?{p.query}" if p.query else ""
        return f"{p.scheme}://{p.netloc}{path}{q}"
    except Exception:
        return url.split("#")[0].rstrip("/")


def _settle_dynamic_content(driver: webdriver.Chrome) -> None:
    """Scroll and brief waits so lazy-loaded content appears."""
    try:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.35);")
        time.sleep(0.35)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(0.45)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(0.25)
    except WebDriverException:
        pass


def _content_hash(driver: webdriver.Chrome) -> str:
    """Fast-ish DOM fingerprint for incremental testing and dedupe."""
    try:
        src = driver.page_source or ""
    except Exception:
        src = ""
    if not src:
        try:
            src = str(driver.execute_script("return document.documentElement ? document.documentElement.outerHTML : ''") or "")
        except Exception:
            src = ""
    return hashlib.sha256(src.encode("utf-8", errors="ignore")).hexdigest()


def _url_priority(url: str, link_text: str = "") -> int:
    """
    Lower is higher priority.
    - login/auth: highest
    - forms: medium
    - dashboard/search: medium
    - static/legal/blog: low
    """
    u = (url or "").lower()
    t = (link_text or "").lower()
    s = u + " " + t
    if any(k in s for k in ("login", "log in", "signin", "sign in", "auth", "account")):
        return 0
    if any(k in s for k in ("signup", "sign up", "register", "create account")):
        return 5
    if any(k in s for k in ("dashboard", "admin", "account", "settings")):
        return 15
    if any(k in s for k in ("form", "contact", "subscribe", "checkout", "payment")):
        return 20
    if any(k in s for k in ("search", "find")):
        return 25
    if any(k in s for k in ("pricing", "plans")):
        return 35
    if any(k in s for k in ("blog", "docs", "help", "faq", "privacy", "terms")):
        return 70
    return 50


def _collect_interactive(driver: webdriver.Chrome, page_url: str) -> PageSnapshot:
    snap = PageSnapshot(url=driver.current_url or page_url)
    try:
        snap.title = driver.title or ""
    except Exception:
        snap.title = ""

    # Links
    for el in driver.find_elements(By.TAG_NAME, "a"):
        try:
            href = el.get_attribute("href") or ""
            text = (el.text or "").strip()[:200]
            snap.links.append(
                {
                    "href": href,
                    "text": text,
                    "visible": el.is_displayed(),
                }
            )
        except WebDriverException:
            continue

    # Buttons (button + input[type=submit|button])
    for el in driver.find_elements(By.TAG_NAME, "button"):
        try:
            snap.buttons.append(
                {
                    "tag": "button",
                    "text": (el.text or "").strip()[:200],
                    "type": el.get_attribute("type") or "button",
                    "visible": el.is_displayed(),
                }
            )
        except WebDriverException:
            continue
    for el in driver.find_elements(By.CSS_SELECTOR, 'input[type="submit"], input[type="button"]'):
        try:
            snap.buttons.append(
                {
                    "tag": "input",
                    "text": (el.get_attribute("value") or "").strip()[:200],
                    "type": el.get_attribute("type") or "button",
                    "visible": el.is_displayed(),
                }
            )
        except WebDriverException:
            continue

    # Inputs
    for el in driver.find_elements(By.CSS_SELECTOR, "input, textarea, select"):
        try:
            snap.inputs.append(
                {
                    "tag": el.tag_name.lower(),
                    "type": (el.get_attribute("type") or "text").lower(),
                    "name": el.get_attribute("name") or "",
                    "placeholder": el.get_attribute("placeholder") or "",
                    "visible": el.is_displayed(),
                }
            )
        except WebDriverException:
            continue

    # Forms
    for idx, el in enumerate(driver.find_elements(By.TAG_NAME, "form")):
        try:
            snap.forms.append(
                {
                    "index": idx,
                    "action": el.get_attribute("action") or "",
                    "method": (el.get_attribute("method") or "get").upper(),
                    "visible": el.is_displayed(),
                }
            )
        except WebDriverException:
            continue

    try:
        from services.page_classifier import classify_page

        snap.page_class = classify_page(snap)
    except Exception:
        snap.page_class = "STATIC"

    return snap


def crawl_site(
    start_url: str,
    max_pages: Optional[int],
    *,
    max_depth: int = 2,
    on_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Dict[str, Any]:
    """
    Breadth-first crawl within same origin. Returns pages list and aggregate stats.
    Uses explicit (url, depth) queue with priority ordering.
    """
    start_url = _normalize_url(start_url.rstrip("/") or start_url)
    visited: Set[str] = set()
    queue: List[Dict[str, Any]] = [{"url": start_url, "depth": 0, "priority": _url_priority(start_url), "via_text": ""}]
    pages: List[PageSnapshot] = []
    errors: List[str] = []
    discovered: Set[str] = set([start_url])
    failed_pages = 0
    skipped_pages = 0
    crawl_logs: List[str] = []

    def _crawl_one(url: str, depth: int, priority: int) -> tuple[PageSnapshot, List[Dict[str, Any]], int]:
        local_skipped = 0
        new_links: List[Dict[str, Any]] = []
        driver: Optional[webdriver.Chrome] = None
        t0 = time.perf_counter()
        try:
            driver = _build_driver()
            last_err = ""
            ok = False
            crawl_logs.append(f"loading {url} (depth={depth})")
            for _attempt in range(config.CRAWL_RETRIES + 1):
                try:
                    driver.get(url)
                    WebDriverWait(driver, config.SELENIUM_PAGE_LOAD_TIMEOUT).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
                    _settle_dynamic_content(driver)
                    # Detect common bot-block pages early so we can downgrade cleanly.
                    page_text = (driver.page_source or "").lower()
                    if any(
                        sig in page_text
                        for sig in (
                            "access denied",
                            "unusual traffic",
                            "verify you are human",
                            "captcha",
                            "bot detection",
                            "are you a robot",
                        )
                    ):
                        raise WebDriverException("blocked_or_bot_detected")
                    ok = True
                    break
                except Exception as e:
                    last_err = str(e)[:300]
                    crawl_logs.append(f"retry {url}: {last_err}")
                    continue
            if not ok:
                raise TimeoutException(last_err or "page load timeout")
            snap = _collect_interactive(driver, url)
            snap.depth = int(depth or 0)
            snap.priority = int(priority or 50)
            snap.load_time_ms = (time.perf_counter() - t0) * 1000
            snap.js_errors = _browser_js_errors(driver)
            if snap.js_errors:
                snap.error_type = "js_error"
                snap.error_message = snap.js_errors[0]
            snap.content_hash = _content_hash(driver)
            perf = collect_window_performance(driver)
            try:
                page_name = urlparse(url).path.strip("/").replace("/", "_") or "home"
                shot_name = f"crawl_{int(time.time()*1000)}_{page_name[:80]}.png"
                abs_shot = os.path.join(config.SCREENSHOTS_DIR, shot_name)
                if driver.save_screenshot(abs_shot):
                    perf["screenshot_path"] = abs_shot
            except Exception:
                pass
            snap.performance = perf
            snap.performance_score = score_page(perf)
            snap.perf_issues = detect_issues(perf)
            snap.suggestions = map_suggestions(snap.perf_issues)
            if snap.load_time_ms >= config.SLOW_PAGE_THRESHOLD_MS:
                snap.load_status = "slow"
            if not snap.links and not snap.buttons and not snap.inputs and not snap.forms:
                crawl_logs.append(f"no interactive elements found: {snap.url}")
            for link in snap.links:
                href = link.get("href") or ""
                ltxt = link.get("text") or ""
                if not _is_crawlable_href(href):
                    local_skipped += 1
                    continue
                abs_u = _normalize_url(urljoin(url, href))
                if not _same_site(start_url, abs_u):
                    local_skipped += 1
                    continue
                if abs_u:
                    new_links.append(
                        {
                            "url": abs_u,
                            "depth": depth + 1,
                            "priority": _url_priority(abs_u, ltxt),
                            "via_text": str(ltxt)[:200],
                        }
                    )
            return snap, new_links, local_skipped
        except TimeoutException:
            crawl_logs.append(f"timeout {url}")
            snap = PageSnapshot(
                url=url,
                error="Page load timeout",
                load_status="failed",
                error_type="timeout",
                error_message="Page load timeout",
                page_class="ERROR",
            )
            snap.depth = int(depth or 0)
            snap.priority = int(priority or 50)
            snap.load_time_ms = (time.perf_counter() - t0) * 1000
            return snap, [], 0
        except WebDriverException as e:
            emsg = str(e)[:500]
            etype = "http_error" if ("404" in emsg or "500" in emsg) else "webdriver_error"
            crawl_logs.append(f"webdriver error {url}: {etype} :: {emsg[:160]}")
            snap = PageSnapshot(
                url=url,
                error=emsg,
                load_status="failed",
                error_type=etype,
                error_message=emsg,
                page_class="ERROR",
            )
            snap.depth = int(depth or 0)
            snap.priority = int(priority or 50)
            snap.load_time_ms = (time.perf_counter() - t0) * 1000
            return snap, [], 0
        except Exception as e:
            emsg = str(e)[:500]
            crawl_logs.append(f"crawl error {url}: {emsg[:160]}")
            snap = PageSnapshot(
                url=url,
                error=emsg or "crawl error",
                load_status="failed",
                error_type="crawl_error",
                error_message=emsg or "crawl error",
                page_class="ERROR",
            )
            snap.depth = int(depth or 0)
            snap.priority = int(priority or 50)
            snap.load_time_ms = (time.perf_counter() - t0) * 1000
            return snap, [], 0
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass

    while queue:
        if config.CRAWL_SOFT_PAGE_CAP > 0 and len(visited) >= config.CRAWL_SOFT_PAGE_CAP:
            break
        if max_pages is not None and len(visited) >= max_pages:
            break
        if max_pages is None and len(visited) >= config.MAX_PAGES_SAFETY_FULL:
            crawl_logs.append(f"safety stop: reached {config.MAX_PAGES_SAFETY_FULL} pages in full mode")
            break
        # Priority BFS: always prefer lower depth, then higher priority.
        queue.sort(key=lambda x: (int(x.get("depth") or 0), int(x.get("priority") or 50)))
        batch: List[Dict[str, Any]] = []
        while queue and len(batch) < max(config.CRAWL_WORKERS, 1):
            item = queue.pop(0)
            raw = str(item.get("url") or "")
            depth = int(item.get("depth") or 0)
            if depth > int(max_depth or 0):
                skipped_pages += 1
                continue
            nu = _normalize_url(raw)
            if nu in visited:
                continue
            visited.add(nu)
            batch.append({"url": nu, "depth": depth, "priority": int(item.get("priority") or 50)})
        if not batch:
            continue
        with ThreadPoolExecutor(max_workers=max(config.CRAWL_WORKERS, 1)) as pool:
            futures = {pool.submit(_crawl_one, b["url"], b["depth"], b["priority"]): b for b in batch}
            for fut in as_completed(futures):
                meta = futures.get(fut) or {}
                try:
                    snap, found_links, sk = fut.result()
                except Exception as e:
                    # Keep the crawl alive even if one worker blows up unexpectedly.
                    emsg = str(e)[:300]
                    url = str(meta.get("url") or start_url)
                    depth = int(meta.get("depth") or 0)
                    crawl_logs.append(f"worker failure {url}: {emsg[:160]}")
                    snap = PageSnapshot(
                        url=url,
                        depth=depth,
                        priority=int(meta.get("priority") or 50),
                        error=emsg or "crawl worker failure",
                        load_status="failed",
                        error_type="crawl_worker_error",
                        error_message=emsg or "crawl worker failure",
                        page_class="ERROR",
                    )
                    found_links = []
                    sk = 0
                skipped_pages += sk
                if snap.load_status == "failed":
                    failed_pages += 1
                    if snap.error_message:
                        errors.append(snap.error_message[:300])
                        crawl_logs.append(f"failed {snap.url} :: {snap.error_type or 'error'}")
                else:
                    crawl_logs.append(f"visited {snap.url}")
                pages.append(snap)
                for it in found_links:
                    abs_u = _normalize_url(str(it.get("url") or ""))
                    if not abs_u:
                        continue
                    discovered.add(abs_u)
                    if abs_u in visited:
                        continue
                    # prevent runaway queue growth
                    if len(queue) >= config.MAX_LINKS_TO_QUEUE:
                        break
                    queue.append(
                        {
                            "url": abs_u,
                            "depth": int(it.get("depth") or (snap.depth + 1)),
                            "priority": int(it.get("priority") or 50),
                            "via_text": it.get("via_text") or "",
                        }
                    )
                if on_progress:
                    try:
                        on_progress(
                            {
                                "visited": len(visited),
                                "discovered": len(discovered),
                                "failed": failed_pages,
                                "skipped": skipped_pages,
                                "remaining": max(len(discovered) - len(visited), 0),
                                "log_line": crawl_logs[-1] if crawl_logs else "",
                            }
                        )
                    except Exception:
                        pass

    load_times = [p.load_time_ms for p in pages if not p.error and p.load_time_ms > 0]
    if not pages:
        # Final safety net: always return at least one page so downstream steps stay alive.
        pages.append(
            PageSnapshot(
                url=start_url,
                depth=0,
                priority=0,
                title=start_url,
                page_class="FALLBACK",
                load_status="fallback",
                error="Crawler fallback page injected",
                error_type="fallback",
                error_message="Crawler fallback page injected",
            )
        )
        visited.add(start_url)
        discovered.add(start_url)
        errors.append("Crawler fallback page injected")
        crawl_logs.append(f"fallback injected: {start_url}")

    valid_urls = [p.url for p in pages if not getattr(p, "error", None)]

    return {
        "start_url": start_url,
        "pages": pages,
        "visited_urls": list(visited),
        "valid_urls": valid_urls or [start_url],
        "errors": errors,
        "load_times_ms": load_times,
        "total_pages_discovered": len(discovered),
        "total_pages_visited": len(visited),
        "failed_pages": failed_pages,
        "skipped_pages": skipped_pages,
        "crawl_logs": crawl_logs[-500:],
    }
