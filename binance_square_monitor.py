#!/usr/bin/env python3
"""
币安广场（Binance Square）热门帖子实时流量数据监控工具

功能：
1. 抓取币安广场热门帖子的浏览量、点赞数、评论数、分享数
2. 支持持续监控模式，定时采集数据并记录变化
3. 新增48小时全量数据抓取，双数据源 + 自动去重
4. 输出 CSV 和 JSON 格式的监控报告

API 端点：
- 热门文章列表: /bapi/composite/v3/friendly/pgc/content/article/list
  - type=1 (trending, ~9页), type=2 (latest, ~50页)
- 新闻 Feed: /bapi/composite/v4/friendly/pgc/feed/news/list (~80页)
"""

import requests
import json
import csv
import time
import os
import sys
import argparse
from datetime import datetime, timezone, timedelta


# ==================== 配置 ====================

BASE_URL = "https://www.binance.com"
ARTICLE_API = f"{BASE_URL}/bapi/composite/v3/friendly/pgc/content/article/list"
NEWS_FEED_API = f"{BASE_URL}/bapi/composite/v4/friendly/pgc/feed/news/list"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://www.binance.com/zh-CN/square/trending",
    "Origin": "https://www.binance.com",
}

# 默认输出目录
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "binance_square_data")

# 请求间隔（秒）
REQUEST_DELAY = 0.5

# 分页上限（安全限制）
MAX_PAGES_ARTICLE = 60
MAX_PAGES_NEWS = 100


# ==================== 数据抓取 ====================

def fetch_trending_posts(page_index=1, page_size=20):
    """
    抓取币安广场热门帖子列表（type=1, trending）。

    参数:
        page_index: 页码，从1开始
        page_size: 每页帖子数量，最大20

    返回:
        解析后的帖子列表（字典数组），失败返回空列表
    """
    return _fetch_article_list(page_index, page_size, article_type=1)


def fetch_latest_posts(page_index=1, page_size=20):
    """
    抓取币安广场最新帖子列表（type=2, latest）。

    参数:
        page_index: 页码，从1开始
        page_size: 每页帖子数量，最大20

    返回:
        解析后的帖子列表（字典数组），失败返回空列表
    """
    return _fetch_article_list(page_index, page_size, article_type=2)


def fetch_news_feed(page_index=1, page_size=20):
    """
    抓取币安广场新闻 Feed。

    参数:
        page_index: 页码，从1开始
        page_size: 每页帖子数量，最大20

    返回:
        解析后的帖子列表（字典数组），失败返回空列表
    """
    params = {
        "pageIndex": page_index,
        "pageSize": page_size,
    }

    try:
        resp = requests.get(NEWS_FEED_API, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        if data.get("code") != "000000":
            print(f"[ERROR] News Feed API 返回错误: code={data.get('code')}, message={data.get('message')}")
            return []

        vos = data.get("data", {}).get("vos", [])
        return [_parse_post(v) for v in vos]

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] 网络请求失败: {e}")
        return []
    except (json.JSONDecodeError, KeyError) as e:
        print(f"[ERROR] 数据解析失败: {e}")
        return []


def _fetch_article_list(page_index, page_size, article_type=1):
    """内部方法：抓取文章列表 API。"""
    params = {
        "pageIndex": page_index,
        "pageSize": page_size,
        "type": article_type,
    }

    try:
        resp = requests.get(ARTICLE_API, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        if data.get("code") != "000000":
            print(f"[ERROR] API 返回错误: code={data.get('code')}, message={data.get('message')}")
            return []

        vos = data.get("data", {}).get("vos", [])
        return [_parse_post(v) for v in vos]

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] 网络请求失败: {e}")
        return []
    except (json.JSONDecodeError, KeyError) as e:
        print(f"[ERROR] 数据解析失败: {e}")
        return []


def fetch_all_trending(total_pages=3, page_size=20):
    """
    抓取多页热门帖子（type=1）。

    参数:
        total_pages: 总页数
        page_size: 每页数量

    返回:
        所有帖子的列表
    """
    all_posts = []
    for page in range(1, total_pages + 1):
        posts = fetch_trending_posts(page_index=page, page_size=page_size)
        all_posts.extend(posts)
        if len(posts) < page_size:
            break  # 没有更多数据
        if page < total_pages:
            time.sleep(REQUEST_DELAY)
    return all_posts


# ==================== 48小时全量抓取 ====================

def fetch_48h_full(hours=48, page_size=20, verbose=True):
    """
    抓取过去指定小时数内的全量帖子数据。

    使用三数据源策略：
    1. article/list (type=2, latest) — 按时间倒序，覆盖约42小时
    2. news/feed — 补充更多帖子，覆盖约52小时+
    3. article/list (type=1, trending) — 补充热门帖子
    合并后按 post_id 去重。

    参数:
        hours: 抓取时间范围（小时），默认48
        page_size: 每页数量
        verbose: 是否打印进度

    返回:
        (去重后的帖子列表, 统计信息字典)
    """
    now = datetime.now(timezone.utc)
    cutoff_ts = (now - timedelta(hours=hours)).timestamp()
    cutoff_str = datetime.fromtimestamp(cutoff_ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    if verbose:
        print(f"\n{'='*80}")
        print(f"[48h全量抓取] 开始采集过去 {hours} 小时的全量数据")
        print(f"  当前时间: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"  截止时间: {cutoff_str}")
        print(f"{'='*80}")

    all_posts = {}  # post_id -> post dict (用于去重)
    stats = {"source_latest": 0, "source_news": 0, "source_trending": 0, "duplicates": 0}

    # ---- 数据源1: article/list type=2 (latest) ----
    if verbose:
        print(f"\n[数据源1] 最新帖子 (article/list type=2)...")
    source1_count = _fetch_pages_until_cutoff(
        fetch_func=fetch_latest_posts,
        all_posts=all_posts,
        cutoff_ts=cutoff_ts,
        max_pages=MAX_PAGES_ARTICLE,
        page_size=page_size,
        source_name="latest",
        stats=stats,
        verbose=verbose,
    )
    stats["source_latest"] = source1_count

    # ---- 数据源2: news/feed ----
    if verbose:
        print(f"\n[数据源2] 新闻 Feed (news/feed)...")
    source2_count = _fetch_pages_until_cutoff(
        fetch_func=fetch_news_feed,
        all_posts=all_posts,
        cutoff_ts=cutoff_ts,
        max_pages=MAX_PAGES_NEWS,
        page_size=page_size,
        source_name="news",
        stats=stats,
        verbose=verbose,
    )
    stats["source_news"] = source2_count

    # ---- 数据源3: article/list type=1 (trending) ----
    if verbose:
        print(f"\n[数据源3] 热门帖子 (article/list type=1)...")
    source3_count = _fetch_pages_until_cutoff(
        fetch_func=fetch_trending_posts,
        all_posts=all_posts,
        cutoff_ts=cutoff_ts,
        max_pages=15,  # trending 通常不超过 10 页
        page_size=page_size,
        source_name="trending",
        stats=stats,
        verbose=verbose,
    )
    stats["source_trending"] = source3_count

    # 按发布时间倒序排列
    result = sorted(all_posts.values(), key=lambda p: p["timestamp"], reverse=True)

    # 过滤掉超出时间范围的帖子
    result = [p for p in result if p["timestamp"] >= cutoff_ts]

    if verbose:
        print(f"\n{'='*80}")
        print(f"[48h全量抓取] 采集完成")
        print(f"  数据源1 (latest):   {stats['source_latest']} 条")
        print(f"  数据源2 (news):     {stats['source_news']} 条")
        print(f"  数据源3 (trending): {stats['source_trending']} 条")
        print(f"  去重数量:           {stats['duplicates']} 条")
        print(f"  最终帖子数:         {len(result)} 条")
        if result:
            oldest = min(p["post_time"] for p in result)
            newest = max(p["post_time"] for p in result)
            print(f"  时间范围: {oldest} ~ {newest}")
        print(f"{'='*80}\n")

    return result, stats


def _fetch_pages_until_cutoff(fetch_func, all_posts, cutoff_ts, max_pages, page_size,
                               source_name, stats, verbose=True):
    """
    逐页抓取数据直到超出时间截止点或无更多数据。

    参数:
        fetch_func: 抓取函数 (接受 page_index, page_size 参数)
        all_posts: 全局帖子字典 (post_id -> post)，用于去重
        cutoff_ts: 截止时间戳
        max_pages: 最大页数限制
        page_size: 每页数量
        source_name: 数据源名称
        stats: 统计字典
        verbose: 是否打印进度

    返回:
        本数据源新增的帖子数
    """
    new_count = 0
    consecutive_empty = 0
    max_consecutive_empty = 3  # 连续空页数达到此值则停止

    for page in range(1, max_pages + 1):
        try:
            posts = fetch_func(page_index=page, page_size=page_size)
        except Exception as e:
            print(f"  [WARN] 第 {page} 页请求异常: {e}")
            consecutive_empty += 1
            if consecutive_empty >= max_consecutive_empty:
                break
            time.sleep(REQUEST_DELAY * 2)
            continue

        if not posts:
            consecutive_empty += 1
            if verbose:
                print(f"  第 {page} 页: 空 (连续空页: {consecutive_empty}/{max_consecutive_empty})")
            if consecutive_empty >= max_consecutive_empty:
                if verbose:
                    print(f"  [停止] 连续 {max_consecutive_empty} 页无数据，停止翻页")
                break
            time.sleep(REQUEST_DELAY)
            continue

        consecutive_empty = 0

        # 检查时间范围
        page_new = 0
        page_dup = 0
        oldest_in_page = float('inf')

        for post in posts:
            pid = post["post_id"]
            ts = post["timestamp"]
            oldest_in_page = min(oldest_in_page, ts)

            if pid in all_posts:
                page_dup += 1
                stats["duplicates"] += 1
                # 更新已有帖子的流量数据（取较大值）
                existing = all_posts[pid]
                for field in ["view_count", "like_count", "comment_count", "share_count", "reply_count", "quote_count"]:
                    if post.get(field, 0) > existing.get(field, 0):
                        existing[field] = post[field]
            else:
                all_posts[pid] = post
                page_new += 1
                new_count += 1

        if verbose:
            oldest_str = datetime.fromtimestamp(oldest_in_page, tz=timezone.utc).strftime("%m-%d %H:%M") if oldest_in_page != float('inf') else "N/A"
            print(f"  第 {page:>3} 页: {len(posts)} 条, 新增 {page_new}, 重复 {page_dup}, 最早 {oldest_str}")

        # 如果本页最早的帖子已超出截止时间，停止翻页
        if oldest_in_page < cutoff_ts:
            if verbose:
                print(f"  [停止] 已达到 {datetime.fromtimestamp(cutoff_ts, tz=timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} 截止时间")
            break

        time.sleep(REQUEST_DELAY)

    return new_count


# ==================== 数据解析 ====================

def _parse_post(raw):
    """将原始 API 响应中的单个帖子解析为标准化字典。"""
    content = raw.get("content", "") or ""
    title = raw.get("title", "") or ""

    # 截取内容摘要（前150字符）
    summary = title if title else content[:150].replace("\n", " ")
    if len(summary) > 150:
        summary = summary[:147] + "..."

    # 时间戳转换
    timestamp = raw.get("date", 0)
    try:
        post_time = datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    except (OSError, ValueError):
        post_time = "unknown"

    return {
        "post_id": raw.get("id", ""),
        "author": raw.get("authorName", ""),
        "author_verified": raw.get("authorIsVerified", False),
        "card_type": raw.get("cardType", ""),
        "title": title,
        "summary": summary,
        "view_count": raw.get("viewCount", 0),
        "like_count": raw.get("likeCount", 0),
        "comment_count": raw.get("commentCount", 0),
        "share_count": raw.get("shareCount", 0),
        "reply_count": raw.get("replyCount", 0),
        "quote_count": raw.get("quoteCount", 0),
        "post_time": post_time,
        "timestamp": timestamp,
        "hashtags": [h.strip() for h in raw.get("hashtagList", []) if h],
        "web_link": raw.get("webLink", ""),
        "has_images": bool(raw.get("images")),
        "image_count": len(raw.get("images", []) or []),
        "is_featured": raw.get("isFeatured", False),
        "detected_language": raw.get("detectedLanguage", ""),
    }


# ==================== 数据输出 ====================

def save_to_csv(posts, filepath):
    """将帖子列表保存为 CSV 文件（追加模式）。"""
    if not posts:
        return

    fieldnames = [
        "snapshot_time", "post_id", "author", "author_verified", "card_type",
        "title", "summary", "view_count", "like_count", "comment_count",
        "share_count", "reply_count", "quote_count", "post_time",
        "hashtags", "web_link", "has_images", "image_count",
        "is_featured", "detected_language"
    ]

    file_exists = os.path.isfile(filepath)

    with open(filepath, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        if not file_exists:
            writer.writeheader()
        for post in posts:
            row = dict(post)
            row["snapshot_time"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            row["hashtags"] = "; ".join(post.get("hashtags", []))
            writer.writerow(row)


def save_to_json(posts, filepath):
    """将帖子列表保存为 JSON 文件（追加模式）。"""
    if not posts:
        return

    snapshot_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    snapshot = {
        "snapshot_time": snapshot_time,
        "post_count": len(posts),
        "posts": posts,
    }

    # 读取已有数据
    existing = []
    if os.path.isfile(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except (json.JSONDecodeError, IOError):
            existing = []

    existing.append(snapshot)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)


def save_48h_csv(posts, filepath):
    """将48小时全量数据保存为独立的 CSV 文件（覆盖模式）。"""
    if not posts:
        return

    fieldnames = [
        "post_id", "author", "author_verified", "card_type",
        "title", "summary", "view_count", "like_count", "comment_count",
        "share_count", "reply_count", "quote_count", "post_time",
        "hashtags", "web_link", "has_images", "image_count",
        "is_featured", "detected_language"
    ]

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for post in posts:
            row = dict(post)
            row["hashtags"] = "; ".join(post.get("hashtags", []))
            writer.writerow(row)


def save_48h_json(posts, stats, filepath):
    """将48小时全量数据保存为 JSON 文件（覆盖模式）。"""
    if not posts:
        return

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    output = {
        "fetch_time": now,
        "total_posts": len(posts),
        "stats": stats,
        "time_range": {
            "newest": posts[0]["post_time"] if posts else None,
            "oldest": posts[-1]["post_time"] if posts else None,
        },
        "posts": posts,
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)


def print_summary(posts, snapshot_num=None):
    """在终端打印帖子摘要表格。"""
    header_prefix = f"[快照 #{snapshot_num}] " if snapshot_num else ""
    now = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S CST")
    print(f"\n{'='*100}")
    print(f"{header_prefix}币安广场热门帖子流量数据 | 采集时间: {now} | 帖子数: {len(posts)}")
    print(f"{'='*100}")
    print(f"{'排名':<4} {'作者':<20} {'浏览量':>10} {'点赞数':>8} {'评论数':>8} {'分享数':>8} {'发布时间':<22} {'摘要':<30}")
    print(f"{'-'*4} {'-'*20} {'-'*10} {'-'*8} {'-'*8} {'-'*8} {'-'*22} {'-'*30}")

    for i, post in enumerate(posts, 1):
        summary = post["summary"][:28] + ".." if len(post["summary"]) > 30 else post["summary"]
        author = post["author"][:18] + ".." if len(post["author"]) > 20 else post["author"]
        print(
            f"{i:<4} {author:<20} {post['view_count']:>10,} {post['like_count']:>8,} "
            f"{post['comment_count']:>8,} {post['share_count']:>8,} {post['post_time']:<22} {summary:<30}"
        )

    # 汇总统计
    total_views = sum(p["view_count"] for p in posts)
    total_likes = sum(p["like_count"] for p in posts)
    total_comments = sum(p["comment_count"] for p in posts)
    total_shares = sum(p["share_count"] for p in posts)
    print(f"{'-'*100}")
    print(
        f"{'合计':<4} {'':<20} {total_views:>10,} {total_likes:>8,} "
        f"{total_comments:>8,} {total_shares:>8,}"
    )
    print(f"{'='*100}\n")


def print_48h_summary(posts, stats):
    """打印48小时全量数据的汇总统计。"""
    now = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S CST")
    print(f"\n{'='*100}")
    print(f"币安广场48小时全量数据汇总 | 采集时间: {now}")
    print(f"{'='*100}")

    if not posts:
        print("  [无数据]")
        return

    total_views = sum(p["view_count"] for p in posts)
    total_likes = sum(p["like_count"] for p in posts)
    total_comments = sum(p["comment_count"] for p in posts)
    total_shares = sum(p["share_count"] for p in posts)
    total_replies = sum(p["reply_count"] for p in posts)
    total_quotes = sum(p["quote_count"] for p in posts)

    # 按语言统计
    lang_counts = {}
    for p in posts:
        lang = p.get("detected_language", "unknown") or "unknown"
        lang_counts[lang] = lang_counts.get(lang, 0) + 1

    # 按作者统计
    author_counts = {}
    for p in posts:
        author = p.get("author", "unknown")
        author_counts[author] = author_counts.get(author, 0) + 1

    print(f"\n  总帖子数:   {len(posts):>8,}")
    print(f"  总浏览量:   {total_views:>8,}")
    print(f"  总点赞数:   {total_likes:>8,}")
    print(f"  总评论数:   {total_comments:>8,}")
    print(f"  总分享数:   {total_shares:>8,}")
    print(f"  总回复数:   {total_replies:>8,}")
    print(f"  总引用数:   {total_quotes:>8,}")

    print(f"\n  --- 数据源统计 ---")
    print(f"  latest 数据源:   {stats.get('source_latest', 0):>6} 条")
    print(f"  news 数据源:     {stats.get('source_news', 0):>6} 条")
    print(f"  trending 数据源: {stats.get('source_trending', 0):>6} 条")
    print(f"  去重数量:        {stats.get('duplicates', 0):>6} 条")

    print(f"\n  --- 语言分布 (Top 10) ---")
    for lang, count in sorted(lang_counts.items(), key=lambda x: -x[1])[:10]:
        print(f"  {lang:<10} {count:>6} 条 ({count/len(posts)*100:.1f}%)")

    print(f"\n  --- 活跃作者 (Top 10) ---")
    for author, count in sorted(author_counts.items(), key=lambda x: -x[1])[:10]:
        display = author[:25] + ".." if len(author) > 27 else author
        print(f"  {display:<28} {count:>4} 条")

    # Top 10 高浏览量帖子
    print(f"\n  --- 浏览量 Top 10 ---")
    print(f"  {'排名':<4} {'作者':<20} {'浏览量':>10} {'点赞':>8} {'评论':>8} {'分享':>8} {'发布时间':<22}")
    top_posts = sorted(posts, key=lambda p: p["view_count"], reverse=True)[:10]
    for i, p in enumerate(top_posts, 1):
        author = p["author"][:18] + ".." if len(p["author"]) > 20 else p["author"]
        print(f"  {i:<4} {author:<20} {p['view_count']:>10,} {p['like_count']:>8,} "
              f"{p['comment_count']:>8,} {p['share_count']:>8,} {p['post_time']:<22}")

    print(f"\n{'='*100}\n")


# ==================== 变化追踪 ====================

def compute_changes(current_posts, previous_posts):
    """计算两次快照之间的数据变化。"""
    prev_map = {p["post_id"]: p for p in previous_posts}
    changes = []

    for post in current_posts:
        pid = post["post_id"]
        if pid in prev_map:
            prev = prev_map[pid]
            delta = {
                "post_id": pid,
                "author": post["author"],
                "view_delta": post["view_count"] - prev["view_count"],
                "like_delta": post["like_count"] - prev["like_count"],
                "comment_delta": post["comment_count"] - prev["comment_count"],
                "share_delta": post["share_count"] - prev["share_count"],
            }
            if any(delta[k] != 0 for k in ["view_delta", "like_delta", "comment_delta", "share_delta"]):
                changes.append(delta)

    return changes


def print_changes(changes):
    """打印数据变化摘要。"""
    if not changes:
        print("  [无变化] 所有帖子的流量数据与上次快照相同。\n")
        return

    print(f"\n  --- 数据变化 (与上次快照对比) ---")
    print(f"  {'作者':<20} {'浏览量变化':>12} {'点赞变化':>10} {'评论变化':>10} {'分享变化':>10}")
    for c in changes:
        author = c["author"][:18] + ".." if len(c["author"]) > 20 else c["author"]
        print(
            f"  {author:<20} {_fmt_delta(c['view_delta']):>12} {_fmt_delta(c['like_delta']):>10} "
            f"{_fmt_delta(c['comment_delta']):>10} {_fmt_delta(c['share_delta']):>10}"
        )
    print()


def _fmt_delta(val):
    """格式化增量值，正数加+号。"""
    if val > 0:
        return f"+{val:,}"
    elif val < 0:
        return f"{val:,}"
    return "0"


# ==================== 持续监控 ====================

def monitor(interval_seconds=300, total_pages=3, page_size=20, output_dir=None, max_snapshots=0):
    """持续监控模式：定时抓取热门帖子数据并记录变化。"""
    if output_dir is None:
        output_dir = OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)

    csv_path = os.path.join(output_dir, "trending_posts.csv")
    json_path = os.path.join(output_dir, "trending_posts.json")
    changes_csv = os.path.join(output_dir, "changes_log.csv")

    print(f"[启动] 币安广场热门帖子持续监控")
    print(f"  采集间隔: {interval_seconds} 秒")
    print(f"  每次采集: {total_pages} 页 x {page_size} 条")
    print(f"  数据目录: {output_dir}")
    print(f"  CSV 文件: {csv_path}")
    print(f"  JSON 文件: {json_path}")
    if max_snapshots > 0:
        print(f"  最大快照数: {max_snapshots}")
    print(f"  按 Ctrl+C 停止监控\n")

    previous_posts = []
    snapshot_count = 0

    try:
        while True:
            snapshot_count += 1
            print(f"[采集 #{snapshot_count}] 正在抓取热门帖子...")

            posts = fetch_all_trending(total_pages=total_pages, page_size=page_size)

            if posts:
                print_summary(posts, snapshot_num=snapshot_count)
                save_to_csv(posts, csv_path)
                save_to_json(posts, json_path)

                # 计算变化
                if previous_posts:
                    changes = compute_changes(posts, previous_posts)
                    print_changes(changes)

                    # 记录变化到CSV
                    if changes:
                        _save_changes_csv(changes, changes_csv, snapshot_count)

                previous_posts = posts
                print(f"  [保存] 数据已写入 CSV 和 JSON 文件。")
            else:
                print(f"  [警告] 未获取到数据，将在下次重试。")

            # 检查是否达到最大快照数
            if max_snapshots > 0 and snapshot_count >= max_snapshots:
                print(f"\n[完成] 已达到最大快照数 {max_snapshots}，监控结束。")
                break

            print(f"  [等待] 下次采集将在 {interval_seconds} 秒后...")
            time.sleep(interval_seconds)

    except KeyboardInterrupt:
        print(f"\n[停止] 用户中断，共完成 {snapshot_count} 次采集。")

    # 生成最终报告
    _generate_report(output_dir, snapshot_count)


def _save_changes_csv(changes, filepath, snapshot_num):
    """将变化数据追加到变化日志CSV。"""
    fieldnames = ["snapshot_num", "time", "post_id", "author",
                  "view_delta", "like_delta", "comment_delta", "share_delta"]
    file_exists = os.path.isfile(filepath)

    with open(filepath, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        for c in changes:
            row = dict(c)
            row["snapshot_num"] = snapshot_num
            row["time"] = now
            writer.writerow(row)


def _generate_report(output_dir, total_snapshots):
    """生成监控总结报告。"""
    report_path = os.path.join(output_dir, "monitor_report.md")
    now = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S CST")

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# 币安广场热门帖子监控报告\n\n")
        f.write(f"**生成时间**: {now}\n\n")
        f.write(f"**总采集次数**: {total_snapshots}\n\n")
        f.write(f"## 数据文件\n\n")
        f.write(f"| 文件 | 说明 |\n")
        f.write(f"|------|------|\n")
        f.write(f"| `trending_posts.csv` | 所有快照的帖子流量数据 |\n")
        f.write(f"| `trending_posts.json` | JSON 格式的完整数据 |\n")
        f.write(f"| `changes_log.csv` | 各快照间的数据变化记录 |\n")
        f.write(f"| `monitor_report.md` | 本报告 |\n")

    print(f"  [报告] 监控报告已生成: {report_path}")


def _generate_48h_report(output_dir, posts, stats):
    """生成48小时全量数据报告。"""
    report_path = os.path.join(output_dir, "48h_report.md")
    now = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S CST")

    total_views = sum(p["view_count"] for p in posts)
    total_likes = sum(p["like_count"] for p in posts)
    total_comments = sum(p["comment_count"] for p in posts)
    total_shares = sum(p["share_count"] for p in posts)
    total_replies = sum(p["reply_count"] for p in posts)
    total_quotes = sum(p["quote_count"] for p in posts)

    # 按语言统计
    lang_counts = {}
    for p in posts:
        lang = p.get("detected_language", "unknown") or "unknown"
        lang_counts[lang] = lang_counts.get(lang, 0) + 1

    # 按作者统计
    author_counts = {}
    for p in posts:
        author = p.get("author", "unknown")
        author_counts[author] = author_counts.get(author, 0) + 1

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# 币安广场48小时全量数据报告\n\n")
        f.write(f"**生成时间**: {now}\n\n")
        f.write(f"## 数据概览\n\n")
        f.write(f"| 指标 | 数值 |\n")
        f.write(f"|------|------|\n")
        f.write(f"| 总帖子数 | {len(posts):,} |\n")
        f.write(f"| 总浏览量 | {total_views:,} |\n")
        f.write(f"| 总点赞数 | {total_likes:,} |\n")
        f.write(f"| 总评论数 | {total_comments:,} |\n")
        f.write(f"| 总分享数 | {total_shares:,} |\n")
        f.write(f"| 总回复数 | {total_replies:,} |\n")
        f.write(f"| 总引用数 | {total_quotes:,} |\n")
        if posts:
            f.write(f"| 最新帖子 | {posts[0]['post_time']} |\n")
            f.write(f"| 最早帖子 | {posts[-1]['post_time']} |\n")
        f.write(f"\n")

        f.write(f"## 数据源统计\n\n")
        f.write(f"| 数据源 | 新增帖子数 |\n")
        f.write(f"|--------|------------|\n")
        f.write(f"| latest (最新帖子) | {stats.get('source_latest', 0):,} |\n")
        f.write(f"| news (新闻Feed) | {stats.get('source_news', 0):,} |\n")
        f.write(f"| trending (热门) | {stats.get('source_trending', 0):,} |\n")
        f.write(f"| 去重数量 | {stats.get('duplicates', 0):,} |\n")
        f.write(f"\n")

        f.write(f"## 语言分布\n\n")
        f.write(f"| 语言 | 帖子数 | 占比 |\n")
        f.write(f"|------|--------|------|\n")
        for lang, count in sorted(lang_counts.items(), key=lambda x: -x[1])[:15]:
            f.write(f"| {lang} | {count:,} | {count/len(posts)*100:.1f}% |\n")
        f.write(f"\n")

        f.write(f"## 活跃作者 Top 20\n\n")
        f.write(f"| 作者 | 帖子数 |\n")
        f.write(f"|------|--------|\n")
        for author, count in sorted(author_counts.items(), key=lambda x: -x[1])[:20]:
            f.write(f"| {author} | {count} |\n")
        f.write(f"\n")

        f.write(f"## 浏览量 Top 20\n\n")
        f.write(f"| 排名 | 作者 | 浏览量 | 点赞 | 评论 | 分享 | 发布时间 |\n")
        f.write(f"|------|------|--------|------|------|------|----------|\n")
        top_posts = sorted(posts, key=lambda p: p["view_count"], reverse=True)[:20]
        for i, p in enumerate(top_posts, 1):
            f.write(f"| {i} | {p['author']} | {p['view_count']:,} | {p['like_count']:,} | "
                    f"{p['comment_count']:,} | {p['share_count']:,} | {p['post_time']} |\n")
        f.write(f"\n")

        f.write(f"## 数据文件\n\n")
        f.write(f"| 文件 | 说明 |\n")
        f.write(f"|------|------|\n")
        f.write(f"| `48h_full_data.csv` | 48小时全量帖子数据 (CSV) |\n")
        f.write(f"| `48h_full_data.json` | 48小时全量帖子数据 (JSON) |\n")
        f.write(f"| `48h_report.md` | 本报告 |\n")

    print(f"  [报告] 48小时全量数据报告已生成: {report_path}")


# ==================== 单次抓取 ====================

def single_fetch(total_pages=3, page_size=20, output_dir=None, output_format="all"):
    """单次抓取模式：抓取一次热门帖子数据并输出。"""
    posts = fetch_all_trending(total_pages=total_pages, page_size=page_size)

    if not posts:
        print("[错误] 未能获取到热门帖子数据。")
        return []

    print_summary(posts)

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        if output_format in ("csv", "all"):
            csv_path = os.path.join(output_dir, "trending_posts.csv")
            save_to_csv(posts, csv_path)
            print(f"[保存] CSV: {csv_path}")
        if output_format in ("json", "all"):
            json_path = os.path.join(output_dir, "trending_posts.json")
            save_to_json(posts, json_path)
            print(f"[保存] JSON: {json_path}")

    return posts


def fetch_48h(hours=48, page_size=20, output_dir=None, output_format="all"):
    """48小时全量抓取模式：抓取过去48小时的全量帖子数据。"""
    posts, stats = fetch_48h_full(hours=hours, page_size=page_size, verbose=True)

    if not posts:
        print("[错误] 未能获取到帖子数据。")
        return []

    print_48h_summary(posts, stats)

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        if output_format in ("csv", "all"):
            csv_path = os.path.join(output_dir, "48h_full_data.csv")
            save_48h_csv(posts, csv_path)
            print(f"[保存] CSV: {csv_path}")
        if output_format in ("json", "all"):
            json_path = os.path.join(output_dir, "48h_full_data.json")
            save_48h_json(posts, stats, json_path)
            print(f"[保存] JSON: {json_path}")
        # 生成报告
        _generate_48h_report(output_dir, posts, stats)

    return posts


# ==================== 命令行入口 ====================

def main():
    parser = argparse.ArgumentParser(
        description="币安广场热门帖子实时流量数据监控工具（支持48小时全量抓取）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 单次抓取热门帖子，打印到终端
  python3 binance_square_monitor.py fetch

  # 单次抓取，保存到文件
  python3 binance_square_monitor.py fetch --output ./data --pages 3

  # 48小时全量数据抓取
  python3 binance_square_monitor.py fetch-48h --output ./data

  # 自定义时间范围（如24小时）
  python3 binance_square_monitor.py fetch-48h --hours 24 --output ./data

  # 持续监控，每5分钟采集一次
  python3 binance_square_monitor.py monitor --interval 300

  # 持续监控，每10分钟采集一次，最多采集12次（共2小时）
  python3 binance_square_monitor.py monitor --interval 600 --max-snapshots 12
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="操作模式")

    # 单次抓取
    fetch_parser = subparsers.add_parser("fetch", help="单次抓取热门帖子数据")
    fetch_parser.add_argument("--pages", type=int, default=3, help="采集页数 (默认: 3)")
    fetch_parser.add_argument("--page-size", type=int, default=20, help="每页数量 (默认: 20)")
    fetch_parser.add_argument("--output", "-o", type=str, default=None, help="输出目录")
    fetch_parser.add_argument("--format", choices=["csv", "json", "all", "print"], default="all", help="输出格式")

    # 48小时全量抓取
    fetch_48h_parser = subparsers.add_parser("fetch-48h", help="抓取过去48小时的全量帖子数据")
    fetch_48h_parser.add_argument("--hours", type=int, default=48, help="抓取时间范围（小时），默认48")
    fetch_48h_parser.add_argument("--page-size", type=int, default=20, help="每页数量 (默认: 20)")
    fetch_48h_parser.add_argument("--output", "-o", type=str, default=None, help="输出目录")
    fetch_48h_parser.add_argument("--format", choices=["csv", "json", "all", "print"], default="all", help="输出格式")

    # 持续监控
    monitor_parser = subparsers.add_parser("monitor", help="持续监控热门帖子流量变化")
    monitor_parser.add_argument("--interval", type=int, default=300, help="采集间隔秒数 (默认: 300)")
    monitor_parser.add_argument("--pages", type=int, default=3, help="每次采集页数 (默认: 3)")
    monitor_parser.add_argument("--page-size", type=int, default=20, help="每页数量 (默认: 20)")
    monitor_parser.add_argument("--output", "-o", type=str, default=None, help="输出目录")
    monitor_parser.add_argument("--max-snapshots", type=int, default=0, help="最大快照数 (0=无限制)")

    args = parser.parse_args()

    if args.command == "fetch":
        single_fetch(
            total_pages=args.pages,
            page_size=args.page_size,
            output_dir=args.output,
            output_format=args.format,
        )
    elif args.command == "fetch-48h":
        fetch_48h(
            hours=args.hours,
            page_size=args.page_size,
            output_dir=args.output,
            output_format=args.format,
        )
    elif args.command == "monitor":
        monitor(
            interval_seconds=args.interval,
            total_pages=args.pages,
            page_size=args.page_size,
            output_dir=args.output,
            max_snapshots=args.max_snapshots,
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
