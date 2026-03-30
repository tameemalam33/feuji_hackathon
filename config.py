"""Application configuration for AutoQA Pro."""
import os

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
DATABASE_PATH = os.path.join(INSTANCE_DIR, "autoqa.db")
SCREENSHOTS_DIR = os.path.join(BASE_DIR, "static", "screenshots")
VISUAL_BASE_DIR = os.path.join(SCREENSHOTS_DIR, "visual")

# Selenium
SELENIUM_PAGE_LOAD_TIMEOUT = int(_env("AUTOQA_PAGE_LOAD_TIMEOUT_SEC", "10"))
SELENIUM_IMPLICIT_WAIT = 3
SELENIUM_SCRIPT_TIMEOUT = 20
PER_TEST_TIMEOUT_SEC = 18

# Crawl settings
MAX_CRAWL_PAGES_DEFAULT = int(_env("MAX_CRAWL_PAGES", "30"))
MAX_CRAWL_PAGES_MIN = 10
MAX_CRAWL_PAGES_MAX = 5000
MAX_PAGES_QUICK = 10
MAX_PAGES_STANDARD = 30
MAX_PAGES_DEEP = 100
MAX_DEPTH_QUICK = int(_env("AUTOQA_MAX_DEPTH_QUICK", "1"))
MAX_DEPTH_STANDARD = int(_env("AUTOQA_MAX_DEPTH_STANDARD", "2"))
MAX_DEPTH_DEEP = int(_env("AUTOQA_MAX_DEPTH_DEEP", "3"))
MAX_DEPTH_FULL = int(_env("AUTOQA_MAX_DEPTH_FULL", "3"))
MAX_PAGES_SAFETY_FULL = int(_env("AUTOQA_FULL_MODE_SAFETY_PAGES", "200"))
MAX_LINKS_TO_QUEUE = 120
CRAWL_ALLOW_FULL_SITE = _env("AUTOQA_FULL_SITE_CRAWL", "1") == "1"
CRAWL_SOFT_PAGE_CAP = int(_env("AUTOQA_CRAWL_SOFT_CAP", "5000"))
CRAWL_WORKERS = max(1, int(_env("AUTOQA_CRAWL_WORKERS", "3")))
CRAWL_RETRIES = max(0, int(_env("AUTOQA_CRAWL_RETRIES", "2")))
SLOW_PAGE_THRESHOLD_MS = int(_env("AUTOQA_SLOW_PAGE_MS", "3500"))
VISUAL_DIFF_THRESHOLD_PERCENT = float(_env("AUTOQA_VISUAL_DIFF_THRESHOLD", "5"))
# Performance scoring (ms)
PERF_SCORE_GOOD_MS = 2000.0
PERF_SCORE_BAD_MS = 15000.0

# Smart test generation (category-based; no brute-force filler)
SMART_TESTS_PER_PAGE_QUICK = 8
SMART_TESTS_PER_PAGE_STANDARD = 14
SMART_TESTS_PER_PAGE_DEEP = 20
# Legacy aliases (kept for external scripts)
MIN_TEST_CASES = 1
MAX_TEST_CASES = 500

# Parallel test execution (one WebDriver per worker)
TEST_EXECUTION_WORKERS = max(1, min(6, int(_env("AUTOQA_TEST_WORKERS", "4"))))
TEST_EXECUTION_WORKERS = max(1, min(5, TEST_EXECUTION_WORKERS))

# Integrations: set AUTOQA_API_KEY to require Bearer / X-API-Key on POST /api/run-full-test
AUTOQA_API_KEY = _env("AUTOQA_API_KEY")
# Public base URL for webhook payloads (links). If empty, each request uses Host header.
PUBLIC_BASE_URL = _env("PUBLIC_BASE_URL").rstrip("/")

WEBHOOK_TIMEOUT_SEC = int(_env("WEBHOOK_TIMEOUT_SEC", "12"))

# Alert if latest run has at least this many critical-severity failures
CRITICAL_ALERT_THRESHOLD = int(_env("AUTOQA_CRITICAL_ALERT_THRESHOLD", "1"))

# LLM analysis settings (failure-only intelligence layer)
LLM_API_KEY = _env("LLM_API_KEY")
OPENAI_API_KEY = _env("OPENAI_API_KEY")
GROQ_API_KEY = _env("GROQ_API_KEY")
LLM_PROVIDER = _env(
    "LLM_PROVIDER",
    "groq" if GROQ_API_KEY else "openai",
).lower()
LLM_MODEL = _env("LLM_MODEL")
LLM_MAX_FAILURE_ANALYSIS = max(0, min(5, int(_env("LLM_MAX_FAILURE_ANALYSIS", "3"))))

os.makedirs(INSTANCE_DIR, exist_ok=True)
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
os.makedirs(VISUAL_BASE_DIR, exist_ok=True)
