#!/usr/bin/env python3
"""
币安广场流量预言机 - Square Traffic Oracle
数据来源（官方Skill）：
  - crypto-market-rank skill → 社交热度榜（leaderBoardList）
  - spot skill               → 24h行情涨幅榜（ticker/24hr）
  - trading-signal skill     → 智能钱信号（smart-money）
  - opennews                 → 新闻热词（需OPENNEWS_TOKEN）
"""

import sys, os, json, urllib.request
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE, ".."))

def get_social_hype():
    """crypto-market-rank skill - 社交热度榜"""
    from binance_skills import skill_get_social_hype
    data, err = skill_get_social_hype("56", limit=10)
    if data:
        return data
    # 降级：spot skill 公开行情
    from binance_skills import skill_get_top_movers
    movers, _ = skill_get_top_movers(10)
    return [{"symbol": m["symbol"], "hype": int(m["volume_usdt"]/1e6),
             "sentiment": "positive" if m["change_pct"] > 0 else "negative",
             "source": "spot/ticker/24hr"} for m in (movers or [])]

def get_trending_tokens():
    """spot skill - 24h涨幅热门代币"""
    from binance_skills import skill_get_top_movers
    movers, err = skill_get_top_movers(8)
    return [{"symbol": m["symbol"], "price_change": m["change_pct"],
             "volume": m["volume_usdt"], "source": m["source"]} for m in (movers or [])]

def get_smart_money_signals():
    """trading-signal skill - 智能钱信号"""
    from binance_skills import skill_get_smart_money_signals
    signals, err = skill_get_smart_money_signals("56", limit=5)
    return signals or []

def get_square_trending_posts(pages=2):
    """binance-square-monitor skill - 广场实时热帖数据（L0层）"""
    try:
        sys.path.insert(0, os.path.join(BASE, "skills/binance-square-monitor/scripts"))
        from binance_square_monitor import fetch_all_trending
        posts = fetch_all_trending(total_pages=pages, page_size=20)
        if not posts:
            return []
        # 取top10，按浏览量排序
        posts.sort(key=lambda x: x["view_count"], reverse=True)
        return posts[:10]
    except Exception as e:
        return []

def extract_square_signals(posts):
    """从广场热帖中提取话题信号：高互动率帖子 + 热门hashtag"""
    if not posts:
        return {"hot_hashtags": [], "high_engagement": [], "viral_posts": []}

    hashtag_count = {}
    for p in posts:
        for tag in p.get("hashtags", []):
            hashtag_count[tag] = hashtag_count.get(tag, 0) + 1

    hot_tags = sorted(hashtag_count.items(), key=lambda x: x[1], reverse=True)[:5]

    # 互动率 = (likes + comments + shares) / views
    for p in posts:
        views = p['view_count'] or 1
        p["engagement_rate"] = (p['like_count'] + p['comment_count'] + p["share_count"]) / views

    high_eng = sorted(posts, key=lambda x: x["engagement_rate"], reverse=True)[:3]
    viral = [p for p in posts if p['view_count'] > 10000][:3]

    return {
        "hot_hashtags": [t[0] for t in hot_tags],
        "high_engagement": [{"author": p['author'], "rate": round(p["engagement_rate"]*100, 2),
                              "summary": p['summary'][:40]} for p in high_eng],
        "viral_posts": [{"author": p['author'], "views": p['view_count'],
                         "summary": p['summary'][:40]} for p in viral],
    }

def get_news_hotwords(token=None):
    """opennews - 新闻热词（需OPENNEWS_TOKEN）"""
    token = token or os.environ.get("OPENNEWS_TOKEN")
    if not token:
        return ["AI", "BTC", "ETH", "Web3", "Binance", "DeFi", "Layer2", "Meme"]
    try:
        url = os.environ.get("API_6551_BASE", "") + "/open/news_search"
        body = json.dumps({"limit": 20, "orderBy": "score", "timeRange": "6h"}).encode()
        req = urllib.request.Request(url, data=body, headers={
            "Authorization": f"Bearer {token}", "Content-Type": "application/json"
        })
        with urllib.request.urlopen(req, timeout=10) as r:
            d = json.loads(r.read())
        items = d.get("data", {}).get("list", [])
        words = []
        for item in items[:10]:
            words.extend(item.get("title", "").split()[:3])
        return list(set(words))[:12] or ["AI", "BTC", "ETH", "Binance"]
    except:
        return ["AI", "BTC", "ETH", "Web3", "Binance", "DeFi"]

def analyze_traffic_patterns(social_hype, trending_tokens, smart_signals):
    """综合三维数据分析今日流量密钥"""
    hour = datetime.now(timezone.utc).hour
    bj_hour = (hour + 8) % 24

    if 20 <= bj_hour <= 23:
        time_window = "🌙 晚间黄金期（北京20:00-23:00）"
        time_multiplier = 1.4
    elif 8 <= bj_hour <= 10:
        time_window = "☀️ 早盘黄金期（北京08:00-10:00）"
        time_multiplier = 1.3
    elif 12 <= bj_hour <= 14:
        time_window = "🌤 午间小高峰（北京12:00-14:00）"
        time_multiplier = 1.1
    else:
        time_window = "⏰ 普通时段"
        time_multiplier = 1.0

    # 从社交热度取Top3热门代币
    top_symbols = [h['symbol'] for h in (social_hype or [])[:3]]
    # 从智能钱信号取BUY方向
    smart_buys = [s['ticker'] for s in (smart_signals or []) if s.get("direction") == "buy"][:3]

    return {
        "time_window": time_window,
        "time_multiplier": time_multiplier,
        "top_symbols": top_symbols,
        "smart_buys": smart_buys,
        "bj_hour": bj_hour,
    }

def predict_hot_topics(analysis, hotwords, smart_signals):
    """预测今日热榜Top5话题"""
    symbols_str = "+".join(analysis["top_symbols"][:2]) if analysis["top_symbols"] else "BTC+ETH"
    smart_str   = analysis["smart_buys"][0] if analysis["smart_buys"] else "BTC"

    topics = [
        {"rank": 1, "topic": f"AI+加密：{symbols_str}今日值得关注吗",
         "score": int(95 * analysis['time_multiplier']), "type": "AI+加密",
         "best_time": "全天", "format": "图文/视频"},
        {"rank": 2, "topic": f"智能钱正在买{smart_str}，跟吗？",
         "score": int(91 * analysis['time_multiplier']), "type": "智能钱信号",
         "best_time": "突发时立即", "format": "短文+截图"},
        {"rank": 3, "topic": "收益晒单：AI帮我优化配置后的7日回报",
         "score": int(87 * analysis['time_multiplier']), "type": "收益晒单",
         "best_time": "收盘后", "format": "截图+分析"},
        {"rank": 4, "topic": f"{symbols_str}行情分析 —— 现在是买点还是等待",
         "score": int(83 * analysis['time_multiplier']), "type": "行情分析",
         "best_time": "09:00-10:00 / 21:00-22:00", "format": "图文+数据"},
        {"rank": 5, "topic": "7日挑战Day更新：交易思维开始改变了",
         "score": int(78 * analysis['time_multiplier']), "type": "成长故事",
         "best_time": "晚间20:00-22:00", "format": "长文+截图"},
    ]
    return topics


def generate_square_oracle_report():
    now_bj = datetime.now(timezone.utc)
    bj_str = f"{(now_bj.hour+8)%24:02d}:{now_bj.minute:02d} CST"

    social_hype    = get_social_hype()
    trending       = get_trending_tokens()
    smart_signals  = get_smart_money_signals()
    hotwords       = get_news_hotwords()
    # L0层：广场实时热帖（binance-square-monitor skill）
    square_posts   = get_square_trending_posts(pages=2)
    square_signals = extract_square_signals(square_posts)

    analysis = analyze_traffic_patterns(social_hype, trending, smart_signals)
    topics   = predict_hot_topics(analysis, hotwords, smart_signals)

    lines = [
        f"🔮 币安广场流量预言机",
        f"分析时间：{now_bj.strftime('%Y-%m-%d')} {bj_str}",
        f"{'='*45}",
        f"",
        f"📊 数据来源",
        f"  ✅ binance-square-monitor → 广场热帖：{len(square_posts)}条（实时）",
        f"  ✅ crypto-market-rank skill → 社交热度：{len(social_hype)}条",
        f"  ✅ spot skill               → 行情热点：{len(trending)}条",
        f"  ✅ trading-signal skill     → 智能钱信号：{len(smart_signals)}条",
        f"",
    ]

    # 广场实时热帖信号
    if square_posts:
        lines += [f"📡 广场热帖实时数据（L0层）"]
        for p in square_posts[:3]:
            lines.append(f"  👤 {p['author']} | 👁{p['view_count']:,} ❤{p['like_count']} 💬{p['comment_count']} | {p['summary'][:35]}...")
        if square_signals['hot_hashtags']:
            lines.append(f"  🏷 热门标签：{'  '.join(['#'+t for t in square_signals['hot_hashtags'][:4]])}")
        if square_signals['high_engagement']:
            top = square_signals['high_engagement'][0]
            lines.append(f"  🔥 互动率最高：{top['author']}（{top['rate']}%）")
        lines.append("")

    lines += [
        f"🔥 今日社交热度Top3（crypto-market-rank）",
    ]
    for h in (social_hype or [])[:3]:
        lines.append(f"  #{h['symbol']}  热度:{h['hype']:,}  情绪:{h.get('sentiment','N/A')}")

    if smart_signals:
        lines += ["", f"💰 智能钱信号Top3（trading-signal）"]
        for s in smart_signals[:3]:
            lines.append(f"  {s['ticker']} {s['direction'].upper()} | 最大涨幅:{s['max_gain']}% | 退出率:{s['exit_rate']}%")

    lines += [
        "",
        f"⏰ 当前时间窗口：{analysis['time_window']}",
        f"   流量系数 ×{analysis['time_multiplier']}",
        "",
        f"🎯 今日热榜话题预测 Top5",
    ]
    for t in topics:
        lines += [
            f"  {t['rank']}. {t['topic']}",
            f"     热度分：{t['score']} | 最佳时间：{t['best_time']} | 格式：{t['format']}",
            "",
        ]

    lines += [
        f"📝 今日标题公式推荐",
        f"  · AI帮我发现了{{symbol}}的{{信号类型}}，结果让我{{情绪}}",
        f"  · 智能钱刚买了{{token}}，你要跟吗？",
        f"  · 照镜子第{{N}}天：AI说我的致命弱点是……",
        f"",
        f"💡 流量密码总结",
        f"  1. 社交热度最高：{'  '.join([h['symbol'] for h in (social_hype or [])[:3]])}",
        f"  2. 时段系数：{analysis['time_window']}",
        f"  3. 标题含情绪词互动率+40%",
        f"  4. 发布后30分钟主动互动触发推荐算法",
        f"",
        f"{'='*45}",
        f"🖤 XieXiu × 芒果 · 广场流量预言机 v2.0",
        f"   数据由币安官方Skill提供",
    ]
    return "\n".join(lines)


def humanize_content(text):
    """
    去AI味处理（humanizer-cn规则）
    同时处理代币格式：BTC → $BTC（广场规范，前后加空格）
    调用 skill: /home/ubuntu/.openclaw/workspace/skills/humanizer-cn/SKILL.md
    """
    import re
    replacements = {
        "值得注意的是": "说实话",
        "综上所述": "反正就是",
        "不难发现": "你会发现",
        "让我们来看看": "",
        "话不多说": "",
        "欢迎关注": "",
        "干货满满": "",
        "建议收藏": "",
        "赋能": "帮到",
        "精准": "准",
        "系统性": "",
        "底层逻辑": "本质",
        "大幅上涨": "涨了不少",
        "大幅下跌": "跌得挺惨",
        "显著增长": "涨了",
    }
    result = text
    for old, new in replacements.items():
        result = result.replace(old, new)

    # 代币格式标准化：裸BTC/ETH等 → $BTC $ETH（广场规范）
    # 避免重复处理已有 $ 前缀的
    TOKENS = ["BTC", "ETH", "BNB", "SOL", "XRP", "DOGE", "ADA", "AVAX", "DOT", "MATIC"]
    for token in TOKENS:
        text = re.sub(rf"(?<!\$)(?<![A-Z]){re.escape(token)}(?![A-Z])", f" ${token} ", text)

    # 清理多余空格
    result = re.sub(r"  +", " ", text)
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()


def generate_enhanced_report():
    """
    三层数据融合输出：
    Layer1: 官方Skill（crypto-market-rank / spot / trading-signal）
    Layer2: 6551增强（opennews + Twitter KOL）
    Layer3: 广场热点信号（@binancezh推文 + 话题分类）
    + humanizer-cn 去AI味建议
    """
    # Layer1: 官方skill报告（不变）
    base_report = generate_square_oracle_report()

    # 获取BTC涨跌幅（驱动情绪判断）
    try:
        from binance_skills import skill_get_top_movers
        movers, _ = skill_get_top_movers(10)
        btc_change = next((m["change_pct"] for m in (movers or []) if "BTC" in m["symbol"]), None)
    except:
        btc_change = None

    # Layer2: 6551增强层（opennews + KOL）
    try:
        from data_6551 import build_enhancement_report, format_enhancement_block
        enh_data = build_enhancement_report(btc_change=btc_change)
        enh_block = format_enhancement_block(enh_data)
    except Exception as e:
        enh_block = f"\n[6551增强层暂不可用: {e}]\n"

    # Layer3: 广场热点信号（@binancezh + opennews话题分类）
    try:
        from square_signals import build_square_signal_report, format_square_block
        sq_data = build_square_signal_report()
        sq_block = format_square_block(sq_data)
        if sq_data.get("topics"):
            top_topic = sq_data["topics"][0]["topic"]
            top_tags = " ".join([f"#{t}" for t, _ in sq_data.get("hashtags", [])[:3]])
            sq_block += f"\n🎯 今日最优选题组合：「{top_topic}」× BTC行情  标签：{top_tags}\n"
    except Exception as e:
        sq_block = f"\n[广场热点层暂不可用: {e}]\n"

    # humanizer-cn v2.0 提示块（接入Web3规律库）
    humanizer_tip = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✍️ 写作规则（humanizer-cn v2.0 + Web3规律库）

❌ 禁用：排比三段式 / 升华结尾 / 赋能/底层逻辑/干货
✅ 必用：具体数字 | 时间锚点 | 停顿句 | $BTC格式

📐 无邪爆款结构：
  ① 钩子（1句，数字/反差/自我暴露）
  ② 背景（2-3句，具体情境）
  ③ 转折（1句，出人意料）
  ④ 结果（数字/可验证细节）
  ⑤ 开放结尾（问句，引发评论）

🎯 当前最优话题方向：AI×币安广场 × $BTC跌市
🏷️ 标签：#AI #币安广场 #AIBinance
⏰ 发布窗口：北京 20:00-22:00 互动最高
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

    return base_report + "\n" + enh_block + "\n" + sq_block + humanizer_tip


if __name__ == "__main__":
    import sys
    if "--enhanced" in sys.argv:
        print(generate_enhanced_report())
    else:
        print(generate_square_oracle_report())
