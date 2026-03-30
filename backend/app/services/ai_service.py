"""ai_service.py — AI-powered time-block suggestions.

Supports two providers:
  - mistral   : Mistral API via httpx
  - claude-code : Local `claude` CLI via subprocess (non-interactive -p mode)
  - disabled  : No-op

Both providers receive the same structured prompt and are expected to return
a JSON object matching {"blocks": [...], "rationale": "..."}.
"""
from __future__ import annotations

import json
import logging
import re
import subprocess

import httpx

from app.config import settings
from app.models import AISuggestionResponse, TimeBlock

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a personal productivity assistant. "
    "You help plan daily schedules by suggesting time blocks. "
    "Respond ONLY with valid JSON — no markdown, no explanation outside the JSON object."
)

_RESPONSE_SCHEMA = """{
  "blocks": [
    {"start": "HH:MM", "end": "HH:MM", "label": "string", "type": "focus|admin|break|personal|health"}
  ],
  "rationale": "one or two sentence explanation"
}"""


def _build_prompt(date_str: str, content: str, open_tasks: list[str]) -> str:
    tasks_text = "\n".join(f"- {t}" for t in open_tasks) if open_tasks else "(none)"
    return (
        f"Today is {date_str}.\n\n"
        f"Current daily note:\n```\n{content[:3000]}\n```\n\n"
        f"Open tasks:\n{tasks_text}\n\n"
        f"Suggest a realistic schedule of time blocks for today.\n"
        f"Respond with this exact JSON schema:\n{_RESPONSE_SCHEMA}"
    )


def _strip_fences(text: str) -> str:
    """Remove ```json ... ``` or ``` ... ``` wrappers from LLM output."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _parse_response(raw: str) -> AISuggestionResponse:
    cleaned = _strip_fences(raw)
    data = json.loads(cleaned)
    blocks = [TimeBlock(**b) for b in data.get("blocks", [])]
    return AISuggestionResponse(blocks=blocks, rationale=data.get("rationale", ""))


# ---------------------------------------------------------------------------
# Provider implementations
# ---------------------------------------------------------------------------

async def _call_mistral(prompt: str) -> str:
    if not settings.MISTRAL_API_KEY:
        raise RuntimeError("MISTRAL_API_KEY is not set")
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.MISTRAL_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.MISTRAL_MODEL,
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 1024,
                "temperature": 0.3,
            },
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


def _call_claude_code(prompt: str) -> str:
    """Invoke the local `claude` CLI in non-interactive print mode."""
    full_prompt = f"{_SYSTEM_PROMPT}\n\n{prompt}"
    result = subprocess.run(
        ["claude", "-p", full_prompt],
        capture_output=True,
        text=True,
        timeout=90,
    )
    if result.returncode != 0:
        raise RuntimeError(f"claude CLI exited {result.returncode}: {result.stderr[:500]}")
    return result.stdout


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def suggest(
    date_str: str,
    daily_content: str,
    open_tasks: list[str],
    free_slots: list[dict] | None = None,
) -> AISuggestionResponse:
    if settings.AI_PROVIDER == "disabled":
        return AISuggestionResponse(blocks=[], rationale="AI suggestions are disabled.")

    prompt = _build_prompt(date_str, daily_content, open_tasks)

    if free_slots:
        slots_text = "\n".join(
            f"- {s['start']} – {s['end']} ({s.get('duration_minutes', '?')} min free)"
            for s in free_slots
        )
        prompt += f"\n\nFree time blocks from Google Calendar:\n{slots_text}"

    try:
        if settings.AI_PROVIDER == "mistral":
            raw = await _call_mistral(prompt)
        elif settings.AI_PROVIDER == "claude-code":
            # subprocess is blocking; run in threadpool via asyncio
            import asyncio
            raw = await asyncio.get_event_loop().run_in_executor(
                None, _call_claude_code, prompt
            )
        else:
            return AISuggestionResponse(blocks=[], rationale="Unknown AI provider.")

        return _parse_response(raw)

    except json.JSONDecodeError as exc:
        logger.error("AI response was not valid JSON: %s", exc)
        return AISuggestionResponse(blocks=[], rationale=f"AI returned invalid JSON: {exc}")
    except Exception as exc:
        logger.error("AI suggestion failed: %s", exc)
        return AISuggestionResponse(blocks=[], rationale=f"AI error: {exc}")
