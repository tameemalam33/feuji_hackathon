"""WebDriver factory for Chrome, Edge, and mobile-style viewports."""
from __future__ import annotations

import os

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.edge.service import Service as EdgeService
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager

import config


def _chrome_options() -> ChromeOptions:
    opts = ChromeOptions()
    opts.add_argument("--headless")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    # Keep Chrome closer to a normal user session and away from automation defaults.
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
    return opts


def _edge_options() -> EdgeOptions:
    opts = EdgeOptions()
    opts.add_argument("--headless")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    try:
        opts.set_capability("ms:loggingPrefs", {"browser": "ALL", "performance": "ALL"})
    except Exception:
        pass
    return opts


def create_executor_driver(browser_profile: str | None = None) -> webdriver.Remote:
    """
    AUTOQA_BROWSER: chrome | edge | mobile (Chrome with phone viewport).
    """
    raw = (browser_profile or os.environ.get("AUTOQA_BROWSER", "chrome") or "chrome").lower()
    if raw in ("mobile", "mobile_chrome", "phone"):
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=_chrome_options())
        driver.set_window_size(390, 844)
        driver.set_page_load_timeout(config.SELENIUM_PAGE_LOAD_TIMEOUT)
        driver.set_script_timeout(config.SELENIUM_SCRIPT_TIMEOUT)
        driver.implicitly_wait(config.SELENIUM_IMPLICIT_WAIT)
        return driver

    if raw == "edge":
        service = EdgeService(EdgeChromiumDriverManager().install())
        driver = webdriver.Edge(service=service, options=_edge_options())
        driver.set_page_load_timeout(config.SELENIUM_PAGE_LOAD_TIMEOUT)
        driver.set_script_timeout(config.SELENIUM_SCRIPT_TIMEOUT)
        driver.implicitly_wait(config.SELENIUM_IMPLICIT_WAIT)
        return driver

    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=_chrome_options())
    driver.set_page_load_timeout(config.SELENIUM_PAGE_LOAD_TIMEOUT)
    driver.set_script_timeout(config.SELENIUM_SCRIPT_TIMEOUT)
    driver.implicitly_wait(config.SELENIUM_IMPLICIT_WAIT)
    # Remove the simplest webdriver fingerprint before any page scripts run.
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
