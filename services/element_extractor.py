"""Normalize crawled DOM hints into structured records for test execution."""
from __future__ import annotations

import json
from typing import Any, Dict, List

from services.crawler import PageSnapshot, _normalize_url


def extract_elements(crawl_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Produce structured records: type, selector (strategy hint), text, page_url, meta.
    Execution uses tag + index within page for stability.
    """
    out: List[Dict[str, Any]] = []
    pages: List[PageSnapshot] = crawl_result.get("pages") or []

    for snap in pages:
        url = _normalize_url(snap.url or "")
        pc = getattr(snap, "page_class", None) or "STATIC"
        if snap.error:
            out.append(
                {
                    "type": "page",
                    "selector": "body",
                    "text": snap.error,
                    "page_url": url,
                    "meta": {
                        "broken": True,
                        "strategy": "tag",
                        "tag": "body",
                        "index": 0,
                        "page_class": pc,
                    },
                }
            )
            continue

        out.append(
            {
                "type": "document",
                "selector": "title",
                "text": snap.title or "",
                "page_url": url,
                "meta": {"strategy": "title", "load_ms": snap.load_time_ms, "page_class": pc},
            }
        )

        for i, link in enumerate(snap.links[:60]):
            if not link.get("href"):
                continue
            out.append(
                {
                    "type": "link",
                    "selector": f"a[{i}]",
                    "text": (link.get("text") or link.get("href") or "")[:200],
                    "page_url": url,
                    "meta": {
                        "strategy": "tag_index",
                        "tag": "a",
                        "index": i,
                        "visible": link.get("visible"),
                        "page_class": pc,
                    },
                }
            )

        for i, btn in enumerate(snap.buttons[:40]):
            out.append(
                {
                    "type": "button",
                    "selector": f"button-input[{i}]",
                    "text": (btn.get("text") or "")[:200] or f"button-{i}",
                    "page_url": url,
                    "meta": {
                        "strategy": "tag_index",
                        "tag": btn.get("tag", "button"),
                        "index": i,
                        "visible": btn.get("visible"),
                        "page_class": pc,
                    },
                }
            )

        for i, inp in enumerate(snap.inputs[:50]):
            name = inp.get("name") or ""
            ph = inp.get("placeholder") or ""
            itype = inp.get("type") or "text"
            label = name or ph or f"{itype}-{i}"
            out.append(
                {
                    "type": "input",
                    "selector": f"input[{i}]",
                    "text": label[:200],
                    "page_url": url,
                    "meta": {
                        "strategy": "tag_index",
                        "tag": inp.get("tag", "input"),
                        "index": i,
                        "input_type": itype,
                        "visible": inp.get("visible"),
                        "page_class": pc,
                    },
                }
            )

        for i, form in enumerate(snap.forms[:20]):
            out.append(
                {
                    "type": "form",
                    "selector": f"form[{i}]",
                    "text": f"form-{i}-{form.get('method', 'GET')}",
                    "page_url": url,
                    "meta": {"strategy": "tag_index", "tag": "form", "index": i, "page_class": pc},
                }
            )

    return out


def elements_to_json(elements: List[Dict[str, Any]]) -> str:
    return json.dumps(elements, ensure_ascii=False, indent=2)
