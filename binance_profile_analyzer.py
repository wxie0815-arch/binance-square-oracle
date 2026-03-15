#!/usr/bin/env python3
"""
币安广场（Binance Square）用户主页内容抓取与创作分析工具

功能：
1. 通过用户名搜索并定位币安广场用户
2. 抓取用户完整 Profile 信息（粉丝、关注、帖子数等）
3. 抓取用户全部历史帖子（支持分页遍历）
4. 分析用户写作内容、创作喜好、活跃度等
5. 生成结构化的分析报告（CSV/JSON/Markdown）

所有接口均为未登录态，无需认证。

API 端点：
- 用户搜索: /bapi/composite/v2/friendly/pgc/feed/search/list (需 Playwright)
- 用户 Profile: /bapi/composite/v3/friendly/pgc/user/client
- 用户帖子: /bapi/composite/v2/friendly/pgc/content/queryUserProfilePageContentsWithFilter
"""

import requests
import json
import csv
import os
import sys
import re
import argparse
import time
from datetime import datetime, timezone, timedelta
from collections import Counter


# ==================== 配置 ====================

BASE_URL = "https://www.binance.com"
USER_PROFILE_API = f"{BASE_URL}/bapi/composite/v3/friendly/pgc/user/client"
USER_POSTS_API = f"{BASE_URL}/bapi/composite/v2/friendly/pgc/content/queryUserProfilePageContentsWithFilter"
SEARCH_API = f"{BASE_URL}/bapi/composite/v2/friendly/pgc/feed/search/list"
SEARCH_INTENT_API = f"{BASE_URL}/bapi/composite/v1/friendly/pgc/search/query/intended"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://www.binance.com",
    "Content-Type": "application/json",
    "clienttype": "web",
    "lang": "en",
}

# 请求间隔（秒）
REQUEST_DELAY = 0.3

# 分页安全上限
MAX_PAGES = 100


# ==================== 用户搜索与 Profile ====================

def search_user_by_keyword(keyword):
    """
    通过关键词搜索币安广场用户。
    尝试多种方式匹配：直接用户名、去空格变体、搜索意图 API。

    参数:
        keyword: 搜索关键词（用户名）

    返回:
        匹配的用户 profile 信息，或 None
    """
    print(f"[搜索] 正在搜索用户: {keyword}")

    # 生成用户名变体
    variants = [keyword]
    # 去空格
    no_space = keyword.replace(" ", "")
    if no_space != keyword:
        variants.append(no_space)
    # 下划线替换空格
    underscore = keyword.replace(" ", "_")
    if underscore != keyword:
        variants.append(underscore)
    # 连字符替换空格
    hyphen = keyword.replace(" ", "-")
    if hyphen != keyword:
        variants.append(hyphen)

    # 方法1: 直接尝试各变体作为 username
    for variant in variants:
        profile = fetch_user_profile(variant)
        if profile and profile.get("squareUid"):
            print(f"[搜索] 匹配到用户: {profile.get('displayName', '')} (@{profile.get('username', '')})")
            return profile
        time.sleep(REQUEST_DELAY)

    # 方法2: 搜索意图 API 获取建议
    try:
        headers = dict(HEADERS)
        headers["Referer"] = f"https://www.binance.com/en/square/search?s={keyword}"
        resp = requests.get(
            SEARCH_INTENT_API,
            params={"searchStr": keyword},
            headers=headers,
            timeout=10,
        )
        data = resp.json()
        if data.get("code") == "000000" and data.get("data"):
            suggestions = data["data"].get("suggestionsList", [])
            print(f"[搜索] 搜索建议: {suggestions[:5]}")

            for suggestion in suggestions[:5]:
                # 跳过已尝试过的
                if suggestion in variants:
                    continue
                profile = fetch_user_profile(suggestion)
                if profile and profile.get("squareUid"):
                    print(f"[搜索] 通过建议匹配到用户: {profile.get('displayName', '')} (@{profile.get('username', '')})")
                    return profile
                time.sleep(REQUEST_DELAY)
    except Exception as e:
        print(f"[搜索] 搜索意图 API 错误: {e}")

    print(f"[搜索] 未找到用户: {keyword}")
    return None


def fetch_user_profile(username):
    """
    获取用户完整 Profile 信息。

    参数:
        username: 用户名

    返回:
        用户 profile 字典，包含 squareUid, displayName, biography 等
    """
    try:
        headers = dict(HEADERS)
        headers["Referer"] = f"https://www.binance.com/en/square/profile/{username}"
        body = {
            "username": username,
            "getFollowCount": True,
            "queryFollowersInfo": True,
            "queryRelationTokens": True,
        }
        resp = requests.post(USER_PROFILE_API, json=body, headers=headers, timeout=10)
        data = resp.json()
        if data.get("code") == "000000" and data.get("data"):
            return data["data"]
    except Exception as e:
        pass
    return None


def format_profile_summary(profile):
    """将 profile 数据格式化为可读的摘要字典。"""
    return {
        "username": profile.get("username") or "",
        "display_name": profile.get("displayName") or "",
        "square_uid": profile.get("squareUid") or "",
        "biography": profile.get("biography") or "",
        "verification_type": profile.get("verificationType") or 0,
        "verification_desc": profile.get("verificationDescription") or "",
        "total_followers": profile.get("totalFollowerCount") or 0,
        "total_following": profile.get("totalFollowCount") or 0,
        "total_posts": profile.get("totalListedPostCount") or 0,
        "total_likes_received": profile.get("totalLikeCount") or 0,
        "total_shares_received": profile.get("totalShareCount") or 0,
        "total_articles": profile.get("totalArticleCount") or 0,
        "account_language": profile.get("accountLang") or "",
        "avatar_url": profile.get("avatar") or "",
        "role": profile.get("role") or 0,
        "tipping_control": profile.get("tippingControl") or 0,
    }


# ==================== 帖子抓取 ====================

def fetch_user_posts(square_uid, filter_type="ALL", max_posts=None):
    """
    抓取用户全部帖子，支持分页遍历。

    参数:
        square_uid: 用户的 squareUid
        filter_type: 筛选类型 (ALL, ORIGINAL, QUOTE, LIVE)
        max_posts: 最大抓取帖子数，None 表示全部

    返回:
        帖子列表
    """
    all_posts = []
    time_offset = -1
    page = 0

    print(f"[抓取] 开始抓取帖子 (filterType={filter_type})...")

    while page < MAX_PAGES:
        page += 1
        try:
            headers = dict(HEADERS)
            headers["Referer"] = f"https://www.binance.com/en/square/profile/"
            params = {
                "targetSquareUid": square_uid,
                "timeOffset": time_offset,
                "filterType": filter_type,
            }
            resp = requests.get(USER_POSTS_API, params=params, headers=headers, timeout=15)
            data = resp.json()

            if data.get("code") != "000000" or not data.get("data"):
                print(f"[抓取] 第 {page} 页无数据，停止")
                break

            page_data = data["data"]
            contents = page_data.get("contents")
            if not contents:
                print(f"[抓取] 第 {page} 页内容为空，停止")
                break

            all_posts.extend(contents)
            new_offset = page_data.get("timeOffset")
            has_more = page_data.get("isExistSecondPage")

            print(f"[抓取] 第 {page} 页: {len(contents)} 条帖子 (累计 {len(all_posts)})")

            if max_posts and len(all_posts) >= max_posts:
                all_posts = all_posts[:max_posts]
                print(f"[抓取] 达到最大帖子数限制 ({max_posts})，停止")
                break

            if not new_offset or new_offset == time_offset:
                print(f"[抓取] 无更多分页，停止")
                break

            time_offset = new_offset
            time.sleep(REQUEST_DELAY)

        except Exception as e:
            print(f"[抓取] 第 {page} 页错误: {e}")
            break

    print(f"[抓取] 完成，共获取 {len(all_posts)} 条帖子")
    return all_posts


def parse_post(post):
    """
    解析单条帖子数据，提取关键字段。

    参数:
        post: 原始帖子字典

    返回:
        结构化的帖子数据字典
    """
    # 提取纯文本内容
    body_text = post.get("bodyTextOnly", "")
    if not body_text:
        body_raw = post.get("body", "")
        if body_raw:
            try:
                body_json = json.loads(body_raw)
                # 从 hash 结构中提取文本
                texts = []
                for key, block in body_json.get("hash", {}).items():
                    config = block.get("config", {})
                    for item in config.get("content", []):
                        if item.get("id") == "RichTextText":
                            text = item.get("config", {}).get("content", "")
                            if text:
                                texts.append(text)
                body_text = " ".join(texts)
            except (json.JSONDecodeError, AttributeError):
                body_text = re.sub(r'<[^>]+>', '', body_raw)[:500]

    # 提取 hashtag 列表
    hashtags = []
    for ht in post.get("hashtagList", []) or []:
        if isinstance(ht, dict):
            hashtags.append(ht.get("hashtag", ""))
        elif isinstance(ht, str):
            hashtags.append(ht)

    # 提取提到的币种
    trading_pairs = []
    for tp in post.get("tradingPairsV2", []) or post.get("tradingPairs", []) or []:
        if isinstance(tp, dict):
            trading_pairs.append(tp.get("symbol", tp.get("name", "")))
        elif isinstance(tp, str):
            trading_pairs.append(tp)

    # 提取时间
    create_time = post.get("firstReleaseTime") or post.get("createTime") or post.get("latestReleaseTime")
    create_dt = ""
    if create_time:
        try:
            if isinstance(create_time, (int, float)):
                create_dt = datetime.fromtimestamp(create_time / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            else:
                create_dt = str(create_time)
        except:
            create_dt = str(create_time)

    # 帖子类型
    content_type_map = {1: "short_post", 2: "long_article", 3: "live", 4: "video"}
    content_type = content_type_map.get(post.get("contentType"), str(post.get("contentType", "")))

    # 情绪倾向
    tendency_map = {0: "neutral", 1: "bullish", 2: "bearish"}
    tendency = tendency_map.get(post.get("tendency"), str(post.get("tendency", "")))

    return {
        "post_id": str(post.get("id", "")),
        "content_type": content_type,
        "title": post.get("title", ""),
        "body_text": body_text[:2000],
        "body_full": body_text,
        "language": post.get("lan", post.get("detectedLang", "")),
        "tendency": tendency,
        "hashtags": hashtags,
        "trading_pairs": trading_pairs,
        "image_count": len(post.get("imageList", []) or []),
        "has_video": bool(post.get("videoLink")),
        "is_featured": bool(post.get("isFeatured")),
        "is_quote": bool(post.get("quoteContent") or post.get("quotedContentId")),
        "view_count": post.get("viewCount", 0) or 0,
        "like_count": post.get("likeCount", 0) or 0,
        "comment_count": post.get("commentCount", 0) or 0,
        "share_count": post.get("shareCount", 0) or 0,
        "reply_count": post.get("replyCount", 0) or 0,
        "quote_count": post.get("quoteCount", 0) or 0,
        "tipping_count": post.get("tippingCount", 0) or 0,
        "tipping_amount": post.get("tippingTotalAmount", 0) or 0,
        "create_time": create_dt,
        "create_timestamp": create_time,
        "mentioned_users": [m.get("displayName", "") for m in (post.get("mentionUserVOs") or [])],
        "web_link": post.get("webLink", ""),
    }


# ==================== 内容分析 ====================

def analyze_content(parsed_posts, profile_summary):
    """
    对用户帖子进行全面的内容分析。

    参数:
        parsed_posts: 解析后的帖子列表
        profile_summary: 用户 profile 摘要

    返回:
        分析结果字典
    """
    if not parsed_posts:
        return {"error": "无帖子数据可分析"}

    analysis = {}

    # ---- 基础统计 ----
    total = len(parsed_posts)
    total_views = sum(p["view_count"] for p in parsed_posts)
    total_likes = sum(p["like_count"] for p in parsed_posts)
    total_comments = sum(p["comment_count"] for p in parsed_posts)
    total_shares = sum(p["share_count"] for p in parsed_posts)
    total_replies = sum(p["reply_count"] for p in parsed_posts)
    total_quotes = sum(p["quote_count"] for p in parsed_posts)

    analysis["basic_stats"] = {
        "total_posts": total,
        "total_views": total_views,
        "total_likes": total_likes,
        "total_comments": total_comments,
        "total_shares": total_shares,
        "total_replies": total_replies,
        "total_quotes": total_quotes,
        "avg_views_per_post": round(total_views / total, 1) if total else 0,
        "avg_likes_per_post": round(total_likes / total, 1) if total else 0,
        "avg_comments_per_post": round(total_comments / total, 1) if total else 0,
        "avg_engagement_rate": round((total_likes + total_comments + total_shares) / max(total_views, 1) * 100, 4),
    }

    # ---- 内容类型分布 ----
    type_counter = Counter(p["content_type"] for p in parsed_posts)
    analysis["content_type_distribution"] = dict(type_counter.most_common())

    # ---- 语言分布 ----
    lang_counter = Counter(p["language"] for p in parsed_posts if p["language"])
    analysis["language_distribution"] = dict(lang_counter.most_common())

    # ---- 情绪倾向分布 ----
    tendency_counter = Counter(p["tendency"] for p in parsed_posts if p["tendency"])
    analysis["tendency_distribution"] = dict(tendency_counter.most_common())

    # ---- Hashtag 分析 ----
    all_hashtags = []
    for p in parsed_posts:
        all_hashtags.extend(p["hashtags"])
    hashtag_counter = Counter(all_hashtags)
    analysis["top_hashtags"] = dict(hashtag_counter.most_common(30))

    # ---- 提及币种分析 ----
    all_coins = []
    for p in parsed_posts:
        all_coins.extend(p["trading_pairs"])
    coin_counter = Counter(all_coins)
    analysis["top_mentioned_coins"] = dict(coin_counter.most_common(20))

    # ---- 提及用户分析 ----
    all_mentions = []
    for p in parsed_posts:
        all_mentions.extend(p["mentioned_users"])
    mention_counter = Counter(m for m in all_mentions if m)
    analysis["top_mentioned_users"] = dict(mention_counter.most_common(20))

    # ---- 热门帖子 (按浏览量) ----
    sorted_by_views = sorted(parsed_posts, key=lambda x: x["view_count"], reverse=True)
    analysis["top_posts_by_views"] = [
        {
            "post_id": p["post_id"],
            "body_text": p["body_text"][:100],
            "view_count": p["view_count"],
            "like_count": p["like_count"],
            "comment_count": p["comment_count"],
            "create_time": p["create_time"],
        }
        for p in sorted_by_views[:10]
    ]

    # ---- 热门帖子 (按互动率) ----
    for p in parsed_posts:
        views = max(p["view_count"], 1)
        p["_engagement"] = (p["like_count"] + p["comment_count"] + p["share_count"]) / views
    sorted_by_engagement = sorted(parsed_posts, key=lambda x: x["_engagement"], reverse=True)
    analysis["top_posts_by_engagement"] = [
        {
            "post_id": p["post_id"],
            "body_text": p["body_text"][:100],
            "engagement_rate": round(p["_engagement"] * 100, 4),
            "view_count": p["view_count"],
            "like_count": p["like_count"],
            "create_time": p["create_time"],
        }
        for p in sorted_by_engagement[:10]
    ]

    # ---- 发布时间分析 ----
    time_analysis = {"by_hour": Counter(), "by_weekday": Counter(), "by_month": Counter()}
    for p in parsed_posts:
        ts = p.get("create_timestamp")
        if ts and isinstance(ts, (int, float)):
            dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
            time_analysis["by_hour"][dt.hour] += 1
            time_analysis["by_weekday"][dt.strftime("%A")] += 1
            time_analysis["by_month"][dt.strftime("%Y-%m")] += 1

    analysis["posting_time_by_hour"] = dict(sorted(time_analysis["by_hour"].items()))
    analysis["posting_time_by_weekday"] = dict(time_analysis["by_weekday"].most_common())
    analysis["posting_time_by_month"] = dict(sorted(time_analysis["by_month"].items()))

    # ---- 发布频率 ----
    timestamps = sorted([p["create_timestamp"] for p in parsed_posts if p.get("create_timestamp") and isinstance(p["create_timestamp"], (int, float))])
    if len(timestamps) >= 2:
        first_ts = timestamps[0] / 1000
        last_ts = timestamps[-1] / 1000
        span_days = max((last_ts - first_ts) / 86400, 1)
        analysis["posting_frequency"] = {
            "first_post_date": datetime.fromtimestamp(first_ts, tz=timezone.utc).strftime("%Y-%m-%d"),
            "latest_post_date": datetime.fromtimestamp(last_ts, tz=timezone.utc).strftime("%Y-%m-%d"),
            "active_span_days": round(span_days, 1),
            "avg_posts_per_week": round(total / span_days * 7, 2),
            "avg_posts_per_month": round(total / span_days * 30, 2),
        }

    # ---- 内容长度分析 ----
    lengths = [len(p["body_full"]) for p in parsed_posts if p["body_full"]]
    if lengths:
        analysis["content_length"] = {
            "avg_length": round(sum(lengths) / len(lengths), 1),
            "min_length": min(lengths),
            "max_length": max(lengths),
            "median_length": sorted(lengths)[len(lengths) // 2],
        }

    # ---- 多媒体使用分析 ----
    posts_with_images = sum(1 for p in parsed_posts if p["image_count"] > 0)
    posts_with_video = sum(1 for p in parsed_posts if p["has_video"])
    posts_with_quotes = sum(1 for p in parsed_posts if p["is_quote"])
    analysis["media_usage"] = {
        "posts_with_images": posts_with_images,
        "posts_with_images_pct": round(posts_with_images / total * 100, 1),
        "posts_with_video": posts_with_video,
        "posts_with_video_pct": round(posts_with_video / total * 100, 1),
        "posts_with_quotes": posts_with_quotes,
        "posts_with_quotes_pct": round(posts_with_quotes / total * 100, 1),
        "avg_images_per_post": round(sum(p["image_count"] for p in parsed_posts) / total, 2),
    }

    # ---- 打赏分析 ----
    tipped_posts = [p for p in parsed_posts if p["tipping_count"] > 0]
    if tipped_posts:
        analysis["tipping_stats"] = {
            "posts_with_tips": len(tipped_posts),
            "total_tip_count": sum(p["tipping_count"] for p in tipped_posts),
            "total_tip_amount": sum(p["tipping_amount"] for p in tipped_posts),
        }

    # ---- 关键词提取（简单频率分析）----
    word_counter = Counter()
    stop_words = set([
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "shall", "can", "to", "of", "in", "for",
        "on", "with", "at", "by", "from", "as", "into", "through", "during",
        "before", "after", "above", "below", "between", "out", "off", "over",
        "under", "again", "further", "then", "once", "here", "there", "when",
        "where", "why", "how", "all", "each", "every", "both", "few", "more",
        "most", "other", "some", "such", "no", "not", "only", "own", "same",
        "so", "than", "too", "very", "just", "because", "but", "and", "or",
        "if", "while", "about", "up", "it", "its", "this", "that", "these",
        "those", "i", "me", "my", "we", "our", "you", "your", "he", "him",
        "his", "she", "her", "they", "them", "their", "what", "which", "who",
        "whom", "whose", "de", "la", "el", "en", "es", "un", "una", "los",
        "las", "del", "al", "le", "les", "se", "que", "por", "con", "para",
        "的", "了", "是", "在", "我", "有", "和", "就", "不", "人", "都", "一",
        "个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着",
        "没有", "看", "好", "自己", "这", "他", "么", "那", "她",
    ])
    for p in parsed_posts:
        text = p["body_full"].lower()
        # 提取英文单词和中文词
        words = re.findall(r'[a-zA-Z]{3,}|[\u4e00-\u9fff]{2,}', text)
        for w in words:
            if w.lower() not in stop_words and len(w) >= 3:
                word_counter[w.lower()] += 1
    analysis["top_keywords"] = dict(word_counter.most_common(50))

    return analysis


# ==================== 输出生成 ====================

def save_posts_csv(parsed_posts, filepath):
    """保存帖子数据为 CSV 格式。"""
    if not parsed_posts:
        return

    csv_fields = [
        "post_id", "content_type", "title", "body_text", "language",
        "tendency", "hashtags", "trading_pairs", "image_count", "has_video",
        "is_featured", "is_quote", "view_count", "like_count", "comment_count",
        "share_count", "reply_count", "quote_count", "tipping_count",
        "tipping_amount", "create_time", "mentioned_users", "web_link",
    ]

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields, extrasaction="ignore")
        writer.writeheader()
        for p in parsed_posts:
            row = dict(p)
            row["hashtags"] = "; ".join(row.get("hashtags", []))
            row["trading_pairs"] = "; ".join(row.get("trading_pairs", []))
            row["mentioned_users"] = "; ".join(row.get("mentioned_users", []))
            row["body_text"] = row.get("body_text", "")[:500]
            writer.writerow(row)

    print(f"[输出] CSV 已保存: {filepath}")


def save_posts_json(parsed_posts, filepath):
    """保存帖子数据为 JSON 格式。"""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(parsed_posts, f, ensure_ascii=False, indent=2)
    print(f"[输出] JSON 已保存: {filepath}")


def generate_analysis_report(profile_summary, analysis, parsed_posts, filepath):
    """生成 Markdown 格式的分析报告。"""
    lines = []
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # 标题
    display_name = profile_summary.get("display_name", "Unknown")
    username = profile_summary.get("username", "Unknown")
    lines.append(f"# 币安广场用户分析报告: {display_name} (@{username})")
    lines.append(f"")
    lines.append(f"> 报告生成时间: {now}")
    lines.append(f"")

    # Profile 概览
    lines.append(f"## 1. 用户概览")
    lines.append(f"")
    vt = profile_summary.get("verification_type", 0)
    vt_label = {0: "未认证", 1: "已认证创作者", 2: "官方账号"}.get(vt, str(vt))
    lines.append(f"| 字段 | 值 |")
    lines.append(f"|------|------|")
    lines.append(f"| 用户名 | @{username} |")
    lines.append(f"| 显示名 | {display_name} |")
    lines.append(f"| 简介 | {profile_summary.get('biography', '')} |")
    lines.append(f"| 认证状态 | {vt_label} |")
    lines.append(f"| 粉丝数 | {profile_summary.get('total_followers', 0):,} |")
    lines.append(f"| 关注数 | {profile_summary.get('total_following', 0):,} |")
    lines.append(f"| 帖子数 | {profile_summary.get('total_posts', 0):,} |")
    lines.append(f"| 累计获赞 | {profile_summary.get('total_likes_received', 0):,} |")
    lines.append(f"| 累计分享 | {profile_summary.get('total_shares_received', 0):,} |")
    lines.append(f"| 账号语言 | {profile_summary.get('account_language', '')} |")
    lines.append(f"| 主页链接 | https://www.binance.com/en/square/profile/{username} |")
    lines.append(f"")

    if "error" in analysis:
        lines.append(f"**分析失败**: {analysis['error']}")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return

    # 基础统计
    bs = analysis.get("basic_stats", {})
    lines.append(f"## 2. 内容数据总览")
    lines.append(f"")
    lines.append(f"| 指标 | 数值 |")
    lines.append(f"|------|------|")
    lines.append(f"| 分析帖子数 | {bs.get('total_posts', 0):,} |")
    lines.append(f"| 总浏览量 | {bs.get('total_views', 0):,} |")
    lines.append(f"| 总点赞数 | {bs.get('total_likes', 0):,} |")
    lines.append(f"| 总评论数 | {bs.get('total_comments', 0):,} |")
    lines.append(f"| 总分享数 | {bs.get('total_shares', 0):,} |")
    lines.append(f"| 总引用数 | {bs.get('total_quotes', 0):,} |")
    lines.append(f"| 平均浏览量/帖 | {bs.get('avg_views_per_post', 0):,.1f} |")
    lines.append(f"| 平均点赞/帖 | {bs.get('avg_likes_per_post', 0):,.1f} |")
    lines.append(f"| 平均评论/帖 | {bs.get('avg_comments_per_post', 0):,.1f} |")
    lines.append(f"| 综合互动率 | {bs.get('avg_engagement_rate', 0):.4f}% |")
    lines.append(f"")

    # 发布频率
    pf = analysis.get("posting_frequency", {})
    if pf:
        lines.append(f"## 3. 发布频率")
        lines.append(f"")
        lines.append(f"| 指标 | 数值 |")
        lines.append(f"|------|------|")
        lines.append(f"| 最早帖子 | {pf.get('first_post_date', '')} |")
        lines.append(f"| 最新帖子 | {pf.get('latest_post_date', '')} |")
        lines.append(f"| 活跃天数 | {pf.get('active_span_days', 0)} 天 |")
        lines.append(f"| 周均发帖 | {pf.get('avg_posts_per_week', 0)} |")
        lines.append(f"| 月均发帖 | {pf.get('avg_posts_per_month', 0)} |")
        lines.append(f"")

    # 内容类型分布
    ctd = analysis.get("content_type_distribution", {})
    if ctd:
        lines.append(f"## 4. 内容类型分布")
        lines.append(f"")
        lines.append(f"| 类型 | 数量 | 占比 |")
        lines.append(f"|------|------|------|")
        for ct, count in ctd.items():
            pct = round(count / bs.get("total_posts", 1) * 100, 1)
            lines.append(f"| {ct} | {count} | {pct}% |")
        lines.append(f"")

    # 语言分布
    ld = analysis.get("language_distribution", {})
    if ld:
        lines.append(f"## 5. 语言分布")
        lines.append(f"")
        lines.append(f"| 语言 | 数量 | 占比 |")
        lines.append(f"|------|------|------|")
        for lang, count in ld.items():
            pct = round(count / bs.get("total_posts", 1) * 100, 1)
            lines.append(f"| {lang} | {count} | {pct}% |")
        lines.append(f"")

    # 情绪倾向
    td = analysis.get("tendency_distribution", {})
    if td:
        lines.append(f"## 6. 情绪倾向分布")
        lines.append(f"")
        lines.append(f"| 倾向 | 数量 | 占比 |")
        lines.append(f"|------|------|------|")
        for t, count in td.items():
            pct = round(count / bs.get("total_posts", 1) * 100, 1)
            lines.append(f"| {t} | {count} | {pct}% |")
        lines.append(f"")

    # 多媒体使用
    mu = analysis.get("media_usage", {})
    if mu:
        lines.append(f"## 7. 多媒体使用")
        lines.append(f"")
        lines.append(f"| 指标 | 数值 |")
        lines.append(f"|------|------|")
        lines.append(f"| 含图片帖子 | {mu.get('posts_with_images', 0)} ({mu.get('posts_with_images_pct', 0)}%) |")
        lines.append(f"| 含视频帖子 | {mu.get('posts_with_video', 0)} ({mu.get('posts_with_video_pct', 0)}%) |")
        lines.append(f"| 引用帖子 | {mu.get('posts_with_quotes', 0)} ({mu.get('posts_with_quotes_pct', 0)}%) |")
        lines.append(f"| 平均图片数/帖 | {mu.get('avg_images_per_post', 0)} |")
        lines.append(f"")

    # Top Hashtags
    th = analysis.get("top_hashtags", {})
    if th:
        lines.append(f"## 8. 常用 Hashtag (Top 20)")
        lines.append(f"")
        lines.append(f"| Hashtag | 使用次数 |")
        lines.append(f"|---------|----------|")
        for ht, count in list(th.items())[:20]:
            lines.append(f"| {ht} | {count} |")
        lines.append(f"")

    # Top 提及币种
    tc = analysis.get("top_mentioned_coins", {})
    if tc:
        lines.append(f"## 9. 常提及币种 (Top 15)")
        lines.append(f"")
        lines.append(f"| 币种 | 提及次数 |")
        lines.append(f"|------|----------|")
        for coin, count in list(tc.items())[:15]:
            lines.append(f"| {coin} | {count} |")
        lines.append(f"")

    # Top 提及用户
    tmu = analysis.get("top_mentioned_users", {})
    if tmu:
        lines.append(f"## 10. 常提及用户 (Top 15)")
        lines.append(f"")
        lines.append(f"| 用户 | 提及次数 |")
        lines.append(f"|------|----------|")
        for user, count in list(tmu.items())[:15]:
            lines.append(f"| {user} | {count} |")
        lines.append(f"")

    # Top 关键词
    tk = analysis.get("top_keywords", {})
    if tk:
        lines.append(f"## 11. 高频关键词 (Top 30)")
        lines.append(f"")
        lines.append(f"| 关键词 | 出现次数 |")
        lines.append(f"|--------|----------|")
        for kw, count in list(tk.items())[:30]:
            lines.append(f"| {kw} | {count} |")
        lines.append(f"")

    # 热门帖子 (浏览量)
    tpv = analysis.get("top_posts_by_views", [])
    if tpv:
        lines.append(f"## 12. 热门帖子 (按浏览量 Top 10)")
        lines.append(f"")
        lines.append(f"| 排名 | 浏览量 | 点赞 | 评论 | 发布时间 | 内容摘要 |")
        lines.append(f"|------|--------|------|------|----------|----------|")
        for i, p in enumerate(tpv, 1):
            text = p["body_text"][:60].replace("|", "/").replace("\n", " ")
            lines.append(f"| {i} | {p['view_count']:,} | {p['like_count']:,} | {p['comment_count']:,} | {p['create_time'][:10]} | {text} |")
        lines.append(f"")

    # 热门帖子 (互动率)
    tpe = analysis.get("top_posts_by_engagement", [])
    if tpe:
        lines.append(f"## 13. 热门帖子 (按互动率 Top 10)")
        lines.append(f"")
        lines.append(f"| 排名 | 互动率 | 浏览量 | 点赞 | 发布时间 | 内容摘要 |")
        lines.append(f"|------|--------|--------|------|----------|----------|")
        for i, p in enumerate(tpe, 1):
            text = p["body_text"][:60].replace("|", "/").replace("\n", " ")
            lines.append(f"| {i} | {p['engagement_rate']:.2f}% | {p['view_count']:,} | {p['like_count']:,} | {p['create_time'][:10]} | {text} |")
        lines.append(f"")

    # 发布时间分析
    pth = analysis.get("posting_time_by_hour", {})
    if pth:
        lines.append(f"## 14. 发布时间分析 (UTC)")
        lines.append(f"")
        lines.append(f"### 按小时分布")
        lines.append(f"")
        lines.append(f"| 小时 | 帖子数 |")
        lines.append(f"|------|--------|")
        for h in range(24):
            count = pth.get(h, 0)
            if count > 0:
                bar = "█" * min(count, 30)
                lines.append(f"| {h:02d}:00 | {count} {bar} |")
        lines.append(f"")

    ptw = analysis.get("posting_time_by_weekday", {})
    if ptw:
        lines.append(f"### 按星期分布")
        lines.append(f"")
        lines.append(f"| 星期 | 帖子数 |")
        lines.append(f"|------|--------|")
        for day, count in ptw.items():
            lines.append(f"| {day} | {count} |")
        lines.append(f"")

    # 打赏统计
    ts = analysis.get("tipping_stats", {})
    if ts:
        lines.append(f"## 15. 打赏统计")
        lines.append(f"")
        lines.append(f"| 指标 | 数值 |")
        lines.append(f"|------|------|")
        lines.append(f"| 获得打赏的帖子数 | {ts.get('posts_with_tips', 0)} |")
        lines.append(f"| 总打赏次数 | {ts.get('total_tip_count', 0)} |")
        lines.append(f"| 总打赏金额 | {ts.get('total_tip_amount', 0)} |")
        lines.append(f"")

    # 月度发帖趋势
    ptm = analysis.get("posting_time_by_month", {})
    if ptm:
        lines.append(f"## 16. 月度发帖趋势")
        lines.append(f"")
        lines.append(f"| 月份 | 帖子数 |")
        lines.append(f"|------|--------|")
        for month, count in ptm.items():
            bar = "█" * min(count, 30)
            lines.append(f"| {month} | {count} {bar} |")
        lines.append(f"")

    # 内容长度分析
    cl = analysis.get("content_length", {})
    if cl:
        lines.append(f"## 17. 内容长度分析")
        lines.append(f"")
        lines.append(f"| 指标 | 字符数 |")
        lines.append(f"|------|--------|")
        lines.append(f"| 平均长度 | {cl.get('avg_length', 0)} |")
        lines.append(f"| 最短 | {cl.get('min_length', 0)} |")
        lines.append(f"| 最长 | {cl.get('max_length', 0)} |")
        lines.append(f"| 中位数 | {cl.get('median_length', 0)} |")
        lines.append(f"")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[输出] 分析报告已保存: {filepath}")


# ==================== 主入口 ====================

def cmd_profile(args):
    """获取用户 Profile 信息。"""
    profile = search_user_by_keyword(args.username)
    if not profile:
        print(f"[错误] 未找到用户: {args.username}")
        sys.exit(1)

    summary = format_profile_summary(profile)
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if args.output:
        os.makedirs(args.output, exist_ok=True)
        filepath = os.path.join(args.output, f"profile_{summary['username']}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        print(f"[输出] Profile 已保存: {filepath}")


def cmd_fetch(args):
    """抓取用户全部帖子。"""
    profile = search_user_by_keyword(args.username)
    if not profile:
        print(f"[错误] 未找到用户: {args.username}")
        sys.exit(1)

    summary = format_profile_summary(profile)
    square_uid = summary["square_uid"]
    username = summary["username"]

    print(f"\n[信息] 用户: {summary['display_name']} (@{username})")
    print(f"[信息] 粉丝: {summary['total_followers']:,}, 帖子: {summary['total_posts']}")

    # 抓取帖子
    filter_type = args.filter.upper() if args.filter else "ALL"
    raw_posts = fetch_user_posts(square_uid, filter_type=filter_type, max_posts=args.max_posts)
    parsed_posts = [parse_post(p) for p in raw_posts]

    # 保存
    output_dir = args.output or os.path.join(os.path.dirname(os.path.abspath(__file__)), f"data_{username}")
    os.makedirs(output_dir, exist_ok=True)

    save_posts_csv(parsed_posts, os.path.join(output_dir, f"posts_{username}.csv"))
    save_posts_json(parsed_posts, os.path.join(output_dir, f"posts_{username}.json"))

    # 保存 profile
    with open(os.path.join(output_dir, f"profile_{username}.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"\n[完成] 共抓取 {len(parsed_posts)} 条帖子，保存至 {output_dir}")


def cmd_analyze(args):
    """抓取并分析用户内容。"""
    profile = search_user_by_keyword(args.username)
    if not profile:
        print(f"[错误] 未找到用户: {args.username}")
        sys.exit(1)

    summary = format_profile_summary(profile)
    square_uid = summary["square_uid"]
    username = summary["username"]

    print(f"\n[信息] 用户: {summary['display_name']} (@{username})")
    print(f"[信息] 粉丝: {summary['total_followers']:,}, 帖子: {summary['total_posts']}")

    # 抓取帖子
    filter_type = args.filter.upper() if args.filter else "ALL"
    raw_posts = fetch_user_posts(square_uid, filter_type=filter_type, max_posts=args.max_posts)
    parsed_posts = [parse_post(p) for p in raw_posts]

    # 分析
    analysis = analyze_content(parsed_posts, summary)

    # 保存
    output_dir = args.output or os.path.join(os.path.dirname(os.path.abspath(__file__)), f"analysis_{username}")
    os.makedirs(output_dir, exist_ok=True)

    save_posts_csv(parsed_posts, os.path.join(output_dir, f"posts_{username}.csv"))
    save_posts_json(parsed_posts, os.path.join(output_dir, f"posts_{username}.json"))
    generate_analysis_report(summary, analysis, parsed_posts, os.path.join(output_dir, f"analysis_report_{username}.md"))

    # 保存分析 JSON
    with open(os.path.join(output_dir, f"analysis_{username}.json"), "w", encoding="utf-8") as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2, default=str)

    # 保存 profile
    with open(os.path.join(output_dir, f"profile_{username}.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"\n[完成] 分析报告已生成，保存至 {output_dir}")
    print(f"  - posts_{username}.csv / .json  (帖子数据)")
    print(f"  - analysis_report_{username}.md  (分析报告)")
    print(f"  - analysis_{username}.json  (分析数据)")


def main():
    parser = argparse.ArgumentParser(
        description="币安广场用户主页内容抓取与创作分析工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 查看用户 Profile
  python3 binance_profile_analyzer.py profile CZ

  # 抓取用户全部帖子
  python3 binance_profile_analyzer.py fetch CZ --output ./data

  # 抓取并分析用户内容（完整报告）
  python3 binance_profile_analyzer.py analyze CZ --output ./report

  # 只分析原创帖子
  python3 binance_profile_analyzer.py analyze CZ --filter ORIGINAL

  # 限制最多抓取 50 条帖子
  python3 binance_profile_analyzer.py analyze CZ --max-posts 50
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # profile 命令
    p_profile = subparsers.add_parser("profile", help="获取用户 Profile 信息")
    p_profile.add_argument("username", help="币安广场用户名")
    p_profile.add_argument("--output", "-o", help="输出目录")

    # fetch 命令
    p_fetch = subparsers.add_parser("fetch", help="抓取用户全部帖子")
    p_fetch.add_argument("username", help="币安广场用户名")
    p_fetch.add_argument("--output", "-o", help="输出目录")
    p_fetch.add_argument("--filter", "-f", choices=["ALL", "ORIGINAL", "QUOTE", "LIVE"], default="ALL", help="帖子筛选类型")
    p_fetch.add_argument("--max-posts", "-m", type=int, help="最大帖子数")

    # analyze 命令
    p_analyze = subparsers.add_parser("analyze", help="抓取并分析用户内容")
    p_analyze.add_argument("username", help="币安广场用户名")
    p_analyze.add_argument("--output", "-o", help="输出目录")
    p_analyze.add_argument("--filter", "-f", choices=["ALL", "ORIGINAL", "QUOTE", "LIVE"], default="ALL", help="帖子筛选类型")
    p_analyze.add_argument("--max-posts", "-m", type=int, help="最大帖子数")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "profile":
        cmd_profile(args)
    elif args.command == "fetch":
        cmd_fetch(args)
    elif args.command == "analyze":
        cmd_analyze(args)


if __name__ == "__main__":
    main()
