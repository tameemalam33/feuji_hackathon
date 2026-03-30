"""HTTP webhook delivery for integration (Slack, CI, custom receivers)."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Dict, Optional, Tuple


def send_run_completed_webhook(
    webhook_url: str,
    payload: Dict[str, Any],
    timeout_sec: int = 12,
) -> Tuple[bool, Optional[int], str]:
    """
    POST JSON to webhook_url. Returns (success, http_status_or_none, error_message).
    Failures do not raise; callers decide whether to surface to clients.
    """
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "AutoQA-Pro/1.0 (+https://github.com)",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            code = resp.getcode()
            return True, code, ""
    except urllib.error.HTTPError as e:
        try:
            code = e.code
        except Exception:
            code = None
        return False, code, (e.reason or str(e))[:300]
    except urllib.error.URLError as e:
        return False, None, str(e.reason or e)[:300]
    except Exception as e:
        return False, None, str(e)[:300]
