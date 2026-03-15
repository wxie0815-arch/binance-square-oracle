#!/usr/bin/env python3
"""
publish.py — Binance Square Oracle v1.0 广场发布层（可选）
调用官方 binance/square-post 接口，发布文章到币安广场。
需要 SQUARE_API_KEY 环境变量。
"""

import json
import os
import re
import urllib.request
import urllib.error

SQUARE_API_KEY = os.environ.get("SQUARE_API_KEY", "")
SQUARE_API_URL = "https://www.binance.com/bapi/composite/v1/public/pgc/openApi/content/add"

# 常见加密货币代币列表（用于从文章中提取 mentionedCoins）
KNOWN_COINS = [
    "BTC", "ETH", "BNB", "SOL", "XRP", "DOGE", "ADA", "AVAX", "DOT", "MATIC",
    "LINK", "UNI", "ATOM", "FIL", "APT", "ARB", "OP", "SUI", "SEI", "TIA",
    "PEPE", "SHIB", "FLOKI", "WIF", "BONK", "MEME", "ORDI", "SATS", "INJ",
    "FET", "RNDR", "NEAR", "ICP", "TRX", "LTC", "BCH", "ETC", "TON", "ALGO",
]


def _extract_coins(text):
    """从文章文本中提取提及的加密货币代币"""
    found = []
    upper_text = text.upper()
    for coin in KNOWN_COINS:
        if coin in upper_text:
            found.append(coin)
    return found[:5]  # 最多 5 个


def _extract_hashtags(text):
    """从文章文本中提取 #hashtags"""
    tags = re.findall(r'#(\w+)', text)
    # 去重并保持顺序
    seen = set()
    unique_tags = []
    for tag in tags:
        if tag.lower() not in seen:
            seen.add(tag.lower())
            unique_tags.append(f"#{tag}")
    # 确保至少有基础标签
    base_tags = ["#Binance", "#CryptoAnalysis"]
    for bt in base_tags:
        if bt.lower() not in seen:
            unique_tags.append(bt)
    return unique_tags[:5]


def publish_to_square(article_content, title=""):
    """
    发布文章到币安广场。
    使用官方 binance/square-post 接口。
    """
    if not SQUARE_API_KEY:
        return {"skipped": True, "reason": "SQUARE_API_KEY not configured"}

    # 检查字符限制
    if len(article_content) > 500:
        print(f"[publish] Warning: Article length ({len(article_content)}) exceeds 500 chars, truncating...")
        article_content = article_content[:497] + "..."

    # 动态提取 hashtags 和 mentionedCoins
    coins = _extract_coins(article_content)
    hashtags = _extract_hashtags(article_content)

    # 构建发布内容（hashtags 追加到正文末尾）
    body_text = article_content
    tag_str = " ".join(hashtags)
    if tag_str and tag_str not in body_text:
        body_text = f"{body_text}\n\n{tag_str}"

    payload = {
        "bodyTextOnly": body_text,
    }

    headers = {
        "Content-Type": "application/json",
        "X-Square-OpenAPI-Key": SQUARE_API_KEY,
        "clienttype": "binanceSkill",
    }

    try:
        body = json.dumps(payload).encode()
        req = urllib.request.Request(SQUARE_API_URL, data=body, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as r:
            response = json.loads(r.read().decode())
            if response.get("code") == "000000":
                post_id = response.get("data", {}).get("id", "")
                post_url = f"https://www.binance.com/square/post/{post_id}" if post_id else ""
                print(f"[publish] Success! Post URL: {post_url}")
                return {"success": True, "data": response.get("data"), "url": post_url}
            else:
                return {"error": True, "code": response.get("code"), "message": response.get("message"), "response": response}
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    print("[publish] Binance Square Publisher v1.0")
    if not SQUARE_API_KEY:
        print("[publish] SQUARE_API_KEY not configured. Set it to enable publishing.")
    else:
        print("[publish] Ready to publish. Use: publish_to_square('your article text')")
