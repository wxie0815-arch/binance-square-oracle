#!/usr/bin/env python3
import os
from openai import OpenAI

# --- 版本号 ---
VERSION = "1.1"

# --- 核心目录 ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROMPTS_DIR = os.path.join(SCRIPT_DIR, "prompts")
SKILLS_DIR = os.path.join(SCRIPT_DIR, "skills")
MEMORY_DIR = os.path.join(SCRIPT_DIR, "workspace", "memory")
WORKSPACE_DIR = os.path.join(SCRIPT_DIR, "workspace")

# --- 广场发布 ---
SQUARE_API_KEY = os.environ.get("SQUARE_API_KEY", "")
SQUARE_POST_BASE = "https://www.binance.com/en/square/post"

# --- LLM 调用 --- 
client = OpenAI()

def call_llm(system_prompt, user_prompt):
    model = os.environ.get("OPENCLAW_MODEL", "gpt-4.1-mini")
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
    )
    return response.choices[0].message.content
