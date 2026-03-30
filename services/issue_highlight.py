"""Highlight failing DOM element (by selector) and return screenshot evidence."""
from __future__ import annotations

import hashlib
import os
import time
from typing import Any, Dict, Optional, Tuple

import config
from services.driver_factory import create_executor_driver


def _web_path(abs_path: str) -> str:
    base = os.path.basename(abs_path)
    return f"/static/screenshots/{base}"


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def highlight_element_screenshot(
    *,
    page_url: str,
    element_selector: str,
    run_id: int,
    test_id: str,
    timeout_sec: int = 10,
) -> Dict[str, Any]:
    """
    Loads page_url, applies a red border/outline to the first element matching element_selector,
    and returns a screenshot URL + whether selector was found.
    """
    driver = create_executor_driver()
    highlights_dir = os.path.join(config.SCREENSHOTS_DIR, "highlights")
    _ensure_dir(highlights_dir)

    selector = (element_selector or "").strip()
    page_url = (page_url or "").strip()

    selector_hash = hashlib.sha256(selector.encode("utf-8")).hexdigest()[:10]
    safe_test = (test_id or "").replace("/", "-").replace("\\", "-")[:60]
    fname = f"hl_{run_id}_{safe_test}_{selector_hash}.png"
    abs_shot = os.path.join(highlights_dir, fname)

    found = False
    try:
        driver.get(page_url)
        # Wait a tick for SPA render.
        time.sleep(0.8)

        found = bool(
            driver.execute_script(
                """
                (function(sel){
                  try {
                    if(!sel) return {found:false};
                    var el = document.querySelector(sel);
                    if(!el) return {found:false};
                    el.style.outline = '2px solid rgba(239, 68, 68, 0.95)';
                    el.style.border = '3px solid rgba(239, 68, 68, 0.95)';
                    el.scrollIntoView({block:'center', inline:'nearest'});
                    return {found:true};
                  } catch (e) {
                    return {found:false};
                  }
                })(arguments[0]);
                """,
                selector,
            ).get("found", False)
        )
        time.sleep(0.35)
        driver.save_screenshot(abs_shot)
    finally:
        try:
            driver.quit()
        except Exception:
            pass

    return {
        "found": found,
        "screenshotUrl": _web_path(abs_shot),
        "screenshotPath": abs_shot,
    }

