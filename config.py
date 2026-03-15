#!/usr/bin/env python3
"""
config.py - 统一配置中心 v1.0 (终版)
================================================================

- 彻底移除所有 AI 模型选配配置，统一调用 OpenClaw 系统 API
- 移除 config.yaml 依赖
- 统一版本号为 1.0
"""

import os
import time
import requests
from openai import OpenAI, APIError

# ---------------------------------------------------------------------------
# 版本信息
# ---------------------------------------------------------------------------
VERSION = "1.0"
PROJECT_NAME = "Binance Square Oracle"
PROJECT_DESC = "币安广场流量预言机 — 基于 Binance Skills Hub 的智能内容创作引擎"

# ---------------------------------------------------------------------------
# 路径配置
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE = os.environ.get("WORKSPACE", "/home/ubuntu/workspace")
CACHE_DIR = os.path.join(WORKSPACE, "cache")
LOG_DIR = os.path.join(WORKSPACE, "logs")
SAVE_DIR = os.path.join(WORKSPACE, "output")
MEMORY_DIR = os.path.join(WORKSPACE, "memory")

# ---------------------------------------------------------------------------
# API Keys (从 OpenClaw 配置系统读取)
# ---------------------------------------------------------------------------
SQUARE_API_KEY = os.environ.get("SQUARE_API_KEY", "")
TOKEN_6551 = os.environ.get("TOKEN_6551", "")

# ---------------------------------------------------------------------------
# 可选模块可用性检测
# ---------------------------------------------------------------------------
HAS_6551_API = bool(TOKEN_6551)
HAS_SQUARE_API = bool(SQUARE_API_KEY)
HAS_ALPHA_MONITOR = True
HAS_DERIVATIVES_DATA = True

# ---------------------------------------------------------------------------
# API URLs
# ---------------------------------------------------------------------------
API_6551_BASE = "https://api.6551.io/v1"
SQUARE_POST_URL = "https://www.binance.com/bapi/composite/v1/public/pgc/openApi/content/add"
SQUARE_POST_BASE = "https://www.binance.com/square/post"
ALPHA_BASE_URL = "https://www.binance.com/bapi/defi/v1/public/alpha-trade"
ALPHA_TOKEN_LIST_URL = "https://www.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/cex/alpha/all/token/list"
FAPI_BASE_URL = "https://fapi.binance.com/fapi/v1"
FUTURES_DATA_URL = "https://fapi.binance.com/futures/data"

# ---------------------------------------------------------------------------
# 统一 LLM 调用 (直接使用 OpenClaw 预置的 OpenAI 客户端)
# ---------------------------------------------------------------------------
_llm_client = None

def get_llm_client() -> OpenAI:
    """获取全局唯一的 OpenAI 客户端实例"""
    global _llm_client
    if _llm_client is None:
        try:
            # OpenClaw 环境下，OpenAI() 会自动使用预置的 API Key 和 Base URL
            _llm_client = OpenAI()
        except Exception as e:
            raise ConnectionError(f"无法初始化 OpenAI 客户端: {e}。请确保在 OpenClaw 环境中运行。")
    return _llm_client

def call_llm(system_prompt: str, user_prompt: str, max_tokens: int = 3500) -> str:
    """统一的 LLM 调用函数，不再接受 model 参数"""
    client = get_llm_client()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    # OpenClaw 默认模型（可通过环境变量覆盖）
    _default_model = os.environ.get("OPENCLAW_MODEL", "gpt-4.1-mini")
    try:
        response = client.chat.completions.create(
            model=_default_model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except APIError as e:
        print(f"[LLM Error] API 调用失败: {e}")
        raise
    except Exception as e:
        print(f"[LLM Error] 未知错误: {e}")
        raise

# ---------------------------------------------------------------------------
# 统一 HTTP 客户端
# ---------------------------------------------------------------------------
DEFAULT_TIMEOUT = 15
MAX_RETRIES = 3
RETRY_BACKOFF = 1.5
COMMON_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

def http_get(url: str, **kwargs) -> requests.Response:
    """带重试的 GET 请求"""
    kwargs.setdefault("timeout", DEFAULT_TIMEOUT)
    kwargs.setdefault("headers", {})
    kwargs["headers"].update(COMMON_HEADERS)
    last_err = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, **kwargs)
            resp.raise_for_status()
            return resp
        except Exception as e:
            last_err = e
            time.sleep(RETRY_BACKOFF * (2 ** attempt))
    raise last_err

def http_post(url: str, **kwargs) -> requests.Response:
    """带重试的 POST 请求"""
    kwargs.setdefault("timeout", DEFAULT_TIMEOUT)
    kwargs.setdefault("headers", {})
    kwargs["headers"].update(COMMON_HEADERS)
    if "json" in kwargs:
        kwargs["headers"]["Content-Type"] = "application/json"
    last_err = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.post(url, **kwargs)
            resp.raise_for_status()
            return resp
        except Exception as e:
            last_err = e
            time.sleep(RETRY_BACKOFF * (2 ** attempt))
    raise last_err
