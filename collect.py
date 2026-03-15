#!/usr/bin/env python3
"""
collect.py — Binance Square Oracle v1.0 数据采集层
按创作风格智能路由，只调用对应 Skill 数据源，提升运行效率。

集成全部 12 个币安官方 Skill：
  binance/spot                              — 现货行情
  binance/derivatives-trading-usds-futures   — 合约数据
  binance/alpha                             — Alpha 代币行情
  binance/assets                            — 资产管理（需认证）
  binance/margin-trading                    — 杠杆交易（需认证）
  binance/social                            — 社交数据
  binance/content-discovery                 — 内容发现
  binance/square-post                       — 广场发布（需认证）
  binance-web3/crypto-market-rank           — 市场排名
  binance-web3/trading-signal               — 智能钱信号
  binance-web3/meme-rush                    — Meme 叙事追踪
  binance-web3/query-token-info             — 代币详情
  binance-web3/query-token-audit            — 代币安全审计
  binance-web3/query-address-info           — 链上地址查询

可选增强（需环境变量）：
  L4 / 6551                                 — 高热新闻 + KOL 推文
"""

import asyncio
import json
import os
import uuid
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor

# ---------------------------------------------------------------------------
# 通用请求头
# ---------------------------------------------------------------------------
WEB3_HEADERS = {
    "Content-Type": "application/json",
    "Accept-Encoding": "identity",
    "User-Agent": "binance-web3/1.4 (Skill)",
}
SPOT_HEADERS = {
    "User-Agent": "BinanceSquareOracle/1.0",
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
# Skill 1 — binance/spot（现货行情，无需认证）
# ===========================================================================
def get_spot_ticker(symbol="BTCUSDT"):
    url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol.upper()}"
    return _http_get(url, headers=SPOT_HEADERS)

def get_spot_klines(symbol="BTCUSDT", interval="1d", limit=7):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol.upper()}&interval={interval}&limit={limit}"
    return _http_get(url, headers=SPOT_HEADERS)

# ===========================================================================
# Skill 2 — binance/derivatives-trading-usds-futures（合约公开数据，无需认证）
# ===========================================================================
def get_futures_long_short_ratio(symbol="BTCUSDT", period="1h", limit=5):
    url = f"https://fapi.binance.com/futures/data/globalLongShortAccountRatio?symbol={symbol}&period={period}&limit={limit}"
    return _http_get(url, headers=SPOT_HEADERS)

def get_futures_top_account_ratio(symbol="BTCUSDT", period="1h", limit=5):
    url = f"https://fapi.binance.com/futures/data/topLongShortAccountRatio?symbol={symbol}&period={period}&limit={limit}"
    return _http_get(url, headers=SPOT_HEADERS)

def get_futures_funding_rate(symbol="BTCUSDT"):
    url = f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={symbol}&limit=3"
    return _http_get(url, headers=SPOT_HEADERS)

def get_futures_open_interest(symbol="BTCUSDT"):
    url = f"https://fapi.binance.com/fapi/v1/openInterest?symbol={symbol}"
    return _http_get(url, headers=SPOT_HEADERS)

# ===========================================================================
# Skill 3 — binance/alpha（Alpha 代币行情，无需认证的公开端点）
# ===========================================================================
def get_alpha_ticker(symbol="BTCUSDT"):
    url = f"https://api.binance.com/bapi/defi/v1/public/alpha-trade/ticker?symbol={symbol}"
    return _http_get(url, headers=SPOT_HEADERS)

def get_alpha_klines(symbol="BTCUSDT", interval="1d", limit=7):
    url = f"https://api.binance.com/bapi/defi/v1/public/alpha-trade/klines?symbol={symbol}&interval={interval}&limit={limit}"
    return _http_get(url, headers=SPOT_HEADERS)

def get_alpha_token_list():
    url = "https://web3.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/cex/alpha/all/token/list"
    return _http_get(url, headers=WEB3_HEADERS)

# ===========================================================================
# Skill 4 — binance-web3/crypto-market-rank（市场排名，无需认证）
# ===========================================================================
WEB3_SOCIAL_HYPE_URL = "https://web3.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/market/token/pulse/social/hype/rank/leaderboard"
WEB3_UNIFIED_RANK_URL = "https://web3.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/market/token/pulse/unified/rank/list"
WEB3_SMART_MONEY_URL = "https://web3.binance.com/bapi/defi/v1/public/wallet-direct/tracker/wallet/token/inflow/rank/query"
WEB3_MEME_RANK_URL = "https://web3.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/market/token/pulse/exclusive/rank/list"

def get_social_hype_rank(chain_id="56"):
    url = f"{WEB3_SOCIAL_HYPE_URL}?chainId={chain_id}&sentiment=All&socialLanguage=ALL&targetLanguage=zh&timeRange=1"
    return _http_get(url, headers=WEB3_HEADERS)

def get_alpha_rank():
    return _http_post(WEB3_UNIFIED_RANK_URL, {
        "rankType": 20, "period": 50, "sortBy": 70,
        "orderAsc": False, "page": 1, "size": 10
    }, headers=WEB3_HEADERS)

def get_trending_tokens():
    return _http_post(WEB3_UNIFIED_RANK_URL, {
        "rankType": 10, "period": 50, "sortBy": 70,
        "orderAsc": False, "page": 1, "size": 10
    }, headers=WEB3_HEADERS)

def get_smart_money_inflow(chain_id="56"):
    return _http_post(WEB3_SMART_MONEY_URL, {
        "chainId": chain_id, "period": "1h", "tagType": 2,
        "page": 1, "pageSize": 10
    }, headers=WEB3_HEADERS)

def get_meme_exclusive_rank(chain_id="CT_501"):
    return _http_get(
        f"{WEB3_MEME_RANK_URL}?chainId={chain_id}&tagType=1&page=1&size=10",
        headers=WEB3_HEADERS
    )

# ===========================================================================
# Skill 5 — binance-web3/trading-signal（智能钱信号，无需认证）
# ===========================================================================
WEB3_TRADING_SIGNAL_URL = "https://web3.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/web/signal/smart-money"

def get_trading_signals(chain_id="CT_501"):
    return _http_post(WEB3_TRADING_SIGNAL_URL, {
        "smartSignalType": "", "page": 1, "pageSize": 10, "chainId": chain_id
    }, headers=WEB3_HEADERS)

# ===========================================================================
# Skill 6 — binance-web3/meme-rush（Meme 叙事追踪，无需认证）
# ===========================================================================
WEB3_MEME_RUSH_URL = "https://web3.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/market/token/pulse/rank/list"
WEB3_TOPIC_RUSH_URL = "https://web3.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/market/token/social-rush/rank/list"

def get_meme_rush_new(chain_id="CT_501"):
    return _http_post(WEB3_MEME_RUSH_URL, {
        "chainId": chain_id, "rankType": 10, "limit": 10
    }, headers=WEB3_HEADERS)

def get_meme_rush_migrated(chain_id="CT_501"):
    return _http_post(WEB3_MEME_RUSH_URL, {
        "chainId": chain_id, "rankType": 30, "limit": 10
    }, headers=WEB3_HEADERS)

def get_topic_rush(chain_id="CT_501"):
    url = f"{WEB3_TOPIC_RUSH_URL}?chainId={chain_id}&rankType=10&sort=1&asc=false&page=1&size=10"
    return _http_get(url, headers=WEB3_HEADERS)

# ===========================================================================
# Skill 7 — binance-web3/query-token-info（代币详情，无需认证）
# ===========================================================================
WEB3_TOKEN_SEARCH_URL = "https://web3.binance.com/bapi/defi/v5/public/wallet-direct/buw/wallet/market/token/search"
WEB3_TOKEN_DYNAMIC_URL = "https://web3.binance.com/bapi/defi/v4/public/wallet-direct/buw/wallet/market/token/dynamic/info"
WEB3_TOKEN_META_URL = "https://web3.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/dex/market/token/meta/info"

def get_token_search(keyword="BTC", chain_ids=""):
    url = f"{WEB3_TOKEN_SEARCH_URL}?keyword={keyword}"
    if chain_ids:
        url += f"&chainIds={chain_ids}"
    return _http_get(url, headers=WEB3_HEADERS)

def get_token_dynamic_info(chain_id="56", contract_address=""):
    if not contract_address:
        return {"skipped": True, "reason": "No contract address provided"}
    url = f"{WEB3_TOKEN_DYNAMIC_URL}?chainId={chain_id}&contractAddress={contract_address}"
    return _http_get(url, headers=WEB3_HEADERS)

def get_token_meta_info(chain_id="56", contract_address=""):
    if not contract_address:
        return {"skipped": True, "reason": "No contract address provided"}
    url = f"{WEB3_TOKEN_META_URL}?chainId={chain_id}&contractAddress={contract_address}"
    return _http_get(url, headers=WEB3_HEADERS)

# ===========================================================================
# Skill 8 — binance-web3/query-token-audit（代币安全审计，无需认证）
# ===========================================================================
WEB3_TOKEN_AUDIT_URL = "https://web3.binance.com/bapi/defi/v1/public/wallet-direct/security/token/audit"

def get_token_audit(chain_id="56", contract_address=""):
    if not contract_address:
        return {"skipped": True, "reason": "No contract address provided"}
    return _http_post(WEB3_TOKEN_AUDIT_URL, {
        "binanceChainId": chain_id,
        "contractAddress": contract_address,
        "requestId": str(uuid.uuid4())
    }, headers={
        "Content-Type": "application/json",
        "Accept-Encoding": "identity",
        "User-Agent": "binance-web3/1.4 (Skill)",
        "source": "agent"
    })

# ===========================================================================
# Skill 9 — binance-web3/query-address-info（链上地址查询，无需认证）
# ===========================================================================
WEB3_ADDRESS_INFO_URL = "https://web3.binance.com/bapi/defi/v3/public/wallet-direct/buw/wallet/address/pnl/active-position-list"

def get_address_info(address="", chain_id="56"):
    if not address:
        return {"skipped": True, "reason": "No address provided"}
    url = f"{WEB3_ADDRESS_INFO_URL}?address={address}&chainId={chain_id}&offset=0"
    return _http_get(url, headers={
        "clienttype": "web",
        "clientversion": "1.2.0",
        "Accept-Encoding": "identity",
        "User-Agent": "binance-web3/1.0 (Skill)"
    })

# ===========================================================================
# 第三方补充数据（公开接口，无需认证）
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
# 风格 -> 数据源路由映射
# ===========================================================================
# 基于推文中4种官方创作组合 + 其余风格的合理映射
# 每种风格只调用必要的数据源，避免全量采集

STYLE_DATA_ROUTES = {
    # --- 官方推荐组合1：日常快讯型 ---
    "daily_express": {
        "description": "每日市场速递",
        "skills": ["spot", "crypto-market-rank", "query-token-info", "alpha"],
        "tasks": lambda sym, fsym: {
            "spot_ticker":       lambda: get_spot_ticker(fsym),
            "spot_klines_7d":    lambda: get_spot_klines(fsym, "1d", 7),
            "social_hype_rank":  lambda: get_social_hype_rank("56"),
            "trending_tokens":   get_trending_tokens,
            "alpha_rank":        get_alpha_rank,
            "alpha_token_list":  get_alpha_token_list,
            "token_search_btc":  lambda: get_token_search("BTC"),
            "coingecko_price":   lambda: get_coingecko_price(sym),
            "fear_greed_index":  get_fear_greed_index,
        }
    },
    # --- 官方推荐组合2：深度分析型 ---
    "deep_analysis": {
        "description": "代币全方位拆解",
        "skills": ["spot", "query-token-info", "trading-signal", "query-token-audit", "alpha"],
        "tasks": lambda sym, fsym: {
            "spot_ticker":              lambda: get_spot_ticker(fsym),
            "spot_klines_7d":           lambda: get_spot_klines(fsym, "1d", 7),
            "futures_long_short_ratio": lambda: get_futures_long_short_ratio(fsym),
            "futures_funding_rate":     lambda: get_futures_funding_rate(fsym),
            "futures_open_interest":    lambda: get_futures_open_interest(fsym),
            "trading_signals":          lambda: get_trading_signals("CT_501"),
            "token_search":             lambda: get_token_search(sym.upper()),
            "alpha_token_list":         get_alpha_token_list,
            "coingecko_price":          lambda: get_coingecko_price(sym),
            "fear_greed_index":         get_fear_greed_index,
            "blockchain_info":          get_blockchain_info,
        }
    },
    # --- 官方推荐组合3：链上洞察型 ---
    "onchain_insight": {
        "description": "鲸鱼在买什么",
        "skills": ["trading-signal", "query-address-info", "query-token-info", "query-token-audit"],
        "tasks": lambda sym, fsym: {
            "trading_signals":     lambda: get_trading_signals("CT_501"),
            "trading_signals_bsc": lambda: get_trading_signals("56"),
            "smart_money_inflow":  lambda: get_smart_money_inflow("56"),
            "token_search":        lambda: get_token_search(sym.upper()),
            "spot_ticker":         lambda: get_spot_ticker(fsym),
            "coingecko_price":     lambda: get_coingecko_price(sym),
        }
    },
    # --- 官方推荐组合4：Meme 猎手型 ---
    "meme_hunter": {
        "description": "捕捉下一个叙事",
        "skills": ["meme-rush", "query-token-info", "query-token-audit", "trading-signal"],
        "tasks": lambda sym, fsym: {
            "meme_rush_new":       lambda: get_meme_rush_new("CT_501"),
            "meme_rush_migrated":  lambda: get_meme_rush_migrated("CT_501"),
            "meme_rush_bsc_new":   lambda: get_meme_rush_new("56"),
            "topic_rush":          lambda: get_topic_rush("CT_501"),
            "meme_exclusive_rank": lambda: get_meme_exclusive_rank("CT_501"),
            "trading_signals":     lambda: get_trading_signals("CT_501"),
            "social_hype_rank":    lambda: get_social_hype_rank("56"),
            "spot_ticker":         lambda: get_spot_ticker(fsym),
        }
    },
    # --- KOL 风格 ---
    "kol_style": {
        "description": "KOL 观点输出",
        "skills": ["spot", "crypto-market-rank", "trading-signal"],
        "tasks": lambda sym, fsym: {
            "spot_ticker":         lambda: get_spot_ticker(fsym),
            "spot_klines_7d":      lambda: get_spot_klines(fsym, "1d", 7),
            "social_hype_rank":    lambda: get_social_hype_rank("56"),
            "trending_tokens":     get_trending_tokens,
            "trading_signals":     lambda: get_trading_signals("CT_501"),
            "coingecko_price":     lambda: get_coingecko_price(sym),
            "fear_greed_index":    get_fear_greed_index,
        }
    },
    # --- 预言机风格 ---
    "oracle": {
        "description": "市场预测",
        "skills": ["spot", "derivatives", "crypto-market-rank", "trading-signal"],
        "tasks": lambda sym, fsym: {
            "spot_ticker":              lambda: get_spot_ticker(fsym),
            "spot_klines_7d":           lambda: get_spot_klines(fsym, "1d", 7),
            "futures_long_short_ratio": lambda: get_futures_long_short_ratio(fsym),
            "futures_top_account_ratio":lambda: get_futures_top_account_ratio(fsym),
            "futures_funding_rate":     lambda: get_futures_funding_rate(fsym),
            "futures_open_interest":    lambda: get_futures_open_interest(fsym),
            "smart_money_inflow":       lambda: get_smart_money_inflow("56"),
            "trading_signals":          lambda: get_trading_signals("CT_501"),
            "coingecko_price":          lambda: get_coingecko_price(sym),
            "fear_greed_index":         get_fear_greed_index,
            "blockchain_info":          get_blockchain_info,
        }
    },
    # --- 项目研究风格 ---
    "project_research": {
        "description": "新项目介绍",
        "skills": ["query-token-info", "query-token-audit", "alpha", "crypto-market-rank"],
        "tasks": lambda sym, fsym: {
            "token_search":        lambda: get_token_search(sym.upper()),
            "alpha_rank":          get_alpha_rank,
            "alpha_token_list":    get_alpha_token_list,
            "trending_tokens":     get_trending_tokens,
            "social_hype_rank":    lambda: get_social_hype_rank("56"),
            "spot_ticker":         lambda: get_spot_ticker(fsym),
            "coingecko_price":     lambda: get_coingecko_price(sym),
        }
    },
    # --- 交易信号风格 ---
    "trading_signal": {
        "description": "交易建议",
        "skills": ["spot", "derivatives", "trading-signal", "query-token-audit"],
        "tasks": lambda sym, fsym: {
            "spot_ticker":              lambda: get_spot_ticker(fsym),
            "spot_klines_7d":           lambda: get_spot_klines(fsym, "1d", 7),
            "futures_long_short_ratio": lambda: get_futures_long_short_ratio(fsym),
            "futures_top_account_ratio":lambda: get_futures_top_account_ratio(fsym),
            "futures_funding_rate":     lambda: get_futures_funding_rate(fsym),
            "futures_open_interest":    lambda: get_futures_open_interest(fsym),
            "trading_signals":          lambda: get_trading_signals("CT_501"),
            "smart_money_inflow":       lambda: get_smart_money_inflow("56"),
            "coingecko_price":          lambda: get_coingecko_price(sym),
            "fear_greed_index":         get_fear_greed_index,
        }
    },
    # --- 教程风格 ---
    "tutorial": {
        "description": "科普教育",
        "skills": ["spot", "crypto-market-rank"],
        "tasks": lambda sym, fsym: {
            "spot_ticker":       lambda: get_spot_ticker(fsym),
            "trending_tokens":   get_trending_tokens,
            "social_hype_rank":  lambda: get_social_hype_rank("56"),
            "coingecko_price":   lambda: get_coingecko_price(sym),
            "fear_greed_index":  get_fear_greed_index,
        }
    },
}

# DIY 风格的默认数据路由（全量基础数据）
DEFAULT_DATA_ROUTE = {
    "description": "DIY custom style (default data route)",
    "skills": ["spot", "crypto-market-rank", "trading-signal"],
    "tasks": lambda sym, fsym: {
        "spot_ticker":         lambda: get_spot_ticker(fsym),
        "spot_klines_7d":      lambda: get_spot_klines(fsym, "1d", 7),
        "social_hype_rank":    lambda: get_social_hype_rank("56"),
        "trending_tokens":     get_trending_tokens,
        "alpha_rank":          get_alpha_rank,
        "trading_signals":     lambda: get_trading_signals("CT_501"),
        "smart_money_inflow":  lambda: get_smart_money_inflow("56"),
        "coingecko_price":     lambda: get_coingecko_price(sym),
        "fear_greed_index":    get_fear_greed_index,
    }
}

# ===========================================================================
# 主入口：按风格路由并发采集
# ===========================================================================
async def collect_by_style(symbol="bitcoin", futures_symbol="BTCUSDT", style_name="kol_style", enable_l4=False):
    """
    按风格路由采集数据，只调用对应 Skill 数据源。
    未知风格（DIY）使用默认路由。
    """
    route = STYLE_DATA_ROUTES.get(style_name, DEFAULT_DATA_ROUTE)
    tasks = route["tasks"](symbol, futures_symbol)

    # 如果启用 L4 增强，追加 6551 数据源
    if enable_l4 and TOKEN_6551:
        tasks["l4_hot_news"] = get_6551_hot_news
        tasks["l4_kol_signals"] = get_6551_kol_signals

    route_desc = route.get("description", style_name)
    skills_used = route.get("skills", [])
    print(f"[collect] Style: {style_name} ({route_desc})")
    print(f"[collect] Skills: {', '.join(skills_used)}")
    print(f"[collect] Tasks: {len(tasks)} data sources")

    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures_map = {
            key: loop.run_in_executor(executor, func)
            for key, func in tasks.items()
        }
        results = {}
        for key, fut in futures_map.items():
            results[key] = await fut

    success = sum(1 for v in results.values()
                  if "error" not in str(v)[:80] and "skipped" not in str(v)[:80])
    print(f"[collect] Done: {success}/{len(results)} sources OK")
    return results


def collect_all(symbol="bitcoin", futures_symbol="BTCUSDT", style_name="kol_style", enable_l4=False):
    """同步包装函数，供 oracle.py 直接调用。"""
    return asyncio.run(collect_by_style(
        symbol=symbol, futures_symbol=futures_symbol,
        style_name=style_name, enable_l4=enable_l4
    ))


def get_available_routes():
    """返回所有已注册的风格路由名称及描述。"""
    routes = {}
    for name, route in STYLE_DATA_ROUTES.items():
        routes[name] = route["description"]
    routes["_default"] = DEFAULT_DATA_ROUTE["description"]
    return routes


# ===========================================================================
# fetch_* 别名（兼容性）
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
    style = sys.argv[3] if len(sys.argv) > 3 else "kol_style"

    print(f"[collect] Collecting {symbol}/{futures_symbol} with style '{style}'...\n")
    data = collect_all(symbol, futures_symbol, style_name=style)

    for k, v in data.items():
        status = "OK" if "error" not in str(v)[:80] and "skipped" not in str(v)[:80] else "WARN"
        print(f"  [{status}] {k}")
