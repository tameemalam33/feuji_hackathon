"""Execute generated tests with Selenium; capture results and screenshots."""
from __future__ import annotations

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional, Tuple

from selenium.common.exceptions import (
    ElementClickInterceptedException,
    ElementNotInteractableException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

import config
from config import SCREENSHOTS_DIR
from services.data_generator import SyntheticProfile
from services.driver_factory import create_executor_driver


def _shot_path(run_id: int, test_id: str) -> str:
    safe = test_id.replace("/", "-").replace("\\", "-")
    fname = f"{run_id}_{safe}.png"
    return os.path.join(SCREENSHOTS_DIR, fname)


def _web_path(abs_path: str) -> str:
    base = os.path.basename(abs_path)
    return f"/static/screenshots/{base}"


def _combined_buttons(driver):
    btns = driver.find_elements(By.TAG_NAME, "button")
    subs = driver.find_elements(By.CSS_SELECTOR, 'input[type="submit"], input[type="button"]')
    return list(btns) + list(subs)


def _combined_inputs(driver):
    return driver.find_elements(By.CSS_SELECTOR, "input, textarea, select")


def _norm_url(u: str) -> str:
    return u.split("#")[0].rstrip("/")


def _ensure_page(driver, url: str) -> None:
    if _norm_url(driver.current_url or "") != _norm_url(url):
        driver.get(url)


def _get_target_element(driver, action: Dict[str, Any]):
    kind = action.get("kind")
    page_url = action.get("url", "")
    _ensure_page(driver, page_url)
    try:
        if kind == "link_click_probe":
            idx = int(action.get("index", 0))
            links = driver.find_elements(By.TAG_NAME, "a")
            if idx < len(links):
                return links[idx]
        if kind == "button_click_probe":
            idx = int(action.get("index", 0))
            c = _combined_buttons(driver)
            if idx < len(c):
                return c[idx]
        if kind in ("input_type_probe", "input_validation_probe"):
            idx = int(action.get("index", 0))
            els = _combined_inputs(driver)
            if idx < len(els):
                return els[idx]
        if kind == "form_present":
            idx = int(action.get("index", 0))
            forms = driver.find_elements(By.TAG_NAME, "form")
            if idx < len(forms):
                return forms[idx]
    except WebDriverException:
        return None
    return None


def _link_text_lower(el) -> str:
    try:
        return (el.text or "").strip().lower()
    except WebDriverException:
        return ""


def _find_first_link_matching(driver, keywords: Tuple[str, ...]) -> Optional[Any]:
    links = driver.find_elements(By.TAG_NAME, "a")
    for a in links:
        try:
            if not a.is_displayed():
                continue
            t = _link_text_lower(a)
            href = a.get_attribute("href") or ""
            if not href or href.startswith("#"):
                continue
            if any(k in t for k in keywords):
                return a
        except WebDriverException:
            continue
    return None


def _first_password_input(driver):
    for el in driver.find_elements(By.CSS_SELECTOR, 'input[type="password"]'):
        try:
            if el.is_displayed():
                return el
        except WebDriverException:
            continue
    return None


def _first_email_or_text_input(driver):
    for sel in ('input[type="email"]', 'input[type="text"]', "input:not([type])", "textarea"):
        for el in driver.find_elements(By.CSS_SELECTOR, sel):
            try:
                tag = el.tag_name.lower()
                it = (el.get_attribute("type") or "text").lower()
                if it in ("hidden", "submit", "button", "image", "checkbox", "radio"):
                    continue
                if el.is_displayed():
                    return el
            except WebDriverException:
                continue
    return None


def _submit_visible_form(driver) -> Tuple[bool, str]:
    forms = driver.find_elements(By.TAG_NAME, "form")
    for form in forms[:5]:
        try:
            if not form.is_displayed():
                continue
            subs = form.find_elements(By.CSS_SELECTOR, '[type="submit"],button[type="submit"],button:not([type])')
            for s in subs:
                if s.is_displayed():
                    s.click()
                    time.sleep(0.5)
                    return True, "submit clicked"
            form.submit()
            time.sleep(0.5)
            return True, "form.submit()"
        except WebDriverException as e:
            continue
    return False, "no submittable form"


def _run_user_flow(driver, action: Dict[str, Any], profile: SyntheticProfile) -> tuple[bool, str]:
    start = action.get("start_url") or action.get("url", "")
    flow = (action.get("flow_type") or "").lower()
    driver.get(start)
    WebDriverWait(driver, config.SELENIUM_PAGE_LOAD_TIMEOUT).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )
    time.sleep(0.35)

    if flow == "login":
        link = _find_first_link_matching(driver, ("log in", "login", "sign in", "signin"))
        if link:
            try:
                link.click()
                time.sleep(0.7)
            except WebDriverException as e:
                return False, f"login link click failed: {e}"
        pwd = _first_password_input(driver)
        if not pwd:
            return False, "login flow: no password field found"
        email_el = _first_email_or_text_input(driver)
        try:
            if email_el:
                try:
                    email_el.clear()
                except WebDriverException:
                    pass
                email_el.send_keys(profile.email)
            try:
                pwd.clear()
            except WebDriverException:
                pass
            pwd.send_keys(profile.password or "AutoQA_Safe_P@ssw0rd!")
        except WebDriverException as e:
            return False, f"credential entry failed: {e}"
        ok, msg = _submit_visible_form(driver)
        time.sleep(0.4)
        bodies = driver.find_elements(By.TAG_NAME, "body")
        return ok and len(bodies) >= 1, f"{msg}; url={driver.current_url[:120]}"

    if flow == "signup":
        link = _find_first_link_matching(
            driver,
            ("sign up", "signup", "register", "create account", "join"),
        )
        if link:
            try:
                link.click()
                time.sleep(0.7)
            except WebDriverException as e:
                return False, f"signup link failed: {e}"
        filled = 0
        for el in _combined_inputs(driver)[:10]:
            try:
                it = (el.get_attribute("type") or "text").lower()
                if it in ("hidden", "submit", "button", "image", "checkbox", "radio"):
                    continue
                if not el.is_displayed():
                    continue
                el.clear()
                if it == "email":
                    el.send_keys(profile.email)
                elif it == "password":
                    el.send_keys(profile.password or "AutoQA_Safe_P@ss!")
                elif it == "tel":
                    el.send_keys(profile.phone or "+15551234567")
                else:
                    el.send_keys("AutoQA User")
                filled += 1
            except WebDriverException:
                continue
        _submit_visible_form(driver)
        time.sleep(0.4)
        return filled > 0 or link is not None, f"signup fields_touched={filled}; url={driver.current_url[:120]}"

    if flow == "search":
        search_el = None
        for sel in ('input[type="search"]', 'input[name*="search"]', 'input[name*="Search"]', 'input[placeholder*="search"]'):
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            for el in els:
                try:
                    if el.is_displayed():
                        search_el = el
                        break
                except WebDriverException:
                    continue
            if search_el:
                break
        if not search_el:
            return False, "search flow: no search input found"
        try:
            search_el.clear()
        except WebDriverException:
            pass
        search_el.send_keys("autoqa test query")
        try:
            search_el.submit()
        except WebDriverException:
            btns = driver.find_elements(By.CSS_SELECTOR, '[type="submit"],button')
            clicked = False
            for b in btns[:12]:
                try:
                    if b.is_displayed():
                        b.click()
                        clicked = True
                        break
                except WebDriverException:
                    continue
            if not clicked:
                search_el.send_keys(Keys.RETURN)
        time.sleep(0.5)
        return True, f"search executed; url={driver.current_url[:120]}"

    if flow == "generic_form":
        els = _combined_inputs(driver)
        filled = 0
        for el in els[:6]:
            try:
                it = (el.get_attribute("type") or "text").lower()
                if it in ("hidden", "submit", "button", "image", "checkbox", "radio"):
                    continue
                if not el.is_displayed():
                    continue
                el.clear()
                el.send_keys(profile.email if it == "email" else "AutoQA flow data")
                filled += 1
                if filled >= 2:
                    break
            except WebDriverException:
                continue
        ok, msg = _submit_visible_form(driver)
        time.sleep(0.4)
        return ok or filled > 0, f"filled={filled}, {msg}; url={driver.current_url[:100]}"

    return False, f"unknown flow_type={flow}"


def _highlight_element(driver, element) -> None:
    if not element:
        return
    try:
        driver.execute_script("arguments[0].style.border='3px solid red'", element)
        driver.execute_script("arguments[0].scrollIntoView({block:'center',inline:'nearest'});", element)
    except WebDriverException:
        pass


def _compute_element_selector(driver, element) -> str:
    """Best-effort CSS selector for the highlighted element (used by Fix/Issue UI)."""
    if not element:
        return ""
    try:
        el_id = element.get_attribute("id") or ""
        if el_id:
            # Only safe ids become '#id'. Otherwise fall back to attribute selector.
            if all(ch.isalnum() or ch in ("-", "_") for ch in el_id):
                return f"#{el_id}"
            el_id_esc = el_id.replace('"', '\\"')
            return f'[id=\"{el_id_esc}\"]'
        name = element.get_attribute("name") or ""
        if name:
            name_esc = name.replace('"', '\\"')
            return f'[name=\"{name_esc}\"]'

        # Fallback: nth-of-type within same-tag siblings.
        tag = (element.tag_name or "").lower()
        if tag:
            selector = driver.execute_script(
                """
                (function(el){
                  if(!el) return '';
                  var tag = (el.tagName || '').toLowerCase();
                  if(!tag) return '';
                  var ix = 1;
                  var prev = el.previousElementSibling;
                  while(prev){
                    if(prev.tagName && prev.tagName.toLowerCase() === tag) ix++;
                    prev = prev.previousElementSibling;
                  }
                  return tag + ':nth-of-type(' + ix + ')';
                })(arguments[0]);
                """,
                element,
            )
            return str(selector or "")
    except Exception:
        pass
    return ""


def _run_action(driver, action: Dict[str, Any], profile: SyntheticProfile) -> tuple[bool, str]:
    kind = action.get("kind")
    url = action.get("url", "")

    if kind == "load_page":
        t0 = time.perf_counter()
        driver.get(url)
        WebDriverWait(driver, config.SELENIUM_PAGE_LOAD_TIMEOUT).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        dt = (time.perf_counter() - t0) * 1000
        return True, f"Loaded in {dt:.0f} ms"

    if kind == "assert_title_present":
        _ensure_page(driver, url)
        title = (driver.title or "").strip()
        return (len(title) > 0), f"title={title!r}"

    if kind == "assert_body":
        _ensure_page(driver, url)
        bodies = driver.find_elements(By.TAG_NAME, "body")
        return len(bodies) >= 1, f"body_count={len(bodies)}"

    if kind == "assert_password_field":
        _ensure_page(driver, url)
        for el in driver.find_elements(By.CSS_SELECTOR, 'input[type="password"]'):
            try:
                if el.is_displayed():
                    return True, "password field visible"
            except WebDriverException:
                continue
        return False, "no visible password field"

    if kind == "assert_viewport_content":
        _ensure_page(driver, url)
        h = driver.execute_script("return window.innerHeight || 0;")
        raw_len = driver.execute_script(
            "return document.body && document.body.innerText ? document.body.innerText.length : 0;"
        )
        txt_len = int(raw_len) if raw_len is not None else 0
        ok = h > 200 and txt_len > 5
        return ok, f"innerHeight={h}, textLen={txt_len}"

    if kind == "performance_navigation":
        _ensure_page(driver, url)
        max_ms = float(action.get("max_ms", 20000))
        t0 = time.perf_counter()
        driver.get(url)
        WebDriverWait(driver, config.SELENIUM_PAGE_LOAD_TIMEOUT).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        dt = (time.perf_counter() - t0) * 1000
        return dt <= max_ms, f"navigation_ms={dt:.0f} (max {max_ms})"

    if kind == "assert_ready_state":
        _ensure_page(driver, url)
        state = driver.execute_script("return document.readyState")
        ok = state in ("interactive", "complete")
        return ok, f"readyState={state!r}"

    if kind == "a11y_images_alt":
        _ensure_page(driver, url)
        imgs = driver.find_elements(By.TAG_NAME, "img")[:30]
        missing = 0
        for im in imgs:
            try:
                alt = im.get_attribute("alt")
                if alt is None or str(alt).strip() == "":
                    missing += 1
            except WebDriverException:
                missing += 1
        ok = missing <= max(3, len(imgs) // 3)
        return ok, f"images_checked={len(imgs)}, missing_alt~={missing}"

    if kind == "a11y_input_names":
        _ensure_page(driver, url)
        els = _combined_inputs(driver)[:15]
        ok_count = 0
        for el in els:
            try:
                aria = el.get_attribute("aria-label")
                lab = el.get_attribute("aria-labelledby")
                ph = el.get_attribute("placeholder")
                nid = el.get_attribute("id")
                has_label = bool(aria or lab or ph)
                if nid:
                    labs = driver.find_elements(By.CSS_SELECTOR, f'label[for="{nid}"]')
                    if labs:
                        has_label = True
                if has_label:
                    ok_count += 1
            except WebDriverException:
                continue
        ok = len(els) == 0 or ok_count >= max(1, len(els) // 2)
        return ok, f"inputs={len(els)}, with_accessible_name~={ok_count}"

    if kind == "a11y_tab_focus":
        _ensure_page(driver, url)
        focusable = driver.find_elements(
            By.CSS_SELECTOR,
            "a[href], button, input, select, textarea, [tabindex]:not([tabindex='-1'])",
        )
        return len(focusable) > 0, f"focusable_nodes={len(focusable)}"

    if kind == "a11y_headings":
        _ensure_page(driver, url)
        n = len(driver.find_elements(By.CSS_SELECTOR, "h1, h2, h3, h4, h5, h6"))
        txt_len = len(driver.execute_script("return document.body.innerText || ''"))
        ok = n > 0 or txt_len < 400
        return ok, f"heading_count={n}, textLen={txt_len}"

    if kind == "link_click_probe":
        _ensure_page(driver, url)
        idx = int(action.get("index", 0))
        links = driver.find_elements(By.TAG_NAME, "a")
        if idx >= len(links):
            return False, f"No link at index {idx} (found {len(links)})"
        el = links[idx]
        try:
            if not el.is_displayed():
                return True, "Link not visible — skipped"
            href = el.get_attribute("href") or ""
            if not href or href.startswith("#"):
                return True, "Non-navigating link skipped"
            el.click()
            time.sleep(0.4)
            return True, f"Clicked link, current={driver.current_url[:120]}"
        except (ElementClickInterceptedException, ElementNotInteractableException) as e:
            return False, f"Not clickable: {e}"

    if kind == "button_click_probe":
        _ensure_page(driver, url)
        idx = int(action.get("index", 0))
        c = _combined_buttons(driver)
        if idx >= len(c):
            return False, f"No button at index {idx} (found {len(c)})"
        el = c[idx]
        try:
            if not el.is_displayed():
                return True, "Button not visible — skipped"
            el.click()
            time.sleep(0.3)
            return True, "Button clicked"
        except (ElementClickInterceptedException, ElementNotInteractableException, StaleElementReferenceException) as e:
            return False, f"Not clickable: {e}"

    if kind == "input_type_probe":
        _ensure_page(driver, url)
        idx = int(action.get("index", 0))
        itype = (action.get("input_type") or "text").lower()
        els = _combined_inputs(driver)
        if idx >= len(els):
            return False, f"No input at index {idx} (found {len(els)})"
        el = els[idx]
        try:
            tag = el.tag_name.lower()
            if tag == "select":
                return True, "Select element — skipped typing"
            if itype in ("hidden", "submit", "button", "image", "checkbox", "radio"):
                return True, f"type={itype} — skipped text entry"
            try:
                el.clear()
            except WebDriverException:
                pass
            sample = profile.email if itype == "email" else "AutoQA sample text"
            el.send_keys(sample)
            val = el.get_attribute("value") or ""
            return sample in val or len(val) > 0, f"value_len={len(val)}"
        except WebDriverException as e:
            return False, str(e)[:300]

    if kind == "input_validation_probe":
        _ensure_page(driver, url)
        idx = int(action.get("index", 0))
        itype = (action.get("input_type") or "text").lower()
        els = _combined_inputs(driver)
        if idx >= len(els):
            return False, f"No input at index {idx}"
        el = els[idx]
        try:
            if itype != "email":
                return True, "Not an email field — validation N/A"
            el.clear()
            el.send_keys("not-an-email")
            validity = el.get_property("validity")
            bad = getattr(validity, "typeMismatch", False) if validity else False
            el.clear()
            el.send_keys(profile.email)
            return True, f"email validity probe typeMismatch={bad}"
        except WebDriverException as e:
            return False, str(e)[:300]

    if kind == "form_present":
        _ensure_page(driver, url)
        idx = int(action.get("index", 0))
        forms = driver.find_elements(By.TAG_NAME, "form")
        if idx >= len(forms):
            return False, f"No form at index {idx}"
        return True, f"forms={len(forms)}"

    if kind == "scroll_bottom":
        _ensure_page(driver, url)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(0.2)
        y = driver.execute_script("return window.scrollY || window.pageYOffset")
        return True, f"scrollY={y}"

    if kind == "scroll_top":
        _ensure_page(driver, url)
        driver.execute_script("window.scrollTo(0, 0);")
        return True, "scrolled top"

    if kind == "resize":
        _ensure_page(driver, url)
        driver.set_window_size(1366, 768)
        return True, "window 1366x768"

    if kind == "console_errors":
        _ensure_page(driver, url)
        try:
            logs = driver.get_log("browser")
        except Exception:
            logs = []
        sev = [x for x in logs if x.get("level") == "SEVERE"]
        return len(sev) < 8, f"severe_console={len(sev)}"

    if kind == "dom_depth":
        _ensure_page(driver, url)
        depth = driver.execute_script(
            """
            let d=0; function walk(n,l){d=Math.max(d,l);
            for (let c of n.children||[]) walk(c,l+1);} walk(document.body,0); return d;
            """
        )
        return int(depth) < 120, f"approx_depth={depth}"

    if kind == "count_interactive":
        _ensure_page(driver, url)
        n = len(
            driver.find_elements(
                By.CSS_SELECTOR,
                "a, button, input, textarea, select",
            )
        )
        return n >= 0, f"interactive={n}"

    if kind == "reload_twice":
        _ensure_page(driver, url)
        driver.get(url)
        driver.refresh()
        time.sleep(0.3)
        driver.refresh()
        WebDriverWait(driver, config.SELENIUM_PAGE_LOAD_TIMEOUT).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        return True, "double reload ok"

    if kind == "user_flow":
        return _run_user_flow(driver, action, profile)

    if kind == "nav_menu_internal_links_probe":
        _ensure_page(driver, url)
        max_n = int(action.get("max_links", 6))
        nav_links = driver.find_elements(By.CSS_SELECTOR, "header a[href], nav a[href], [role='navigation'] a[href]")
        visited_ok = 0
        errors: List[str] = []
        for a in nav_links[: max_n * 2]:
            if visited_ok >= max_n:
                break
            try:
                if not a.is_displayed():
                    continue
                href = a.get_attribute("href") or ""
                if not href or href.startswith("#") or "javascript:" in href.lower():
                    continue
                a.click()
                time.sleep(0.45)
                WebDriverWait(driver, config.SELENIUM_PAGE_LOAD_TIMEOUT).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                if driver.find_elements(By.TAG_NAME, "body"):
                    visited_ok += 1
                driver.get(url)
                WebDriverWait(driver, config.SELENIUM_PAGE_LOAD_TIMEOUT).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
            except WebDriverException as e:
                errors.append(str(e)[:80])
                try:
                    driver.get(url)
                except WebDriverException:
                    pass
        ok = visited_ok > 0 or len(nav_links) == 0
        return ok, f"menu_links_ok={visited_ok}, tried_nav={len(nav_links)}, errs={len(errors)}"

    if kind == "nav_footer_links_probe":
        _ensure_page(driver, url)
        max_n = int(action.get("max_links", 5))
        flinks = driver.find_elements(By.CSS_SELECTOR, "footer a[href], [role='contentinfo'] a[href]")
        visited_ok = 0
        for a in flinks[: max_n * 2]:
            if visited_ok >= max_n:
                break
            try:
                if not a.is_displayed():
                    continue
                href = a.get_attribute("href") or ""
                if not href or href.startswith("#"):
                    continue
                a.click()
                time.sleep(0.45)
                WebDriverWait(driver, config.SELENIUM_PAGE_LOAD_TIMEOUT).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                visited_ok += 1
                driver.get(url)
                WebDriverWait(driver, config.SELENIUM_PAGE_LOAD_TIMEOUT).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
            except WebDriverException:
                try:
                    driver.get(url)
                except WebDriverException:
                    pass
        return visited_ok > 0 or len(flinks) == 0, f"footer_links_ok={visited_ok}"

    if kind == "nav_breadcrumb_probe":
        _ensure_page(driver, url)
        crumbs = driver.find_elements(
            By.CSS_SELECTOR,
            "nav[aria-label*='breadcrumb'] a, nav[aria-label*='Breadcrumb'] a, .breadcrumb a, [class*='breadcrumb'] a",
        )
        if not crumbs:
            return True, "no breadcrumbs — N/A"
        try:
            c = crumbs[0]
            if c.is_displayed():
                c.click()
                time.sleep(0.4)
                return True, f"breadcrumb navigated to {driver.current_url[:100]}"
        except WebDriverException as e:
            return False, str(e)[:200]
        return True, "breadcrumb skip"

    if kind == "browser_back_refresh_probe":
        _ensure_page(driver, url)
        first = _norm_url(driver.current_url or "")
        link = None
        for a in driver.find_elements(By.CSS_SELECTOR, "main a[href], article a[href], a[href]"):
            try:
                if not a.is_displayed():
                    continue
                h = a.get_attribute("href") or ""
                if h and not h.startswith("#") and "javascript:" not in h.lower():
                    link = a
                    break
            except WebDriverException:
                continue
        if link:
            try:
                link.click()
                time.sleep(0.5)
                WebDriverWait(driver, config.SELENIUM_PAGE_LOAD_TIMEOUT).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
            except WebDriverException:
                pass
        try:
            driver.back()
            time.sleep(0.35)
        except WebDriverException as e:
            return False, f"back() failed: {e}"
        driver.refresh()
        time.sleep(0.35)
        WebDriverWait(driver, config.SELENIUM_PAGE_LOAD_TIMEOUT).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        bodies = driver.find_elements(By.TAG_NAME, "body")
        return len(bodies) >= 1, f"back+refresh ok; url={_norm_url(driver.current_url)}"

    if kind == "form_empty_submit_probe":
        _ensure_page(driver, url)
        forms = driver.find_elements(By.TAG_NAME, "form")
        if not forms:
            return True, "no forms — N/A"
        ok, msg = _submit_visible_form(driver)
        time.sleep(0.3)
        return ok, f"empty submit: {msg}"

    if kind == "form_invalid_phone_probe":
        _ensure_page(driver, url)
        tel = None
        for el in driver.find_elements(By.CSS_SELECTOR, 'input[type="tel"]'):
            try:
                if el.is_displayed():
                    tel = el
                    break
            except WebDriverException:
                continue
        if not tel:
            return True, "no tel input — N/A"
        try:
            tel.clear()
            tel.send_keys("abc-not-phone")
            val = tel.get_property("validity")
            bad = getattr(val, "patternMismatch", False) or getattr(val, "typeMismatch", False) if val else False
            return True, f"tel validity mismatch={bad}"
        except WebDriverException as e:
            return False, str(e)[:200]

    if kind == "form_boundary_length_probe":
        _ensure_page(driver, url)
        el = _first_email_or_text_input(driver)
        if not el:
            return True, "no text input — N/A"
        try:
            el.clear()
            el.send_keys("x" * 500)
            ln = len(el.get_attribute("value") or "")
            return ln > 0, f"stored_len={ln}"
        except WebDriverException as e:
            return False, str(e)[:200]

    if kind == "form_special_chars_probe":
        _ensure_page(driver, url)
        el = _first_email_or_text_input(driver)
        if not el:
            return True, "no text input — N/A"
        sample = "测试 «ταБ» • €"
        try:
            el.clear()
            el.send_keys(sample)
            v = el.get_attribute("value") or ""
            return len(v) > 0, f"value_len={len(v)}"
        except WebDriverException as e:
            return False, str(e)[:200]

    if kind == "edge_long_string_probe":
        _ensure_page(driver, url)
        el = _first_email_or_text_input(driver)
        if not el:
            return True, "no text input — N/A"
        try:
            el.clear()
            el.send_keys("A" * 4000)
            bodies = driver.find_elements(By.TAG_NAME, "body")
            return len(bodies) >= 1, "long string accepted or truncated"
        except WebDriverException as e:
            return False, str(e)[:200]

    if kind == "edge_xss_string_probe":
        _ensure_page(driver, url)
        el = _first_email_or_text_input(driver)
        if not el:
            return True, "no text input — N/A"
        payload = "<script>alert(1)</script>"
        try:
            el.clear()
            el.send_keys(payload)
            # Heuristic: inline script should not create new script elements from this value alone
            n_scripts = driver.execute_script(
                "return document.querySelectorAll('script:not([src])').length;"
            )
            html = driver.execute_script("return document.body ? document.body.innerHTML : ''") or ""
            executed = False
            try:
                logs = driver.get_log("browser")
                executed = any("script" in str(x.get("message", "")).lower() for x in logs[-5:])
            except Exception:
                pass
            return not executed and len(driver.find_elements(By.TAG_NAME, "body")) > 0, (
                f"body_ok scripts={n_scripts} reflected_literal={payload in html}"
            )
        except WebDriverException as e:
            return False, str(e)[:200]

    if kind == "edge_sqli_string_probe":
        _ensure_page(driver, url)
        el = _first_email_or_text_input(driver)
        if not el:
            return True, "no text input — N/A"
        payload = "' OR 1=1 --"
        try:
            el.clear()
            el.send_keys(payload)
            el.submit()
        except WebDriverException:
            try:
                _submit_visible_form(driver)
            except Exception:
                pass
        time.sleep(0.4)
        bodies = driver.find_elements(By.TAG_NAME, "body")
        txt = ""
        try:
            txt = driver.execute_script("return document.body ? document.body.innerText : ''") or ""
        except WebDriverException:
            pass
        dead = len(txt.strip()) < 3 and len(bodies) < 1
        return not dead, f"body_text_len={len(txt)}"

    if kind == "security_https_check":
        _ensure_page(driver, url)
        cur = driver.current_url or ""
        ok = cur.lower().startswith("https:")
        return ok, f"current_url={cur[:120]}"

    if kind == "security_headers_meta_probe":
        _ensure_page(driver, url)
        has_csp = driver.execute_script(
            """
            var m=document.querySelector('meta[http-equiv=Content-Security-Policy],meta[http-equiv=content-security-policy]');
            return !!m;
            """
        )
        has_ref = driver.execute_script(
            """return !!document.querySelector('meta[name=referrer],meta[http-equiv=Referrer-Policy]');"""
        )
        score = int(bool(has_csp)) + int(bool(has_ref))
        return score >= 1, f"csp_meta={bool(has_csp)} referrer_meta={bool(has_ref)}"

    if kind == "a11y_wcag_aggregate_score":
        _ensure_page(driver, url)
        min_score = float(action.get("min_score", 55.0))
        imgs = driver.find_elements(By.TAG_NAME, "img")[:40]
        miss_alt = 0
        for im in imgs:
            try:
                alt = im.get_attribute("alt")
                if alt is None:
                    miss_alt += 1
            except WebDriverException:
                miss_alt += 1
        img_score = 100.0 if not imgs else max(0.0, 100.0 - (miss_alt / max(len(imgs), 1)) * 100.0)
        els = _combined_inputs(driver)[:20]
        named = 0
        for inp in els:
            try:
                aria = inp.get_attribute("aria-label")
                ph = inp.get_attribute("placeholder")
                nid = inp.get_attribute("id")
                has_l = bool(aria or ph)
                if nid:
                    labs = driver.find_elements(By.CSS_SELECTOR, f'label[for="{nid}"]')
                    if labs:
                        has_l = True
                if has_l:
                    named += 1
            except WebDriverException:
                continue
        inp_score = 100.0 if not els else (named / len(els)) * 100.0
        focus_n = len(
            driver.find_elements(
                By.CSS_SELECTOR,
                "a[href], button, input, select, textarea",
            )
        )
        focus_score = min(100.0, focus_n * 5.0)
        # Sample contrast: first large text vs body bg (rough luminance)
        contrast_ok = driver.execute_script(
            """
            var h=document.querySelector('h1,h2,h3');
            if(!h) return 1;
            var s=getComputedStyle(h);
            var c=s.color;
            return c && c !== 'rgba(0, 0, 0, 0)' ? 1 : 0;
            """
        )
        contrast_score = 70.0 if contrast_ok else 40.0
        total = img_score * 0.35 + inp_score * 0.35 + min(focus_score, 100.0) * 0.15 + contrast_score * 0.15
        passed = total >= min_score
        return passed, f"a11y_composite_score={total:.1f} (min {min_score})"

    if kind == "responsive_multi_viewport_probe":
        _ensure_page(driver, url)
        sizes = [(375, 812), (768, 1024), (1280, 720)]
        bad = 0
        for w, h in sizes:
            try:
                driver.set_window_size(w, h)
                time.sleep(0.25)
                overflow = driver.execute_script(
                    """
                    var sw=document.documentElement.scrollWidth||0;
                    var iw=window.innerWidth||0;
                    return sw - iw;
                    """
                )
                if int(overflow or 0) > 80:
                    bad += 1
            except WebDriverException:
                bad += 1
        driver.set_window_size(1920, 1080)
        return bad == 0, f"viewport_overflow_issues={bad}/3"

    if kind == "performance_navigation_timing":
        _ensure_page(driver, url)
        driver.get(url)
        WebDriverWait(driver, config.SELENIUM_PAGE_LOAD_TIMEOUT).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        max_ttfb = float(action.get("max_ttfb_ms", 3500))
        data = driver.execute_script(
            """
            var e=performance.getEntriesByType('navigation')[0];
            if(!e) return null;
            return {ttfb: (e.responseStart - e.fetchStart), load: e.duration};
            """
        )
        if not data:
            return True, "Navigation Timing API unavailable — skip"
        ttfb = float(data.get("ttfb") or 0)
        load_d = float(data.get("load") or 0)
        ok = ttfb <= max_ttfb
        return ok, f"ttfb_ms={ttfb:.0f}, load_ms={load_d:.0f}"

    if kind == "performance_multi_load_probe":
        _ensure_page(driver, url)
        n = int(action.get("visits", 3))
        times: List[float] = []
        for _ in range(max(1, min(n, 5))):
            t0 = time.perf_counter()
            driver.get(url)
            WebDriverWait(driver, config.SELENIUM_PAGE_LOAD_TIMEOUT).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            times.append((time.perf_counter() - t0) * 1000)
        spread = max(times) - min(times) if times else 0
        ok = spread < 25000 and all(t < 60000 for t in times)
        return ok, f"loads_ms={','.join(f'{t:.0f}' for t in times)}, spread={spread:.0f}"

    if kind == "performance_slowest_page_revalidate":
        base_u = action.get("url") or url
        urls_list = action.get("urls") or []
        tms = action.get("load_times_ms") or []
        if not urls_list or not tms or len(urls_list) != len(tms):
            return True, "no crawl timing pairs — N/A"
        imax = max(range(len(tms)), key=lambda i: tms[i])
        slow = urls_list[imax]
        t0 = time.perf_counter()
        driver.get(slow)
        WebDriverWait(driver, config.SELENIUM_PAGE_LOAD_TIMEOUT).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        dt = (time.perf_counter() - t0) * 1000
        return True, f"slowest={slow[:80]} fresh_load_ms={dt:.0f} crawl_ms={tms[imax]:.0f}"

    if kind == "noop_probe":
        _ensure_page(driver, url)
        return True, "noop ok"

    if kind == "api_ui_network_probe":
        _ensure_page(driver, url)
        time.sleep(0.45)
        bad: List[int] = []
        codes: List[int] = []
        try:
            logs = driver.get_log("performance")
            for entry in logs[-400:]:
                try:
                    msg = json.loads(entry.get("message") or "{}")
                    m = msg.get("message") or {}
                    if m.get("method") != "Network.responseReceived":
                        continue
                    st = (m.get("params") or {}).get("response") or {}
                    status = st.get("status")
                    if status is not None:
                        c = int(status)
                        codes.append(c)
                        if c >= 500:
                            bad.append(c)
                except Exception:
                    continue
        except Exception as e:
            return True, f"network log unavailable: {e!s}"[:200]
        if bad:
            return False, f"HTTP 5xx in captured API responses: {bad[:6]}"
        tail = codes[-12:] if codes else []
        return True, f"xhr_fetch_samples={len(codes)} last_statuses={tail}"

    return False, f"Unknown action kind: {kind}"


def _browser_log_lines(driver) -> List[str]:
    out: List[str] = []
    try:
        for entry in driver.get_log("browser")[-20:]:
            out.append(str(entry.get("message", ""))[:240])
    except Exception:
        pass
    return out


def _run_one_case(
    driver,
    tc: Dict[str, Any],
    profile: SyntheticProfile,
    run_id: int,
) -> Dict[str, Any]:
    tid = tc["id"]
    action = tc.get("action") or {}
    passed = False
    actual = ""
    err_detail = ""
    shot: Optional[str] = None
    element_selector: str = ""
    retry_count = 0
    issue_type = tc.get("category", "") or ""

    for attempt in range(3):
        err_detail = ""
        try:
            passed, actual = _run_action(driver, action, profile)
        except TimeoutException as e:
            passed = False
            actual = f"Timeout: {e}"
            err_detail = "timeout"
        except WebDriverException as e:
            passed = False
            actual = str(e)[:500]
            err_detail = "webdriver"

        if passed:
            retry_count = attempt
            break
    else:
        passed = False
        retry_count = 2

    logs: List[str] = []
    if not passed:
        try:
            el = _get_target_element(driver, action)
            _highlight_element(driver, el)
            element_selector = _compute_element_selector(driver, el)
            time.sleep(0.2)
            path = _shot_path(run_id, tid)
            driver.save_screenshot(path)
            shot = _web_path(path)
        except Exception:
            shot = None
        logs = _browser_log_lines(driver)

    flow_type = action.get("flow_type") if action.get("kind") == "user_flow" else None
    message = actual if actual else err_detail
    return {
        "test_id": tid,
        "name": tc.get("name", ""),
        "title": tc.get("title") or tc.get("name", ""),
        "user_story": tc.get("user_story", ""),
        "scenario": tc.get("scenario", ""),
        "test_type": tc.get("test_type", "Positive"),
        "component": tc.get("component") or "",
        "page": tc.get("page") or action.get("url") or action.get("start_url") or "",
        "category": tc.get("category", ""),
        "priority": tc.get("priority", ""),
        "status": "passed" if passed else "failed",
        "expected": tc.get("expected_result", ""),
        "expected_result": tc.get("expected_result", ""),
        "actual": actual,
        "actual_result": actual,
        "error_kind": err_detail,
        "element_selector": element_selector,
        "issue_type": issue_type,
        "message": message,
        "screenshot": shot,
        "screenshot_path": shot,
        "steps": tc.get("steps", []),
        "action_kind": action.get("kind"),
        "flow_type": flow_type,
        "retry_count": retry_count,
        "logs": logs,
    }


def _execute_chunk(
    indexed_chunk: List[Tuple[int, Dict[str, Any]]],
    profile: SyntheticProfile,
    run_id: int,
) -> List[Tuple[int, Dict[str, Any]]]:
    driver = create_executor_driver()
    out: List[Tuple[int, Dict[str, Any]]] = []
    try:
        for idx, tc in indexed_chunk:
            out.append((idx, _run_one_case(driver, tc, profile, run_id)))
    finally:
        try:
            driver.quit()
        except Exception:
            pass
    return out


def execute_tests(
    test_cases: List[Dict[str, Any]],
    profile: SyntheticProfile,
    batch_id: str,
    run_id: int,
    progress: Optional[Callable[[int, int, str], None]] = None,
) -> List[Dict[str, Any]]:
    total = len(test_cases)
    if total == 0:
        return []

    def _is_critical_case(tc: Dict[str, Any]) -> bool:
        pr = str(tc.get("priority") or "")
        action = tc.get("action") or {}
        flow = str(action.get("flow_type") or "").lower()
        return pr == "Critical" or flow == "login"

    critical_cases = [tc for tc in test_cases if _is_critical_case(tc)]
    remaining_cases = [tc for tc in test_cases if not _is_critical_case(tc)]

    early_results: List[Dict[str, Any]] = []
    # Execute critical tests first for fast fail/early-exit decisions.
    if critical_cases:
        crit_driver = create_executor_driver()
        try:
            for tc in critical_cases:
                early_results.append(_run_one_case(crit_driver, tc, profile, run_id))
                if progress:
                    progress(len(early_results), total, tc["id"])
        finally:
            try:
                crit_driver.quit()
            except Exception:
                pass

    login_failed = any(
        r.get("status") == "failed" and str(r.get("flow_type") or "").lower() == "login" for r in early_results
    )
    if login_failed:
        skipped_tail: List[Dict[str, Any]] = []
        run_after: List[Dict[str, Any]] = []
        for tc in remaining_cases:
            action = tc.get("action") or {}
            is_dependent = action.get("kind") == "user_flow" or str(tc.get("category") or "").lower() in (
                "validation",
                "functional",
            )
            if is_dependent:
                skipped_tail.append(
                    {
                        "test_id": tc["id"],
                        "name": tc.get("name", ""),
                        "title": tc.get("title") or tc.get("name", ""),
                        "user_story": tc.get("user_story", ""),
                        "scenario": tc.get("scenario", ""),
                        "test_type": tc.get("test_type", "Positive"),
                        "component": tc.get("component") or "",
                        "page": tc.get("page") or action.get("url") or "",
                        "category": tc.get("category", ""),
                        "priority": tc.get("priority", ""),
                        "status": "skipped",
                        "expected": tc.get("expected_result", ""),
                        "expected_result": tc.get("expected_result", ""),
                        "actual": "Skipped due to critical login failure",
                        "actual_result": "Skipped due to critical login failure",
                        "error_kind": "",
                        "element_selector": "",
                        "issue_type": tc.get("category", ""),
                        "message": "early-exit-login-critical-failure",
                        "screenshot": "",
                        "screenshot_path": "",
                        "steps": tc.get("steps", []),
                        "action_kind": action.get("kind"),
                        "flow_type": action.get("flow_type"),
                        "retry_count": 0,
                        "logs": [],
                    }
                )
            else:
                # still run non-dependent checks (e.g., security/perf probes)
                run_after.append(tc)
        done = len(early_results) + len(skipped_tail)
        if progress:
            progress(done, total, "")
        if not run_after:
            return early_results + skipped_tail
        remaining_cases = run_after

    test_cases = remaining_cases
    total_remaining = len(test_cases)
    if total_remaining == 0:
        return early_results

    workers = min(int(config.TEST_EXECUTION_WORKERS), 5, max(1, total_remaining))
    if total_remaining <= 3 or workers <= 1:
        driver = create_executor_driver()
        results: List[Dict[str, Any]] = []
        try:
            for i, tc in enumerate(test_cases, start=1):
                if progress:
                    progress(len(early_results) + i, total, tc["id"])
                results.append(_run_one_case(driver, tc, profile, run_id))
        finally:
            try:
                driver.quit()
            except Exception:
                pass
        return early_results + results

    indexed = list(enumerate(test_cases))
    n_chunks = min(workers, max(1, total_remaining // 3))
    chunk_size = max(1, (total_remaining + n_chunks - 1) // n_chunks)
    chunks = [indexed[i : i + chunk_size] for i in range(0, len(indexed), chunk_size)]
    merged: Dict[int, Dict[str, Any]] = {}
    done = 0
    with ThreadPoolExecutor(max_workers=len(chunks)) as pool:
        futures = [pool.submit(_execute_chunk, ch, profile, run_id) for ch in chunks]
        for fut in as_completed(futures):
            for idx, row in fut.result():
                merged[idx] = row
                done += 1
                if progress:
                    progress(len(early_results) + done, total, row.get("test_id", ""))
    return early_results + [merged[i] for i in range(total_remaining)]
