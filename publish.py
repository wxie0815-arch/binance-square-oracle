#!/usr/bin/env python3
"""
publish.py — C 方案 L8 可选发布层 v1.1
调用官方 square-post v1.1 接口，发布文章到币安广场
"""

import json
import os
import urllib.request
import urllib.error

SQUARE_API_KEY = os.environ.get("SQUARE_API_KEY", "")
SQUARE_API_BASE = "https://www.binance.com/bapi/square/v1/public/square/user-article/post"

def publish_to_square(article_content, title="AI 生成的加密市场分析"):
    if not SQUARE_API_KEY:
        return {"skipped": True, "reason": "SQUARE_API_KEY not configured"}

    payload = {
        "title": title,
        "content": article_content,
        "publishTime": 0, # 0 for immediate publish
        "coverUrl": "",
        "mentionedUsers": [],
        "mentionedCoins": ["BTC"], # Can be dynamically extracted from content
        "hashtags": ["#Binance", "#CryptoAnalysis", "#BTC"], # Can be dynamically generated
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {SQUARE_API_KEY}",
    }

    try:
        body = json.dumps(payload).encode()
        req = urllib.request.Request(SQUARE_API_BASE, data=body, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as r:
            response = json.loads(r.read().decode())
            if response.get("code") == "000000":
                return {"success": True, "data": response.get("data")}
            else:
                return {"error": True, "response": response}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    print("测试 L8 发布功能...")
    if not SQUARE_API_KEY:
        print("SQUARE_API_KEY 未配置，跳过测试。")
    else:
        mock_article = "这是一个由 binance-square-oracle v1.1 (C方案) 生成的测试帖子。#BTC"
        result = publish_to_square(mock_article)
        print(f"发布结果: {result}")
