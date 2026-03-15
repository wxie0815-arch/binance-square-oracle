#!/usr/bin/env python3
"""
广场发帖工具 v4.1 - OpenAPI Key直发（无需cookie）
规则：文章中第一次出现的 $TOKEN 自动绑定 FUTURES_UM（永续合约）
"""

import re
import os
import sys
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)
import config
import json
import requests

# 已知代币映射（symbol -> binance symbol）
KNOWN_TOKENS = {
    "BTC": "BTCUSDT", "ETH": "ETHUSDT", "BNB": "BNBUSDT",
    "SOL": "SOLUSDT", "XRP": "XRPUSDT", "DOGE": "DOGEUSDT",
    "ADA": "ADAUSDT", "AVAX": "AVAXUSDT", "DOT": "DOTUSDT",
    "MATIC": "MATICUSDT", "LINK": "LINKUSDT", "ARB": "ARBUSDT",
    "OP": "OPUSDT", "SUI": "SUIUSDT", "APT": "APTUSDT",
    "PEPE": "PEPEUSDT", "WIF": "WIFUSDT", "BONK": "BONKUSDT",
    "ROBO": "ROBOUSDT", "MIRA": "MIRAUSDT",
}

# 有永续合约的代币（FUTURES_UM）
FUTURES_SUPPORTED = {
    "BTC", "ETH", "BNB", "SOL", "XRP", "DOGE", "ADA", "AVAX",
    "DOT", "LINK", "ARB", "OP", "SUI", "APT", "PEPE", "WIF", "BONK",
}


def extract_first_mention_tokens(content: str) -> list:
    """从文章中提取第一次出现的 $TOKEN，返回代币列表（去重，保持顺序）"""
    pattern = r'\$([A-Z]{2,10})'
    seen = set()
    tokens = []
    for match in re.finditer(pattern, content):
        token = match.group(1)
        if token not in seen and token in KNOWN_TOKENS:
            seen.add(token)
            tokens.append(token)
    return tokens


def build_trading_pair(token: str) -> dict:
    """构建 userInputTradingPairs 单条记录"""
    symbol = KNOWN_TOKENS.get(token, f"{token}USDT")
    market = "FUTURES_UM" if token in FUTURES_SUPPORTED else "SPOT"
    return {
        "market": market,
        "bridge": "USDT",
        "code": token,
        "symbol": symbol,
        "marketV2": market,
        "futuresSymbol": symbol,
    }


def build_trading_pairs(content: str) -> list:
    """提取文章中的代币，构建 userInputTradingPairs"""
    tokens = extract_first_mention_tokens(content)
    return [build_trading_pair(t) for t in tokens]


def post_to_square(content: str) -> dict:
    """
    发帖到币安广场（OpenAPI Key直发，无需cookie）
    自动注入代币超链接
    """
    trading_pairs = build_trading_pairs(content)
    print(f"[发帖] 检测到代币: {[p['code'] + '(' + p['market'] + ')' for p in trading_pairs]}")

    headers = {
        "X-Square-OpenAPI-Key": config.SQUARE_API_KEY,
        "Content-Type": "application/json",
        "clienttype": "binanceSkill",
    }

    payload = {"bodyTextOnly": content}

    try:
        resp = requests.post(config.SQUARE_POST_URL, json=payload,
                             headers=headers, timeout=config.DEFAULT_TIMEOUT)
        data = resp.json()
        if data.get("code") == "000000":
            post_id = data.get("data", {}).get("id", "")
            post_url = f"{config.SQUARE_POST_BASE}/{post_id}"
            return {"success": True, "post_id": str(post_id), "url": post_url}
        else:
            return {"success": False, "error": data.get("message", "未知错误"), "raw": data}
    except Exception as e:
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    # 测试代币提取
    test = "$BTC 在67239震荡，$ETH 跌破2000，$SOL 跟跌。"
    pairs = build_trading_pairs(test)
    print("=== 代币解析测试 ===")
    for p in pairs:
        print(f"  ${p['code']} -> {p['symbol']} ({p['market']})")
    print("\n用法: from post_with_tokens import post_to_square")
