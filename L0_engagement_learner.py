#!/usr/bin/env python3
"""
L0 互动规律学习器 - Engagement Pattern Learner
================================================================
自动从广场高互动帖子中提炼内容规律，写入 memory/engagement_patterns.md
每次运行后更新规律库，L5生成文章时可调用

规律维度：
  - 内容类型分布（地缘政治/价格观点/攻略/情绪帖）
  - 高互动钩子句式
  - 最佳发帖时间
  - 高评论率关键词
"""

import os
import json
import re
import requests
from datetime import datetime, timezone, timedelta
from collections import Counter

WORKSPACE = "/home/ubuntu/.openclaw/workspace"
PATTERN_FILE = f"{WORKSPACE}/memory/engagement_patterns.md"
BASE_URL = "https://www.binance.com"
TRENDING_API = f"{BASE_URL}/bapi/composite/v3/friendly/pgc/content/article/list"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
    "Referer": "https://www.binance.com/en/square",
}
CST = timezone(timedelta(hours=8))


def fetch_posts(feed_type: int, size: int = 60) -> list:
    try:
        r = requests.get(
            TRENDING_API,
            params={"pageSize": size, "pageIndex": 1, "type": feed_type},
            headers=HEADERS, timeout=15
        )
        d = r.json().get("data") or {}
        vos = d.get("vos") or d.get("list") or []
        posts = []
        for item in vos:
            p = item.get("vo", item)
            view = p.get("viewCount", 0) or 0
            if isinstance(view, str): view = int(re.sub(r'[^\d]', '', view) or 0)
            content = ""
            for k in ["body", "bodyText", "content", "text", "title"]:
                v = p.get(k, "")
                if isinstance(v, str) and len(v) > 3:
                    content = v[:200]; break
            # 检测语言（中文判定）
            cn_chars = len(re.findall(r'[\u4e00-\u9fff]', content))
            is_chinese = cn_chars / max(len(content), 1) > 0.2
            posts.append({
                "content": content,
                "view": int(view),
                "like": int(p.get("likeCount", 0) or 0),
                "comment": int(p.get("commentCount", 0) or 0),
                "share": int(p.get("shareCount", 0) or 0),
                "is_chinese": is_chinese,
                "tags": [t.get("name", "") for t in (p.get("hashtags") or []) if isinstance(t, dict)],
                "timestamp": int(p.get("date", 0) or 0),
            })
        return posts
    except Exception as e:
        print(f"[Learner] 抓取失败: {e}")
        return []


def classify_content(content: str) -> str:
    """简单内容分类"""
    c = content.lower()
    if any(k in c for k in ["trump", "iran", "war", "geopolit", "特朗普", "伊朗", "地缘"]):
        return "地缘政治"
    if any(k in c for k in ["btc", "eth", "bitcoin", "比特币", "以太坊", "sol", "xrp"]):
        if any(k in c for k in ["万", "涨", "跌", "多", "空", "仓", "价格", "预测"]):
            return "价格观点"
        return "代币分析"
    if any(k in c for k in ["攻略", "教程", "怎么", "如何", "方法", "技巧", "入金", "出金", "空投", "毛"]):
        return "实用攻略"
    if any(k in c for k in ["哈哈", "笑", "离谱", "牛逼", "草", "绷不住", "情绪", "感觉", "觉得"]):
        return "情绪共鸣"
    if any(k in c for k in ["理财", "年化", "收益", "利息", "本金", "睡后"]):
        return "财富计算"
    return "其他"


def extract_hooks(content: str) -> str:
    """提取前两句作为钩子"""
    lines = [l.strip() for l in content.replace("。", "。\n").split("\n") if l.strip()]
    return " ".join(lines[:2])[:80] if lines else content[:80]


def analyze(posts: list) -> dict:
    """分析互动规律"""
    if not posts:
        return {}

    def interact(p): return p["comment"] * 3 + p["like"] * 2 + p["share"] * 5

    sorted_posts = sorted(posts, key=interact, reverse=True)
    top20 = sorted_posts[:20]
    cn_top = [p for p in sorted_posts if p["is_chinese"]][:10]

    # 内容类型分布
    type_counter = Counter(classify_content(p["content"]) for p in top20)

    # 高互动钩子句式
    hooks = [extract_hooks(p["content"]) for p in top20[:10]]

    # 高频标签
    all_tags = []
    for p in top20:
        all_tags.extend(p["tags"])
    tag_counter = Counter(all_tags).most_common(10)

    # 中文帖平均互动
    cn_avg_comment = sum(p["comment"] for p in cn_top) / max(len(cn_top), 1)
    cn_avg_like = sum(p["like"] for p in cn_top) / max(len(cn_top), 1)

    # 最高互动帖
    best = sorted_posts[0] if sorted_posts else {}

    return {
        "timestamp": datetime.now(CST).strftime("%Y-%m-%d %H:%M CST"),
        "total_analyzed": len(posts),
        "content_type_dist": dict(type_counter.most_common(6)),
        "hot_hooks": hooks,
        "hot_tags": [t[0] for t in tag_counter],
        "cn_avg_comment": round(cn_avg_comment, 1),
        "cn_avg_like": round(cn_avg_like, 1),
        "best_post_preview": best.get("content", "")[:100],
        "best_post_interact": interact(best) if best else 0,
    }


def save_patterns(analysis: dict):
    """写入 memory/engagement_patterns.md"""
    now = analysis["timestamp"]
    type_lines = "\n".join(f"  - {k}: {v}篇" for k, v in analysis["content_type_dist"].items())
    hook_lines = "\n".join(f"  {i+1}. {h}" for i, h in enumerate(analysis["hot_hooks"][:5]))
    tag_line = " / ".join([f"#{t}" for t in analysis["hot_tags"][:8]])

    content = f"""# 广场互动规律库
> 自动生成，最后更新：{now}

## 内容类型互动分布（Top20帖子）
{type_lines}

## 高互动钩子句式（前5）
{hook_lines}

## 热门标签
{tag_line}

## 中文帖基准互动
- 平均评论：{analysis["cn_avg_comment"]}条
- 平均点赞：{analysis["cn_avg_like"]}个

## 当前最高互动帖（互动分{analysis["best_post_interact"]}）
> {analysis["best_post_preview"]}

## 写作建议（从规律提炼）
1. 地缘政治/大人物话题 → 流量天花板最高
2. 真实仓位披露（"我重仓开多了"）→ 评论暴涨
3. 强观点帖（"做空是愚蠢的"）→ 争议带评论
4. 数字对比（"10%年化有多恐怖？"）→ 收藏+转发
5. 疑问句结尾 → 引发回复
"""
    with open(PATTERN_FILE, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[Learner] 规律已写入 {PATTERN_FILE}")


def run_learner() -> dict:
    print("[Learner] 抓取广场数据...")
    posts = fetch_posts(1, 60) + fetch_posts(2, 60)

    # 去重
    seen, unique = set(), []
    for p in posts:
        key = p["content"][:30]
        if key not in seen:
            seen.add(key); unique.append(p)

    print(f"[Learner] 共{len(unique)}条，开始分析...")
    analysis = analyze(unique)
    save_patterns(analysis)
    return analysis


if __name__ == "__main__":
    result = run_learner()
    print(f"\n内容类型分布: {result.get('content_type_dist')}")
    print(f"热门标签: {result.get('hot_tags')}")
    print(f"中文帖均评论: {result.get('cn_avg_comment')}")
