#!/usr/bin/env python3
"""
6551 数据增强层 - 广场流量预言机
引用：opennews（新闻热词）+ twitter KOL（大V动态）
不替换任何官方skill，纯增强
"""
import json, urllib.request, os
from datetime import datetime, timezone

TOKEN = os.environ.get("TOKEN_6551", "")
BASE = os.environ.get("API_6551_BASE", "")

# 监控的加密KOL列表
KOL_LIST = ["binance", "cz_binance", "VitalikButerin", "SBF_FTX", "aantonop"]


def _post(endpoint, payload):
    try:
        body = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{BASE}/open/{endpoint}", data=body,
            headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"error": str(e)}


def get_hot_news(hours=6, limit=10):
    """
    opennews：获取过去N小时高热度新闻
    返回：[{coins, text, newsType, source, ts}, ...]
    """
    raw = _post("news_search", {"limit": limit, "orderBy": "score", "timeRange": f"{hours}h"})
    items = raw.get("data", [])
    if not isinstance(items, list):
        return []

    result = []
    for item in items:
        coins = [c["symbol"] for c in (item.get("coins") or [])]
        text = item.get("text", "").replace("<b>", "").replace("</b>", "")
        # 去掉HTML标签
        import re
        text = re.sub(r'<[^>]+>', '', text)
        result.append({
            "coins": coins,
            "text": text[:120],
            "newsType": item.get("newsType", ""),
            "source": item.get("source", ""),
            "ts": item.get("ts", ""),
        })
    return result


def get_kol_signals(limit_per_kol=2):
    """
    twitter_user_tweets：抓取KOL最新推文，提取热点信号
    返回：[{username, text, likes, retweets, keywords}, ...]
    """
    signals = []
    for username in KOL_LIST:
        raw = _post("twitter_user_tweets", {"username": username, "limit": limit_per_kol})
        items = raw.get("data", [])
        if not isinstance(items, list):
            continue
        for item in items:
            text = item.get("text", "")
            if not text:
                continue
            signals.append({
                "username": username,
                "text": text[:100],
                "likes": item.get("favoriteCount", 0),
                "retweets": item.get("retweetCount", 0),
            })
    return signals


def extract_hot_keywords(news_list, kol_signals):
    """
    从新闻+KOL推文中提取高频热词/代币名
    返回：[(keyword, count), ...] Top10
    """
    from collections import Counter
    import re

    all_text = " ".join([n["text"] for n in news_list] + [s["text"] for s in kol_signals])
    # 提取大写单词（代币名/项目名）
    tokens = re.findall(r'\b[A-Z]{2,10}\b', all_text)
    # 过滤常见无意义词
    stopwords = {"USD", "USDT", "USDC", "THE", "AND", "FOR", "ARE", "NOT", "YOU", "WITH"}
    filtered = [t for t in tokens if t not in stopwords]
    counter = Counter(filtered)
    return counter.most_common(10)


def build_enhancement_report(btc_change=None):
    """
    主入口：获取6551数据，生成增强报告块
    btc_change: BTC当日涨跌幅（来自官方skill），用于情绪判断
    """
    news = get_hot_news(hours=6, limit=10)
    kols = get_kol_signals(limit_per_kol=2)
    keywords = extract_hot_keywords(news, kols)

    # 市场情绪判断
    if btc_change is not None:
        if btc_change >= 3:
            sentiment = "🚀 大涨"
            topic_boost = "行情分析"
        elif btc_change >= 1:
            sentiment = "📈 上涨"
            topic_boost = "行情分析"
        elif btc_change <= -3:
            sentiment = "🔴 大跌"
            topic_boost = "交易心态/抄底讨论"
        elif btc_change <= -1:
            sentiment = "📉 下跌"
            topic_boost = "风险管理"
        else:
            sentiment = "⚖️ 震荡"
            topic_boost = "交易技巧/策略"
    else:
        sentiment = "⚖️ 未知"
        topic_boost = "交易策略"

    # 从新闻提取热门代币
    news_coins = []
    for n in news:
        news_coins.extend(n["coins"])
    from collections import Counter
    top_coins = [c for c, _ in Counter(news_coins).most_common(5)] if news_coins else []

    # 高互动KOL推文
    hot_kol = sorted(kols, key=lambda x: x["likes"] + x["retweets"] * 3, reverse=True)[:3]

    return {
        "sentiment": sentiment,
        "btc_change": btc_change,
        "topic_boost": topic_boost,
        "top_keywords": [k for k, _ in keywords[:6]],
        "top_coins_from_news": top_coins,
        "hot_news": news[:3],
        "hot_kol": hot_kol,
        "news_count": len(news),
        "kol_count": len(kols),
    }


def format_enhancement_block(data):
    """格式化输出增强数据块（嵌入square_oracle报告）"""
    lines = [
        "",
        "━" * 45,
        "📡 6551实时增强数据",
        f"  市场情绪：{data['sentiment']}  |  重点话题方向：{data['topic_boost']}",
        "",
    ]

    if data["top_keywords"]:
        lines.append(f"🔥 全网热词（opennews+Twitter）：{'  '.join(['#'+k for k in data['top_keywords']][:6])}")

    if data["top_coins_from_news"]:
        lines.append(f"📰 新闻热门代币：{'  '.join(data['top_coins_from_news'][:5])}")

    if data["hot_news"]:
        lines.append("")
        lines.append("📰 最新高热新闻（6h内）：")
        for n in data["hot_news"][:3]:
            coins_str = "/".join(n["coins"][:2]) if n["coins"] else ""
            prefix = f"[{coins_str}] " if coins_str else ""
            lines.append(f"  • {prefix}{n['text'][:80]}")

    if data["hot_kol"]:
        lines.append("")
        lines.append("🐦 KOL最新动态：")
        for s in data["hot_kol"][:3]:
            lines.append(f"  • @{s['username']}：{s['text'][:70]}")

    lines += [
        "",
        f"💡 今日选题加成建议（基于实时数据）：",
        f"  写「{data['topic_boost']}」+「{'、'.join(data['top_keywords'][:3])}」组合，概率最高",
        "━" * 45,
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    print("测试6551增强数据层...")
    data = build_enhancement_report(btc_change=-3.84)
    print(format_enhancement_block(data))
