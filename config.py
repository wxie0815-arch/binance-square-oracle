#!/usr/bin/env python3
"""
config.py — Binance Square Oracle v1.0 统一配置
"""

import os
from openai import OpenAI

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
# OpenClaw 平台已通过系统环境变量注入 OPENAI_API_KEY 和 OPENAI_BASE_URL，
# 无需用户手动配置任何大模型 API Key。
_api_key = os.environ.get("OPENAI_API_KEY", "openclaw-builtin")
_base_url = os.environ.get("OPENAI_BASE_URL") or os.environ.get("OPENAI_API_BASE") or None
client = OpenAI(api_key=_api_key, base_url=_base_url)

def call_llm(system_prompt, user_prompt):
    """调用 LLM，使用 OpenClaw 系统内置 API（无需用户配置）"""
    model = os.environ.get("OPENCLAW_MODEL", "gpt-4.1-mini")
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
    )
    return response.choices[0].message.content
