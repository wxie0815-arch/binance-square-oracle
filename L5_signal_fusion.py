#!/usr/bin/env python3
"""
L5 信号融合引擎 (Signal Fusion Engine)
================================================================
将 L0-L4 各层数据进行加权融合，输出统一的预言机信号

融合维度：
  1. 话题热度融合    - 广场热帖 + 社交热度 + 新闻 → 综合话题排名
  2. 代币热度融合    - 各层提及代币交叉验证 → 高确信度代币
  3. 情绪融合        - 技术面 + 社交面 + 链上面 → 综合情绪
  4. 时机评估        - 时间窗口 + 行情阶段 → 发布时机建议
  5. 预言机评分      - 各层评分加权 → 总体流量预测分

输出：fusion_report (dict)
  - oracle_score:       预言机总评分 (0-100)
  - oracle_rating:      评级文字
  - fused_topics:       融合话题排名 Top 10
  - fused_coins:        融合代币热度 Top 10
  - fused_sentiment:    融合情绪
  - timing_advice:      发布时机建议
  - content_strategy:   内容策略建议
  - headline_templates: 标题模板
  - fusion_summary:     融合报告摘要
"""

import time
from datetime import datetime, timezone, timedelta
from collections import Counter


# ---------------------------------------------------------------------------
# 权重配置
# ---------------------------------------------------------------------------
# 默认权重（包含 L4）
LAYER_WEIGHTS_FULL = {
    "L0_square": 0.30,    # 广场实时热帖
    "L1_social": 0.15,    # 社交热度
    "L2_onchain": 0.20,   # 链上异动
    "L3_market": 0.20,    # 行情分析
    "L4_news": 0.15,      # 新闻+KOL
}

# L4 缺失时的降级权重（L4 的 15% 重新分配给 L0 和 L3）
LAYER_WEIGHTS_NO_L4 = {
    "L0_square": 0.35,    # +5%
    "L1_social": 0.15,
    "L2_onchain": 0.20,
    "L3_market": 0.25,    # +5%
    "L4_news": 0.05,      # 保留最小权重（使用默认值 50）
}


def _get_weights(l4_report: dict = None) -> dict:
    """根据 L4 是否可用动态选择权重"""
    if l4_report and l4_report.get("available", True) and l4_report.get("news_score", 0) > 0:
        return LAYER_WEIGHTS_FULL
    return LAYER_WEIGHTS_NO_L4


# 向后兼容：保留旧名称
LAYER_WEIGHTS = LAYER_WEIGHTS_FULL


# ---------------------------------------------------------------------------
# 1. 话题热度融合
# ---------------------------------------------------------------------------
def fuse_topics(l0_report: dict, l1_report: dict, l4_report: dict) -> list:
    """融合各层话题数据，输出综合话题排名"""
    topic_scores = Counter()

    # L0: 广场内容分类
    for cat, cnt in (l0_report.get("content_categories") or {}).items():
        topic_scores[cat] += cnt * 3  # 广场权重高

    # L0: 热门标签转话题
    for tag, cnt in (l0_report.get("hot_hashtags") or []):
        topic_scores[f"#{tag}"] += cnt * 2

    # L1: 热门叙事
    for narrative, cnt in (l1_report.get("hot_narratives") or []):
        topic_scores[narrative] += cnt * 2

    # L4: 话题分类
    for topic in (l4_report.get("topic_classification") or []):
        topic_scores[topic["topic"]] += topic["score"]

    # L4: 热门标签
    for tag, cnt in (l4_report.get("hot_hashtags") or []):
        topic_scores[f"#{tag}"] += cnt

    results = []
    for topic, score in topic_scores.most_common(10):
        results.append({"topic": topic, "fusion_score": round(score, 1)})
    return results


# ---------------------------------------------------------------------------
# 2. 代币热度融合
# ---------------------------------------------------------------------------
def fuse_coins(l0_report: dict, l1_report: dict, l2_report: dict,
               l3_report: dict, l4_report: dict) -> list:
    """融合各层代币数据，交叉验证输出高确信度代币"""
    coin_data = {}

    def _add(symbol: str, source: str, score: float, extra: dict = None):
        if not symbol:
            return
        sym = symbol.upper()
        if sym not in coin_data:
            coin_data[sym] = {"symbol": sym, "sources": [], "total_score": 0, "details": {}}
        coin_data[sym]["sources"].append(source)
        coin_data[sym]["total_score"] += score
        if extra:
            coin_data[sym]["details"].update(extra)

    # L0: 广场提及代币
    for coin, cnt in (l0_report.get("mentioned_coins") or []):
        _add(coin, "L0_square", cnt * 3)

    # L1: 社交热度代币
    for item in (l1_report.get("social_hype_list") or [])[:10]:
        hype = item.get("social_hype", 0)
        score = min(hype / 100000, 10)
        _add(item["symbol"], "L1_social", score, {
            "sentiment": item.get("sentiment", ""),
            "social_hype": hype,
        })

    # L2: 链上智能钱代币
    for signal in (l2_report.get("smart_money_signals") or []):
        ticker = signal.get("ticker", "")
        _add(ticker, "L2_onchain", 5, {
            "onchain_direction": signal.get("direction", ""),
            "smart_money_count": signal.get("smartMoneyCount", 0),
        })

    # L2: 净流入代币
    for token in (l2_report.get("net_inflow_tokens") or [])[:10]:
        inflow = float(token.get("netInflow", 0))
        if inflow > 0:
            _add(token.get("symbol", ""), "L2_inflow", min(inflow / 10000, 5), {
                "net_inflow": inflow,
            })

    # L3: 趋势代币
    for token in (l3_report.get("trending_tokens") or [])[:10]:
        _add(token["symbol"], "L3_trending", 3, {
            "change_24h": token.get("change_24h", "0"),
        })

    # L4: 新闻代币
    for coin, cnt in (l4_report.get("news_coins") or []):
        _add(coin, "L4_news", cnt * 2)

    # L4: 热词中的代币
    for kw, cnt in (l4_report.get("hot_keywords") or []):
        if len(kw) <= 5 and kw.isupper():
            _add(kw, "L4_keyword", cnt)

    # 排序 + 交叉验证加分
    for sym, data in coin_data.items():
        source_count = len(set(data["sources"]))
        if source_count >= 3:
            data["total_score"] *= 1.5  # 三层以上交叉验证加 50%
            data["confidence"] = "HIGH"
        elif source_count >= 2:
            data["total_score"] *= 1.2
            data["confidence"] = "MEDIUM"
        else:
            data["confidence"] = "LOW"
        data["source_count"] = source_count

    results = sorted(coin_data.values(), key=lambda x: x["total_score"], reverse=True)
    return results[:15]


# ---------------------------------------------------------------------------
# 3. 情绪融合
# ---------------------------------------------------------------------------
def fuse_sentiment(l1_report: dict, l2_report: dict, l3_report: dict, l4_report: dict) -> dict:
    """融合各层情绪数据"""
    # L1 社交情绪
    l1_sentiment = l1_report.get("sentiment_overview", {})
    l1_pos = l1_sentiment.get("positive_ratio", 50)

    # L2 链上情绪（买入信号 vs 卖出信号）
    l2_signals = l2_report.get("smart_money_signals", [])
    buy_count = sum(1 for s in l2_signals if s.get("direction") == "buy")
    sell_count = sum(1 for s in l2_signals if s.get("direction") == "sell")
    l2_score = 50 + (buy_count - sell_count) * 10

    # L3 行情情绪
    l3_score = l3_report.get("market_score", 50)
    fear_greed = l3_report.get("fear_greed", {}).get("value", 50)

    # L4 新闻情绪
    l4_sentiment = l4_report.get("market_sentiment", {}).get("sentiment", "中性")
    l4_map = {"极度贪婪": 80, "偏多": 65, "中性": 50, "偏空": 35, "极度恐惧": 20}
    l4_score = l4_map.get(l4_sentiment, 50)

    # 加权融合
    fused_score = (
        l1_pos * 0.2 +
        l2_score * 0.2 +
        l3_score * 0.3 +
        l4_score * 0.15 +
        fear_greed * 0.15
    )
    fused_score = max(0, min(100, round(fused_score)))

    if fused_score >= 70:
        label = "极度贪婪"
        advice = "市场过热，注意风险，可发布风险提醒类内容"
    elif fused_score >= 55:
        label = "偏多"
        advice = "市场偏暖，适合发布行情分析和操作记录"
    elif fused_score >= 45:
        label = "中性"
        advice = "市场观望，适合发布教育类和策略类内容"
    elif fused_score >= 30:
        label = "偏空"
        advice = "市场偏冷，适合发布心态管理和抄底分析"
    else:
        label = "极度恐惧"
        advice = "市场恐慌，发布逆向思维内容容易引发讨论"

    return {
        "fused_score": fused_score,
        "label": label,
        "advice": advice,
        "components": {
            "social_sentiment": round(l1_pos, 1),
            "onchain_sentiment": l2_score,
            "market_sentiment": l3_score,
            "news_sentiment": l4_score,
            "fear_greed": fear_greed,
        },
    }


# ---------------------------------------------------------------------------
# 4. 时机评估
# ---------------------------------------------------------------------------
def evaluate_timing() -> dict:
    """评估当前发布时机"""
    tz_cn = timezone(timedelta(hours=8))
    now = datetime.now(tz_cn)
    bj_hour = now.hour
    weekday = now.weekday()  # 0=Monday

    if 20 <= bj_hour <= 23:
        window = "晚间黄金期"
        multiplier = 1.4
        desc = "北京20:00-23:00，互动最高时段"
    elif 8 <= bj_hour <= 10:
        window = "早盘黄金期"
        multiplier = 1.3
        desc = "北京08:00-10:00，抢占话题位"
    elif 12 <= bj_hour <= 14:
        window = "午间小高峰"
        multiplier = 1.1
        desc = "北京12:00-14:00，上班族刷机时间"
    elif 0 <= bj_hour <= 6:
        window = "深夜低谷"
        multiplier = 0.6
        desc = "北京00:00-06:00，流量最低"
    else:
        window = "普通时段"
        multiplier = 1.0
        desc = "常规时段"

    # 周末加成
    if weekday >= 5:
        multiplier *= 1.10
        desc += "（周末流量偏低）"

    return {
        "bj_hour": bj_hour,
        "weekday": weekday,
        "window": window,
        "multiplier": round(multiplier, 2),
        "description": desc,
        "best_times": ["20:00-22:00", "08:00-10:00", "12:00-14:00"],
    }


# ---------------------------------------------------------------------------
# 5. 内容策略建议
# ---------------------------------------------------------------------------
def generate_content_strategy(fused_topics: list, fused_coins: list,
                                fused_sentiment: dict, timing: dict,
                                l0_hot_hashtags: list = None) -> dict:
    """
    基于融合数据生成内容策略建议（v2改进版）
    改进点：
    1. 避免内容类型重复：记录历史使用，强制多样化
    2. 融合L0热门标签：确保标题模板蹭热点
    3. 基于广场内容分类调整类型权重
    """
    import json, os
    from datetime import datetime, timedelta

    # 最优话题
    top_topics = [t["topic"] for t in fused_topics[:3]]

    # 融合L0热门标签（如果提供）
    l0_tags = []
    if l0_hot_hashtags:
        l0_tags = [tag for tag, cnt in l0_hot_hashtags[:5]]
        # 将热门标签加入话题
        for tag in l0_tags[:3]:
            if f"#{tag}" not in top_topics:
                top_topics.append(f"#{tag}")

    # 最优代币（高确信度）
    high_conf_coins = [c["symbol"] for c in fused_coins if c.get("confidence") in ("HIGH", "MEDIUM")][:5]
    if not high_conf_coins:
        high_conf_coins = [c["symbol"] for c in fused_coins[:3]]

    # 情绪驱动的内容类型（扩展版）
    sentiment_label = fused_sentiment.get("label", "中性")
    content_type_pool = {
        "极度贪婪": ["风险提醒", "获利了结分析", "历史对比", "仓位管理", "止盈策略"],
        "偏多": ["行情分析", "操作记录", "趋势解读", "技术教学", "突破确认"],
        "中性": ["教育科普", "策略分享", "工具推荐", "数据解读", "行业观察"],
        "偏空": ["心态管理", "抄底分析", "风险控制", "止损策略", "市场回顾"],
        "极度恐惧": ["逆向思维", "历史底部对比", "长期价值", "定投策略", "价值投资"],
    }

    # 加载历史使用记录
    history_file = "/tmp/oracle_content_history.json"
    used_types_last_7days = []
    try:
        if os.path.exists(history_file):
            with open(history_file, "r") as f:
                history = json.load(f)
                # 只保留最近7天的记录
                cutoff = (datetime.now() - timedelta(days=7)).timestamp()
                used_types_last_7days = [h["type"] for h in history if h.get("timestamp", 0) > cutoff]
    except:
        used_types_last_7days = []

    # 从池中排除最近使用过的类型，强制多样化
    available_types = content_type_pool.get(sentiment_label, ["行情分析"])
    fresh_types = [t for t in available_types if t not in used_types_last_7days]

    # 如果所有类型都用过了，重置
    if not fresh_types:
        fresh_types = available_types

    # ★ 读取自适应权重，对表现好的类型提高被选概率
    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from post_history import load_weights, get_top_styles
        weights = load_weights()
        top_styles = get_top_styles(3)
        # 把高权重类型优先排在候选池前面
        fresh_types = sorted(fresh_types, key=lambda t: weights.get(t, 1.0), reverse=True)
        # 如果高权重类型不在当前池，强制插入一个
        for ts in top_styles:
            if ts not in fresh_types and ts in available_types:
                fresh_types.insert(0, ts)
                break
    except:
        pass

    # 选择2-3个类型
    import random
    recommended_types = random.sample(fresh_types, min(3, len(fresh_types)))

    # 记录本次使用
    try:
        history_entry = {
            "timestamp": datetime.now().timestamp(),
            "types": recommended_types,
            "sentiment": sentiment_label
        }
        if os.path.exists(history_file):
            with open(history_file, "r") as f:
                history = json.load(f)
        else:
            history = []
        history.append(history_entry)
        # 只保留最近30条
        history = history[-30:]
        with open(history_file, "w") as f:
            json.dump(history, f)
    except:
        pass

    return {
        "top_topics": top_topics,
        "recommended_coins": high_conf_coins,
        "recommended_content_types": recommended_types,
        "sentiment_label": sentiment_label,
        "timing_window": timing["window"],
        "timing_multiplier": timing["multiplier"],
        "l0_hot_tags": l0_tags[:3] if l0_tags else [],
    }


def generate_headline_templates(strategy: dict, fused_coins: list, l0_hot_tags: list = None) -> list:
    """生成标题模板（v2改进版：强制注入L0热门标签）"""
    coins = strategy["recommended_coins"]
    coin1 = coins[0] if coins else "BTC"
    coin2 = coins[1] if len(coins) > 1 else "ETH"
    sentiment = strategy["sentiment_label"]
    hot_tags = strategy.get("l0_hot_tags", []) or l0_hot_tags or []

    templates = []

    # 基础模板（情绪驱动）
    if sentiment in ("极度恐惧", "偏空"):
        templates.extend([
            f"${coin1} 又跌了，但我看到了一个数据让我不敢做空",
            f"说实话，今天的行情让我想起了去年那次……",
            f"所有人都在恐慌，但智能钱正在悄悄买入 ${coin1}",
            f"${coin1} 跌到这个位置，我做了一个决定",
            f"恐惧贪婪指数到了极端值，历史上每次都是……",
        ])
    elif sentiment in ("极度贪婪", "偏多"):
        templates.extend([
            f"${coin1} 突破关键位了，但我没有追，原因是……",
            f"智能钱刚买了 ${coin2}，你要跟吗？",
            f"一个很多人没注意到的数据：${coin1} 的链上异动",
            f"${coin1} 涨了，但真正值得关注的是这个信号",
            f"今天赚了，但我更想聊聊我的止盈策略",
        ])
    else:
        templates.extend([
            f"${coin1} 在震荡，但链上数据告诉我方向已经定了",
            f"AI帮我分析了 ${coin1} 的走势，结果出乎意料",
            f"今天的行情很无聊？看看这个数据你就不这么想了",
            f"${coin2} 最近的社交热度暴涨，背后是什么？",
            f"我用AI跑了一遍今天的数据，发现了一个有趣的规律",
        ])

    # 强制注入L0热门标签（至少2个标题要蹭热点）
    if hot_tags:
        hot_tag = hot_tags[0]
        # 热点标签模板
        hot_templates = [
            f"为什么大家都在聊 #{hot_tag}？我的看法是……",
            f"#{hot_tag} 突然火了，但真正值得关注的是这个",
            f"关于 #{hot_tag}，我发现了几个关键数据",
            f"大家都在追 #{hot_tag}，但我想提醒一个风险",
            f"#{hot_tag} 热度第一，现在上车还来得及吗？",
        ]
        # 替换前2个模板为热点模板
        templates = hot_templates[:2] + templates[2:]

    return templates


# ---------------------------------------------------------------------------
# 6. 预言机总评分
# ---------------------------------------------------------------------------
def calculate_oracle_score(l0_report: dict, l1_report: dict, l2_report: dict,
                            l3_report: dict, l4_report: dict) -> dict:
    """计算预言机总评分（v2：返回总分+子分，支持 L4 缺失时动态权重）"""
    scores = {
        "L0_square": l0_report.get("square_score", 50),
        "L1_social": l1_report.get("social_score", 50),
        "L2_onchain": l2_report.get("anomaly_score", 50),
        "L3_market": l3_report.get("market_score", 50),
        "L4_news": l4_report.get("news_score", 50),
    }

    # 动态选择权重
    weights = _get_weights(l4_report)
    weighted_sum = sum(scores[k] * weights[k] for k in scores)
    total_score = max(0, min(100, round(weighted_sum)))

    # 计算子维度分（简化版）
    sub_scores = {
        "广场热度": scores["L0_square"],
        "社交情绪": scores["L1_social"],
        "链上异动": scores["L2_onchain"],
        "市场结构": scores["L3_market"],
        "新闻热度": scores["L4_news"],
    }

    return {
        "total": total_score,
        "sub_scores": sub_scores,
        "layer_scores": scores
    }


# ---------------------------------------------------------------------------
# 摘要
# ---------------------------------------------------------------------------
def generate_fusion_summary(oracle_score: int, fused_topics: list,
                             fused_coins: list, fused_sentiment: dict,
                             timing: dict, strategy: dict,
                             headlines: list, layer_scores: dict,
                             sub_scores: dict = None) -> str:
    """生成融合报告摘要"""
    lines = []
    tz_cn = timezone(timedelta(hours=8))
    now_str = datetime.now(tz_cn).strftime("%Y-%m-%d %H:%M")

    # 评级
    if oracle_score >= 75:
        rating = "流量爆发期"
    elif oracle_score >= 60:
        rating = "流量活跃期"
    elif oracle_score >= 45:
        rating = "流量平稳期"
    elif oracle_score >= 30:
        rating = "流量低迷期"
    else:
        rating = "流量冰点期"

    lines.append(f"## 币安广场流量预言机 ({now_str} UTC+8)")
    lines.append(f"**预言机评分: {oracle_score}/100 ({rating})**")
    lines.append("")

    # 各层评分
    lines.append("### 各层数据评分")
    for layer, score in layer_scores.items():
        bar = "█" * (score // 10) + "░" * (10 - score // 10)
        lines.append(f"- {layer}: {bar} {score}/100")
    lines.append("")

    # 融合情绪
    lines.append(f"### 综合市场情绪: **{fused_sentiment['label']}** ({fused_sentiment['fused_score']}/100)")
    lines.append(f"- {fused_sentiment['advice']}")
    lines.append("")

    # 热门话题
    if fused_topics:
        lines.append("### 融合话题排名 Top 5")
        for i, t in enumerate(fused_topics[:5], 1):
            lines.append(f"  {i}. {t['topic']} (融合分: {t['fusion_score']})")
        lines.append("")

    # 热门代币
    if fused_coins:
        lines.append("### 融合代币热度 Top 5")
        for c in fused_coins[:5]:
            sources = ", ".join(set(c["sources"]))
            lines.append(
                f"- **${c['symbol']}**: 融合分 {c['total_score']:.1f} | "
                f"确信度 {c.get('confidence', 'LOW')} | 来源: {sources}"
            )
        lines.append("")

    # 时机建议
    lines.append(f"### 发布时机: {timing['window']} (系数 x{timing['multiplier']})")
    lines.append(f"- {timing['description']}")
    lines.append(f"- 最佳时段: {', '.join(timing['best_times'])}")
    lines.append("")

    # 内容策略
    lines.append("### 内容策略建议")
    lines.append(f"- 推荐话题: {', '.join(strategy['top_topics'][:3])}")
    lines.append(f"- 推荐代币: {', '.join(['$' + c for c in strategy['recommended_coins'][:3]])}")
    lines.append(f"- 推荐内容类型: {', '.join(strategy['recommended_content_types'])}")
    lines.append("")

    # 标题模板
    if headlines:
        lines.append("### 标题模板推荐")
        for i, h in enumerate(headlines[:5], 1):
            lines.append(f"  {i}. {h}")
        lines.append("")

    # 写作规则提醒
    lines.append("### 写作规则 (humanizer-cn)")
    lines.append("- 禁用: 排比三段式 / 升华结尾 / 赋能/底层逻辑/干货")
    lines.append("- 禁用表情符号: 全文不使用任何 emoji，包括开头、结尾、强调符号（✅❌🔥💡📊等）")
    lines.append("- 必用: 具体数字 | 时间锚点 | 停顿句 | $BTC格式")
    lines.append("- 结构: 钩子(1句) → 背景(2-3句) → 转折(1句) → 结果(数字) → 开放结尾(问句)")
    lines.append("- 发布后30分钟主动互动触发推荐算法")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 主函数
# ---------------------------------------------------------------------------
def run_signal_fusion(l0_report: dict, l1_report: dict, l2_report: dict,
                       l3_report: dict, l4_report: dict) -> dict:
    """执行信号融合

    Args:
        l0_report: L0 广场监控报告
        l1_report: L1 社交热度报告
        l2_report: L2 链上异动报告
        l3_report: L3 行情分析报告
        l4_report: L4 新闻+KOL 报告

    Returns:
        fusion_report (dict)
    """
    # 1. 话题融合
    fused_topics = fuse_topics(l0_report, l1_report, l4_report)

    # 2. 代币融合
    fused_coins = fuse_coins(l0_report, l1_report, l2_report, l3_report, l4_report)

    # 3. 情绪融合
    fused_sentiment = fuse_sentiment(l1_report, l2_report, l3_report, l4_report)

    # 4. 时机评估
    timing = evaluate_timing()

    # 5. 内容策略（传入L0热门标签）
    l0_hot_hashtags = l0_report.get("hot_hashtags", [])
    strategy = generate_content_strategy(fused_topics, fused_coins, fused_sentiment, timing, l0_hot_hashtags)

    # 6. 标题模板（传入L0热门标签）
    headlines = generate_headline_templates(strategy, fused_coins, l0_hot_hashtags)

    # 7. 预言机评分（新版返回dict）
    oracle_score_result = calculate_oracle_score(l0_report, l1_report, l2_report, l3_report, l4_report)
    oracle_score = oracle_score_result["total"]
    sub_scores = oracle_score_result["sub_scores"]
    layer_scores_raw = oracle_score_result["layer_scores"]

    # 评级
    if oracle_score >= 75:
        rating = "流量爆发期"
    elif oracle_score >= 60:
        rating = "流量活跃期"
    elif oracle_score >= 45:
        rating = "流量平稳期"
    elif oracle_score >= 30:
        rating = "流量低迷期"
    else:
        rating = "流量冰点期"

    layer_scores = {
        "L0 广场热帖": l0_report.get("square_score", 50),
        "L1 社交热度": l1_report.get("social_score", 50),
        "L2 链上异动": l2_report.get("anomaly_score", 50),
        "L3 行情分析": l3_report.get("market_score", 50),
        "L4 新闻KOL": l4_report.get("news_score", 50),
    }

    summary = generate_fusion_summary(
        oracle_score, fused_topics, fused_coins, fused_sentiment,
        timing, strategy, headlines, layer_scores
    )

    report = {
        "oracle_score": oracle_score,
        "oracle_rating": rating,
        "layer_scores": layer_scores,
        "fused_topics": fused_topics,
        "fused_coins": fused_coins,
        "fused_sentiment": fused_sentiment,
        "timing_advice": timing,
        "content_strategy": strategy,
        "headline_templates": headlines,
        "fusion_summary": summary,
        "timestamp": int(time.time()),
    }

    return report
