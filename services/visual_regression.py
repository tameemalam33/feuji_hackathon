"""Baseline/current screenshot diff utilities."""
from __future__ import annotations

import os
from typing import Dict

try:
    from PIL import Image, ImageChops
except Exception:  # pragma: no cover
    Image = None
    ImageChops = None


def ensure_dirs(base_dir: str) -> Dict[str, str]:
    baseline = os.path.join(base_dir, "baseline")
    current = os.path.join(base_dir, "current")
    diff = os.path.join(base_dir, "diff")
    for p in (baseline, current, diff):
        os.makedirs(p, exist_ok=True)
    return {"baseline": baseline, "current": current, "diff": diff}


def compare_page_screenshot(
    *,
    page_key: str,
    run_id: int,
    src_path: str,
    screenshots_root: str,
    mismatch_threshold: float = 5.0,
) -> Dict[str, object]:
    dirs = ensure_dirs(screenshots_root)
    safe = page_key.replace("/", "_").replace("\\", "_").replace(":", "_")[:140]
    base_path = os.path.join(dirs["baseline"], f"{safe}.png")
    cur_path = os.path.join(dirs["current"], f"{run_id}_{safe}.png")
    diff_path = os.path.join(dirs["diff"], f"{run_id}_{safe}.png")

    if Image is None or ImageChops is None:
        return {"baseline_path": "", "current_path": "", "diff_path": "", "mismatch_percent": 0.0, "status": "pillow_missing"}

    try:
        img_cur = Image.open(src_path).convert("RGB")
        img_cur.save(cur_path)
    except Exception:
        return {"baseline_path": "", "current_path": cur_path, "diff_path": "", "mismatch_percent": 0.0, "status": "error"}

    if not os.path.exists(base_path):
        img_cur.save(base_path)
        return {
            "baseline_path": base_path,
            "current_path": cur_path,
            "diff_path": "",
            "mismatch_percent": 0.0,
            "status": "baseline_created",
            "failed": False,
        }

    img_base = Image.open(base_path).convert("RGB")
    if img_base.size != img_cur.size:
        img_base = img_base.resize(img_cur.size)

    delta = ImageChops.difference(img_base, img_cur)
    gray = delta.convert("L")
    hist = gray.histogram()
    changed = sum(hist[1:])
    total = gray.size[0] * gray.size[1]
    mismatch = round((changed / max(total, 1)) * 100.0, 2)

    mask = gray.point(lambda p: 255 if p > 15 else 0)
    overlay = img_cur.copy()
    red = Image.new("RGB", img_cur.size, (255, 0, 0))
    overlay.paste(red, mask=mask)
    overlay.save(diff_path)

    return {
        "baseline_path": base_path,
        "current_path": cur_path,
        "diff_path": diff_path,
        "mismatch_percent": mismatch,
        "status": "changed" if mismatch > 0 else "same",
        "failed": mismatch > float(mismatch_threshold),
    }
