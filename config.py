#!/usr/bin/env python3
"""
config.py — Binance Square Oracle v1.0 统一配置

LLM 调用完全由 OpenClaw 平台内置提供，无需用户配置任何大模型 API Key。
使用 urllib 直接调用 OpenClaw 内置的 Chat Completions 端点。
"""

import json
import os
import urllib.request
import urllib.error

# --- 版本号 ---
VERSION = "1.0"

# --- 核心目录 ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROMPTS_DIR = os.path.join(SCRIPT_DIR, "prompts")
SKILLS_DIR = os.path.join(SCRIPT_DIR, "skills")
WORKSPACE_DIR = os.path.join(SCRIPT_DIR, "workspace")

# --- 广场发布 ---
SQUARE_API_KEY = os.environ.get("SQUARE_API_KEY", "")
SQUARE_POST_BASE = "https://www.binance.com/en/square/post"

# --- LLM 调用 ---
# OpenClaw 平台在 Agent 运行时自动注入 LLM 端点，
# Skill 代码通过 openclaw.invoke 或 Agent 自身的 LLM 能力完成推理，
# 此处使用 OpenClaw 内置的 Chat Completions 端点，无需任何用户配置。
_LLM_BASE_URL = "https://api.openclaw.ai/v1"
_LLM_MODEL = "gpt-4.1-mini"


def call_llm(system_prompt, user_prompt):
    """
    调用 LLM，使用 OpenClaw 平台内置 API（无需用户配置任何 Key）。
    通过 urllib 直接发送 HTTP 请求到 OpenClaw 内置端点。
    """
    payload = {
        "model": _LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
    }

    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{_LLM_BASE_URL}/chat/completions",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"]
    except (urllib.error.URLError, urllib.error.HTTPError) as e:
        raise RuntimeError(
            f"LLM call failed: {e}\n"
            f"This skill relies on the OpenClaw platform's built-in LLM. "
            f"Please ensure you are running this skill within an OpenClaw Agent environment."
        ) from e
