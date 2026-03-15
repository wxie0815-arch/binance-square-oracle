
"""
L0 广场实时热帖监控模块 v5.1 (Binance Square Monitor)
================================================================
v5.1 升级（基于API实测诊断优化）：
  1. 多维度深度抓取 — 5种type + 多语言 + NewsFeed，目标1000-2000+条去重帖子
  2. pageSize=50 — 减少请求次数，单源容量×2.5
  3. 5种article type — type=1(Trending) + type=2(Latest) + type=3/4/5(新发现)
  4. 多语言覆盖 — zh-CN/en/ko/ru/tr 返回不同帖子池
  5. 智能热门筛选 — 按阅读量、互动量、互动率多维排序
  6. 热门文章/话题提取 — 输出Top50热帖+Top20话题
  7. 并发抓取 — 使用线程池加速

API实测数据（2026-03-10）：
  - article/list type=2 pageSize=50: 20页=998条（无上限）
  - article/list type=1: 5页=100条（有上限）
  - article/list type=3/4/5: 有效，返回不同内容
  - news/feed: 15+页持续有效
  - 不同语言返回不同帖子（首条ID不同）

数据源：币安广场公开 API（无需认证）
  - /bapi/composite/v3/friendly/pgc/content/article/list (type=1~5)
  - /bapi/composite/v4/friendly/pgc/feed/news/list

输出：square_monitor_report (dict)
"""

import sys
import os
import config
sys.path.insert(0, os.path.abspath(os.path.join(config.SCRIPT_DIR, "skills", "binance-square-monitor", "scripts")))
import json
import re
import time
import requests
from datetime import datetime, timezone, timedelta
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
BASE_URL = "https://www.binance.com"
ARTICLE_API = f"{BASE_URL}/bapi/composite/v3/friendly/pgc/content/article/list"
NEWS_FEED_API = f"{BASE_URL}/bapi/composite/v4/friendly/pgc/feed/news/list"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://www.binance.com/zh-CN/square/trending",
    "Origin": "https://www.binance.com",
}

# 多语言配置（实测返回不同帖子池）
LANG_CONFIGS = [
    {"lang": "zh-CN", "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"},
    {"lang": "en",    "Accept-Language": "en;q=0.9"},
    {"lang": "ko",    "Accept-Language": "ko;q=0.9,en;q=0.8"},
    {"lang": "ru",    "Accept-Language": "ru;q=0.9,en;q=0.8"},
    {"lang": "tr",    "Accept-Language": "tr;q=0.9,en;q=0.8"},
]

# 内容分类关键词
TOPIC_PATTERNS = [
    ("新币/Launchpad", r"上市|新币|Launchpad|Launchpool|Alpha|空投|airdrop|新上线|IDO|IEO"),
    ("行情分析", r"BTC|ETH|涨|跌|行情|价格|突破|支撑|阻力|多|空|现货|K线|技术分析|趋势"),
    ("活动/交易竞赛", r"竞赛|瓜分|奖励|交易任务|活动|奖池|参与|报名|红包"),
    ("AI/技能", r"AI|广场|技能|Skill|智能|机器人|agent|#AI|OpenClaw|MCP"),
    ("安全/储备金", r"储备金|安全|PoR|2FA|钱包|助记词|黑客|漏洞"),
    ("Web3/DeFi", r"Web3|DeFi|链上|Layer|BNBChain|质押|TVL|流动性|DEX"),
    ("Meme币", r"Meme|DOGE|SHIB|PEPE|WIF|BONK|meme|土狗|pump"),
    ("交易技巧", r"止损|仓位|情绪|策略|复盘|纪律|心态|技巧|回撤|风控"),
    ("宏观/监管", r"SEC|监管|政策|美联储|利率|CPI|ETF|合规|法规"),
    ("NFT/GameFi", r"NFT|GameFi|游戏|元宇宙|Metaverse|铭文|Ordinals"),
]

# 主流代币列表
KNOWN_COINS = [
    "BTC", "ETH", "BNB", "SOL", "XRP", "DOGE", "ADA", "AVAX", "DOT", "LINK",
    "SUI", "PEPE", "WIF", "ARB", "OP", "MATIC", "NEAR", "APT", "SEI", "TIA",
    "JUP", "RENDER", "FET", "TAO", "INJ", "TRX", "TON", "ATOM", "FIL", "UNI",
    "AAVE", "MKR", "LDO", "ONDO", "PENDLE", "ENA", "BOME", "FLOKI", "ORDI",
    "STX", "RUNE", "CAKE", "GMT", "HOOK", "EDU", "CYBER", "ID", "ARKM",
]


# ---------------------------------------------------------------------------
# 数据抓取（单页）
# ---------------------------------------------------------------------------
def _fetch_page(api_url: str, params: dict, headers: dict = None,
                label: str = "") -> list:
    """抓取单页数据"""
    hdrs = headers or HEADERS
    try:
        resp = requests.get(api_url, params=params, headers=hdrs, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != "000000":
            return []
        vos = (data.get("data", {}).get("vos", []) or
               data.get("data", {}).get("list", []))
        return [_parse_post(v) for v in vos if v]
    except Exception:
        return []


def _fetch_source(api_url: str, params_base: dict, max_pages: int,
                  page_size: int, label: str, headers: dict = None,
                  seen_ids: set = None) -> list:
    """串行抓取单个数据源的多页数据（带去重和空页检测）"""
    if seen_ids is None:
        seen_ids = set()
    posts = []
    empty_streak = 0

    for page in range(1, max_pages + 1):
        params = {**params_base, "pageIndex": page, "pageSize": page_size}
        page_posts = _fetch_page(api_url, params, headers, label)

        if not page_posts:
            empty_streak += 1
            if empty_streak >= 3:
                break
            continue

        empty_streak = 0
        new_count = 0
        for p in page_posts:
            pid = p.get("post_id", "")
            if pid and pid not in seen_ids:
                seen_ids.add(pid)
                posts.append(p)
                new_count += 1

        # 如果整页都是重复的，停止
        if new_count == 0:
            break

        # 如果返回不足一页，说明到底了
        if len(page_posts) < page_size:
            break

        time.sleep(0.15)  # 礼貌延迟

    return posts


# ---------------------------------------------------------------------------
# v5.1 多维度深度抓取
# ---------------------------------------------------------------------------
def fetch_all_deep(max_pages_per_source: int = 25, page_size: int = 50) -> list:
    """
    多维度深度抓取 v5.1：
    策略：5种type × 多语言 + NewsFeed = 大量不重复数据

    数据源矩阵：
    ┌─────────────┬──────────┬──────────┬──────────────────┐
    │ 数据源       │ 每页条数  │ 最大页数  │ 预期条数          │
    ├─────────────┼──────────┼──────────┼──────────────────┤
    │ type=2 zh-CN│ 50       │ 25       │ ~500             │
    │ type=2 en   │ 50       │ 15       │ ~400（不同帖子池）│
    │ type=3 zh-CN│ 50       │ 10       │ ~200             │
    │ type=4 zh-CN│ 50       │ 10       │ ~200             │
    │ type=5 zh-CN│ 50       │ 10       │ ~200             │
    │ type=1 zh-CN│ 50       │ 5        │ ~100             │
    │ NewsFeed    │ 50       │ 15       │ ~400             │
    │ NewsFeed en │ 50       │ 10       │ ~300             │
    │ type=2 ko   │ 50       │ 10       │ ~200             │
    │ type=2 ru   │ 50       │ 5        │ ~100             │
    └─────────────┴──────────┴──────────┴──────────────────┘
    目标：1000-2000+ 条去重帖子
    """
    seen_ids = set()
    all_posts = []
    stats = []

    def _merge(new_posts, label):
        count = len(new_posts)
        all_posts.extend(new_posts)
        stats.append((label, count))
        if count > 0:
            print(f"[L0] {label}: +{count}条 (累计去重: {len(seen_ids)})")

    def _make_headers(lang_config):
        h = dict(HEADERS)
        h["Accept-Language"] = lang_config["Accept-Language"]
        h["lang"] = lang_config["lang"]
        return h

    # ---- 第一梯队：主力数据源（中文Latest，量最大）----
    print(f"[L0] === 深度抓取启动 (pageSize={page_size}) ===")

    # 数据源1: Latest(type=2) 中文 — 主力源
    h_zh = _make_headers(LANG_CONFIGS[0])
    posts = _fetch_source(ARTICLE_API, {"type": 2}, max_pages_per_source,
                          page_size, "Latest-ZH", h_zh, seen_ids)
    _merge(posts, "Latest(type=2) zh-CN")

    # 数据源2: Latest(type=2) 英文 — 不同帖子池
    h_en = _make_headers(LANG_CONFIGS[1])
    posts = _fetch_source(ARTICLE_API, {"type": 2}, min(max_pages_per_source, 15),
                          page_size, "Latest-EN", h_en, seen_ids)
    _merge(posts, "Latest(type=2) en")

    # ---- 第二梯队：新发现的type 3/4/5 ----
    for t in [3, 4, 5]:
        posts = _fetch_source(ARTICLE_API, {"type": t}, min(max_pages_per_source, 10),
                              page_size, f"Type{t}", h_zh, seen_ids)
        _merge(posts, f"Article(type={t}) zh-CN")

    # ---- 第三梯队：NewsFeed ----
    posts = _fetch_source(NEWS_FEED_API, {}, min(max_pages_per_source, 15),
                          page_size, "NewsFeed-ZH", h_zh, seen_ids)
    _merge(posts, "NewsFeed zh-CN")

    posts = _fetch_source(NEWS_FEED_API, {}, min(max_pages_per_source, 10),
                          page_size, "NewsFeed-EN", h_en, seen_ids)
    _merge(posts, "NewsFeed en")

    # ---- 第四梯队：Trending + 其他语言 ----
    # Trending(type=1) 只有约5页
    posts = _fetch_source(ARTICLE_API, {"type": 1}, 5,
                          page_size, "Trending", h_zh, seen_ids)
    _merge(posts, "Trending(type=1)")

    # 韩语/俄语补充
    for lang_cfg in LANG_CONFIGS[2:4]:  # ko, ru
        h = _make_headers(lang_cfg)
        posts = _fetch_source(ARTICLE_API, {"type": 2}, min(max_pages_per_source, 8),
                              page_size, f"Latest-{lang_cfg['lang']}", h, seen_ids)
        _merge(posts, f"Latest(type=2) {lang_cfg['lang']}")

    # ---- 汇总 ----
    print(f"\n[L0] === 深度抓取完成 ===")
    print(f"[L0] 数据源统计:")
    for label, count in stats:
        print(f"  {label}: {count}条")
    print(f"[L0] 总计去重: {len(all_posts)}条")

    return all_posts


def fetch_all_deep_concurrent(max_pages_per_source: int = 25,
                               page_size: int = 50,
                               max_workers: int = 5) -> list:
    """
    并发版深度抓取 — 多个数据源同时抓取，速度更快
    """
    seen_ids = set()
    all_posts = []
    stats = []
    _lock = __import__("threading").Lock()

    def _make_headers(lang_config):
        h = dict(HEADERS)
        h["Accept-Language"] = lang_config["Accept-Language"]
        h["lang"] = lang_config["lang"]
        return h

    def _fetch_and_collect(api_url, params_base, max_pages, label, headers):
        """线程安全的抓取+收集"""
        local_posts = []
        local_ids = set()
        empty_streak = 0

        for page in range(1, max_pages + 1):
            params = {**params_base, "pageIndex": page, "pageSize": page_size}
            page_posts = _fetch_page(api_url, params, headers, label)

            if not page_posts:
                empty_streak += 1
                if empty_streak >= 3:
                    break
                continue

            empty_streak = 0
            for p in page_posts:
                pid = p.get("post_id", "")
                if pid and pid not in local_ids:
                    local_ids.add(pid)
                    local_posts.append(p)

            if len(page_posts) < page_size:
                break
            time.sleep(0.2)

        # 线程安全合并
        with _lock:
            new_count = 0
            for p in local_posts:
                pid = p.get("post_id", "")
                if pid not in seen_ids:
                    seen_ids.add(pid)
                    all_posts.append(p)
                    new_count += 1
            stats.append((label, new_count))
            if new_count > 0:
                print(f"[L0] {label}: +{new_count}条 (累计: {len(all_posts)})")

    # 构建任务列表
    h_zh = _make_headers(LANG_CONFIGS[0])
    h_en = _make_headers(LANG_CONFIGS[1])

    tasks = [
        # 第一梯队：主力
        (ARTICLE_API, {"type": 2}, max_pages_per_source, "Latest(type=2) zh-CN", h_zh),
        (ARTICLE_API, {"type": 2}, min(max_pages_per_source, 15), "Latest(type=2) en", h_en),
        (NEWS_FEED_API, {}, min(max_pages_per_source, 15), "NewsFeed zh-CN", h_zh),
        (NEWS_FEED_API, {}, min(max_pages_per_source, 10), "NewsFeed en", h_en),
        # 第二梯队：新type
        (ARTICLE_API, {"type": 3}, min(max_pages_per_source, 10), "Article(type=3)", h_zh),
        (ARTICLE_API, {"type": 4}, min(max_pages_per_source, 10), "Article(type=4)", h_zh),
        (ARTICLE_API, {"type": 5}, min(max_pages_per_source, 10), "Article(type=5)", h_zh),
        # 第三梯队：Trending + 其他语言
        (ARTICLE_API, {"type": 1}, 5, "Trending(type=1)", h_zh),
    ]

    # 添加其他语言
    for lang_cfg in LANG_CONFIGS[2:4]:  # ko, ru
        h = _make_headers(lang_cfg)
        tasks.append((ARTICLE_API, {"type": 2}, min(max_pages_per_source, 8),
                       f"Latest(type=2) {lang_cfg['lang']}", h))

    print(f"[L0] === 并发深度抓取启动 ({len(tasks)}个数据源, pageSize={page_size}) ===")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for api_url, params_base, max_pages, label, headers in tasks:
            f = executor.submit(_fetch_and_collect, api_url, params_base,
                                max_pages, label, headers)
            futures.append(f)

        for f in as_completed(futures):
            try:
                f.result()
            except Exception as e:
                print(f"[L0] 数据源异常: {e}")

    print(f"\n[L0] === 并发深度抓取完成 ===")
    print(f"[L0] 数据源统计:")
    for label, count in sorted(stats, key=lambda x: -x[1]):
        print(f"  {label}: {count}条")
    print(f"[L0] 总计去重: {len(all_posts)}条")

    return all_posts


# ---------------------------------------------------------------------------
# 快速抓取（向后兼容）
# ---------------------------------------------------------------------------
def fetch_all_trending(total_pages: int = 5, page_size: int = 20,
                       use_3sources: bool = True) -> list:
    """向后兼容的快速抓取接口"""
    if not use_3sources:
        all_posts = []
        for page in range(1, total_pages + 1):
            params = {"pageIndex": page, "pageSize": page_size, "type": 1}
            posts = _fetch_page(ARTICLE_API, params, HEADERS, "Trending")
            all_posts.extend(posts)
            if len(posts) < page_size:
                break
            if page < total_pages:
                time.sleep(0.3)
        return all_posts

    # 使用三源策略（小规模）
    seen_ids = set()
    all_posts = []

    def _pull(api_url, params_base, max_pages, label):
        count = 0
        for page in range(1, max_pages + 1):
            params = {**params_base, "pageIndex": page, "pageSize": page_size}
            posts = _fetch_page(api_url, params, HEADERS, label)
            if not posts:
                break
            for p in posts:
                pid = p.get("post_id", "")
                if pid and pid not in seen_ids:
                    seen_ids.add(pid)
                    all_posts.append(p)
                    count += 1
            if len(posts) < page_size:
                break
            time.sleep(0.3)
        print(f"[L0] {label}: +{count}条")

    _pull(ARTICLE_API, {"type": 2}, total_pages, "数据源1(Latest)")
    _pull(NEWS_FEED_API, {}, total_pages, "数据源2(NewsFeed)")
    _pull(ARTICLE_API, {"type": 1}, min(total_pages, 5), "数据源3(Trending)")

    print(f"[L0] 三源合并去重: {len(all_posts)}条")
    return all_posts


# ---------------------------------------------------------------------------
# 帖子解析
# ---------------------------------------------------------------------------
def _parse_post(raw: dict) -> dict:
    """解析单个帖子"""
    if "vo" in raw:
        raw = raw["vo"]

    content = raw.get("content", "") or ""
    title = raw.get("title", "") or ""
    # 修复：有些内容可能在 summary 字段中
    if not content and raw.get("summary"):
        content = raw.get("summary")
        
    summary = title if title else content[:200].replace("\n", " ")
    if len(summary) > 200:
        summary = summary[:197] + "..."

    timestamp = raw.get("date", 0)
    try:
        post_time = datetime.fromtimestamp(
            timestamp, tz=timezone.utc
        ).strftime("%Y-%m-%d %H:%M:%S UTC")
    except (OSError, ValueError):
        post_time = "unknown"

    def _safe_int(val, default=0):
        if isinstance(val, (int, float)):
            return int(val)
        if isinstance(val, str):
            try:
                return int(val)
            except Exception:
                return default
        return default

    view_count = _safe_int(raw.get("viewCount", 0))
    like_count = _safe_int(raw.get("likeCount", 0))
    comment_count = _safe_int(raw.get("commentCount", 0))
    share_count = _safe_int(raw.get("shareCount", 0))
    reply_count = _safe_int(raw.get("replyCount", 0))
    quote_count = _safe_int(raw.get("quoteCount", 0))

    # 修复：提取标签，支持多种可能的字段
    raw_hashtags = raw.get("hashtagList", []) or []
    if not raw_hashtags and raw.get("hashtagIdentifyList"):
        # hashtagIdentifyList 可能是字典列表或字符串列表，需要兼容两种格式
        for h in raw.get("hashtagIdentifyList", []):
            if isinstance(h, dict):
                name = h.get("hashtagName") or h.get("name") or h.get("tag")
                if name:
                    raw_hashtags.append(name)
            elif isinstance(h, str) and h:
                raw_hashtags.append(h)
    
    # 修复：作者名提取
    author = (raw.get("authorName") or raw.get("nickName") or raw.get("username") or
              (raw.get("author", {}).get("nickName", "") if isinstance(raw.get("author"), dict) else ""))

    post = {
        "post_id": raw.get("id", ""),
        "author": author,
        "author_verified": raw.get("authorIsVerified", False),
        "card_type": raw.get("cardType", ""),
        "title": title,
        "summary": summary,
        "content_preview": content[:500] if content else "",
        "content_length": len(content) if content else 0,
        "view_count": view_count,
        "like_count": like_count,
        "comment_count": comment_count,
        "share_count": share_count,
        "reply_count": reply_count,
        "quote_count": quote_count,
        "total_interactions": (like_count + comment_count + share_count +
                               reply_count + quote_count),
        "post_time": post_time,
        "timestamp": timestamp,
        "hashtags": [h.strip() for h in raw_hashtags if h],
        "web_link": raw.get("webLink", ""),
        "has_images": bool(raw.get("images")),
        "image_count": len(raw.get("images", []) or []),
        "is_featured": raw.get("isFeatured", False),
        "detected_language": raw.get("detectedLanguage", ""),
    }

    views = post["view_count"] or 1
    post["engagement_rate"] = round(
        (post["like_count"] + post["comment_count"] + post["share_count"])
        / views * 100, 4
    )
    post["heat_score"] = _calculate_heat_score(post)

    return post


def _calculate_heat_score(post: dict) -> float:
    """计算帖子综合热度分"""
    views = post.get("view_count", 0)
    likes = post.get("like_count", 0)
    comments = post.get("comment_count", 0)
    shares = post.get("share_count", 0)
    engagement_rate = post.get("engagement_rate", 0)

    score = (
        views * 0.3 +
        likes * 5 +
        comments * 15 +
        shares * 20 +
        engagement_rate * 100
    )

    ts = post.get("timestamp", 0)
    if ts > 0:
        age_hours = (time.time() - ts) / 3600
        if age_hours < 6:
            score *= 1.5
        elif age_hours < 12:
            score *= 1.3
        elif age_hours < 24:
            score *= 1.1

    return round(score, 2)


# ---------------------------------------------------------------------------
# 分析函数
# ---------------------------------------------------------------------------
def extract_hot_hashtags(posts: list, top_n: int = 20) -> list:
    """提取热门标签，增加容错处理"""
    counter = Counter()
    for p in posts:
        tags = p.get("hashtags", [])
        if not tags:
            # 尝试从正文中提取 #标签
            text = (p.get("summary", "") + " " + p.get("content_preview", ""))
            tags = re.findall(r'#(\w{2,20})', text)
        
        for tag in tags:
            if tag and len(tag) > 1:
                # 统一转为大写或保留原始？通常标签不区分大小写
                counter[tag.strip()] += 1
    return counter.most_common(top_n)


def extract_mentioned_coins(posts: list, top_n: int = 15) -> list:
    """提取提及的代币，增加正则表达式容错"""
    counter = Counter()
    # 扩大匹配范围：$TOKEN, #TOKEN, 或者正文中的大写字母
    coins_pattern = "|".join(KNOWN_COINS)
    for p in posts:
        text = (p.get("summary", "") + " " + p.get("content_preview", "") +
                " " + " ".join(p.get("hashtags", [])))
        
        # 1. 匹配 $TOKEN (最准确)
        dollar_coins = re.findall(r'\$([A-Z]{2,10})', text)
        # 2. 匹配 #TOKEN
        hash_coins = re.findall(r'#([A-Z]{2,10})', text)
        # 3. 匹配已知代币列表 (需全词匹配)
        upper_coins = re.findall(rf'\b({coins_pattern})\b', text.upper())
        
        for c in set(dollar_coins + hash_coins + upper_coins):
            if c in KNOWN_COINS or len(c) <= 6: # 过滤掉过长的非已知词
                counter[c.upper()] += 1
    
    # 如果还是没抓到，尝试更宽松的匹配
    if not counter:
        for p in posts:
            text = p.get("summary", "") + " " + p.get("content_preview", "")
            # 匹配 3-6 位全大写字母
            potential = re.findall(r'\b([A-Z]{3,6})\b', text)
            for c in potential:
                if c not in ["THE", "AND", "FOR", "WITH", "THIS", "THAT"]:
                    counter[c] += 1
                    
    return counter.most_common(top_n)


def classify_content(posts: list) -> dict:
    categories = Counter()
    for p in posts:
        text = (p.get("summary", "") + " " + " ".join(p.get("hashtags", [])) +
                " " + p.get("content_preview", "")[:200])
        matched = False
        for topic_name, pattern in TOPIC_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                categories[topic_name] += 1
                matched = True
        if not matched:
            categories["其他"] += 1
    return dict(categories.most_common())


def identify_viral_posts(posts: list, threshold: int = 10000) -> list:
    viral = [p for p in posts if p["view_count"] > threshold]
    viral.sort(key=lambda x: x["view_count"], reverse=True)
    return viral


def identify_high_engagement(posts: list, top_n: int = 10) -> list:
    filtered = [p for p in posts if p["view_count"] > 500]
    sorted_posts = sorted(filtered, key=lambda x: x["engagement_rate"], reverse=True)
    return sorted_posts[:top_n]


def identify_hot_articles(posts: list, top_n: int = 20) -> list:
    sorted_posts = sorted(posts, key=lambda x: x.get("heat_score", 0), reverse=True)
    return sorted_posts[:top_n]


def extract_hot_topics_digest(posts: list, hot_hashtags: list,
                               mentioned_coins: list, categories: dict) -> dict:
    top_tags = [tag for tag, _ in hot_hashtags[:5]]
    top_coins = [coin for coin, _ in mentioned_coins[:5]]
    top_categories = list(categories.keys())[:3]

    hot_posts = sorted(posts, key=lambda x: x.get("heat_score", 0), reverse=True)[:10]
    key_topics = []
    for p in hot_posts:
        if p.get("title"):
            key_topics.append(p["title"][:80])
        elif p.get("summary"):
            key_topics.append(p["summary"][:80])

    now_ts = time.time()
    recent_6h = sum(1 for p in posts if now_ts - p.get("timestamp", 0) < 6 * 3600)
    recent_24h = sum(1 for p in posts if now_ts - p.get("timestamp", 0) < 24 * 3600)

    return {
        "top_tags": top_tags,
        "top_coins": top_coins,
        "top_categories": top_categories,
        "key_topics": key_topics[:5],
        "recent_6h_count": recent_6h,
        "recent_24h_count": recent_24h,
        "total_posts": len(posts),
    }


def calculate_engagement_metrics(posts: list) -> dict:
    if not posts:
        return {}
    rates = [p["engagement_rate"] for p in posts]
    total_views = sum(p["view_count"] for p in posts)
    total_likes = sum(p["like_count"] for p in posts)
    total_comments = sum(p["comment_count"] for p in posts)
    total_shares = sum(p["share_count"] for p in posts)
    total_interactions = sum(p.get("total_interactions", 0) for p in posts)

    valid_posts = [p for p in posts if p["view_count"] > 0]
    valid_ratio = len(valid_posts) / len(posts) * 100 if posts else 0

    return {
        "avg_engagement_rate": round(sum(rates) / len(rates), 4),
        "max_engagement_rate": round(max(rates), 4),
        "min_engagement_rate": round(min(rates), 4),
        "total_views": total_views,
        "total_likes": total_likes,
        "total_comments": total_comments,
        "total_shares": total_shares,
        "total_interactions": total_interactions,
        "avg_views": round(total_views / len(posts)),
        "post_count": len(posts),
        "valid_post_count": len(valid_posts),
        "valid_ratio": round(valid_ratio, 1),
    }


# ---------------------------------------------------------------------------
# 评分
# ---------------------------------------------------------------------------
def calculate_square_score(posts: list, viral: list, metrics: dict) -> int:
    score = 0

    post_count = len(posts)
    if post_count >= 2000:
        score += 15
    elif post_count >= 1000:
        score += 13
    elif post_count >= 500:
        score += 12
    elif post_count >= 100:
        score += 10
    elif post_count >= 30:
        score += 7
    else:
        score += min(post_count * 0.5, 5)

    total_views = metrics.get("total_views", 0)
    if total_views > 10000000:
        score += 25
    elif total_views > 5000000:
        score += 22
    elif total_views > 1000000:
        score += 18
    elif total_views > 500000:
        score += 15
    elif total_views > 100000:
        score += 10
    else:
        score += 5

    score += min(len(viral) * 2, 20)

    avg_rate = metrics.get("avg_engagement_rate", 0)
    if avg_rate > 5:
        score += 20
    elif avg_rate > 3:
        score += 15
    elif avg_rate > 1:
        score += 10
    else:
        score += 5

    total_comments = metrics.get("total_comments", 0)
    if total_comments > 50000:
        score += 20
    elif total_comments > 20000:
        score += 17
    elif total_comments > 5000:
        score += 13
    elif total_comments > 2000:
        score += 10
    elif total_comments > 500:
        score += 7
    else:
        score += 3

    return max(0, min(100, round(score)))


# ---------------------------------------------------------------------------
# 摘要
# ---------------------------------------------------------------------------
def generate_square_summary(posts: list, hashtags: list, viral: list,
                             high_eng: list, categories: dict,
                             metrics: dict, score: int,
                             hot_articles: list = None) -> str:
    lines = []
    tz_cn = timezone(timedelta(hours=8))
    now_str = datetime.now(tz_cn).strftime("%Y-%m-%d %H:%M")

    lines.append(f"## L0 广场实时热帖报告 ({now_str} UTC+8)")
    lines.append(f"**广场热度评分: {score}/100** | 采集帖子: {len(posts)} 条")
    lines.append("")

    if metrics:
        lines.append("### 互动数据概览")
        lines.append(
            f"- 总浏览量: {metrics['total_views']:,} | "
            f"总点赞: {metrics['total_likes']:,} | "
            f"总评论: {metrics['total_comments']:,} | "
            f"总互动: {metrics.get('total_interactions', 0):,}"
        )
        lines.append(f"- 平均互动率: {metrics['avg_engagement_rate']}% | "
                     f"有效帖子: {metrics.get('valid_post_count', 0)}/{metrics['post_count']} "
                     f"({metrics.get('valid_ratio', 0)}%)")
        lines.append("")

    if hot_articles:
        lines.append("### 热门文章 Top 5 (综合热度)")
        for i, p in enumerate(hot_articles[:5], 1):
            lines.append(
                f"  {i}. **{p['author']}**: {p['summary'][:60]} "
                f"(浏览{p['view_count']:,} 点赞{p['like_count']} 评论{p['comment_count']} "
                f"热度分{p.get('heat_score', 0):,.0f})"
            )
        lines.append("")

    if posts:
        lines.append("### 浏览量 Top 3")
        sorted_posts = sorted(posts, key=lambda x: x["view_count"], reverse=True)
        for p in sorted_posts[:3]:
            lines.append(
                f"- **{p['author']}**: {p['summary'][:50]} "
                f"(浏览{p['view_count']:,} 点赞{p['like_count']} 评论{p['comment_count']})"
            )
        lines.append("")

    if hashtags:
        tags_str = " ".join([f"#{tag}({cnt})" for tag, cnt in hashtags[:8]])
        lines.append(f"### 热门标签\n{tags_str}")
        lines.append("")

    if categories:
        lines.append("### 内容分类分布")
        for cat, cnt in list(categories.items())[:6]:
            lines.append(f"- {cat}: {cnt} 篇")
        lines.append("")

    if viral:
        lines.append(f"### 病毒式帖子 ({len(viral)} 篇)")
        for p in viral[:5]:
            lines.append(f"- {p['author']}: {p['view_count']:,} 浏览 | {p['summary'][:40]}")
        lines.append("")

    if high_eng:
        lines.append("### 高互动率帖子 Top 3")
        for p in high_eng[:3]:
            lines.append(
                f"- {p['author']}: 互动率{p['engagement_rate']}% | "
                f"{p['summary'][:40]} (浏览{p['view_count']:,})"
            )
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 主函数
# ---------------------------------------------------------------------------
def run_square_monitor(pages: int = 3, deep: bool = False,
                       max_pages_per_source: int = 25,
                       concurrent: bool = True) -> dict:
    """执行完整的广场监控

    Args:
        pages: 快速模式抓取页数
        deep: 是否启用深度抓取（1000-2000+条）
        max_pages_per_source: 深度模式每源最大页数
        concurrent: 深度模式是否使用并发

    Returns:
        square_monitor_report (dict)
    """
    start_time = time.time()

    # 1. 抓取热帖
    if deep:
        if concurrent:
            posts = fetch_all_deep_concurrent(
                max_pages_per_source=max_pages_per_source,
                page_size=50,
                max_workers=5,
            )
        else:
            posts = fetch_all_deep(
                max_pages_per_source=max_pages_per_source,
                page_size=50,
            )
    else:
        posts = fetch_all_trending(total_pages=pages, page_size=20)

    # 数据质量检查
    posts_with_views = sum(1 for p in posts if p.get("view_count", 0) > 0)
    print(f"[L0] 数据质量: 共{len(posts)}篇，有浏览量数据{posts_with_views}篇")
    if posts_with_views == 0 and len(posts) > 0:
        print(f"[L0] 警告: 所有帖子浏览量均为0")
        for i, p in enumerate(posts[:3]):
            print(f"  第{i+1}条: view_count={p.get('view_count')}, "
                  f"like={p.get('like_count')}, author={p.get('author')}")

    # 2. 分析
    hot_hashtags = extract_hot_hashtags(posts)
    mentioned_coins = extract_mentioned_coins(posts)
    categories = classify_content(posts)
    viral = identify_viral_posts(posts)
    high_eng = identify_high_engagement(posts)
    hot_articles = identify_hot_articles(posts)
    metrics = calculate_engagement_metrics(posts)

    # 3. 评分
    score = calculate_square_score(posts, viral, metrics)

    # 4. 热门话题摘要
    topics_digest = extract_hot_topics_digest(posts, hot_hashtags,
                                              mentioned_coins, categories)

    # 5. 摘要
    summary = generate_square_summary(
        posts, hot_hashtags, viral, high_eng, categories, metrics, score,
        hot_articles
    )

    # 按浏览量排序
    posts.sort(key=lambda x: x["view_count"], reverse=True)

    elapsed = round(time.time() - start_time, 1)
    print(f"[L0] 分析完成，耗时{elapsed}s")

    report = {
        "total_fetched": len(posts),
        "trending_posts": posts[:50],
        "hot_articles": [
            {
                "author": p["author"],
                "title": p.get("title", ""),
                "summary": p["summary"][:100],
                "views": p["view_count"],
                "likes": p["like_count"],
                "comments": p["comment_count"],
                "shares": p["share_count"],
                "engagement_rate": p["engagement_rate"],
                "heat_score": p.get("heat_score", 0),
                "hashtags": p.get("hashtags", []),
                "content_preview": p.get("content_preview", "")[:300],
            }
            for p in hot_articles[:20]
        ],
        "hot_hashtags": hot_hashtags,
        "mentioned_coins": mentioned_coins,
        "high_engagement": [
            {
                "author": p["author"],
                "rate": p["engagement_rate"],
                "summary": p["summary"][:60],
                "views": p["view_count"],
            }
            for p in high_eng
        ],
        "viral_posts": [
            {
                "author": p["author"],
                "views": p["view_count"],
                "likes": p["like_count"],
                "summary": p["summary"][:60],
            }
            for p in viral
        ],
        "content_categories": categories,
        "engagement_metrics": metrics,
        "square_score": score,
        "square_summary": summary,
        "hot_topics_digest": topics_digest,
        "timestamp": int(time.time()),
        "fetch_elapsed": elapsed,
    }

    return report


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="L0 广场实时热帖监控 v5.1")
    parser.add_argument("--deep", action="store_true",
                        help="深度抓取模式（1000-2000+条）")
    parser.add_argument("--pages", type=int, default=25,
                        help="深度模式每源最大页数（默认25）")
    parser.add_argument("--no-concurrent", action="store_true",
                        help="禁用并发（串行抓取）")
    args = parser.parse_args()

    print("[L0] 广场实时热帖监控启动...")
    report = run_square_monitor(
        deep=args.deep,
        max_pages_per_source=args.pages,
        concurrent=not args.no_concurrent,
    )
    print(report["square_summary"])
    print(f"\n[L0] 广场热度评分: {report['square_score']}/100")
    print(f"[L0] 总抓取帖子: {report['total_fetched']} 条")
    print(f"[L0] 热门文章: {len(report['hot_articles'])} 篇")
    print(f"[L0] 病毒帖: {len(report['viral_posts'])} 篇")
    print(f"[L0] 热门标签: {report['hot_hashtags'][:5]}")
    print(f"[L0] 热议代币: {report['mentioned_coins'][:5]}")
    print(f"[L0] 抓取耗时: {report['fetch_elapsed']}s")

    with open("/tmp/L0_square_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)
    print("[L0] 报告已保存至 /tmp/L0_square_report.json")
