#!/usr/bin/env python3
"""
Binance Skills Hub 集成模块 v2.0
================================================================
直接调用 binance/binance-skills-hub 官方 Skill API：
  - crypto-market-rank  (Social Hype / Unified Token Rank / Smart Money / Meme Rank / PnL Rank)
  - query-token-info    (Search / Metadata / Dynamic Data / K-Line)
  - trading-signal      (Smart Money Buy/Sell Signals)
  - query-token-audit   (Token Security Audit)
  - query-address-info  (Wallet Token Balance)
  - meme-rush           (Meme Rank List / Topic Rush Rank)
  - spot                (Binance Spot Ticker / Klines)
  - square-post         (Post to Binance Square)

参考: https://github.com/binance/binance-skills-hub
"""

import json
import time
import hashlib
import hmac
import requests
from urllib.parse import urlencode

# ---------------------------------------------------------------------------
# 公共常量
# ---------------------------------------------------------------------------
WEB3_BASE = "https://web3.binance.com"
# 使用 www.binance.com 替代 api.binance.com，避免部分云服务商 IP 被地域限制 (HTTP 451)
SPOT_BASE = "https://www.binance.com"
SQUARE_BASE = "https://www.binance.com"
KLINE_BASE = "https://dquery.sintral.io"

COMMON_HEADERS = {
    "Accept-Encoding": "identity",
    "User-Agent": "binance-web3/2.0 (Skill)",
}

CHAIN_MAP = {
    "bsc": "56",
    "base": "8453",
    "solana": "CT_501",
    "ethereum": "1",
}

# ---------------------------------------------------------------------------
# 1. Crypto Market Rank Skill
# ---------------------------------------------------------------------------
class CryptoMarketRank:
    """市场排名 Skill — Social Hype / Unified Token Rank / Smart Money / Meme / PnL"""

    @staticmethod
    def social_hype_leaderboard(chain_id: str = "56", sentiment: str = "All",
                                 target_language: str = "zh", time_range: int = 1) -> dict:
        """社交热度排行榜"""
        url = f"{WEB3_BASE}/bapi/defi/v1/public/wallet-direct/buw/wallet/market/token/pulse/social/hype/rank/leaderboard"
        params = {
            "chainId": chain_id,
            "sentiment": sentiment,
            "targetLanguage": target_language,
            "timeRange": time_range,
            "socialLanguage": "ALL",
        }
        return _get(url, params)

    @staticmethod
    def unified_token_rank(rank_type: int = 10, chain_id: str = None,
                            period: int = 50, sort_by: int = 0,
                            page: int = 1, size: int = 200, **filters) -> dict:
        """统一代币排名 (rankType: 10=Trending, 11=TopSearch, 20=Alpha, 40=Stock)"""
        url = f"{WEB3_BASE}/bapi/defi/v1/public/wallet-direct/buw/wallet/market/token/pulse/unified/rank/list"
        body = {
            "rankType": rank_type,
            "period": period,
            "sortBy": sort_by,
            "orderAsc": False,
            "page": page,
            "size": size,
        }
        if chain_id:
            body["chainId"] = chain_id
        body.update(filters)
        return _post(url, body)

    @staticmethod
    def smart_money_inflow_rank(chain_id: str = "56", period: str = "24h") -> dict:
        """智能钱净流入排名"""
        url = f"{WEB3_BASE}/bapi/defi/v1/public/wallet-direct/tracker/wallet/token/inflow/rank/query"
        body = {"chainId": chain_id, "period": period, "tagType": 2}
        return _post(url, body)

    @staticmethod
    def meme_rank(chain_id: str = "CT_501", rank_type: int = 10, limit: int = 20) -> dict:
        """Meme代币排名（来自Pulse launchpad）"""
        url = f"{WEB3_BASE}/bapi/defi/v1/public/wallet-direct/buw/wallet/market/token/pulse/rank/list"
        body = {"chainId": chain_id, "rankType": rank_type, "limit": limit}
        return _post(url, body)

    @staticmethod
    def address_pnl_rank(chain_id: str = "56", period: str = "24h",
                          tag_type: int = 2, page: int = 1, size: int = 20) -> dict:
        """交易者PnL排行榜"""
        url = f"{WEB3_BASE}/bapi/defi/v1/public/wallet-direct/tracker/wallet/address/pnl/rank/query"
        body = {
            "chainId": chain_id,
            "period": period,
            "tagType": tag_type,
            "page": page,
            "size": size,
        }
        return _post(url, body)


# ---------------------------------------------------------------------------
# 2. Query Token Info Skill
# ---------------------------------------------------------------------------
class QueryTokenInfo:
    """代币信息查询 Skill — Search / Metadata / Dynamic / K-Line"""

    @staticmethod
    def search_token(keyword: str, chain_id: str = None, page: int = 1, size: int = 20) -> dict:
        """搜索代币"""
        url = f"{WEB3_BASE}/bapi/defi/v1/public/wallet-direct/buw/wallet/market/token/search"
        params = {"keyword": keyword, "page": page, "size": size}
        if chain_id:
            params["chainId"] = chain_id
        return _get(url, params)

    @staticmethod
    def token_metadata(chain_id: str, contract_address: str) -> dict:
        """代币元数据"""
        url = f"{WEB3_BASE}/bapi/defi/v1/public/wallet-direct/buw/wallet/dex/market/token/meta/info"
        params = {"chainId": chain_id, "contractAddress": contract_address}
        return _get(url, params)

    @staticmethod
    def token_dynamic(chain_id: str, contract_address: str) -> dict:
        """代币动态数据（价格、成交量、持有者等）"""
        url = f"{WEB3_BASE}/bapi/defi/v4/public/wallet-direct/buw/wallet/market/token/dynamic/info"
        params = {"chainId": chain_id, "contractAddress": contract_address}
        return _get(url, params)

    @staticmethod
    def token_kline(address: str, platform: str = "bsc", interval: str = "1h",
                     limit: int = 100) -> dict:
        """代币K线数据"""
        url = f"{KLINE_BASE}/u-kline/v1/k-line/candles"
        params = {
            "address": address,
            "platform": platform,
            "interval": interval,
            "limit": limit,
        }
        return _get(url, params)


# ---------------------------------------------------------------------------
# 3. Trading Signal Skill
# ---------------------------------------------------------------------------
class TradingSignal:
    """交易信号 Skill — Smart Money Buy/Sell Signals"""

    @staticmethod
    def smart_money_buy(chain_id: str = "56", page: int = 1, size: int = 20,
                         period: str = "24h") -> dict:
        """智能钱买入信号"""
        url = f"{WEB3_BASE}/bapi/defi/v1/public/wallet-direct/tracker/wallet/token/buy/rank/query"
        body = {"chainId": chain_id, "page": page, "size": size,
                "period": period, "tagType": 2}
        return _post(url, body)

    @staticmethod
    def smart_money_sell(chain_id: str = "56", page: int = 1, size: int = 20,
                          period: str = "24h") -> dict:
        """智能钱卖出信号"""
        url = f"{WEB3_BASE}/bapi/defi/v1/public/wallet-direct/tracker/wallet/token/sell/rank/query"
        body = {"chainId": chain_id, "page": page, "size": size,
                "period": period, "tagType": 2}
        return _post(url, body)


# ---------------------------------------------------------------------------
# 4. Query Token Audit Skill
# ---------------------------------------------------------------------------
class QueryTokenAudit:
    """代币安全审计 Skill"""

    @staticmethod
    def audit(chain_id: str, contract_address: str) -> dict:
        """查询代币安全审计信息"""
        url = f"{WEB3_BASE}/bapi/defi/v1/public/wallet-direct/buw/wallet/market/token/audit/info"
        params = {"chainId": chain_id, "contractAddress": contract_address}
        return _get(url, params)


# ---------------------------------------------------------------------------
# 5. Query Address Info Skill
# ---------------------------------------------------------------------------
class QueryAddressInfo:
    """地址信息查询 Skill — 钱包持仓"""

    @staticmethod
    def wallet_balance(address: str, chain_id: str = "56", offset: int = 0) -> dict:
        """查询钱包代币持仓"""
        url = f"{WEB3_BASE}/bapi/defi/v3/public/wallet-direct/buw/wallet/address/pnl/active-position-list"
        params = {"address": address, "chainId": chain_id, "offset": offset}
        headers = {
            **COMMON_HEADERS,
            "clienttype": "web",
            "clientversion": "1.2.0",
        }
        return _get(url, params, extra_headers=headers)


# ---------------------------------------------------------------------------
# 6. Meme Rush Skill
# ---------------------------------------------------------------------------
class MemeRush:
    """Meme Rush Skill — Meme Rank / Topic Rush"""

    @staticmethod
    def meme_rank_list(chain_id: str = "CT_501", rank_type: int = 10, limit: int = 20) -> dict:
        """Meme代币排名列表"""
        url = f"{WEB3_BASE}/bapi/defi/v1/public/wallet-direct/buw/wallet/market/token/pulse/rank/list"
        body = {"chainId": chain_id, "rankType": rank_type, "limit": limit}
        return _post(url, body)

    @staticmethod
    def topic_rush_rank(chain_id: str = "CT_501", rank_type: int = 10,
                         sort: int = 10) -> dict:
        """话题热度排名 (rankType: 10=Latest, 20=Rising, 30=Viral)"""
        url = f"{WEB3_BASE}/bapi/defi/v1/public/wallet-direct/buw/wallet/market/token/social-rush/rank/list"
        params = {
            "chainId": chain_id,
            "rankType": rank_type,
            "sort": sort,
            "asc": "false",
        }
        return _get(url, params)


# ---------------------------------------------------------------------------
# 7. Binance Spot Skill
# ---------------------------------------------------------------------------
class BinanceSpot:
    """币安现货 Skill — 行情数据（无需认证部分）"""

    @staticmethod
    def ticker_24hr(symbol: str = None) -> dict:
        """24小时行情统计"""
        url = f"{SPOT_BASE}/api/v3/ticker/24hr"
        params = {}
        if symbol:
            params["symbol"] = symbol
        result = _get(url, params, use_web3_headers=False)
        # 修复：处理 API 返回错误（如地区限制）
        if isinstance(result, dict) and result.get("code") != 0 and result.get("msg"):
            print(f"[Skills Hub] Spot API Warning: {result.get('msg')}")
            # 返回空结构以防后续崩溃
            if symbol:
                return {"symbol": symbol, "lastPrice": "0", "priceChangePercent": "0"}
            return []
        return result

    @staticmethod
    def ticker_24h(symbol: str = None) -> list:
        """向后兼容方法名: ticker_24h -> ticker_24hr"""
        return BinanceSpot.ticker_24hr(symbol=symbol)

    @staticmethod
    def ticker_price(symbol: str = None) -> dict:
        """最新价格"""
        url = f"{SPOT_BASE}/api/v3/ticker/price"
        params = {}
        if symbol:
            params["symbol"] = symbol
        return _get(url, params, use_web3_headers=False)

    @staticmethod
    def klines(symbol: str, interval: str = "1h", limit: int = 100) -> dict:
        """K线数据"""
        url = f"{SPOT_BASE}/api/v3/klines"
        params = {"symbol": symbol, "interval": interval, "limit": limit}
        return _get(url, params, use_web3_headers=False)

    @staticmethod
    def depth(symbol: str, limit: int = 20) -> dict:
        """订单簿深度"""
        url = f"{SPOT_BASE}/api/v3/depth"
        params = {"symbol": symbol, "limit": limit}
        return _get(url, params, use_web3_headers=False)

    @staticmethod
    def exchange_info(symbol: str = None) -> dict:
        """交易对信息"""
        url = f"{SPOT_BASE}/api/v3/exchangeInfo"
        params = {}
        if symbol:
            params["symbol"] = symbol
        return _get(url, params, use_web3_headers=False)


# ---------------------------------------------------------------------------
# 8. Square Post Skill
# ---------------------------------------------------------------------------
class SquarePost:
    """币安广场发帖 Skill"""

    @staticmethod
    def post_content(api_key: str, body_text: str) -> dict:
        """发布内容到币安广场"""
        url = f"{SQUARE_BASE}/bapi/composite/v1/public/pgc/openApi/content/add"
        headers = {
            "X-Square-OpenAPI-Key": api_key,
            "Content-Type": "application/json",
            "clienttype": "binanceSkill",
        }
        body = {"bodyTextOnly": body_text}
        try:
            resp = requests.post(url, json=body, headers=headers, timeout=30)
            resp.raise_for_status()
            result = resp.json()
            if result.get("code") == "000000" and result.get("data", {}).get("id"):
                content_id = result["data"]["id"]
                result["post_url"] = f"https://www.binance.com/square/post/{content_id}"
            return result
        except Exception as e:
            return {"code": "error", "message": str(e)}


# ---------------------------------------------------------------------------
# 组合模式 — 官方4种内容质量指南
# ---------------------------------------------------------------------------
class ContentCombo:
    """
    官方4种内容组合模式，叠加多个Skill获取全方位数据：
      组合1: 日常快讯型 — Crypto Market Rank + Query Token Info + Spot
      组合2: 深度分析型 — Query Token Info + Trading Signal + Token Audit + Spot
      组合3: 链上洞察型 — Trading Signal + Address Info + Token Info + Token Audit
      组合4: Meme猎手型 — Meme Rush + Token Info + Token Audit + Trading Signal
    """

    @staticmethod
    def combo_daily_express(chains: list = None) -> dict:
        """组合1: 日常快讯型 — 每日市场速递"""
        if chains is None:
            chains = ["56", "CT_501"]

        data = {"combo_type": "daily_express", "chains": chains}

        # 1. Social Hype Leaderboard（多链）
        social_hype = {}
        for chain in chains:
            try:
                result = CryptoMarketRank.social_hype_leaderboard(chain_id=chain)
                if result.get("success"):
                    social_hype[chain] = result.get("data", {}).get("leaderBoardList", [])
            except:
                pass
        data["social_hype"] = social_hype

        # 2. Trending Token Rank
        try:
            trending = CryptoMarketRank.unified_token_rank(rank_type=10, period=50, size=50)
            data["trending_tokens"] = trending.get("data", {}).get("tokens", [])
        except:
            data["trending_tokens"] = []

        # 3. Top Search Token Rank
        try:
            top_search = CryptoMarketRank.unified_token_rank(rank_type=11, period=50, size=20)
            data["top_search_tokens"] = top_search.get("data", {}).get("tokens", [])
        except:
            data["top_search_tokens"] = []

        # 4. Smart Money Inflow
        smart_money = {}
        for chain in chains:
            try:
                result = CryptoMarketRank.smart_money_inflow_rank(chain_id=chain)
                if result.get("success"):
                    smart_money[chain] = result.get("data", [])
            except:
                pass
        data["smart_money_inflow"] = smart_money

        # 5. Spot Ticker（主流币）
        top_symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
                       "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT"]
        spot_data = []
        for sym in top_symbols:
            try:
                ticker = BinanceSpot.ticker_24hr(symbol=sym)
                if ticker:
                    spot_data.append(ticker)
            except:
                pass
        data["spot_tickers"] = spot_data

        return data

    @staticmethod
    def combo_deep_analysis(token_symbol: str, chain_id: str = "56",
                             contract_address: str = None) -> dict:
        """组合2: 深度分析型 — 代币全方位拆解"""
        data = {
            "combo_type": "deep_analysis",
            "token_symbol": token_symbol,
            "chain_id": chain_id,
        }

        # 1. 搜索代币获取合约地址
        if not contract_address:
            try:
                search_result = QueryTokenInfo.search_token(token_symbol, chain_id=chain_id)
                tokens = search_result.get("data", {}).get("list", [])
                if tokens:
                    contract_address = tokens[0].get("contractAddress", "")
                    data["search_result"] = tokens[0]
            except:
                pass

        data["contract_address"] = contract_address

        if contract_address:
            # 2. Token Metadata
            try:
                meta = QueryTokenInfo.token_metadata(chain_id, contract_address)
                data["token_metadata"] = meta.get("data", {})
            except:
                data["token_metadata"] = {}

            # 3. Token Dynamic Data
            try:
                dynamic = QueryTokenInfo.token_dynamic(chain_id, contract_address)
                data["token_dynamic"] = dynamic.get("data", {})
            except:
                data["token_dynamic"] = {}

            # 4. Token Audit
            try:
                audit = QueryTokenAudit.audit(chain_id, contract_address)
                data["token_audit"] = audit.get("data", {})
            except:
                data["token_audit"] = {}

        # 5. Trading Signal
        try:
            buy_signals = TradingSignal.smart_money_buy(chain_id=chain_id)
            data["smart_money_buy"] = buy_signals.get("data", [])
        except:
            data["smart_money_buy"] = []

        try:
            sell_signals = TradingSignal.smart_money_sell(chain_id=chain_id)
            data["smart_money_sell"] = sell_signals.get("data", [])
        except:
            data["smart_money_sell"] = []

        # 6. Spot Data（如果是CEX上市代币）
        try:
            spot_symbol = f"{token_symbol.upper()}USDT"
            ticker = BinanceSpot.ticker_24hr(symbol=spot_symbol)
            data["spot_ticker"] = ticker
        except:
            data["spot_ticker"] = {}

        # 7. K-Line
        platform_map = {"56": "bsc", "CT_501": "solana", "8453": "base", "1": "ethereum"}
        platform = platform_map.get(chain_id, "bsc")
        if contract_address:
            try:
                kline = QueryTokenInfo.token_kline(contract_address, platform=platform,
                                                     interval="1h", limit=48)
                data["kline_data"] = kline.get("data", [])
            except:
                data["kline_data"] = []

        return data

    @staticmethod
    def combo_onchain_insight(chains: list = None, whale_addresses: list = None) -> dict:
        """组合3: 链上洞察型 — 鲸鱼在买什么"""
        if chains is None:
            chains = ["56", "CT_501"]

        data = {"combo_type": "onchain_insight", "chains": chains}

        # 1. Trading Signal — Smart Money Buy/Sell
        for chain in chains:
            try:
                buy = TradingSignal.smart_money_buy(chain_id=chain, size=30)
                data[f"smart_buy_{chain}"] = buy.get("data", [])
            except:
                data[f"smart_buy_{chain}"] = []

            try:
                sell = TradingSignal.smart_money_sell(chain_id=chain, size=30)
                data[f"smart_sell_{chain}"] = sell.get("data", [])
            except:
                data[f"smart_sell_{chain}"] = []

        # 2. Smart Money Inflow Rank
        for chain in chains:
            try:
                inflow = CryptoMarketRank.smart_money_inflow_rank(chain_id=chain)
                data[f"inflow_rank_{chain}"] = inflow.get("data", [])
            except:
                data[f"inflow_rank_{chain}"] = []

        # 3. PnL Leaderboard
        for chain in chains:
            try:
                pnl = CryptoMarketRank.address_pnl_rank(chain_id=chain)
                data[f"pnl_rank_{chain}"] = pnl.get("data", [])
            except:
                data[f"pnl_rank_{chain}"] = []

        # 4. Address Info（鲸鱼地址持仓）
        if whale_addresses:
            for addr_info in whale_addresses[:5]:
                addr = addr_info if isinstance(addr_info, str) else addr_info.get("address", "")
                chain = "56" if isinstance(addr_info, str) else addr_info.get("chain", "56")
                try:
                    balance = QueryAddressInfo.wallet_balance(addr, chain_id=chain)
                    data[f"whale_{addr[:10]}"] = balance.get("data", {}).get("list", [])
                except:
                    pass

        return data

    @staticmethod
    def combo_meme_hunter(chains: list = None) -> dict:
        """组合4: Meme猎手型 — 捕捉下一个叙事"""
        if chains is None:
            chains = ["CT_501", "56"]

        data = {"combo_type": "meme_hunter", "chains": chains}

        # 1. Meme Rush — Rank List
        for chain in chains:
            for rt in [10, 20, 30]:  # Trending, New, Hot
                try:
                    result = MemeRush.meme_rank_list(chain_id=chain, rank_type=rt, limit=20)
                    data[f"meme_rank_{chain}_type{rt}"] = result.get("data", [])
                except:
                    data[f"meme_rank_{chain}_type{rt}"] = []

        # 2. Topic Rush — Latest + Rising + Viral
        for chain in chains:
            for rt, sort_val in [(10, 10), (20, 10), (30, 30)]:
                try:
                    result = MemeRush.topic_rush_rank(chain_id=chain, rank_type=rt, sort=sort_val)
                    data[f"topic_rush_{chain}_type{rt}"] = result.get("data", [])
                except:
                    data[f"topic_rush_{chain}_type{rt}"] = []

        # 3. Token Info + Audit for top meme tokens
        top_memes = data.get(f"meme_rank_{chains[0]}_type10", [])
        if isinstance(top_memes, list):
            for token in top_memes[:5]:
                ca = token.get("contractAddress", "")
                chain = token.get("chainId", chains[0])
                if ca:
                    try:
                        audit = QueryTokenAudit.audit(chain, ca)
                        token["audit_info"] = audit.get("data", {})
                    except:
                        pass

        # 4. Trading Signal
        for chain in chains:
            try:
                buy = TradingSignal.smart_money_buy(chain_id=chain, size=20)
                data[f"signal_buy_{chain}"] = buy.get("data", [])
            except:
                data[f"signal_buy_{chain}"] = []

        return data


# ---------------------------------------------------------------------------
# HTTP 工具
# ---------------------------------------------------------------------------
def _get(url: str, params: dict = None, extra_headers: dict = None,
         use_web3_headers: bool = True) -> dict:
    """GET请求"""
    headers = {**COMMON_HEADERS} if use_web3_headers else {"Accept-Encoding": "identity"}
    if extra_headers:
        headers.update(extra_headers)
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=20)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"success": False, "error": str(e)}


def _post(url: str, body: dict, extra_headers: dict = None) -> dict:
    """POST请求"""
    headers = {**COMMON_HEADERS, "Content-Type": "application/json"}
    if extra_headers:
        headers.update(extra_headers)
    try:
        resp = requests.post(url, json=body, headers=headers, timeout=20)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# 便捷函数
# ---------------------------------------------------------------------------
def get_market_overview() -> dict:
    """获取市场概览数据（快速版）"""
    overview = {}

    # BTC/ETH/BNB 价格
    for sym in ["BTCUSDT", "ETHUSDT", "BNBUSDT"]:
        try:
            ticker = BinanceSpot.ticker_24hr(symbol=sym)
            overview[sym] = {
                "price": ticker.get("lastPrice"),
                "change_24h": ticker.get("priceChangePercent"),
                "volume_24h": ticker.get("quoteVolume"),
                "high_24h": ticker.get("highPrice"),
                "low_24h": ticker.get("lowPrice"),
            }
        except:
            pass

    # Trending tokens
    try:
        trending = CryptoMarketRank.unified_token_rank(rank_type=10, size=10)
        overview["trending_tokens"] = [
            {"symbol": t.get("symbol"), "price": t.get("price"),
             "change_24h": t.get("percentChange24h")}
            for t in trending.get("data", {}).get("tokens", [])[:10]
        ]
    except:
        overview["trending_tokens"] = []

    return overview


def get_token_full_report(symbol: str, chain_id: str = "56") -> dict:
    """获取代币完整报告"""
    return ContentCombo.combo_deep_analysis(symbol, chain_id=chain_id)


# ---------------------------------------------------------------------------
# CLI 测试
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("[Skills Hub] 测试市场概览...")
    overview = get_market_overview()
    print(json.dumps(overview, indent=2, default=str)[:2000])

    print("\n[Skills Hub] 测试Trending Token Rank...")
    trending = CryptoMarketRank.unified_token_rank(rank_type=10, size=5)
    tokens = trending.get("data", {}).get("tokens", [])
    for t in tokens[:5]:
        print(f"  {t.get('symbol')}: ${t.get('price')} ({t.get('percentChange24h')}%)")
