#!/usr/bin/env python3
"""
L4 新闻+KOL 数据增强层 (News & KOL Signals)
================================================================
数据源：6551 API (opennews + opentwitter)
  1. opennews  — 加密新闻热词+热门代币
  2. opentwitter — KOL 推文信号

输出：news_kol_report (dict)
  - hot_news:         热门新闻列表
  - kol_signals:      KOL 推文信号
  - hot_keywords:     全网热词
  - news_coins:       新闻热门代币
  - market_sentiment: 市场情绪判断
  - news_score:       新闻热度评分 (0-100)
  - news_summary:     中文摘要
"""

import json
import os
import sys
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)
import config
import re
import time
import urllib.request
from datetime import datetime, timezone, timedelta
from collections import Counter
from data_cache import cached

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
TOKEN = config.TOKEN_6551
BASE = config.API_6551_BASE

# 监控的 KOL 列表
KOL_LIST = ["binancezh", "binance", "cz_binance", "VitalikButerin", "haborofficial"]

# 币安广场强相关账号
SQUARE_ACCOUNTS = ["binancezh", "binance", "cz_binance"]

# 话题分类关键词
TOPIC_PATTERNS = [
    ("新币/Launchpad", r"上市|新币|Launchpad|Launchpool|Alpha|ROBO|OPN|空投|airdrop|新上线"),
    ("行情分析", r"BTC|ETH|涨|跌|行情|价格|突破|支撑|阻力|多|空|现货"),
    ("活动/交易竞赛", r"竞赛|瓜分|奖励|交易任务|活动|奖池|参与|报名"),
    ("AI/广场", r"AI|广场|技能|Skill|智能|机器人|agent|#AIBinance"),
    ("安全/储备金", r"储备金|安全|PoR|安全感|2FA|钱包|助记词"),
    ("Web3/DeFi", r"Web3|DeFi|链上|Layer|BNBChain|钱包|质押"),
    ("地缘/宏观", r"政治|经济|通胀|CPI|美联储|战争|地缘|制裁|关税"),
    ("交易技巧/心态", r"止损|仓位|情绪|策略|复盘|纪律|心态|技巧|回撤"),
]


# ---------------------------------------------------------------------------
# HTTP 工具
# ---------------------------------------------------------------------------
def _post(endpoint: str, payload: dict) -> dict:
    """调用 6551 API"""
    try:
        body = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{BASE}/open/{endpoint}",
            data=body,
            headers={
                "Authorization": f"Bearer {TOKEN}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# 数据抓取
# ---------------------------------------------------------------------------
@cached(category="news")
def fetch_hot_news(hours: int = 6, limit: int = 15) -> list:
    """获取热门新闻"""
    raw = _post("news_search", {"limit": limit, "orderBy": "score", "timeRange": f"{hours}h"})
    items = raw.get("data", [])
    if not isinstance(items, list):
        return []

    result = []
    for item in items:
        coins = [c["symbol"] for c in (item.get("coins") or [])]
        text = re.sub(r"<[^>]+>", "", item.get("text", ""))
        result.append({
            "coins": coins,
            "text": text[:150],
            "newsType": item.get("newsType", ""),
            "source": item.get("source", ""),
            "ts": item.get("ts", ""),
        })
    return result


@cached(category="news")
def fetch_kol_tweets(limit_per_kol: int = 3) -> list:
    """获取 KOL 推文"""
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
                "text": text[:200],
                "likes": item.get("favoriteCount", 0),
                "retweets": item.get("retweetCount", 0),
                "created_at": item.get("createdAt", ""),
                "is_square_account": username in SQUARE_ACCOUNTS,
            })
    return signals


def fetch_square_signals() -> list:
    """专门获取币安广场相关账号推文"""
    tweets = []
    for username in SQUARE_ACCOUNTS:
        raw = _post("twitter_user_tweets", {"username": username, "limit": 5})
        items = raw.get("data", [])
        if isinstance(items, list):
            for item in items:
                text = item.get("text", "")
                if text:
                    tweets.append({
                        "source": username,
                        "text": text[:200],
                        "likes": item.get("favoriteCount", 0),
                        "retweets": item.get("retweetCount", 0),
                        "created_at": item.get("createdAt", ""),
                    })
    return tweets


# ---------------------------------------------------------------------------
# 分析函数
# ---------------------------------------------------------------------------
def extract_hot_keywords(news: list, kol_tweets: list) -> list:
    """提取全网热词"""
    all_text = " ".join([n["text"] for n in news] + [s["text"] for s in kol_tweets])
    tokens = re.findall(r"\b[A-Z]{2,10}\b", all_text)
    stopwords = {"USD", "USDT", "USDC", "THE", "AND", "FOR", "ARE", "NOT", "YOU", "WITH",
                 "THIS", "THAT", "FROM", "HAVE", "HAS", "WILL", "CAN", "ALL", "NEW"}
    filtered = [t for t in tokens if t not in stopwords]
    return Counter(filtered).most_common(15)


def extract_news_coins(news: list) -> list:
    """提取新闻中的热门代币"""
    coins = []
    for n in news:
        coins.extend(n["coins"])
    return Counter(coins).most_common(10)


def classify_topics(tweets: list, news: list) -> list:
    """话题分类"""
    topic_scores = Counter()
    topic_examples = {}

    all_content = [(t["text"], t.get("source", t.get("username", "")),
                    t.get("likes", 0) + t.get("retweets", 0) * 3)
                   for t in tweets]
    all_content += [(n["text"], n["source"], 5) for n in news]

    for text, source, weight in all_content:
        for topic_name, pattern in TOPIC_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                topic_scores[topic_name] += (1 + weight * 0.1)
                if topic_name not in topic_examples:
                    topic_examples[topic_name] = (text[:80], source)

    results = []
    for topic, score in topic_scores.most_common():
        example_text, example_source = topic_examples.get(topic, ("", ""))
        results.append({
            "topic": topic,
            "score": round(score, 1),
            "example": example_text,
            "source": example_source,
        })
    return results


def extract_hot_hashtags(tweets: list) -> list:
    """提取热门标签"""
    tags = re.findall(r"#(\w+)", " ".join([t["text"] for t in tweets]))
    stopwords = {"BuildwithBinance", "AskBinance"}
    filtered = [t for t in tags if t not in stopwords and len(t) > 1]
    return Counter(filtered).most_common(10)


def judge_sentiment(btc_change: float = None, news: list = None) -> dict:
    """市场情绪判断"""
    if btc_change is not None:
        if btc_change >= 3:
            sentiment = "极度贪婪"
            topic_boost = "行情分析"
        elif btc_change >= 1:
            sentiment = "偏多"
            topic_boost = "行情分析"
        elif btc_change <= -3:
            sentiment = "极度恐惧"
            topic_boost = "交易心态/抄底讨论"
        elif btc_change <= -1:
            sentiment = "偏空"
            topic_boost = "风险管理"
        else:
            sentiment = "中性"
            topic_boost = "交易技巧/策略"
    else:
        sentiment = "未知"
        topic_boost = "交易策略"

    return {"sentiment": sentiment, "topic_boost": topic_boost, "btc_change": btc_change}


def calculate_news_score(news: list, kol_tweets: list, topics: list) -> int:
    """计算新闻热度评分"""
    score = 50

    # 新闻数量
    score += min(len(news) * 2, 15)

    # KOL 推文数量
    score += min(len(kol_tweets) * 1.5, 10)

    # 话题多样性
    score += min(len(topics) * 2, 10)

    # KOL 互动量
    total_engagement = sum(t.get("likes", 0) + t.get("retweets", 0) * 3 for t in kol_tweets)
    if total_engagement > 10000:
        score += 15
    elif total_engagement > 5000:
        score += 10
    elif total_engagement > 1000:
        score += 5

    return max(0, min(100, round(score)))


# ---------------------------------------------------------------------------
# 摘要
# ---------------------------------------------------------------------------
def generate_news_summary(news: list, kol_tweets: list, keywords: list,
                           news_coins: list, topics: list,
                           sentiment: dict, score: int) -> str:
    """生成新闻+KOL 中文摘要"""
    lines = []
    tz_cn = timezone(timedelta(hours=8))
    now_str = datetime.now(tz_cn).strftime("%Y-%m-%d %H:%M")

    lines.append(f"## L4 新闻+KOL 信号报告 ({now_str} UTC+8)")
    lines.append(f"**新闻热度评分: {score}/100** | 新闻 {len(news)} 条 | KOL推文 {len(kol_tweets)} 条")
    lines.append("")

    # 市场情绪
    lines.append(f"### 市场情绪: {sentiment['sentiment']}")
    lines.append(f"- 推荐话题方向: {sentiment['topic_boost']}")
    lines.append("")

    # 全网热词
    if keywords:
        kw_str = " ".join([f"#{k}({c})" for k, c in keywords[:8]])
        lines.append(f"### 全网热词\n{kw_str}")
        lines.append("")

    # 新闻热门代币
    if news_coins:
        coins_str = " ".join([f"${c}({n})" for c, n in news_coins[:6]])
        lines.append(f"### 新闻热门代币\n{coins_str}")
        lines.append("")

    # 话题分类
    if topics:
        lines.append("### 话题热度排名")
        for t in topics[:5]:
            lines.append(f"- {t['topic']}: 热度 {t['score']}")
        lines.append("")

    # 热门新闻
    if news:
        lines.append("### 最新高热新闻")
        for n in news[:3]:
            coins_str = "/".join(n["coins"][:2]) if n["coins"] else ""
            prefix = f"[{coins_str}] " if coins_str else ""
            lines.append(f"- {prefix}{n['text'][:80]}")
        lines.append("")

    # KOL 动态
    hot_kol = sorted(kol_tweets, key=lambda x: x.get("likes", 0) + x.get("retweets", 0) * 3, reverse=True)
    if hot_kol:
        lines.append("### KOL 热门动态")
        for s in hot_kol[:3]:
            lines.append(f"- @{s['username']}: {s['text'][:70]}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 主函数
# ---------------------------------------------------------------------------
def run_news_kol(btc_change: float = None) -> dict:
    """执行完整的新闻+KOL 分析。如果 6551 API 未配置，返回空报告。"""
    # 可用性检查：无 API 配置时优雅降级
    if not config.HAS_6551_API:
        print("[L4] 6551 API 未配置（TOKEN_6551 / API_6551_BASE 为空），L4 层跳过")
        return {
            "hot_news": [], "kol_signals": [], "square_signals": [],
            "hot_keywords": [], "hot_hashtags": [], "news_coins": [],
            "topic_classification": [], "market_sentiment": judge_sentiment(btc_change),
            "news_score": 0, "news_summary": "[L4 未启用] 6551 API 未配置，新闻+KOL 数据不可用。",
            "timestamp": int(time.time()), "available": False,
        }

    news = fetch_hot_news(hours=6, limit=15)
    kol_tweets = fetch_kol_tweets(limit_per_kol=3)
    square_tweets = fetch_square_signals()

    all_tweets = kol_tweets + square_tweets
    keywords = extract_hot_keywords(news, all_tweets)
    news_coins = extract_news_coins(news)
    topics = classify_topics(all_tweets, news)
    hashtags = extract_hot_hashtags(all_tweets)
    sentiment = judge_sentiment(btc_change, news)
    score = calculate_news_score(news, all_tweets, topics)

    summary = generate_news_summary(
        news, all_tweets, keywords, news_coins, topics, sentiment, score
    )

    report = {
        "hot_news": news,
        "kol_signals": kol_tweets,
        "square_signals": square_tweets,
        "hot_keywords": keywords,
        "hot_hashtags": hashtags,
        "news_coins": news_coins,
        "topic_classification": topics,
        "market_sentiment": sentiment,
        "news_score": score,
        "news_summary": summary,
        "timestamp": int(time.time()),
        "available": True,
    }

    return report


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("[L4] 新闻+KOL 信号引擎启动...")
    report = run_news_kol(btc_change=-1.2)
    print(report["news_summary"])
    print(f"\n[L4] 新闻热度评分: {report['news_score']}/100")
    print(f"[L4] 新闻: {len(report['hot_news'])} 条")
    print(f"[L4] KOL推文: {len(report['kol_signals'])} 条")
    print(f"[L4] 广场信号: {len(report['square_signals'])} 条")

    with open("/tmp/L4_news_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)
    print("[L4] 报告已保存至 /tmp/L4_news_report.json")
