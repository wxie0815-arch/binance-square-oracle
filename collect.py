#!/usr/bin/env python3
"""
collect.py — C 方案数据采集层 v1.1
并发调用全部官方 Binance Skills Hub 数据源 + 第三方补充数据源

官方 Skill 来源（全部公开接口，无需认证）：
  binance/spot                          — 现货行情 (api.binance.com)
  binance/derivatives-trading-usds-futures — 合约多空比/清算 (fapi.binance.com)
  binance-web3/crypto-market-rank       — 社交热度/Alpha/智能钱 (web3.binance.com)
  binance-web3/trading-signal           — 链上智能钱信号 (web3.binance.com)
  binance-web3/meme-rush                — Meme 叙事追踪 (web3.binance.com)

可选增强（需 TOKEN_6551 环境变量）：
  L4 / 6551                             — 高热新闻 + KOL 推文
"""

import asyncio
import json
import os
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor

# ---------------------------------------------------------------------------
# 通用请求头（官方 Skill 推荐格式）
# ---------------------------------------------------------------------------
WEB3_HEADERS = {
    "Content-Type": "application/json",
    "Accept-Encoding": "identity",
    "User-Agent": "binance-web3/2.0 (Skill)",
}
BAPI_HEADERS = {
    "Content-Type": "application/json",
    "Accept-Encoding": "identity",
    "User-Agent": "Mozilla/5.0 (compatible; BinanceSquareOracle/1.1)",
}

# ---------------------------------------------------------------------------
# 6551 可选增强层
# ---------------------------------------------------------------------------
TOKEN_6551 = os.environ.get("TOKEN_6551", "")
API_6551_BASE = os.environ.get("API_6551_BASE", "https://api.6551.io/v1")

# ---------------------------------------------------------------------------
# 底层 HTTP 工具
# ---------------------------------------------------------------------------
def _http_get(url, headers=None, timeout=12):
    try:
        req = urllib.request.Request(url, headers=headers or {})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"error": str(e), "url": url}

def _http_post(url, payload, headers=None, timeout=12):
    try:
        body = json.dumps(payload).encode()
        req = urllib.request.Request(url, data=body, headers=headers or {})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"error": str(e), "url": url}

# ===========================================================================
# 官方 Skill 1 — binance/spot
# 现货行情：24h ticker，无需认证
# ===========================================================================
def get_spot_ticker(symbol="BTCUSDT"):
    url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol.upper()}"
    return _http_get(url, headers={"User-Agent": "BinanceSquareOracle/1.1"})

def get_spot_klines(symbol="BTCUSDT", interval="1d", limit=7):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol.upper()}&interval={interval}&limit={limit}"
    return _http_get(url, headers={"User-Agent": "BinanceSquareOracle/1.1"})

# ===========================================================================
# 官方 Skill 2 — binance/derivatives-trading-usds-futures
# 合约公开数据：多空比、清算、资金费率，无需认证
# ===========================================================================
def get_futures_long_short_ratio(symbol="BTCUSDT", period="1h", limit=5):
    url = f"https://fapi.binance.com/futures/data/globalLongShortAccountRatio?symbol={symbol}&period={period}&limit={limit}"
    return _http_get(url, headers={"User-Agent": "BinanceSquareOracle/1.1"})

def get_futures_top_account_ratio(symbol="BTCUSDT", period="1h", limit=5):
    url = f"https://fapi.binance.com/futures/data/topLongShortAccountRatio?symbol={symbol}&period={period}&limit={limit}"
    return _http_get(url, headers={"User-Agent": "BinanceSquareOracle/1.1"})

def get_futures_funding_rate(symbol="BTCUSDT"):
    url = f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={symbol}&limit=3"
    return _http_get(url, headers={"User-Agent": "BinanceSquareOracle/1.1"})

def get_futures_open_interest(symbol="BTCUSDT"):
    url = f"https://fapi.binance.com/fapi/v1/openInterest?symbol={symbol}"
    return _http_get(url, headers={"User-Agent": "BinanceSquareOracle/1.1"})

# ===========================================================================
# 官方 Skill 4 — binance-web3/crypto-market-rank
# 社交热度排行、Alpha 发现、智能钱流入，无需认证
# ===========================================================================
WEB3_SOCIAL_HYPE_URL = "https://web3.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/market/token/pulse/social/hype/rank/leaderboard"
WEB3_UNIFIED_RANK_URL = "https://web3.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/market/token/pulse/unified/rank/list"
WEB3_SMART_MONEY_URL = "https://web3.binance.com/bapi/defi/v1/public/wallet-direct/tracker/wallet/token/inflow/rank/query"

def get_social_hype_rank(chain_id="56"):
    url = (
        f"{WEB3_SOCIAL_HYPE_URL}"
        f"?chainId={chain_id}&sentiment=All&socialLanguage=ALL&targetLanguage=zh&timeRange=1"
    )
    return _http_get(url, headers=WEB3_HEADERS)

def get_alpha_rank():
    """Alpha 发现：rankType=20"""
    return _http_post(WEB3_UNIFIED_RANK_URL, {
        "rankType": 20, "period": 50, "sortBy": 70,
        "orderAsc": False, "page": 1, "size": 10
    }, headers=WEB3_HEADERS)

def get_trending_tokens():
    """热门趋势：rankType=10"""
    return _http_post(WEB3_UNIFIED_RANK_URL, {
        "rankType": 10, "period": 50, "sortBy": 70,
        "orderAsc": False, "page": 1, "size": 10
    }, headers=WEB3_HEADERS)

def get_smart_money_inflow(chain_id="56"):
    return _http_post(WEB3_SMART_MONEY_URL, {
        "chainId": chain_id, "period": "1h", "tagType": 2,
        "page": 1, "pageSize": 10
    }, headers=WEB3_HEADERS)

# ===========================================================================
# 官方 Skill 5 — binance-web3/trading-signal
# 链上智能钱信号，无需认证
# ===========================================================================
WEB3_TRADING_SIGNAL_URL = "https://web3.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/web/signal/smart-money"

def get_trading_signals(chain_id="CT_501"):
    return _http_post(WEB3_TRADING_SIGNAL_URL, {
        "smartSignalType": "",
        "page": 1,
        "pageSize": 10,
        "chainId": chain_id
    }, headers=WEB3_HEADERS)

# ===========================================================================
# 官方 Skill 6 — binance-web3/meme-rush
# Meme 叙事追踪，无需认证
# ===========================================================================
WEB3_MEME_RUSH_URL = "https://web3.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/market/token/pulse/rank/list"

def get_meme_rush_new(chain_id="CT_501"):
    """新发 Meme 代币（bonding curve 阶段）"""
    return _http_post(WEB3_MEME_RUSH_URL, {
        "chainId": chain_id, "rankType": 10, "limit": 10
    }, headers=WEB3_HEADERS)

def get_meme_rush_migrated(chain_id="CT_501"):
    """已迁移到 DEX 的 Meme 代币"""
    return _http_post(WEB3_MEME_RUSH_URL, {
        "chainId": chain_id, "rankType": 30, "limit": 10
    }, headers=WEB3_HEADERS)

# ===========================================================================
# 第三方补充数据（不依赖币安官方，作为数据兜底）
# ===========================================================================
def get_coingecko_price(coin_id="bitcoin"):
    url = (
        f"https://api.coingecko.com/api/v3/simple/price"
        f"?ids={coin_id}&vs_currencies=usd"
        f"&include_24hr_vol=true&include_24hr_change=true&include_7d_change=true"
    )
    return _http_get(url)

def get_blockchain_info():
    return _http_get("https://api.blockchain.info/stats")

def get_fear_greed_index():
    return _http_get("https://api.alternative.me/fng/?limit=7")

# ===========================================================================
# 可选增强层 L4 — 6551 新闻 + KOL 信号
# ===========================================================================
def _post_6551(endpoint, payload):
    if not TOKEN_6551:
        return {"skipped": True, "reason": "TOKEN_6551 not configured"}
    try:
        body = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{API_6551_BASE}/open/{endpoint}", data=body,
            headers={
                "Authorization": f"Bearer {TOKEN_6551}",
                "Content-Type": "application/json"
            }
        )
        with urllib.request.urlopen(req, timeout=12) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"error": str(e)}

def get_6551_hot_news(hours=6, limit=10):
    return _post_6551("news_search", {"limit": limit, "orderBy": "score", "timeRange": f"{hours}h"})

def get_6551_kol_signals(kol_list=None, limit_per_kol=2):
    kol_list = kol_list or ["binance", "cz_binance", "VitalikButerin"]
    signals = []
    for username in kol_list:
        raw = _post_6551("twitter_user_tweets", {"username": username, "limit": limit_per_kol})
        items = raw.get("data", [])
        if isinstance(items, list):
            signals.extend(items)
    return signals

# ===========================================================================
# 主入口：并发采集全部数据
# ===========================================================================
async def collect_all_data(symbol="bitcoin", futures_symbol="BTCUSDT"):
    """
    并发采集全部数据源，返回结构化字典。
    symbol: CoinGecko 格式（如 bitcoin、ethereum）
    futures_symbol: 合约格式（如 BTCUSDT、ETHUSDT）
    """
    tasks = {
        # --- binance/spot ---
        "spot_ticker":              lambda: get_spot_ticker(f"{futures_symbol}"),
        "spot_klines_7d":           lambda: get_spot_klines(f"{futures_symbol}", "1d", 7),
        # --- binance/derivatives-trading-usds-futures ---
        "futures_long_short_ratio": lambda: get_futures_long_short_ratio(futures_symbol),
        "futures_top_account_ratio":lambda: get_futures_top_account_ratio(futures_symbol),
        "futures_funding_rate":     lambda: get_futures_funding_rate(futures_symbol),
        "futures_open_interest":    lambda: get_futures_open_interest(futures_symbol),
        # --- binance-web3/crypto-market-rank ---
        "social_hype_rank":         lambda: get_social_hype_rank("56"),
        "alpha_rank":               get_alpha_rank,
        "trending_tokens":          get_trending_tokens,
        "smart_money_inflow":       lambda: get_smart_money_inflow("56"),
        # --- binance-web3/trading-signal ---
        "trading_signals":          lambda: get_trading_signals("CT_501"),
        # --- binance-web3/meme-rush ---
        "meme_rush_new":            lambda: get_meme_rush_new("CT_501"),
        "meme_rush_migrated":       lambda: get_meme_rush_migrated("CT_501"),
        # --- 第三方补充 ---
        "coingecko_price":          lambda: get_coingecko_price(symbol),
        "blockchain_info":          get_blockchain_info,
        "fear_greed_index":         get_fear_greed_index,
        # --- L4 可选增强 ---
        "l4_hot_news":              get_6551_hot_news,
        "l4_kol_signals":           get_6551_kol_signals,
    }

    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures_map = {
            key: loop.run_in_executor(executor, func)
            for key, func in tasks.items()
        }
        results = {}
        for key, fut in futures_map.items():
            results[key] = await fut
    return results


def collect_all(symbol="bitcoin", futures_symbol="BTCUSDT"):
    """同步包装函数，供 oracle.py 和测试直接调用。"""
    return asyncio.run(collect_all_data(symbol, futures_symbol))


# ===========================================================================
# fetch_* 别名（兼容 oracle.py 和测试脚本）
# ===========================================================================
fetch_spot_ticker          = get_spot_ticker
fetch_spot_klines          = get_spot_klines
fetch_futures_ls_ratio     = get_futures_long_short_ratio
fetch_futures_top_ratio    = get_futures_top_account_ratio
fetch_futures_funding_rate = get_futures_funding_rate
fetch_futures_open_interest= get_futures_open_interest
fetch_social_hype_rank     = get_social_hype_rank
fetch_alpha_rank           = get_alpha_rank
fetch_trending_tokens      = get_trending_tokens
fetch_smart_money_inflow   = get_smart_money_inflow
fetch_trading_signal       = get_trading_signals
fetch_meme_new             = get_meme_rush_new
fetch_meme_migrated        = get_meme_rush_migrated
fetch_coingecko_price      = get_coingecko_price
fetch_blockchain_stats     = get_blockchain_info
fetch_fear_greed           = get_fear_greed_index


if __name__ == "__main__":
    import sys
    symbol = sys.argv[1] if len(sys.argv) > 1 else "bitcoin"
    futures_symbol = sys.argv[2] if len(sys.argv) > 2 else "BTCUSDT"
    print(f"[collect] 并发采集 {symbol} / {futures_symbol} 数据...")
    data = asyncio.run(collect_all_data(symbol, futures_symbol))

    success = sum(1 for v in data.values() if "error" not in str(v)[:50])
    print(f"\n[collect] 完成：{success}/{len(data)} 个数据源成功\n")
    for k, v in data.items():
        status = "✅" if "error" not in str(v)[:80] and "skipped" not in str(v)[:80] else "⚠️"
        print(f"  {status} {k}")
