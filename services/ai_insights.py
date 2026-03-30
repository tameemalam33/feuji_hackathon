"""Optional LLM-backed insights for failures and summary."""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List

import config


def _resolve_llm_credentials() -> tuple[str, str, str]:
    provider = (config.LLM_PROVIDER or "openai").lower()
    model = config.LLM_MODEL or "gpt-4o-mini"
    api_key = (
        config.LLM_API_KEY
        or (config.GROQ_API_KEY if provider == "groq" else config.OPENAI_API_KEY)
        or os.environ.get("LLM_API_KEY", "").strip()
        or os.environ.get("OPENAI_API_KEY", "").strip()
    )
    if provider == "groq":
        endpoint = "https://api.groq.com/openai/v1/chat/completions"
    else:
        endpoint = "https://api.openai.com/v1/chat/completions"
    return provider, api_key, endpoint


def _chat_completion(messages: List[Dict[str, str]], max_tokens: int = 220, temperature: float = 0.2) -> str:
    provider, api_key, endpoint = _resolve_llm_credentials()
    if not api_key:
        return ""
    try:
        import urllib.request

        payload = {
            "model": config.LLM_MODEL if config.LLM_MODEL else ("llama-3.1-8b-instant" if provider == "groq" else "gpt-4o-mini"),
            "messages": messages,
            "max_tokens": int(max_tokens),
            "temperature": float(temperature),
        }
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=25) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return (
            (data.get("choices") or [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )
    except Exception:
        return ""


def analyze_failure(test_result: Dict[str, Any]) -> Dict[str, str]:
    """
    Analyze one failed test and return structured reason/fix.
    Output: { reason: str, fix: str }
    """
    scenario = str(test_result.get("scenario") or test_result.get("name") or "")[:300]
    error_message = str(test_result.get("actual") or test_result.get("actual_result") or test_result.get("message") or "")[:700]
    expected = str(test_result.get("expected") or test_result.get("expected_result") or "")[:350]
    actual = str(test_result.get("actual") or test_result.get("actual_result") or "")[:350]
    prompt = (
        "Analyze the following test failure and provide:\n"
        "1. Root cause\n"
        "2. Suggested fix\n\n"
        f"Scenario: {scenario}\n"
        f"Error: {error_message}\n"
        f"Expected: {expected}\n"
        f"Actual: {actual}\n\n"
        'Respond as strict JSON object only: {"reason":"...","fix":"..."}'
    )
    text = _chat_completion(
        [
            {"role": "system", "content": "You are a senior QA engineer. Return concise root cause and fix."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=260,
        temperature=0.2,
    )
    if not text:
        return {"reason": "", "fix": ""}
    try:
        data = json.loads(text)
        return {
            "reason": str(data.get("reason") or "").strip(),
            "fix": str(data.get("fix") or "").strip(),
        }
    except Exception:
        return {"reason": "", "fix": ""}


def enrich_failed_results_with_ai(results: List[Dict[str, Any]], max_calls: int | None = None) -> List[Dict[str, Any]]:
    cap = config.LLM_MAX_FAILURE_ANALYSIS if max_calls is None else max(0, min(5, int(max_calls)))
    if cap <= 0:
        return results
    _, api_key, _ = _resolve_llm_credentials()
    if not api_key:
        return results
    out: List[Dict[str, Any]] = []
    used = 0
    for r in results:
        rr = dict(r)
        if rr.get("status") == "failed" and used < cap:
            ai = analyze_failure(rr)
            if ai.get("reason"):
                rr["ai_reason"] = ai["reason"]
                rr["root_cause"] = ai["reason"]
            if ai.get("fix"):
                rr["ai_fix"] = ai["fix"]
                rr["suggestion"] = ai["fix"]
            used += 1
        out.append(rr)
    return out


def maybe_enhance_insights(insights: List[str], results: List[Dict[str, Any]]) -> List[str]:
    """Prepend a short AI summary when LLM key is set; otherwise return insights unchanged."""
    _, api_key, _ = _resolve_llm_credentials()
    if not api_key:
        return insights
    failed = [r for r in results if r.get("status") == "failed"][:12]
    if not failed:
        return insights
    text = _chat_completion(
        [
            {
                "role": "system",
                "content": "You are a QA lead. Reply with 2-4 short plain lines summarizing risk themes.",
            },
            {
                "role": "user",
                "content": json.dumps(
                    [
                        {
                            "name": x.get("name"),
                            "severity": x.get("severity"),
                            "actual": (x.get("actual") or "")[:200],
                        }
                        for x in failed
                    ],
                    ensure_ascii=False,
                ),
            },
        ],
        max_tokens=180,
        temperature=0.3,
    )
    if not text:
        return insights
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    prefix = ["(AI summary)"] + lines[:6]
    return prefix + [""] + insights
