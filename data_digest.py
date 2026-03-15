#!/usr/bin/env python3
"""
data_digest.py - 数据精简层 v1.0
================================================================
将 L0-L5 各层的海量原始数据提炼为精简的"核心情报简报"，
直接供 L7 文章生成引擎使用，避免原始 JSON 截断浪费。

输入：L0-L5 各层 report dict + Skills Hub combo_data
输出：core_digest dict（控制在 ~800 字符以内）
"""

import json


def build_core_digest(
    l0_report: dict = None,
    l1_report: dict = None,
    l2_report: dict = None,
    l3_report: dict = None,
    l4_report: dict = None,
    fusion_report: dict = None,
    skills_data: dict = None,
) -> dict:
    """
    从各层数据中提炼核心情报简报。

    Returns:
        dict: 精简的核心数据，包含情绪、代币、话题、行情、策略等关键信息。
    """
    l0 = l0_report or {}
    l1 = l1_report or {}
    l2 = l2_report or {}
    l3 = l3_report or {}
    l4 = l4_report or {}
    fusion = fusion_report or {}
    skills = skills_data or {}

    digest = {}

    # ---- 1. 情绪摘要（优先用 L5 融合结果）----
    fused_sentiment = fusion.get("fused_sentiment", {})
    if fused_sentiment:
        digest["sentiment"] = {
            "label": fused_sentiment.get("label", "中性"),
            "score": fused_sentiment.get("fused_score", 50),
            "advice": fused_sentiment.get("advice", ""),
        }
    else:
        # 回退：从 L3 提取
        fg = l3.get("fear_greed", {})
        digest["sentiment"] = {
            "label": fg.get("value_classification", "中性"),
            "score": int(fg.get("value", 50)),
            "advice": "",
        }

    # ---- 2. 热门代币 Top 5（优先用 L5 融合结果）----
    fused_coins = fusion.get("fused_coins", [])
    if fused_coins:
        digest["top_coins"] = []
        for c in fused_coins[:5]:
            coin_info = {
                "symbol": c.get("symbol", ""),
                "confidence": c.get("confidence", "LOW"),
                "sources": len(set(c.get("sources", []))),
            }
            # 附加关键细节
            details = c.get("details", {})
            if details.get("change_24h"):
                coin_info["change_24h"] = details["change_24h"]
            if details.get("onchain_direction"):
                coin_info["smart_money"] = details["onchain_direction"]
            if details.get("net_inflow"):
                coin_info["net_inflow"] = round(details["net_inflow"], 2)
            digest["top_coins"].append(coin_info)
    else:
        # 回退：从 L0 mentioned_coins 提取
        mentioned = l0.get("mentioned_coins", [])
        digest["top_coins"] = [
            {"symbol": sym, "mentions": cnt}
            for sym, cnt in (mentioned[:5] if mentioned else [])
        ]

    # ---- 3. 热门话题 Top 3（优先用 L5 融合结果）----
    fused_topics = fusion.get("fused_topics", [])
    if fused_topics:
        digest["top_topics"] = [
            t.get("topic", "") for t in fused_topics[:3]
        ]
    else:
        # 回退：从 L0 content_categories 提取
        categories = l0.get("content_categories", {})
        if categories:
            sorted_cats = sorted(categories.items(), key=lambda x: x[1], reverse=True)
            digest["top_topics"] = [cat for cat, _ in sorted_cats[:3]]
        else:
            digest["top_topics"] = []

    # ---- 4. 行情快照（从 L3 或 skills_data 提取）----
    market_snapshot = {}
    # BTC 价格
    btc_ticker = l3.get("btc_ticker", {})
    if btc_ticker:
        market_snapshot["BTC"] = {
            "price": btc_ticker.get("lastPrice", ""),
            "change_24h": btc_ticker.get("priceChangePercent", ""),
        }
    # ETH 价格
    eth_ticker = l3.get("eth_ticker", {})
    if eth_ticker:
        market_snapshot["ETH"] = {
            "price": eth_ticker.get("lastPrice", ""),
            "change_24h": eth_ticker.get("priceChangePercent", ""),
        }
    # 从 skills_data 补充现货行情
    spot_tickers = skills.get("spot_tickers", {})
    for sym in ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"]:
        ticker = spot_tickers.get(sym, {})
        if ticker and sym[:3] not in market_snapshot:
            base = sym.replace("USDT", "")
            market_snapshot[base] = {
                "price": ticker.get("lastPrice", ""),
                "change_24h": ticker.get("priceChangePercent", ""),
            }
    if market_snapshot:
        digest["market_snapshot"] = market_snapshot

    # ---- 5. 链上信号摘要（从 L2 或 skills_data 提取）----
    smart_signals = l2.get("smart_money_signals", [])
    if smart_signals:
        buys = [s.get("ticker", "") for s in smart_signals if s.get("direction") == "buy"][:3]
        sells = [s.get("ticker", "") for s in smart_signals if s.get("direction") == "sell"][:3]
        digest["onchain"] = {}
        if buys:
            digest["onchain"]["smart_money_buying"] = buys
        if sells:
            digest["onchain"]["smart_money_selling"] = sells

    # ---- 6. 内容策略建议（从 L5 提取）----
    strategy = fusion.get("content_strategy", {})
    if strategy:
        digest["strategy"] = {
            "content_types": strategy.get("recommended_content_types", [])[:2],
            "recommended_coins": ["$" + c for c in strategy.get("recommended_coins", [])[:3]],
        }

    # ---- 7. 预言机评分 ----
    oracle_score = fusion.get("oracle_score")
    if oracle_score is not None:
        digest["oracle_score"] = oracle_score
        digest["oracle_rating"] = fusion.get("oracle_rating", "")

    # ---- 8. 发布时机 ----
    timing = fusion.get("timing_advice", {})
    if timing:
        digest["timing"] = timing.get("window", "")

    return digest


def digest_to_text(digest: dict) -> str:
    """
    将 core_digest 转换为简洁的自然语言文本，直接供 LLM 使用。

    Returns:
        str: 精简的情报简报文本（约 500-800 字符）
    """
    lines = []

    # 情绪
    s = digest.get("sentiment", {})
    if s:
        lines.append(f"市场情绪：{s.get('label', '中性')}（{s.get('score', 50)}/100）。{s.get('advice', '')}")

    # 行情快照
    ms = digest.get("market_snapshot", {})
    if ms:
        parts = []
        for sym, info in ms.items():
            price = info.get("price", "")
            change = info.get("change_24h", "")
            if price:
                parts.append(f"${sym} {price}" + (f"（{change}%）" if change else ""))
        if parts:
            lines.append("行情：" + "，".join(parts))

    # 热门代币
    coins = digest.get("top_coins", [])
    if coins:
        coin_parts = []
        for c in coins:
            sym = c.get("symbol", "")
            conf = c.get("confidence", "")
            extra = ""
            if c.get("smart_money"):
                extra = f"聪明钱{c['smart_money']}"
            elif c.get("change_24h"):
                extra = f"24h {c['change_24h']}%"
            coin_parts.append(f"${sym}（{conf}" + (f"，{extra}" if extra else "") + "）")
        lines.append("热门代币：" + "、".join(coin_parts))

    # 热门话题
    topics = digest.get("top_topics", [])
    if topics:
        lines.append("热门话题：" + "、".join(topics))

    # 链上信号
    onchain = digest.get("onchain", {})
    if onchain:
        parts = []
        buying = onchain.get("smart_money_buying", [])
        selling = onchain.get("smart_money_selling", [])
        if buying:
            parts.append(f"聪明钱在买：{'、'.join(['$' + b for b in buying])}")
        if selling:
            parts.append(f"聪明钱在卖：{'、'.join(['$' + s for s in selling])}")
        if parts:
            lines.append("链上信号：" + "；".join(parts))

    # 策略
    strat = digest.get("strategy", {})
    if strat:
        types = strat.get("content_types", [])
        rec_coins = strat.get("recommended_coins", [])
        parts = []
        if types:
            parts.append(f"推荐内容类型：{'、'.join(types)}")
        if rec_coins:
            parts.append(f"推荐代币：{'、'.join(rec_coins)}")
        if parts:
            lines.append("策略：" + "；".join(parts))

    # 预言机评分
    score = digest.get("oracle_score")
    if score is not None:
        lines.append(f"预言机评分：{score}/100（{digest.get('oracle_rating', '')}）")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 测试
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # 模拟数据
    mock_fusion = {
        "oracle_score": 72,
        "oracle_rating": "流量活跃期",
        "fused_sentiment": {"label": "偏多", "fused_score": 62, "advice": "市场偏暖，适合发布行情分析"},
        "fused_coins": [
            {"symbol": "BTC", "confidence": "HIGH", "sources": ["L0", "L1", "L3"], "details": {"change_24h": "2.5"}},
            {"symbol": "SOL", "confidence": "MEDIUM", "sources": ["L1", "L2"], "details": {"onchain_direction": "buy"}},
            {"symbol": "PEPE", "confidence": "LOW", "sources": ["L1"], "details": {}},
        ],
        "fused_topics": [
            {"topic": "Layer2", "fusion_score": 85},
            {"topic": "RWA", "fusion_score": 72},
            {"topic": "#BTC", "fusion_score": 65},
        ],
        "content_strategy": {
            "recommended_content_types": ["行情分析", "操作记录"],
            "recommended_coins": ["BTC", "SOL", "ETH"],
        },
        "timing_advice": {"window": "晚间黄金期"},
    }

    digest = build_core_digest(fusion_report=mock_fusion)
    print("=== Core Digest ===")
    print(json.dumps(digest, indent=2, ensure_ascii=False))
    print(f"\nJSON 长度: {len(json.dumps(digest, ensure_ascii=False))} 字符")

    print("\n=== Text Digest ===")
    text = digest_to_text(digest)
    print(text)
    print(f"\n文本长度: {len(text)} 字符")
