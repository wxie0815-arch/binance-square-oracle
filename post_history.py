#!/usr/bin/env python3
"""
发帖历史记录 + 表现追踪 + 自适应学习
================================================================
核心逻辑：
  1. 发帖时记录 post_id / token / style / content_type
  2. 每次预言机运行时回查近期帖子的阅读/互动数据
  3. 如果某类型帖子表现明显高于基准，提升该类型权重
  4. 权重写入 memory/style_weights.json，L5/L6生成时读取
"""
import os, json, re, requests
from datetime import datetime, timezone, timedelta

HISTORY_FILE = "/home/ubuntu/.openclaw/workspace/memory/post_history.json"
WEIGHTS_FILE = "/home/ubuntu/.openclaw/workspace/memory/style_weights.json"
CST = timezone(timedelta(hours=8))
DEDUP_DAYS = 7

BASE_URL = "https://www.binance.com"
TRENDING_API = f"{BASE_URL}/bapi/composite/v3/friendly/pgc/content/article/list"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
    "Referer": "https://www.binance.com/en/square",
}

# 默认内容类型权重（初始均等）
DEFAULT_WEIGHTS = {
    "行情分析": 1.0,
    "心态管理": 1.0,
    "抄底分析": 1.0,
    "风险控制": 1.0,
    "数据洞察": 1.0,
    "热点事件": 1.0,
    "实用攻略": 1.0,
}

# 表现提升阈值（相对均值的倍数）
BOOST_THRESHOLD = 1.5   # 超过均值1.5倍 → 权重+0.3
DECAY_THRESHOLD = 0.5   # 低于均值0.5倍 → 权重-0.2
MAX_WEIGHT = 3.0
MIN_WEIGHT = 0.3


# ── 基础读写 ──────────────────────────────────────────────────

def load_history() -> list:
    try:
        with open(HISTORY_FILE) as f:
            return json.load(f)
    except:
        return []


def save_history(history: list):
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    cutoff = (datetime.now(CST) - timedelta(days=DEDUP_DAYS)).strftime("%Y-%m-%d")
    history = [h for h in history if h.get("ts", "") >= cutoff]
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def load_weights() -> dict:
    try:
        with open(WEIGHTS_FILE) as f:
            return json.load(f)
    except:
        return DEFAULT_WEIGHTS.copy()


def save_weights(weights: dict):
    os.makedirs(os.path.dirname(WEIGHTS_FILE), exist_ok=True)
    with open(WEIGHTS_FILE, "w") as f:
        json.dump(weights, f, ensure_ascii=False, indent=2)


# ── 记录发帖 ──────────────────────────────────────────────────

def is_duplicate(topic_key: str) -> bool:
    history = load_history()
    return any(h.get("key") == topic_key for h in history)


def record_post(topic_key: str, post_id: str, preview: str,
                content_type: str = "", token: str = ""):
    history = load_history()
    history.append({
        "ts": datetime.now(CST).strftime("%Y-%m-%d"),
        "key": topic_key,
        "post_id": str(post_id),
        "preview": preview[:60],
        "content_type": content_type,
        "token": token,
        "view": 0,
        "like": 0,
        "comment": 0,
        "checked": False,
    })
    save_history(history)


# ── 回查帖子表现 ───────────────────────────────────────────────

def fetch_post_stats(post_id: str) -> dict:
    """通过广场API查帖子实时数据"""
    # 方法1：从trending列表里找
    for feed_type in [1, 2]:
        try:
            r = requests.get(
                TRENDING_API,
                params={"pageSize": 60, "pageIndex": 1, "type": feed_type},
                headers=HEADERS, timeout=10
            )
            vos = (r.json().get("data") or {}).get("vos") or []
            for item in vos:
                p = item.get("vo", item)
                if str(p.get("id", "")) == str(post_id):
                    view = p.get("viewCount", 0)
                    if isinstance(view, str):
                        view = int(re.sub(r'[^\d]', '', view) or 0)
                    return {
                        "view": int(view),
                        "like": int(p.get("likeCount", 0) or 0),
                        "comment": int(p.get("commentCount", 0) or 0),
                        "share": int(p.get("shareCount", 0) or 0),
                    }
        except:
            pass
    return {}


def update_post_stats():
    """批量更新近期帖子的阅读/互动数据"""
    history = load_history()
    updated = 0
    cutoff = (datetime.now(CST) - timedelta(days=3)).strftime("%Y-%m-%d")

    for h in history:
        if h.get("ts", "") < cutoff:
            continue
        if h.get("checked") and h.get("view", 0) > 0:
            continue
        post_id = h.get("post_id", "")
        if not post_id:
            continue

        stats = fetch_post_stats(post_id)
        if stats:
            h.update(stats)
            h["checked"] = True
            updated += 1

    save_history(history)
    return updated


# ── 自适应权重更新 ─────────────────────────────────────────────

def update_weights():
    """
    根据近期帖子表现，动态调整内容类型权重。
    规则：
    - 互动分（comment×3 + like×2 + share×5）超过均值1.5倍 → 权重+0.3
    - 互动分低于均值0.5倍 → 权重-0.2
    - 权重范围限制在 [0.3, 3.0]
    """
    history = load_history()
    weights = load_weights()

    # 只用有数据的近7天帖子
    recent = [h for h in history if h.get("view", 0) > 0 or h.get("like", 0) > 0]
    if len(recent) < 3:
        return weights, "数据不足，权重未变"

    def interact(h):
        return h.get("comment", 0) * 3 + h.get("like", 0) * 2 + h.get("share", 0) * 5

    avg_interact = sum(interact(h) for h in recent) / len(recent)
    if avg_interact == 0:
        return weights, "互动数据均为0，权重未变"

    changes = []
    type_scores = {}

    for h in recent:
        ct = h.get("content_type", "")
        if not ct:
            continue
        score = interact(h)
        if ct not in type_scores:
            type_scores[ct] = []
        type_scores[ct].append(score)

    for ct, scores in type_scores.items():
        avg_score = sum(scores) / len(scores)
        ratio = avg_score / avg_interact

        if ct not in weights:
            weights[ct] = 1.0

        old = weights[ct]
        if ratio >= BOOST_THRESHOLD:
            weights[ct] = min(MAX_WEIGHT, weights[ct] + 0.3)
            changes.append(f"↑ {ct}: {old:.1f}→{weights[ct]:.1f} (互动均值{avg_score:.0f}, 超基准{ratio:.1f}x)")
        elif ratio <= DECAY_THRESHOLD:
            weights[ct] = max(MIN_WEIGHT, weights[ct] - 0.2)
            changes.append(f"↓ {ct}: {old:.1f}→{weights[ct]:.1f} (互动均值{avg_score:.0f}, 低基准{ratio:.1f}x)")

    save_weights(weights)
    summary = "\n".join(changes) if changes else "无明显变化"
    return weights, summary


def get_top_styles(n: int = 3) -> list:
    """返回当前权重最高的N个内容类型（供L5/L6调用）"""
    weights = load_weights()
    sorted_types = sorted(weights.items(), key=lambda x: x[1], reverse=True)
    return [t[0] for t in sorted_types[:n]]


def recent_posts(days: int = 3) -> list:
    history = load_history()
    cutoff = (datetime.now(CST) - timedelta(days=days)).strftime("%Y-%m-%d")
    return [h for h in history if h.get("ts", "") >= cutoff]


# ── 主运行（由预言机调用）────────────────────────────────────────

def run_performance_learning():
    """
    完整流程：回查数据 → 更新权重 → 返回报告
    预言机每次运行时调用
    """
    print("[PerformanceLearner] 回查近期帖子表现...")
    updated = update_post_stats()
    print(f"[PerformanceLearner] 更新了 {updated} 条帖子数据")

    weights, summary = update_weights()
    print(f"[PerformanceLearner] 权重更新:\n{summary}")

    top = get_top_styles(3)
    print(f"[PerformanceLearner] 当前优先内容类型: {top}")

    return {"weights": weights, "changes": summary, "top_styles": top}


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "stats":
        updated = update_post_stats()
        print(f"更新 {updated} 条帖子数据")
        weights, summary = update_weights()
        print(f"\n权重变化:\n{summary}")
        print(f"\n当前权重: {json.dumps(weights, ensure_ascii=False, indent=2)}")
    else:
        posts = recent_posts(7)
        print(f"最近7天发帖: {len(posts)}条")
        for p in posts:
            interact = p.get('comment',0)*3 + p.get('like',0)*2 + p.get('share',0)*5
            print(f"  {p['ts']} | {p.get('content_type','?')} | 互动{interact} | {p['preview'][:40]}")
        print(f"\n优先内容类型: {get_top_styles(3)}")
