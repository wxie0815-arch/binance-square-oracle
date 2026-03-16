#!/usr/bin/env python3
"""
Local Python data collection prototype for Binance Square Oracle.

The main competition path is the OpenClaw-native root skill. This module keeps a
clean local fallback that mirrors the same style-routing idea with public Binance
and supporting data sources.
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

WEB3_HEADERS = {
    "Content-Type": "application/json",
    "Accept-Encoding": "identity",
    "User-Agent": "binance-web3/1.4 (Skill)",
}

SPOT_HEADERS = {
    "User-Agent": "BinanceSquareOracle/1.1",
}

TOKEN_6551 = os.environ.get("TOKEN_6551", "")
API_6551_BASE = os.environ.get("API_6551_BASE", "https://api.6551.io/v1").rstrip("/")


def _http_get(url: str, headers: dict | None = None, timeout: int = 12):
    try:
        req = urllib.request.Request(url, headers=headers or {})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as exc:
        return {"error": str(exc), "url": url}


def _http_post(url: str, payload: dict, headers: dict | None = None, timeout: int = 12):
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode(),
            headers=headers or {},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as exc:
        return {"error": str(exc), "url": url}


def get_spot_ticker(symbol: str = "BTCUSDT"):
    url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol.upper()}"
    return _http_get(url, headers=SPOT_HEADERS)


def get_spot_klines(symbol: str = "BTCUSDT", interval: str = "1d", limit: int = 7):
    url = (
        f"https://api.binance.com/api/v3/klines?symbol={symbol.upper()}"
        f"&interval={interval}&limit={limit}"
    )
    return _http_get(url, headers=SPOT_HEADERS)


def get_futures_long_short_ratio(symbol: str = "BTCUSDT", period: str = "1h", limit: int = 5):
    url = (
        "https://fapi.binance.com/futures/data/globalLongShortAccountRatio"
        f"?symbol={symbol}&period={period}&limit={limit}"
    )
    return _http_get(url, headers=SPOT_HEADERS)


def get_futures_top_account_ratio(symbol: str = "BTCUSDT", period: str = "1h", limit: int = 5):
    url = (
        "https://fapi.binance.com/futures/data/topLongShortAccountRatio"
        f"?symbol={symbol}&period={period}&limit={limit}"
    )
    return _http_get(url, headers=SPOT_HEADERS)


def get_futures_funding_rate(symbol: str = "BTCUSDT"):
    url = f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={symbol}&limit=3"
    return _http_get(url, headers=SPOT_HEADERS)


def get_futures_open_interest(symbol: str = "BTCUSDT"):
    url = f"https://fapi.binance.com/fapi/v1/openInterest?symbol={symbol}"
    return _http_get(url, headers=SPOT_HEADERS)


def get_alpha_ticker(symbol: str = "BTCUSDT"):
    url = f"https://api.binance.com/bapi/defi/v1/public/alpha-trade/ticker?symbol={symbol}"
    return _http_get(url, headers=SPOT_HEADERS)


def get_alpha_klines(symbol: str = "BTCUSDT", interval: str = "1d", limit: int = 7):
    url = (
        "https://api.binance.com/bapi/defi/v1/public/alpha-trade/klines"
        f"?symbol={symbol}&interval={interval}&limit={limit}"
    )
    return _http_get(url, headers=SPOT_HEADERS)


def get_alpha_token_list():
    url = (
        "https://web3.binance.com/bapi/defi/v1/public/wallet-direct/"
        "buw/wallet/cex/alpha/all/token/list"
    )
    return _http_get(url, headers=WEB3_HEADERS)


WEB3_SOCIAL_HYPE_URL = (
    "https://web3.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/"
    "market/token/pulse/social/hype/rank/leaderboard"
)
WEB3_UNIFIED_RANK_URL = (
    "https://web3.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/"
    "market/token/pulse/unified/rank/list"
)
WEB3_SMART_MONEY_URL = (
    "https://web3.binance.com/bapi/defi/v1/public/wallet-direct/tracker/"
    "wallet/token/inflow/rank/query"
)
WEB3_MEME_RANK_URL = (
    "https://web3.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/"
    "market/token/pulse/exclusive/rank/list"
)
WEB3_TRADING_SIGNAL_URL = (
    "https://web3.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/"
    "web/signal/smart-money"
)
WEB3_MEME_RUSH_URL = (
    "https://web3.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/"
    "market/token/pulse/rank/list"
)
WEB3_TOPIC_RUSH_URL = (
    "https://web3.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/"
    "market/token/social-rush/rank/list"
)
WEB3_TOKEN_SEARCH_URL = (
    "https://web3.binance.com/bapi/defi/v5/public/wallet-direct/buw/wallet/"
    "market/token/search"
)
WEB3_TOKEN_DYNAMIC_URL = (
    "https://web3.binance.com/bapi/defi/v4/public/wallet-direct/buw/wallet/"
    "market/token/dynamic/info"
)
WEB3_TOKEN_META_URL = (
    "https://web3.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/"
    "dex/market/token/meta/info"
)
WEB3_TOKEN_AUDIT_URL = (
    "https://web3.binance.com/bapi/defi/v1/public/wallet-direct/security/token/audit"
)
WEB3_ADDRESS_INFO_URL = (
    "https://web3.binance.com/bapi/defi/v3/public/wallet-direct/buw/wallet/"
    "address/pnl/active-position-list"
)


def get_social_hype_rank(chain_id: str = "56"):
    url = (
        f"{WEB3_SOCIAL_HYPE_URL}?chainId={chain_id}&sentiment=All"
        "&socialLanguage=ALL&targetLanguage=zh&timeRange=1"
    )
    return _http_get(url, headers=WEB3_HEADERS)


def get_alpha_rank():
    return _http_post(
        WEB3_UNIFIED_RANK_URL,
        {"rankType": 20, "period": 50, "sortBy": 70, "orderAsc": False, "page": 1, "size": 10},
        headers=WEB3_HEADERS,
    )


def get_trending_tokens():
    return _http_post(
        WEB3_UNIFIED_RANK_URL,
        {"rankType": 10, "period": 50, "sortBy": 70, "orderAsc": False, "page": 1, "size": 10},
        headers=WEB3_HEADERS,
    )


def get_smart_money_inflow(chain_id: str = "56"):
    return _http_post(
        WEB3_SMART_MONEY_URL,
        {"chainId": chain_id, "period": "1h", "tagType": 2, "page": 1, "pageSize": 10},
        headers=WEB3_HEADERS,
    )


def get_meme_exclusive_rank(chain_id: str = "CT_501"):
    url = f"{WEB3_MEME_RANK_URL}?chainId={chain_id}&tagType=1&page=1&size=10"
    return _http_get(url, headers=WEB3_HEADERS)


def get_trading_signals(chain_id: str = "CT_501"):
    return _http_post(
        WEB3_TRADING_SIGNAL_URL,
        {"smartSignalType": "", "page": 1, "pageSize": 10, "chainId": chain_id},
        headers=WEB3_HEADERS,
    )


def get_meme_rush_new(chain_id: str = "CT_501"):
    return _http_post(
        WEB3_MEME_RUSH_URL,
        {"chainId": chain_id, "rankType": 10, "limit": 10},
        headers=WEB3_HEADERS,
    )


def get_meme_rush_migrated(chain_id: str = "CT_501"):
    return _http_post(
        WEB3_MEME_RUSH_URL,
        {"chainId": chain_id, "rankType": 30, "limit": 10},
        headers=WEB3_HEADERS,
    )


def get_topic_rush(chain_id: str = "CT_501"):
    url = f"{WEB3_TOPIC_RUSH_URL}?chainId={chain_id}&rankType=10&sort=1&asc=false&page=1&size=10"
    return _http_get(url, headers=WEB3_HEADERS)


def get_token_search(keyword: str = "BTC", chain_ids: str = ""):
    url = f"{WEB3_TOKEN_SEARCH_URL}?keyword={keyword}"
    if chain_ids:
        url += f"&chainIds={chain_ids}"
    return _http_get(url, headers=WEB3_HEADERS)


def get_token_dynamic_info(chain_id: str = "56", contract_address: str = ""):
    if not contract_address:
        return {"skipped": True, "reason": "No contract address provided"}
    url = f"{WEB3_TOKEN_DYNAMIC_URL}?chainId={chain_id}&contractAddress={contract_address}"
    return _http_get(url, headers=WEB3_HEADERS)


def get_token_meta_info(chain_id: str = "56", contract_address: str = ""):
    if not contract_address:
        return {"skipped": True, "reason": "No contract address provided"}
    url = f"{WEB3_TOKEN_META_URL}?chainId={chain_id}&contractAddress={contract_address}"
    return _http_get(url, headers=WEB3_HEADERS)


def get_token_audit(chain_id: str = "56", contract_address: str = ""):
    if not contract_address:
        return {"skipped": True, "reason": "No contract address provided"}
    return _http_post(
        WEB3_TOKEN_AUDIT_URL,
        {
            "binanceChainId": chain_id,
            "contractAddress": contract_address,
            "requestId": str(uuid.uuid4()),
        },
        headers={
            "Content-Type": "application/json",
            "Accept-Encoding": "identity",
            "User-Agent": "binance-web3/1.4 (Skill)",
            "source": "agent",
        },
    )


def get_address_info(address: str = "", chain_id: str = "56"):
    if not address:
        return {"skipped": True, "reason": "No address provided"}
    url = f"{WEB3_ADDRESS_INFO_URL}?address={address}&chainId={chain_id}&offset=0"
    return _http_get(
        url,
        headers={
            "clienttype": "web",
            "clientversion": "1.2.0",
            "Accept-Encoding": "identity",
            "User-Agent": "binance-web3/1.0 (Skill)",
        },
    )


def get_coingecko_price(coin_id: str = "bitcoin"):
    url = (
        "https://api.coingecko.com/api/v3/simple/price"
        f"?ids={coin_id}&vs_currencies=usd"
        "&include_24hr_vol=true&include_24hr_change=true&include_7d_change=true"
    )
    return _http_get(url)


def get_blockchain_info():
    return _http_get("https://api.blockchain.info/stats")


def get_fear_greed_index():
    return _http_get("https://api.alternative.me/fng/?limit=7")


def _post_6551(endpoint: str, payload: dict):
    if not TOKEN_6551:
        return {"skipped": True, "reason": "TOKEN_6551 not configured"}
    try:
        req = urllib.request.Request(
            f"{API_6551_BASE}/open/{endpoint}",
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": f"Bearer {TOKEN_6551}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=12) as resp:
            return json.loads(resp.read().decode())
    except Exception as exc:
        return {"error": str(exc)}


def get_6551_hot_news(hours: int = 6, limit: int = 10):
    return _post_6551("news_search", {"limit": limit, "orderBy": "score", "timeRange": f"{hours}h"})


def get_6551_kol_signals(kol_list: list[str] | None = None, limit_per_kol: int = 2):
    usernames = kol_list or ["binance", "cz_binance", "VitalikButerin"]
    signals: list = []
    for username in usernames:
        raw = _post_6551("twitter_user_tweets", {"username": username, "limit": limit_per_kol})
        items = raw.get("data", [])
        if isinstance(items, list):
            signals.extend(items)
    return signals


STYLE_DATA_ROUTES = {
    "daily_express": {
        "description": "Daily market brief",
        "skills": ["spot", "crypto-market-rank", "query-token-info", "alpha"],
        "tasks": lambda sym, fsym: {
            "spot_ticker": lambda: get_spot_ticker(fsym),
            "spot_klines_7d": lambda: get_spot_klines(fsym, "1d", 7),
            "social_hype_rank": lambda: get_social_hype_rank("56"),
            "trending_tokens": get_trending_tokens,
            "alpha_rank": get_alpha_rank,
            "alpha_token_list": get_alpha_token_list,
            "token_search_btc": lambda: get_token_search("BTC"),
            "coingecko_price": lambda: get_coingecko_price(sym),
            "fear_greed_index": get_fear_greed_index,
        },
    },
    "deep_analysis": {
        "description": "Full token thesis",
        "skills": ["spot", "derivatives", "query-token-info", "trading-signal", "query-token-audit", "alpha"],
        "tasks": lambda sym, fsym: {
            "spot_ticker": lambda: get_spot_ticker(fsym),
            "spot_klines_7d": lambda: get_spot_klines(fsym, "1d", 7),
            "futures_long_short_ratio": lambda: get_futures_long_short_ratio(fsym),
            "futures_funding_rate": lambda: get_futures_funding_rate(fsym),
            "futures_open_interest": lambda: get_futures_open_interest(fsym),
            "trading_signals": lambda: get_trading_signals("CT_501"),
            "token_search": lambda: get_token_search(sym.upper()),
            "alpha_token_list": get_alpha_token_list,
            "coingecko_price": lambda: get_coingecko_price(sym),
            "fear_greed_index": get_fear_greed_index,
            "blockchain_info": get_blockchain_info,
        },
    },
    "onchain_insight": {
        "description": "On-chain smart-money angle",
        "skills": ["trading-signal", "query-address-info", "query-token-info", "query-token-audit"],
        "tasks": lambda sym, fsym: {
            "trading_signals": lambda: get_trading_signals("CT_501"),
            "trading_signals_bsc": lambda: get_trading_signals("56"),
            "smart_money_inflow": lambda: get_smart_money_inflow("56"),
            "token_search": lambda: get_token_search(sym.upper()),
            "spot_ticker": lambda: get_spot_ticker(fsym),
            "coingecko_price": lambda: get_coingecko_price(sym),
        },
    },
    "meme_hunter": {
        "description": "Meme discovery",
        "skills": ["meme-rush", "query-token-info", "query-token-audit", "trading-signal"],
        "tasks": lambda sym, fsym: {
            "meme_rush_new": lambda: get_meme_rush_new("CT_501"),
            "meme_rush_migrated": lambda: get_meme_rush_migrated("CT_501"),
            "meme_rush_bsc_new": lambda: get_meme_rush_new("56"),
            "topic_rush": lambda: get_topic_rush("CT_501"),
            "meme_exclusive_rank": lambda: get_meme_exclusive_rank("CT_501"),
            "trading_signals": lambda: get_trading_signals("CT_501"),
            "social_hype_rank": lambda: get_social_hype_rank("56"),
            "spot_ticker": lambda: get_spot_ticker(fsym),
        },
    },
    "kol_style": {
        "description": "Opinionated KOL style",
        "skills": ["spot", "crypto-market-rank", "trading-signal"],
        "tasks": lambda sym, fsym: {
            "spot_ticker": lambda: get_spot_ticker(fsym),
            "spot_klines_7d": lambda: get_spot_klines(fsym, "1d", 7),
            "social_hype_rank": lambda: get_social_hype_rank("56"),
            "trending_tokens": get_trending_tokens,
            "trading_signals": lambda: get_trading_signals("CT_501"),
            "coingecko_price": lambda: get_coingecko_price(sym),
            "fear_greed_index": get_fear_greed_index,
        },
    },
    "oracle": {
        "description": "Directional market call",
        "skills": ["spot", "derivatives", "crypto-market-rank", "trading-signal"],
        "tasks": lambda sym, fsym: {
            "spot_ticker": lambda: get_spot_ticker(fsym),
            "spot_klines_7d": lambda: get_spot_klines(fsym, "1d", 7),
            "futures_long_short_ratio": lambda: get_futures_long_short_ratio(fsym),
            "futures_top_account_ratio": lambda: get_futures_top_account_ratio(fsym),
            "futures_funding_rate": lambda: get_futures_funding_rate(fsym),
            "futures_open_interest": lambda: get_futures_open_interest(fsym),
            "smart_money_inflow": lambda: get_smart_money_inflow("56"),
            "trading_signals": lambda: get_trading_signals("CT_501"),
            "coingecko_price": lambda: get_coingecko_price(sym),
            "fear_greed_index": get_fear_greed_index,
            "blockchain_info": get_blockchain_info,
        },
    },
    "project_research": {
        "description": "Project research",
        "skills": ["query-token-info", "query-token-audit", "alpha", "crypto-market-rank"],
        "tasks": lambda sym, fsym: {
            "token_search": lambda: get_token_search(sym.upper()),
            "alpha_rank": get_alpha_rank,
            "alpha_token_list": get_alpha_token_list,
            "trending_tokens": get_trending_tokens,
            "social_hype_rank": lambda: get_social_hype_rank("56"),
            "spot_ticker": lambda: get_spot_ticker(fsym),
            "coingecko_price": lambda: get_coingecko_price(sym),
        },
    },
    "trading_signal": {
        "description": "Tactical trade setup",
        "skills": ["spot", "derivatives", "trading-signal", "query-token-audit"],
        "tasks": lambda sym, fsym: {
            "spot_ticker": lambda: get_spot_ticker(fsym),
            "spot_klines_7d": lambda: get_spot_klines(fsym, "1d", 7),
            "futures_long_short_ratio": lambda: get_futures_long_short_ratio(fsym),
            "futures_top_account_ratio": lambda: get_futures_top_account_ratio(fsym),
            "futures_funding_rate": lambda: get_futures_funding_rate(fsym),
            "futures_open_interest": lambda: get_futures_open_interest(fsym),
            "trading_signals": lambda: get_trading_signals("CT_501"),
            "smart_money_inflow": lambda: get_smart_money_inflow("56"),
            "coingecko_price": lambda: get_coingecko_price(sym),
            "fear_greed_index": get_fear_greed_index,
        },
    },
    "tutorial": {
        "description": "Educational content",
        "skills": ["spot", "crypto-market-rank"],
        "tasks": lambda sym, fsym: {
            "spot_ticker": lambda: get_spot_ticker(fsym),
            "trending_tokens": get_trending_tokens,
            "social_hype_rank": lambda: get_social_hype_rank("56"),
            "coingecko_price": lambda: get_coingecko_price(sym),
            "fear_greed_index": get_fear_greed_index,
        },
    },
}

DEFAULT_DATA_ROUTE = {
    "description": "DIY custom style",
    "skills": ["spot", "crypto-market-rank", "trading-signal", "alpha"],
    "tasks": lambda sym, fsym: {
        "spot_ticker": lambda: get_spot_ticker(fsym),
        "spot_klines_7d": lambda: get_spot_klines(fsym, "1d", 7),
        "social_hype_rank": lambda: get_social_hype_rank("56"),
        "trending_tokens": get_trending_tokens,
        "alpha_rank": get_alpha_rank,
        "trading_signals": lambda: get_trading_signals("CT_501"),
        "smart_money_inflow": lambda: get_smart_money_inflow("56"),
        "coingecko_price": lambda: get_coingecko_price(sym),
        "fear_greed_index": get_fear_greed_index,
    },
}


async def collect_by_style(
    symbol: str = "bitcoin",
    futures_symbol: str = "BTCUSDT",
    style_name: str = "kol_style",
    enable_l4: bool = False,
):
    route = STYLE_DATA_ROUTES.get(style_name, DEFAULT_DATA_ROUTE)
    tasks = route["tasks"](symbol, futures_symbol)

    if enable_l4 and TOKEN_6551:
        tasks["l4_hot_news"] = get_6551_hot_news
        tasks["l4_kol_signals"] = get_6551_kol_signals

    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=min(20, len(tasks) or 1)) as executor:
        futures_map = {key: loop.run_in_executor(executor, func) for key, func in tasks.items()}
        return {key: await fut for key, fut in futures_map.items()}


def collect_all(
    symbol: str = "bitcoin",
    futures_symbol: str = "BTCUSDT",
    style_name: str = "kol_style",
    enable_l4: bool = False,
):
    return asyncio.run(
        collect_by_style(
            symbol=symbol,
            futures_symbol=futures_symbol,
            style_name=style_name,
            enable_l4=enable_l4,
        )
    )


def get_available_routes():
    routes = {name: route["description"] for name, route in STYLE_DATA_ROUTES.items()}
    routes["_default"] = DEFAULT_DATA_ROUTE["description"]
    return routes


fetch_spot_ticker = get_spot_ticker
fetch_spot_klines = get_spot_klines
fetch_futures_ls_ratio = get_futures_long_short_ratio
fetch_futures_top_ratio = get_futures_top_account_ratio
fetch_futures_funding_rate = get_futures_funding_rate
fetch_futures_open_interest = get_futures_open_interest
fetch_social_hype_rank = get_social_hype_rank
fetch_alpha_rank = get_alpha_rank
fetch_trending_tokens = get_trending_tokens
fetch_smart_money_inflow = get_smart_money_inflow
fetch_trading_signal = get_trading_signals
fetch_meme_new = get_meme_rush_new
fetch_meme_migrated = get_meme_rush_migrated
fetch_coingecko_price = get_coingecko_price
fetch_blockchain_stats = get_blockchain_info
fetch_fear_greed = get_fear_greed_index


if __name__ == "__main__":
    import sys

    coin = sys.argv[1] if len(sys.argv) > 1 else "bitcoin"
    futures_coin = sys.argv[2] if len(sys.argv) > 2 else "BTCUSDT"
    style = sys.argv[3] if len(sys.argv) > 3 else "kol_style"

    print(f"[collect] Collecting {coin}/{futures_coin} with style '{style}'")
    data = collect_all(coin, futures_coin, style_name=style)
    for key, value in data.items():
        text = str(value)
        status = "WARN" if ("error" in text[:120] or "skipped" in text[:120]) else "OK"
        print(f"  [{status}] {key}")
