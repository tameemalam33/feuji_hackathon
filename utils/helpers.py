"""URL validation and normalization."""
import re
from urllib.parse import urlparse

_SCHEMES = ("http", "https")


def normalize_url(url: str) -> str:
    u = (url or "").strip()
    if not u:
        return ""
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", u):
        u = "https://" + u
    return u.rstrip("/") or u


def validate_url(url: str) -> tuple[bool, str]:
    u = normalize_url(url)
    if not u:
        return False, "URL is empty."
    try:
        p = urlparse(u)
    except Exception:
        return False, "Invalid URL format."
    if p.scheme not in _SCHEMES:
        return False, "Only http and https URLs are supported."
    if not p.netloc:
        return False, "Missing host in URL."
    return True, u
