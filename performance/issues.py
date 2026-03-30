"""Detect performance issues and map optimization suggestions."""
from __future__ import annotations

from typing import Any, Dict, List


def detect_issues(perf: Dict[str, Any]) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    load = float(perf.get("load_time_ms") or 0)
    scripts = int(perf.get("script_count") or 0)
    dom_nodes = int(perf.get("dom_nodes") or 0)
    ttfb = float(perf.get("ttfb_ms") or 0)
    imgs = perf.get("images") or []

    if load > 3500:
        out.append({"issue": "Slow page load", "severity": "high"})
    if scripts > 35:
        out.append({"issue": "Too many scripts", "severity": "medium"})
    if dom_nodes > 1700:
        out.append({"issue": "Heavy DOM", "severity": "medium"})
    if ttfb > 800:
        out.append({"issue": "Slow server response", "severity": "high"})
    non_lazy = sum(1 for i in imgs if str(i.get("loading") or "").lower() != "lazy")
    if len(imgs) >= 8 and non_lazy >= len(imgs) // 2:
        out.append({"issue": "No lazy loading on many images", "severity": "medium"})
    if len(imgs) > 40:
        out.append({"issue": "Large image count", "severity": "medium"})
    return out


def map_suggestions(issues: List[Dict[str, str]]) -> List[str]:
    m = {
        "Slow page load": "Minify JS/CSS and reduce render-blocking resources.",
        "Too many scripts": "Bundle and defer non-critical JavaScript.",
        "Heavy DOM": "Simplify markup and reduce nested nodes.",
        "Slow server response": "Enable caching/CDN and optimize backend queries.",
        "No lazy loading on many images": "Use loading=\"lazy\" for below-the-fold images.",
        "Large image count": "Compress images and serve responsive formats (WebP/AVIF).",
    }
    out: List[str] = []
    for it in issues:
        s = m.get(it.get("issue") or "")
        if s and s not in out:
            out.append(s)
    return out
