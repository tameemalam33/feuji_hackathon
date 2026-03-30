"""API key check for external integrations (CI, scripts)."""
from __future__ import annotations

from flask import Request

import config


def api_key_authorized(request: Request) -> bool:
    """If AUTOQA_API_KEY is unset, allow all. Otherwise require Bearer or X-API-Key."""
    expected = config.AUTOQA_API_KEY
    if not expected:
        return True
    auth = request.headers.get("Authorization", "") or ""
    if auth.startswith("Bearer "):
        token = auth[7:].strip()
        if token == expected:
            return True
    if request.headers.get("X-API-Key", "") == expected:
        return True
    return False
