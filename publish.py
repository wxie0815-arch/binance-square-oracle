#!/usr/bin/env python3
"""Optional Binance Square publishing helper."""

from __future__ import annotations

import json
import os
import re
import urllib.request

SQUARE_API_KEY = os.environ.get("SQUARE_API_KEY", "")
SQUARE_API_URL = "https://www.binance.com/bapi/composite/v1/public/pgc/openApi/content/add"
MAX_SQUARE_BODY_LENGTH = 500

KNOWN_COINS = [
    "BTC", "ETH", "BNB", "SOL", "XRP", "DOGE", "ADA", "AVAX", "DOT", "MATIC",
    "LINK", "UNI", "ATOM", "FIL", "APT", "ARB", "OP", "SUI", "SEI", "TIA",
    "PEPE", "SHIB", "FLOKI", "WIF", "BONK", "MEME", "ORDI", "SATS", "INJ",
    "FET", "RNDR", "NEAR", "ICP", "TRX", "LTC", "BCH", "ETC", "TON", "ALGO",
]


def _extract_coins(text: str):
    found = []
    upper_text = text.upper()
    for coin in KNOWN_COINS:
        if coin in upper_text:
            found.append(coin)
    return found[:5]


def _extract_hashtags(text: str):
    tags = re.findall(r"#(\w+)", text)
    seen = set()
    unique_tags = []
    for tag in tags:
        normalized = tag.lower()
        if normalized not in seen:
            seen.add(normalized)
            unique_tags.append(f"#{tag}")

    for default_tag in ["#Binance", "#CryptoAnalysis"]:
        normalized = default_tag[1:].lower()
        if normalized not in seen:
            seen.add(normalized)
            unique_tags.append(default_tag)

    return unique_tags[:5]


def _missing_coin_mentions(text: str, coins: list[str]):
    upper_text = text.upper()
    missing = []
    for coin in coins:
        marker = f"${coin}"
        if marker not in upper_text:
            missing.append(marker)
    return missing


def _missing_hashtags(text: str, hashtags: list[str]):
    existing = {tag.lower() for tag in re.findall(r"#\w+", text)}
    return [tag for tag in hashtags if tag.lower() not in existing]


def _compose_square_body(article_content: str):
    article_content = article_content.strip()
    coins = _extract_coins(article_content)
    hashtags = _extract_hashtags(article_content)

    trailer_parts = []
    missing_coin_markers = _missing_coin_mentions(article_content, coins)
    if missing_coin_markers:
        trailer_parts.append(" ".join(missing_coin_markers))

    missing_tags = _missing_hashtags(article_content, hashtags)
    if missing_tags:
        trailer_parts.append(" ".join(missing_tags))

    trailer = ""
    if trailer_parts:
        trailer = "\n\n" + "\n\n".join(trailer_parts)

    if len(article_content) + len(trailer) > MAX_SQUARE_BODY_LENGTH:
        allowed = MAX_SQUARE_BODY_LENGTH - len(trailer)
        if allowed <= 3:
            body_text = (article_content[:MAX_SQUARE_BODY_LENGTH - 3] + "...") if len(article_content) > 3 else article_content
        else:
            body_text = article_content[:allowed - 3].rstrip() + "..." + trailer
    else:
        body_text = article_content + trailer

    return body_text, coins, hashtags


def _build_publish_payload(article_content: str, title: str = ""):
    body_text, coins, _hashtags = _compose_square_body(article_content)
    payload = {"bodyTextOnly": body_text}
    if title:
        payload["title"] = title
    if coins:
        payload["mentionedCoins"] = coins
    return payload


def publish_to_square(article_content: str, title: str = ""):
    if not SQUARE_API_KEY:
        return {"skipped": True, "reason": "SQUARE_API_KEY not configured"}

    payload = _build_publish_payload(article_content, title=title)
    headers = {
        "Content-Type": "application/json",
        "X-Square-OpenAPI-Key": SQUARE_API_KEY,
        "clienttype": "binanceSkill",
    }

    try:
        req = urllib.request.Request(
            SQUARE_API_URL,
            data=json.dumps(payload).encode(),
            headers=headers,
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            response = json.loads(resp.read().decode())
    except Exception as exc:
        return {"error": str(exc)}

    if response.get("code") == "000000":
        post_id = response.get("data", {}).get("id", "")
        post_url = f"https://www.binance.com/square/post/{post_id}" if post_id else ""
        return {"success": True, "data": response.get("data"), "url": post_url, "payload": payload}

    return {
        "error": True,
        "code": response.get("code"),
        "message": response.get("message"),
        "response": response,
        "payload": payload,
    }


if __name__ == "__main__":
    print("[publish] Binance Square Publisher v1.1")
    if not SQUARE_API_KEY:
        print("[publish] SQUARE_API_KEY not configured. Set it to enable publishing.")
    else:
        print("[publish] Ready to publish. Use: publish_to_square('your article text')")
