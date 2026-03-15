#!/usr/bin/env python3
"""
写作法则自动学习器
每次预言机运行后：抓Top帖 → 提炼爆款规律 → 更新 writing_mastery.md
与 engagement_patterns.md 配合，让L6每次都用最新写作法则
"""
import os, re, json, requests
from datetime import datetime, timezone, timedelta

MASTERY_FILE = "/home/ubuntu/.openclaw/workspace/memory/writing_mastery.md"
CST = timezone(timedelta(hours=8))
BASE = "https://www.binance.com"
TRENDING_API = f"{BASE}/bapi/composite/v3/friendly/pgc/content/article/list"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
           "Referer": "https://www.binance.com/en/square"}

def fetch_top_cn_posts(n: int = 20) -> list:
    """抓取高互动中文帖"""
    all_posts = []
    for t in [1, 2]:
        try:
            r = requests.get(TRENDING_API, params={"pageSize": 60, "pageIndex": 1, "type": t},
                             headers=HEADERS, timeout=12)
            vos = (r.json().get("data") or {}).get("vos") or []
            for item in vos:
                p = item.get("vo", item)
                content = ""
                for k in ["body", "bodyText", "content", "text"]:
                    v = p.get(k, "")
                    if isinstance(v, str) and len(v) > 5:
                        content = v; break
                cn = len(re.findall(r'[\u4e00-\u9fff]', content))
                if cn < 5 or cn / max(len(content), 1) < 0.25:
                    continue
                view = p.get("viewCount", 0) or 0
                if isinstance(view, str): view = int(re.sub(r'[^\d]', '', view) or 0)
                all_posts.append({
                    "content": content,
                    "view": int(view),
                    "like": int(p.get("likeCount", 0) or 0),
                    "comment": int(p.get("commentCount", 0) or 0),
                    "share": int(p.get("shareCount", 0) or 0),
                    "length": len(content),
                })
        except: pass

    def score(p): return p["comment"] * 3 + p["like"] * 2 + p["view"] // 100 + p["share"] * 5
    return sorted(all_posts, key=score, reverse=True)[:n]


def classify_post_type(content: str, length: int) -> str:
    """判断帖子类型"""
    if length <= 30: return "极短情绪帖"
    if any(w in content for w in ["愚蠢", "必然", "一定", "肯定涨", "肯定跌", "必须", "只有傻瓜"]): return "强观点帖"
    if any(w in content for w in ["孙宇晨", "马斯克", "赵长鹏", "特朗普", "CZ", "SBF"]): return "KOL话题帖"
    if any(w in content for w in ["怎么做", "步骤", "教程", "攻略", "1.", "第一步", "方法"]): return "实用攻略帖"
    if any(w in content for w in ["伊朗", "战争", "美联储", "降息", "关税", "地缘"]): return "宏观事件帖"
    if any(w in content for w in ["重仓", "我开", "我买了", "我卖了", "爆仓", "我的仓位"]): return "仓位披露帖"
    return "行情分析帖"


def extract_hook(content: str) -> str:
    """提取钩子句（第一句话）"""
    first = content.split('\n')[0].strip()
    return first[:60] if first else content[:60]


def run_writing_learner():
    """主流程：抓帖 → 分析 → 更新法则"""
    print("[WritingLearner] 抓取实时Top帖...")
    posts = fetch_top_cn_posts(20)
    if not posts:
        print("[WritingLearner] 无数据，跳过")
        return

    # 统计类型分布
    type_stats = {}
    hook_examples = []
    short_examples = []  # ≤30字高互动帖

    for p in posts:
        ptype = classify_post_type(p["content"], p["length"])
        interact = p["comment"] * 3 + p["like"] * 2 + p["share"] * 5
        if ptype not in type_stats:
            type_stats[ptype] = {"count": 0, "total_interact": 0, "examples": []}
        type_stats[ptype]["count"] += 1
        type_stats[ptype]["total_interact"] += interact
        if len(type_stats[ptype]["examples"]) < 2:
            type_stats[ptype]["examples"].append(
                f"({p['comment']}评/{p['like']}赞) {p['content'][:60].strip()}"
            )
        hook_examples.append(extract_hook(p["content"]))
        if p["length"] <= 50:
            short_examples.append(p["content"][:80])

    # 计算均值
    all_comments = [p["comment"] for p in posts]
    all_likes = [p["like"] for p in posts]
    avg_comment = sum(all_comments) / len(all_comments) if all_comments else 0
    avg_like = sum(all_likes) / len(all_likes) if all_likes else 0

    # 排序类型（按平均互动）
    ranked_types = sorted(
        type_stats.items(),
        key=lambda x: x[1]["total_interact"] / max(x[1]["count"], 1),
        reverse=True
    )

    now = datetime.now(CST).strftime("%Y-%m-%d %H:%M CST")

    # 生成更新后的法则文档
    lines = [
        f"# 广场爆款写作法则（自动更新）",
        f"> 基于实时Top{len(posts)}高互动中文帖分析",
        f"> 最后更新：{now}",
        "",
        f"## 基准互动数据",
        f"- 平均评论：{avg_comment:.1f}条",
        f"- 平均点赞：{avg_like:.1f}个",
        "",
        "## 当前最有效内容类型（按互动均值排序）",
    ]

    for ptype, stats in ranked_types:
        avg = stats["total_interact"] / max(stats["count"], 1)
        lines.append(f"\n### {ptype}（{stats['count']}篇，平均互动分{avg:.0f}）")
        for ex in stats["examples"]:
            lines.append(f"  > {ex}")

    lines += [
        "",
        "## 高互动钩子句式（实时Top帖第一句）",
    ]
    for i, hook in enumerate(hook_examples[:8], 1):
        lines.append(f"  {i}. {hook}")

    if short_examples:
        lines += ["", "## 极短爆款帖（≤50字，靠情绪/悬念）"]
        for ex in short_examples[:4]:
            lines.append(f'  > "{ex}"')

    lines += [
        "",
        "## L6生成规则（基于当前数据）",
        f"1. 优先类型：{ranked_types[0][0] if ranked_types else '行情分析帖'}",
        "2. 短帖（≤100字）：开头数字/反常现象 → 中间反转 → 疑问结尾",
        "3. 长帖（≥300字）：强钩子开头 → 每段≤4句 → 行动指令结尾",
        "4. 禁止：平铺直叙 / 结论太早 / 超5行无换行 / emoji",
        "5. 必须：第一句含数字或情绪词，最后一句是问句或悬念",
    ]

    content = "\n".join(lines)
    os.makedirs(os.path.dirname(MASTERY_FILE), exist_ok=True)
    with open(MASTERY_FILE, "w", encoding="utf-8") as f:
        f.write(content)

    top_type = ranked_types[0][0] if ranked_types else "N/A"
    print(f"[WritingLearner] ✅ 法则已更新 | Top类型: {top_type} | 分析{len(posts)}帖")
    return {"top_type": top_type, "post_count": len(posts), "type_stats": type_stats}


if __name__ == "__main__":
    result = run_writing_learner()
    print(json.dumps(result, ensure_ascii=False, indent=2) if result else "无结果")
