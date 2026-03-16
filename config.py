#!/usr/bin/env python3
"""
Shared configuration for Binance Square Oracle.

The supported LLM execution path is the OpenClaw-native root skill. This
repository does not require, document, or expect a separate third-party model
API key for article generation.
"""

from __future__ import annotations

import os

VERSION = "1.1"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROMPTS_DIR = os.path.join(SCRIPT_DIR, "prompts")
SKILLS_DIR = os.path.join(SCRIPT_DIR, "skills")
REFERENCES_DIR = os.path.join(SCRIPT_DIR, "references")
WORKSPACE_DIR = os.path.join(SCRIPT_DIR, "workspace")

SQUARE_API_KEY = os.environ.get("SQUARE_API_KEY", "")
SQUARE_POST_BASE = "https://www.binance.com/en/square/post"


def call_llm(system_prompt: str, user_prompt: str) -> str:
    """
    OpenClaw-native article generation should be executed through the root skill.

    The Python prototype intentionally does not ask for an external model API key.
    Tests can patch this function, while real generation should happen in OpenClaw
    so the skill uses the model already configured in the host system.
    """
    raise RuntimeError(
        "Standalone Python article generation is disabled. "
        "Binance Square Oracle is designed to use the model already configured in OpenClaw. "
        "Install and run the root SKILL.md in OpenClaw for real generation."
    )
