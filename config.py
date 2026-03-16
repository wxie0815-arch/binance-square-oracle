#!/usr/bin/env python3
"""
Shared configuration for the local Python prototype.

The primary product path for this repository is the OpenClaw-native `SKILL.md`.
These Python files are kept as a local fallback and therefore use a standard
OpenAI-compatible chat completions API instead of a hardcoded OpenClaw-only URL.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

VERSION = "1.1"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROMPTS_DIR = os.path.join(SCRIPT_DIR, "prompts")
SKILLS_DIR = os.path.join(SCRIPT_DIR, "skills")
REFERENCES_DIR = os.path.join(SCRIPT_DIR, "references")
WORKSPACE_DIR = os.path.join(SCRIPT_DIR, "workspace")

SQUARE_API_KEY = os.environ.get("SQUARE_API_KEY", "")
SQUARE_POST_BASE = "https://www.binance.com/en/square/post"

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")


def call_llm(system_prompt: str, user_prompt: str) -> str:
    """
    Call an OpenAI-compatible chat completions endpoint.

    This path is for local prototype usage only. Inside OpenClaw, prefer the
    root skill workflow rather than invoking the Python prototype directly.
    """
    if not OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY is not configured for local prototype mode. "
            "Set OPENAI_API_KEY (and optionally OPENAI_BASE_URL / OPENAI_MODEL), "
            "or use the OpenClaw-native SKILL.md workflow instead."
        )

    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }

    req = urllib.request.Request(
        f"{OPENAI_BASE_URL}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError) as exc:
        raise RuntimeError(
            f"LLM call failed against {OPENAI_BASE_URL}: {exc}"
        ) from exc

    try:
        return result["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Unexpected LLM response payload: {result}") from exc
