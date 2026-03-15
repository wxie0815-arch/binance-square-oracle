#!/usr/bin/env python3
"""
L1 社交热度排名模块 (Social Hype Leaderboard)
================================================================
数据源（使用币安官方 crypto-market-rank API）：
  1. Social Hype Leaderboard  — 社交热度排名+情绪分析+摘要
  2. Unified Token Rank       — 趋势代币排名

输出：social_hype_report (dict)
  - social_hype_list:    社交热度排名列表
  - trending_tokens:     趋势代币排名
  - sentiment_overview:  情绪概览
  - hot_narratives:      热门叙事
  - social_score:        社交热度评分 (0-100)
  - social_summary:      中文摘要
"""

import json
import time
import requests
from data_cache import cached
from datetime import datetime, timezone, timedelta
from collections import Counter

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
WEB3_API = "https://web3.binance.com"
HEADERS_GET = {"Accept-Encoding": "identity"}
HEADERS_JSON = {"Content-Type": "application/json", "Accept-Encoding": "identity"}

# 多链覆盖
CHAIN_IDS = ["56", "CT_501"]  # BSC + Solana


# ---------------------------------------------------------------------------
# 1. Social Hype Leaderboard
# ---------------------------------------------------------------------------
@cached(category="social_hype")
def fetch_social_hype(chain_id: str = "56", top_n: int = 15) -> list:
    """获取社交热度排名"""
    url = f"{WEB3_API}/bapi/defi/v1/public/wallet-direct/buw/wallet/market/token/pulse/social/hype/rank/leaderboard"
    params = {
        "chainId": chain_id,
        "sentiment": "All",
        "socialLanguage": "ALL",
        "targetLanguage": "zh",
        "timeRange": 1,
    }
    try:
        resp = requests.get(url, params=params, headers=HEADERS_GET, timeout=15)
        data = resp.json()
        if data.get("success") and data.get("data", {}).get("leaderBoardList"):
            items = data["data"]["leaderBoardList"]
            return [
                {
                    "symbol": item.get("metaInfo", {}).get("symbol", ""),
                    "name": item.get("metaInfo", {}).get("name", ""),
                    "social_hype": item.get("socialHypeInfo", {}).get("socialHype", 0),
                    "sentiment": item.get("socialHypeInfo", {}).get("sentiment", ""),
                    "summary_cn": item.get("socialHypeInfo", {}).get(
                        "socialSummaryBriefTranslated", ""
                    ) or "",
                    "summary_detail": item.get("socialHypeInfo", {}).get(
                        "socialSummaryDetailTranslated", ""
                    ) or "",
                    "market_cap": item.get("marketInfo", {}).get("marketCap", 0),
                    "price_change": item.get("marketInfo", {}).get("priceChange", 0),
                    "chain_id": chain_id,
                }
                for item in items[:top_n]
            ]
    except Exception as e:
        print(f"[L1] Social Hype 请求失败 (chain={chain_id}): {e}")
    return []


# ---------------------------------------------------------------------------
# 2. Trending Token Rank
# ---------------------------------------------------------------------------
@cached(category="social_hype")
def fetch_trending_tokens(chain_id: str = "56", top_n: int = 15) -> list:
    """获取趋势代币排名"""
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
                    "name": t.get("name", ""),
                    "price": t.get("price", "0"),
                    "market_cap": t.get("marketCap", "0"),
                    "change_24h": t.get("percentChange24h", "0"),
                    "volume_24h": t.get("volume24h", "0"),
                    "holders": t.get("holders", "0"),
                    "chain_id": chain_id,
                }
                for t in tokens[:top_n]
            ]
    except Exception as e:
        print(f"[L1] Trending Tokens 请求失败 (chain={chain_id}): {e}")
    return []


# ---------------------------------------------------------------------------
# 分析函数
# ---------------------------------------------------------------------------
def analyze_sentiment(hype_list: list) -> dict:
    """分析情绪概览"""
    if not hype_list:
        return {"positive": 0, "negative": 0, "neutral": 0, "dominant": "Neutral"}
    sentiments = Counter(item.get("sentiment", "Neutral") for item in hype_list)
    total = sum(sentiments.values())
    dominant = sentiments.most_common(1)[0][0] if sentiments else "Neutral"
    return {
        "positive": sentiments.get("Positive", 0),
        "negative": sentiments.get("Negative", 0),
        "neutral": sentiments.get("Neutral", 0),
        "total": total,
        "dominant": dominant,
        "positive_ratio": round(sentiments.get("Positive", 0) / total * 100, 1) if total else 0,
    }


def extract_narratives(hype_list: list) -> list:
    """从社交摘要中提取热门叙事"""
    narratives = Counter()
    keywords_map = {
        "AI": ["AI", "人工智能", "机器学习", "agent"],
        "DeFi": ["DeFi", "DEX", "流动性", "质押"],
        "Meme": ["meme", "DOGE", "PEPE", "WIF", "BONK"],
        "Layer2": ["Layer2", "L2", "扩容", "Rollup"],
        "RWA": ["RWA", "现实资产", "代币化"],
        "GameFi": ["GameFi", "游戏", "NFT"],
        "BTC生态": ["BTC", "比特币", "铭文", "Ordinals"],
        "ETH生态": ["ETH", "以太坊", "Ethereum"],
    }
    for item in hype_list:
        text = (item.get("summary_cn", "") or "") + " " + (item.get("summary_detail", "") or "")
        for narrative, keywords in keywords_map.items():
            for kw in keywords:
                if kw.lower() in text.lower():
                    narratives[narrative] += 1
                    break
    return narratives.most_common()


def calculate_social_score(hype_list: list, sentiment: dict) -> int:
    """计算社交热度评分 (0-100)"""
    score = 50

    # 热度代币数量
    if len(hype_list) > 10:
        score += 10
    elif len(hype_list) > 5:
        score += 5

    # 总热度值
    total_hype = sum(item.get("social_hype", 0) for item in hype_list)
    if total_hype > 5000000:
        score += 15
    elif total_hype > 1000000:
        score += 10
    elif total_hype > 500000:
        score += 5

    # 情绪偏向
    pos_ratio = sentiment.get("positive_ratio", 0)
    if pos_ratio > 60:
        score += 10
    elif pos_ratio < 30:
        score -= 10

    # 价格上涨代币比例
    up_count = sum(1 for item in hype_list if float(item.get("price_change", 0) or 0) > 0)
    if hype_list:
        up_ratio = up_count / len(hype_list)
        score += int((up_ratio - 0.5) * 20)

    return max(0, min(100, score))


# ---------------------------------------------------------------------------
# 摘要
# ---------------------------------------------------------------------------
def generate_social_summary(hype_list: list, trending: list,
                             sentiment: dict, narratives: list,
                             score: int) -> str:
    """生成社交热度中文摘要"""
    lines = []
    tz_cn = timezone(timedelta(hours=8))
    now_str = datetime.now(tz_cn).strftime("%Y-%m-%d %H:%M")

    lines.append(f"## L1 社交热度报告 ({now_str} UTC+8)")
    lines.append(f"**社交热度评分: {score}/100**")
    lines.append("")

    # 情绪概览
    lines.append("### 市场情绪")
    lines.append(
        f"- 看多: {sentiment['positive']} | 看空: {sentiment['negative']} | "
        f"中性: {sentiment['neutral']} | 主导情绪: **{sentiment['dominant']}**"
    )
    lines.append("")

    # 社交热度 Top 5
    if hype_list:
        lines.append("### 社交热度 Top 5")
        for item in hype_list[:5]:
            lines.append(
                f"- **{item['symbol']}**: 热度 {item['social_hype']:,}，"
                f"情绪 {item['sentiment']}，{(item['summary_cn'] or '')[:50]}"
            )
        lines.append("")

    # 热门叙事
    if narratives:
        lines.append("### 热门叙事")
        for narrative, count in narratives[:5]:
            lines.append(f"- {narrative}: {count} 个代币涉及")
        lines.append("")

    # 趋势代币
    if trending:
        lines.append("### 趋势代币 Top 5")
        for t in trending[:5]:
            lines.append(
                f"- **{t['symbol']}**: 24h变化 {t['change_24h']}%"
            )
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 主函数
# ---------------------------------------------------------------------------
def run_social_hype() -> dict:
    """执行完整的社交热度分析"""
    # 多链聚合
    all_hype = []
    all_trending = []
    for chain in CHAIN_IDS:
        all_hype.extend(fetch_social_hype(chain_id=chain, top_n=10))
        all_trending.extend(fetch_trending_tokens(chain_id=chain, top_n=10))

    # 按热度排序去重
    seen = set()
    unique_hype = []
    for item in sorted(all_hype, key=lambda x: x.get("social_hype", 0), reverse=True):
        if item["symbol"] not in seen:
            seen.add(item["symbol"])
            unique_hype.append(item)

    # 分析
    sentiment = analyze_sentiment(unique_hype)
    narratives = extract_narratives(unique_hype)
    score = calculate_social_score(unique_hype, sentiment)

    summary = generate_social_summary(
        unique_hype, all_trending, sentiment, narratives, score
    )

    report = {
        "social_hype_list": unique_hype,
        "trending_tokens": all_trending,
        "sentiment_overview": sentiment,
        "hot_narratives": narratives,
        "social_score": score,
        "social_summary": summary,
        "timestamp": int(time.time()),
    }

    return report


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("[L1] 社交热度排名引擎启动...")
    report = run_social_hype()
    print(report["social_summary"])
    print(f"\n[L1] 社交热度评分: {report['social_score']}/100")
    print(f"[L1] 热度代币: {len(report['social_hype_list'])} 个")
    print(f"[L1] 趋势代币: {len(report['trending_tokens'])} 个")
    print(f"[L1] 主导情绪: {report['sentiment_overview']['dominant']}")

    with open("/tmp/L1_social_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)
    print("[L1] 报告已保存至 /tmp/L1_social_report.json")
