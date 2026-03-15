#!/usr/bin/env python3
"""
L3 行情分析模块 (Market Analysis Engine) v6.0
================================================================
v6.0 新增（L3 升级）：
  - [Alpha] 早期项目监控：接入 /bapi/defi/v1/public/alpha-trade 和
    /bapi/defi/v1/public/wallet-direct/buw/wallet/cex/alpha/all/token/list
    获取 Alpha 平台最新上线项目、价格变动和市值数据。
  - [Derivatives] 合约多空比/清算数据：接入 fapi.binance.com
    获取全局多空持仓人数比、大户持仓多空比和最新强平订单。
  - 以上两个模块均为**可选**（非必选），无 BINANCE_API_KEY 时自动跳过，
    不影响原有核心功能。

数据源（全部使用币安官方 API）：
  1. Binance Spot Ticker/24hr       — BTC/ETH 等主流币 24h 行情
  2. Binance Spot Klines             — K线数据用于技术分析
  3. Unified Token Rank (Trending)   — 趋势代币排名
  4. Social Hype Leaderboard         — 社交热度排名
  5. Fear & Greed Index              — 恐惧贪婪指数
  6. [新增] Alpha Token List         — 早期项目监控（无需认证）
  7. [新增] Alpha Ticker             — Alpha 项目 24h 行情（无需认证）
  8. [新增] Futures Long/Short Ratio — 合约多空比（无需认证）
  9. [新增] Futures Liquidation      — 合约强平订单（无需认证）

输出：market_analysis_report (dict)
  - btc_analysis:          BTC 行情分析
  - eth_analysis:          ETH 行情分析
  - market_overview:       大盘概览
  - trending_tokens:       趋势代币 Top N
  - social_hype:           社交热度 Top N
  - fear_greed:            恐惧贪婪指数
  - technical_signals:     技术指标信号
  - market_score:          综合行情评分 (0-100, 50=中性)
  - market_summary:        中文摘要
  - alpha_monitor:         [新增] Alpha 早期项目监控（可选）
  - derivatives_data:      [新增] 合约多空比/清算数据（可选）
"""

import json
import time
import requests
import statistics
from datetime import datetime, timezone, timedelta

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
BINANCE_API_ENDPOINTS = [
    "https://www.binance.com",
    "https://data-api.binance.vision",
]
BINANCE_API = BINANCE_API_ENDPOINTS[0]
BINANCE_API_BACKUP = BINANCE_API_ENDPOINTS[1]
WEB3_API = "https://web3.binance.com"

# Alpha 平台 API（官方 binance-skills-hub alpha skill v1.0.0）
ALPHA_BASE_URL = "https://www.binance.com/bapi/defi/v1/public/alpha-trade"
ALPHA_TOKEN_LIST_URL = "https://www.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/cex/alpha/all/token/list"

# Derivatives Trading API（官方 binance-skills-hub derivatives-trading-usds-futures skill v1.0.0）
FAPI_BASE_URL = "https://fapi.binance.com/fapi/v1"
FUTURES_DATA_URL = "https://fapi.binance.com/futures/data"

HEADERS_GET = {
    "Accept-Encoding": "identity",
    "User-Agent": "binance-square-oracle/6.0 (Skill)",
}
HEADERS_JSON = {
    "Content-Type": "application/json",
    "Accept-Encoding": "identity",
    "User-Agent": "binance-square-oracle/6.0 (Skill)",
}

# 主要交易对
MAJOR_PAIRS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"]
WATCHLIST_PAIRS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT",
    "SUIUSDT", "PEPEUSDT", "WIFUSDT", "SHIBUSDT", "ARBUSDT",
]


# ---------------------------------------------------------------------------
# 1. Spot Ticker 24hr
# ---------------------------------------------------------------------------
def fetch_ticker_24hr(symbols: list = None) -> list:
    """获取 24 小时行情统计（带多端点自动回退）"""
    for idx, base_url in enumerate(BINANCE_API_ENDPOINTS):
        url = f"{base_url}/api/v3/ticker/24hr"
        try:
            if symbols and "data-api" in base_url:
                params = {"symbols": json.dumps(symbols)}
                resp = requests.get(url, params=params, headers=HEADERS_GET, timeout=10)
                data = resp.json()
                if isinstance(data, list):
                    return data
            elif symbols:
                results = []
                for sym in symbols:
                    resp = requests.get(url, params={"symbol": sym}, headers=HEADERS_GET, timeout=10)
                    data = resp.json()
                    if isinstance(data, dict) and data.get("lastPrice"):
                        results.append(data)
                if results:
                    return results
            else:
                resp = requests.get(url, headers=HEADERS_GET, timeout=10)
                data = resp.json()
                if isinstance(data, list):
                    return data
        except Exception as e:
            print(f"[L3] Ticker 24hr 请求失败 ({base_url}): {e}")
            if idx < len(BINANCE_API_ENDPOINTS) - 1:
                print("[L3] 正在尝试备用端点...")
    return []


def parse_ticker(raw_ticker: dict) -> dict:
    """解析单个 ticker 数据"""
    return {
        "symbol": raw_ticker.get("symbol", ""),
        "price": float(raw_ticker.get("lastPrice", 0)),
        "price_change_pct": float(raw_ticker.get("priceChangePercent", 0)),
        "high_24h": float(raw_ticker.get("highPrice", 0)),
        "low_24h": float(raw_ticker.get("lowPrice", 0)),
        "volume_24h": float(raw_ticker.get("volume", 0)),
        "quote_volume_24h": float(raw_ticker.get("quoteVolume", 0)),
        "trades_24h": int(raw_ticker.get("count", 0)),
        "weighted_avg_price": float(raw_ticker.get("weightedAvgPrice", 0)),
    }


# ---------------------------------------------------------------------------
# 2. K线数据 + 技术分析
# ---------------------------------------------------------------------------
def fetch_klines(symbol: str, interval: str = "1h", limit: int = 50) -> list:
    """获取 K 线数据（带多端点自动回退）"""
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    for idx, base_url in enumerate(BINANCE_API_ENDPOINTS):
        url = f"{base_url}/api/v3/klines"
        try:
            resp = requests.get(url, params=params, headers=HEADERS_GET, timeout=10)
            data = resp.json()
            if isinstance(data, list):
                return data
        except Exception as e:
            print(f"[L3] Klines 请求失败 ({symbol}, {base_url}): {e}")
            if idx < len(BINANCE_API_ENDPOINTS) - 1:
                print("[L3] 正在尝试备用端点...")
    return []


def calculate_sma(closes: list, period: int) -> float:
    if len(closes) < period:
        return 0
    return statistics.mean(closes[-period:])


def calculate_ema(closes: list, period: int) -> float:
    if len(closes) < period:
        return 0
    multiplier = 2 / (period + 1)
    ema = statistics.mean(closes[:period])
    for price in closes[period:]:
        ema = (price - ema) * multiplier + ema
    return ema


def calculate_rsi(closes: list, period: int = 14) -> float:
    if len(closes) < period + 1:
        return 50
    gains = []
    losses = []
    for i in range(1, len(closes)):
        change = closes[i] - closes[i - 1]
        gains.append(max(0, change))
        losses.append(max(0, -change))
    avg_gain = statistics.mean(gains[-period:])
    avg_loss = statistics.mean(losses[-period:])
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


def calculate_macd(closes: list) -> dict:
    ema12 = calculate_ema(closes, 12)
    ema26 = calculate_ema(closes, 26)
    macd_line = ema12 - ema26
    signal = calculate_ema(closes[-9:], 9) if len(closes) >= 9 else 0
    histogram = macd_line - signal
    return {
        "macd": round(macd_line, 4),
        "signal": round(signal, 4),
        "histogram": round(histogram, 4),
        "trend": "BULLISH" if histogram > 0 else "BEARISH",
    }


def calculate_bollinger_bands(closes: list, period: int = 20) -> dict:
    if len(closes) < period:
        return {"upper": 0, "middle": 0, "lower": 0, "position": "NEUTRAL"}
    recent = closes[-period:]
    middle = statistics.mean(recent)
    std = statistics.stdev(recent)
    upper = middle + 2 * std
    lower = middle - 2 * std
    current = closes[-1]
    if current > upper:
        position = "OVERBOUGHT"
    elif current < lower:
        position = "OVERSOLD"
    elif current > middle:
        position = "UPPER_HALF"
    else:
        position = "LOWER_HALF"
    return {
        "upper": round(upper, 2),
        "middle": round(middle, 2),
        "lower": round(lower, 2),
        "position": position,
    }


def analyze_technicals(symbol: str) -> dict:
    klines = fetch_klines(symbol, interval="1h", limit=50)
    if not klines:
        return {"symbol": symbol, "error": "无法获取K线数据"}
    closes = [float(k[4]) for k in klines]
    volumes = [float(k[5]) for k in klines]
    sma7 = calculate_sma(closes, 7)
    sma25 = calculate_sma(closes, 25)
    rsi = calculate_rsi(closes)
    macd = calculate_macd(closes)
    bb = calculate_bollinger_bands(closes)
    avg_vol = statistics.mean(volumes) if volumes else 0
    recent_vol = statistics.mean(volumes[-3:]) if len(volumes) >= 3 else 0
    vol_ratio = round(recent_vol / avg_vol, 2) if avg_vol > 0 else 1
    signals = []
    if sma7 > sma25:
        signals.append("SMA金叉")
    else:
        signals.append("SMA死叉")
    if rsi > 70:
        signals.append("RSI超买")
    elif rsi < 30:
        signals.append("RSI超卖")
    if macd["trend"] == "BULLISH":
        signals.append("MACD多头")
    else:
        signals.append("MACD空头")
    if bb["position"] == "OVERBOUGHT":
        signals.append("突破布林上轨")
    elif bb["position"] == "OVERSOLD":
        signals.append("跌破布林下轨")
    if vol_ratio > 1.5:
        signals.append("放量")
    elif vol_ratio < 0.5:
        signals.append("缩量")
    tech_score = 50
    if sma7 > sma25:
        tech_score += 10
    else:
        tech_score -= 10
    if rsi > 60:
        tech_score += 5
    elif rsi < 40:
        tech_score -= 5
    if macd["trend"] == "BULLISH":
        tech_score += 10
    else:
        tech_score -= 10
    if vol_ratio > 1.3:
        tech_score += 5
    return {
        "symbol": symbol,
        "current_price": closes[-1],
        "sma7": round(sma7, 2),
        "sma25": round(sma25, 2),
        "rsi": rsi,
        "macd": macd,
        "bollinger": bb,
        "volume_ratio": vol_ratio,
        "signals": signals,
        "tech_score": max(0, min(100, tech_score)),
    }


# ---------------------------------------------------------------------------
# 3. Trending Token Rank
# ---------------------------------------------------------------------------
def fetch_trending_tokens(chain_id: str = "56", top_n: int = 15) -> list:
    url = f"{WEB3_API}/bapi/defi/v1/public/wallet-direct/buw/wallet/market/token/pulse/unified/rank/list"
    payload = {
        "rankType": 10,
        "chainId": chain_id,
        "period": 50,
        "sortBy": 0,
        "orderAsc": False,
        "page": 1,
        "size": top_n,
    }
    try:
        resp = requests.post(url, json=payload, headers=HEADERS_JSON, timeout=15)
        data = resp.json()
        if data.get("success") and data.get("data", {}).get("tokens"):
            tokens = data["data"]["tokens"]
            return [
                {
                    "symbol": t.get("symbol", ""),
                    "price": t.get("price", "0"),
                    "market_cap": t.get("marketCap", "0"),
                    "change_24h": t.get("percentChange24h", "0"),
                    "volume_24h": t.get("volume24h", "0"),
                    "holders": t.get("holders", 0),
                    "chain": chain_id,
                }
                for t in tokens
            ]
    except Exception as e:
        print(f"[L3] Trending tokens 请求失败: {e}")
    return []


# ---------------------------------------------------------------------------
# 4. Social Hype Leaderboard
# ---------------------------------------------------------------------------
def fetch_social_hype(chain_id: str = "56", top_n: int = 10) -> list:
    url = f"{WEB3_API}/bapi/defi/v1/public/wallet-direct/buw/wallet/market/token/pulse/social/rank/list"
    payload = {
        "chainId": chain_id,
        "period": 50,
        "sortBy": 0,
        "orderAsc": False,
        "page": 1,
        "size": top_n,
    }
    try:
        resp = requests.post(url, json=payload, headers=HEADERS_JSON, timeout=15)
        data = resp.json()
        if data.get("success") and data.get("data", {}).get("tokens"):
            return [
                {
                    "symbol": t.get("symbol", ""),
                    "social_score": t.get("socialScore", 0),
                    "change_24h": t.get("percentChange24h", "0"),
                    "chain": chain_id,
                }
                for t in data["data"]["tokens"]
            ]
    except Exception as e:
        print(f"[L3] Social hype 请求失败: {e}")
    return []


# ---------------------------------------------------------------------------
# 5. Fear & Greed Index
# ---------------------------------------------------------------------------
def fetch_fear_greed() -> dict:
    try:
        resp = requests.get("https://api.alternative.me/fng/?limit=1", headers=HEADERS_GET, timeout=10)
        data = resp.json()
        if data.get("data"):
            fg = data["data"][0]
            return {
                "value": int(fg.get("value", 50)),
                "label": fg.get("value_classification", "Neutral"),
                "timestamp": fg.get("timestamp", ""),
            }
    except Exception as e:
        print(f"[L3] Fear & Greed 请求失败: {e}")
    return {"value": 50, "label": "Neutral", "timestamp": ""}


# ---------------------------------------------------------------------------
# 6. [新增 v6.0] Alpha 早期项目监控
#    数据源：官方 binance-skills-hub alpha skill v1.0.0
#    端点：无需认证（Authentication: No）
# ---------------------------------------------------------------------------
def fetch_alpha_token_list(top_n: int = 10) -> list:
    """
    获取 Alpha 平台最新上线项目列表。
    端点：GET /bapi/defi/v1/public/wallet-direct/buw/wallet/cex/alpha/all/token/list
    认证：无需（公开接口）
    参考：binance-skills-hub/skills/binance/alpha/SKILL.md v1.0.0
    """
    try:
        resp = requests.get(ALPHA_TOKEN_LIST_URL, headers=HEADERS_GET, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if data.get("data"):
            tokens = data["data"]
            # 按上线时间倒序，取最新 top_n 个
            tokens_sorted = sorted(tokens, key=lambda t: t.get("listingTime", 0), reverse=True)
            return [
                {
                    "alpha_id": t.get("alphaId", ""),
                    "name": t.get("name", ""),
                    "symbol": t.get("symbol", ""),
                    "chain": t.get("chainName", ""),
                    "price": t.get("price", "0"),
                    "change_24h": t.get("percentChange24h", "0"),
                    "volume_24h": t.get("volume24h", "0"),
                    "market_cap": t.get("marketCap", "0"),
                    "holders": t.get("holders", 0),
                    "listing_time": t.get("listingTime", 0),
                    "listing_cex": t.get("listingCex", False),
                    "score": t.get("score", 0),
                }
                for t in tokens_sorted[:top_n]
            ]
    except Exception as e:
        print(f"[L3] Alpha token list 请求失败: {e}")
    return []


def fetch_alpha_ticker(symbol: str) -> dict:
    """
    获取 Alpha 项目的 24h 行情数据。
    端点：GET /bapi/defi/v1/public/alpha-trade/ticker
    认证：无需（公开接口）
    参考：binance-skills-hub/skills/binance/alpha/SKILL.md v1.0.0
    """
    try:
        resp = requests.get(
            f"{ALPHA_BASE_URL}/ticker",
            params={"symbol": symbol},
            headers=HEADERS_GET,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"[L3] Alpha ticker 请求失败 ({symbol}): {e}")
    return {}


def run_alpha_monitor(top_n: int = 10) -> dict:
    """
    执行 Alpha 早期项目监控（可选模块）。
    无需任何 API 密钥，直接调用公开接口。
    """
    tokens = fetch_alpha_token_list(top_n=top_n)
    if not tokens:
        return {"available": False, "reason": "Alpha 平台数据暂时不可用", "tokens": []}

    # 筛选高潜力项目：score > 0 且 24h 涨幅 > 5%
    hot_tokens = [
        t for t in tokens
        if float(t.get("change_24h", 0)) > 5 and t.get("score", 0) > 0
    ]

    summary_lines = []
    for t in tokens[:5]:
        change = float(t.get("change_24h", 0))
        direction = "↑" if change >= 0 else "↓"
        summary_lines.append(
            f"{t['name']}({t['symbol']}) {direction}{abs(change):.2f}% "
            f"市值${float(t.get('market_cap', 0)):,.0f}"
        )

    return {
        "available": True,
        "total_tokens": len(tokens),
        "hot_tokens_count": len(hot_tokens),
        "latest_tokens": tokens,
        "hot_tokens": hot_tokens,
        "summary": "Alpha 最新项目: " + " | ".join(summary_lines),
    }


# ---------------------------------------------------------------------------
# 7. [新增 v6.0] Derivatives 合约多空比/清算数据
#    数据源：官方 binance-skills-hub derivatives-trading-usds-futures skill v1.0.0
#    端点：无需认证（Authentication: No）
# ---------------------------------------------------------------------------
def fetch_futures_long_short_ratio(symbol: str = "BTCUSDT", period: str = "1h", limit: int = 5) -> list:
    """
    获取全局多空持仓人数比。
    端点：GET /futures/data/globalLongShortAccountRatio
    认证：无需（公开接口）
    参考：binance-skills-hub/skills/binance/derivatives-trading-usds-futures/SKILL.md v1.0.0
    """
    try:
        resp = requests.get(
            f"{FUTURES_DATA_URL}/globalLongShortAccountRatio",
            params={"symbol": symbol, "period": period, "limit": limit},
            headers=HEADERS_GET,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            return data
    except Exception as e:
        print(f"[L3] Futures long/short ratio 请求失败 ({symbol}): {e}")
    return []


def fetch_futures_top_trader_ratio(symbol: str = "BTCUSDT", period: str = "1h", limit: int = 5) -> list:
    """
    获取大户持仓多空比（持仓量）。
    端点：GET /futures/data/topLongShortPositionRatio
    认证：无需（公开接口）
    参考：binance-skills-hub/skills/binance/derivatives-trading-usds-futures/SKILL.md v1.0.0
    """
    try:
        resp = requests.get(
            f"{FUTURES_DATA_URL}/topLongShortPositionRatio",
            params={"symbol": symbol, "period": period, "limit": limit},
            headers=HEADERS_GET,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            return data
    except Exception as e:
        print(f"[L3] Futures top trader ratio 请求失败 ({symbol}): {e}")
    return []


def fetch_futures_taker_ratio(symbol: str = "BTCUSDT", period: str = "1h", limit: int = 5) -> list:
    """
    获取主动买卖量比率（Taker Buy/Sell Volume）。
    端点：GET /futures/data/takerlongshortRatio
    认证：无需（公开接口）
    参考：binance-skills-hub/skills/binance/derivatives-trading-usds-futures/SKILL.md v1.0.0
    """
    try:
        resp = requests.get(
            f"{FUTURES_DATA_URL}/takerlongshortRatio",
            params={"symbol": symbol, "period": period, "limit": limit},
            headers=HEADERS_GET,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            return data
    except Exception as e:
        print(f"[L3] Futures taker ratio 请求失败 ({symbol}): {e}")
    return []


def fetch_futures_liquidation_orders(symbol: str = "BTCUSDT", limit: int = 10) -> list:
    """
    获取最新强平订单（公开清算数据）。
    端点：GET /fapi/v1/allForceOrders
    认证：无需（公开接口）
    参考：binance-skills-hub/skills/binance/derivatives-trading-usds-futures/SKILL.md v1.0.0
    """
    try:
        params = {"limit": limit}
        if symbol:
            params["symbol"] = symbol
        resp = requests.get(
            f"{FAPI_BASE_URL}/allForceOrders",
            params=params,
            headers=HEADERS_GET,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            return data
    except Exception as e:
        print(f"[L3] Futures liquidation orders 请求失败 ({symbol}): {e}")
    return []


def run_derivatives_analysis(symbol: str = "BTCUSDT") -> dict:
    """
    执行合约多空比/清算数据分析（可选模块）。
    无需任何 API 密钥，直接调用公开接口。
    """
    ls_ratio = fetch_futures_long_short_ratio(symbol=symbol, period="1h", limit=3)
    top_ratio = fetch_futures_top_trader_ratio(symbol=symbol, period="1h", limit=3)
    taker_ratio = fetch_futures_taker_ratio(symbol=symbol, period="1h", limit=3)
    liquidations = fetch_futures_liquidation_orders(symbol=symbol, limit=10)

    available = bool(ls_ratio or top_ratio or liquidations)
    if not available:
        return {
            "available": False,
            "reason": "合约数据暂时不可用（可能受地区限制）",
            "symbol": symbol,
        }

    # 解析最新多空比
    latest_ls = ls_ratio[-1] if ls_ratio else {}
    latest_top = top_ratio[-1] if top_ratio else {}
    latest_taker = taker_ratio[-1] if taker_ratio else {}

    # 解析清算数据
    long_liq = sum(1 for o in liquidations if o.get("side") == "SELL")
    short_liq = sum(1 for o in liquidations if o.get("side") == "BUY")
    total_liq_value = sum(
        float(o.get("price", 0)) * float(o.get("origQty", 0))
        for o in liquidations
    )

    # 生成摘要
    ls_val = latest_ls.get("longShortRatio", "N/A")
    top_val = latest_top.get("longShortRatio", "N/A")
    summary_parts = [f"{symbol} 多空比: {ls_val}"]
    if top_val != "N/A":
        summary_parts.append(f"大户多空比: {top_val}")
    if liquidations:
        summary_parts.append(
            f"近期清算: 多单{long_liq}笔/空单{short_liq}笔 "
            f"(总价值 ${total_liq_value:,.0f})"
        )

    return {
        "available": True,
        "symbol": symbol,
        "long_short_ratio": ls_ratio,
        "top_trader_ratio": top_ratio,
        "taker_ratio": taker_ratio,
        "liquidations": liquidations,
        "latest_ls_ratio": ls_val,
        "latest_top_ratio": top_val,
        "latest_taker_ratio": latest_taker.get("buySellRatio", "N/A"),
        "liquidation_summary": {
            "long_liquidated": long_liq,
            "short_liquidated": short_liq,
            "total_value_usd": round(total_liq_value, 2),
        },
        "summary": " | ".join(summary_parts),
    }


# ---------------------------------------------------------------------------
# 8. 综合评分
# ---------------------------------------------------------------------------
def calculate_market_score(btc: dict, eth: dict, fear_greed: dict, tickers: list) -> int:
    score = 50
    btc_score = btc.get("tech_score", 50)
    eth_score = eth.get("tech_score", 50)
    score += (btc_score - 50) * 0.4 + (eth_score - 50) * 0.2
    fg_val = fear_greed.get("value", 50)
    if fg_val > 60:
        score += 5
    elif fg_val < 40:
        score -= 5
    if tickers:
        up = sum(1 for t in tickers if t["price_change_pct"] > 0)
        ratio = up / len(tickers)
        score += (ratio - 0.5) * 20
    return max(0, min(100, int(score)))


# ---------------------------------------------------------------------------
# 9. 生成摘要
# ---------------------------------------------------------------------------
def generate_market_summary(
    btc: dict, eth: dict, fear_greed: dict,
    trending: list, social_hype: list, score: int,
    alpha_data: dict = None, derivatives_data: dict = None,
) -> str:
    btc_price = btc.get("current_price", 0)
    btc_rsi = btc.get("rsi", 50)
    eth_price = eth.get("current_price", 0)
    fg_label = fear_greed.get("label", "Neutral")
    fg_val = fear_greed.get("value", 50)

    trend_symbols = [t["symbol"] for t in trending[:5]] if trending else []
    social_symbols = [t["symbol"] for t in social_hype[:3]] if social_hype else []

    summary = (
        f"【市场概览】BTC ${btc_price:,.0f} | ETH ${eth_price:,.0f} | "
        f"恐惧贪婪: {fg_val}({fg_label}) | 综合评分: {score}/100\n"
        f"【技术信号】BTC RSI {btc_rsi} | {' '.join(btc.get('signals', [])[:3])}\n"
    )

    if trend_symbols:
        summary += f"【趋势代币】{' | '.join(trend_symbols)}\n"
    if social_symbols:
        summary += f"【社交热度】{' | '.join(social_symbols)}\n"

    # 新增 Alpha 摘要（可选）
    if alpha_data and alpha_data.get("available"):
        summary += f"【Alpha监控】{alpha_data.get('summary', '')}\n"

    # 新增 Derivatives 摘要（可选）
    if derivatives_data and derivatives_data.get("available"):
        summary += f"【合约数据】{derivatives_data.get('summary', '')}\n"

    return summary.strip()


# ---------------------------------------------------------------------------
# 主函数
# ---------------------------------------------------------------------------
def run_market_analysis(
    enable_alpha: bool = True,
    enable_derivatives: bool = True,
    derivatives_symbol: str = "BTCUSDT",
) -> dict:
    """
    执行完整的行情分析。

    Args:
        enable_alpha:        是否启用 Alpha 早期项目监控（可选，默认 True）
        enable_derivatives:  是否启用合约多空比/清算数据（可选，默认 True）
        derivatives_symbol:  合约数据分析标的（默认 BTCUSDT）

    Returns:
        market_analysis_report (dict)
    """
    # 1. 主流币 24h 行情
    raw_tickers = fetch_ticker_24hr(WATCHLIST_PAIRS)
    tickers = [parse_ticker(t) for t in raw_tickers]

    # 2. BTC/ETH 技术分析
    btc_analysis = analyze_technicals("BTCUSDT")
    eth_analysis = analyze_technicals("ETHUSDT")

    # 3. 趋势代币排名（多链，过滤市值<500万美元的小币）
    trending = []
    for chain in ["56", "CT_501"]:
        tokens = fetch_trending_tokens(chain_id=chain, top_n=10)
        tokens = [t for t in tokens if float(t.get("market_cap", 0)) >= 5_000_000]
        trending.extend(tokens)

    # 4. 社交热度
    social_hype = []
    for chain in ["56", "CT_501"]:
        social_hype.extend(fetch_social_hype(chain_id=chain, top_n=5))

    # 5. Fear & Greed
    fear_greed = fetch_fear_greed()

    # 6. [可选] Alpha 早期项目监控
    alpha_data = None
    if enable_alpha:
        print("[L3] 正在获取 Alpha 早期项目数据...")
        alpha_data = run_alpha_monitor(top_n=10)
        if alpha_data.get("available"):
            print(f"[L3] Alpha 监控: {alpha_data['total_tokens']} 个项目，"
                  f"{alpha_data['hot_tokens_count']} 个热门项目")
        else:
            print(f"[L3] Alpha 监控不可用: {alpha_data.get('reason', '')}")

    # 7. [可选] 合约多空比/清算数据
    derivatives_data = None
    if enable_derivatives:
        print(f"[L3] 正在获取 {derivatives_symbol} 合约数据...")
        derivatives_data = run_derivatives_analysis(symbol=derivatives_symbol)
        if derivatives_data.get("available"):
            print(f"[L3] 合约数据: {derivatives_data.get('summary', '')}")
        else:
            print(f"[L3] 合约数据不可用: {derivatives_data.get('reason', '')}")

    # 8. 综合评分
    market_score = calculate_market_score(btc_analysis, eth_analysis, fear_greed, tickers)

    # 9. 生成摘要
    summary = generate_market_summary(
        btc_analysis, eth_analysis, fear_greed,
        trending, social_hype, market_score,
        alpha_data=alpha_data,
        derivatives_data=derivatives_data,
    )

    report = {
        "btc_analysis": btc_analysis,
        "eth_analysis": eth_analysis,
        "market_overview": {
            "tickers": tickers,
            "up_count": sum(1 for t in tickers if t["price_change_pct"] > 0),
            "down_count": sum(1 for t in tickers if t["price_change_pct"] < 0),
            "total_volume": sum(t["quote_volume_24h"] for t in tickers),
        },
        "trending_tokens": trending,
        "social_hype": social_hype,
        "fear_greed": fear_greed,
        "technical_signals": {
            "btc": btc_analysis.get("signals", []),
            "eth": eth_analysis.get("signals", []),
        },
        "market_score": market_score,
        "market_summary": summary,
        # 新增字段（v6.0）
        "alpha_monitor": alpha_data,
        "derivatives_data": derivatives_data,
        "timestamp": int(time.time()),
    }

    return report


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="L3 行情分析引擎 v6.0")
    parser.add_argument("--no-alpha", action="store_true", help="禁用 Alpha 早期项目监控")
    parser.add_argument("--no-derivatives", action="store_true", help="禁用合约多空比/清算数据")
    parser.add_argument("--symbol", default="BTCUSDT", help="合约数据分析标的（默认 BTCUSDT）")
    args = parser.parse_args()

    print("[L3] 行情分析引擎 v6.0 启动...")
    report = run_market_analysis(
        enable_alpha=not args.no_alpha,
        enable_derivatives=not args.no_derivatives,
        derivatives_symbol=args.symbol,
    )
    print(report["market_summary"])
    print(f"\n[L3] 行情评分: {report['market_score']}/100")
    print(f"[L3] BTC 技术评分: {report['btc_analysis'].get('tech_score', 'N/A')}")
    print(f"[L3] ETH 技术评分: {report['eth_analysis'].get('tech_score', 'N/A')}")
    print(f"[L3] 恐惧贪婪指数: {report['fear_greed']['value']}")
    print(f"[L3] 趋势代币: {len(report['trending_tokens'])} 个")
    print(f"[L3] 社交热度: {len(report['social_hype'])} 个")

    if report.get("alpha_monitor") and report["alpha_monitor"].get("available"):
        print(f"[L3] Alpha 监控: {report['alpha_monitor']['total_tokens']} 个项目")
    if report.get("derivatives_data") and report["derivatives_data"].get("available"):
        liq = report["derivatives_data"]["liquidation_summary"]
        print(f"[L3] 合约清算: 多单{liq['long_liquidated']}笔/空单{liq['short_liquidated']}笔")

    with open("/tmp/L3_market_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)
    print("[L3] 报告已保存至 /tmp/L3_market_report.json")
