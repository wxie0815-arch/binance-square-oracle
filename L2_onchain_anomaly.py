#!/usr/bin/env python3
"""
L2 链上异动监控模块 (On-Chain Anomaly Monitor)
================================================================
数据源（全部使用币安官方 API，无需认证）：
  1. Smart Money Trading Signals  — 智能钱买卖信号
  2. Smart Money Inflow Rank      — 智能钱净流入排名
  3. Meme Rush (Topic Rush)       — AI 热点话题 + 关联代币
  4. Token Security Audit         — 代币安全审计（辅助验证）

输出：on_chain_anomaly_report (dict)
  - smart_money_signals: 最新智能钱信号列表
  - smart_money_inflow:  智能钱净流入 Top 代币
  - topic_rush:          AI 热点话题及关联代币
  - whale_alerts:        巨鲸异动摘要
  - anomaly_score:       综合链上异动评分 (0-100)
  - anomaly_summary:     中文摘要
"""

import json
import time
import uuid
import requests
from data_cache import cached
from datetime import datetime, timezone, timedelta

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
HEADERS_JSON = {
    "Content-Type": "application/json",
    "Accept-Encoding": "identity",
}
HEADERS_GET = {"Accept-Encoding": "identity"}

BSC_CHAIN = "56"
SOL_CHAIN = "CT_501"
BASE_CHAIN = "8453"

ICON_PREFIX = "https://bin.bnbstatic.com"

# ---------------------------------------------------------------------------
# 1. Smart Money Trading Signals
# ---------------------------------------------------------------------------
@cached(category="onchain_data")
def fetch_smart_money_signals(chain_id: str = SOL_CHAIN, page_size: int = 50) -> list:
    """获取智能钱买卖信号"""
    url = "https://web3.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/web/signal/smart-money"
    payload = {
        "smartSignalType": "",
        "page": 1,
        "pageSize": page_size,
        "chainId": chain_id,
    }
    try:
        resp = requests.post(url, json=payload, headers=HEADERS_JSON, timeout=15)
        data = resp.json()
        if data.get("success") and data.get("data"):
            return data["data"]
    except Exception as e:
        print(f"[L2] Smart Money Signals 请求失败: {e}")
    return []


def parse_smart_money_signals(raw_signals: list) -> list:
    """解析智能钱信号，提取关键字段"""
    parsed = []
    now_ms = int(time.time() * 1000)
    for s in raw_signals:
        # 只关注活跃信号或最近 4 小时内的信号
        trigger_time = s.get("signalTriggerTime", 0)
        if now_ms - trigger_time > 4 * 3600 * 1000 and s.get("status") != "active":
            continue

        signal = {
            "signal_id": s.get("signalId"),
            "ticker": s.get("ticker", "UNKNOWN"),
            "chain_id": s.get("chainId"),
            "contract": s.get("contractAddress", ""),
            "direction": s.get("direction", ""),  # buy / sell
            "smart_money_count": s.get("smartMoneyCount", 0),
            "alert_price": float(s.get("alertPrice", 0)),
            "current_price": float(s.get("currentPrice", 0)),
            "max_gain_pct": float(s.get("maxGain", 0)),
            "exit_rate": s.get("exitRate", 0),
            "status": s.get("status", ""),
            "signal_count": s.get("signalCount", 0),
            "trigger_time": trigger_time,
            "is_alpha": s.get("isAlpha", False),
            "launch_platform": s.get("launchPlatform", ""),
        }
        # 计算价格变化
        if signal["alert_price"] > 0:
            signal["price_change_pct"] = round(
                (signal["current_price"] - signal["alert_price"])
                / signal["alert_price"]
                * 100,
                2,
            )
        else:
            signal["price_change_pct"] = 0

        parsed.append(signal)

    # 按 smart_money_count 降序
    parsed.sort(key=lambda x: x["smart_money_count"], reverse=True)
    return parsed


# ---------------------------------------------------------------------------
# 2. Smart Money Inflow Rank
# ---------------------------------------------------------------------------
@cached(category="onchain_data")
def fetch_smart_money_inflow(chain_id: str = SOL_CHAIN, period: str = "24h") -> list:
    """获取智能钱净流入代币排名"""
    url = "https://web3.binance.com/bapi/defi/v1/public/wallet-direct/tracker/wallet/token/inflow/rank/query"
    payload = {
        "chainId": chain_id,
        "period": period,
        "tagType": 2,
    }
    try:
        resp = requests.post(url, json=payload, headers=HEADERS_JSON, timeout=15)
        data = resp.json()
        if data.get("success") and data.get("data"):
            return data["data"]
    except Exception as e:
        print(f"[L2] Smart Money Inflow 请求失败: {e}")
    return []


def parse_inflow_rank(raw_data: list, top_n: int = 15) -> list:
    """解析智能钱净流入排名"""
    parsed = []
    for item in raw_data[:top_n]:
        token = {
            "symbol": item.get("tokenName", "UNKNOWN"),
            "contract": item.get("ca", ""),
            "price": item.get("price", "0"),
            "market_cap": item.get("marketCap", "0"),
            "inflow_usd": float(item.get("inflow", 0)),
            "traders": item.get("traders", 0),
            "price_change_pct": item.get("priceChangeRate", "0"),
            "volume": item.get("volume", "0"),
            "holders": item.get("holders", "0"),
            "risk_level": item.get("tokenRiskLevel", -1),
        }
        parsed.append(token)
    # 按净流入降序
    parsed.sort(key=lambda x: x["inflow_usd"], reverse=True)
    return parsed


# ---------------------------------------------------------------------------
# 3. Topic Rush (AI 热点话题)
# ---------------------------------------------------------------------------
@cached(category="onchain_data")
def fetch_topic_rush(chain_id: str = SOL_CHAIN, rank_type: int = 30) -> list:
    """获取 AI 热点话题及关联代币
    rank_type: 10=Latest, 20=Rising, 30=Viral
    """
    url = "https://web3.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/market/token/social-rush/rank/list"
    params = {
        "chainId": chain_id,
        "rankType": rank_type,
        "sort": 30 if rank_type == 30 else 10,
        "asc": "false",
    }
    try:
        resp = requests.get(url, params=params, headers=HEADERS_GET, timeout=15)
        data = resp.json()
        if data.get("success") and data.get("data"):
            return data["data"]
    except Exception as e:
        print(f"[L2] Topic Rush 请求失败: {e}")
    return []


def parse_topic_rush(raw_topics: list, top_n: int = 10) -> list:
    """解析热点话题"""
    parsed = []
    for t in raw_topics[:top_n]:
        name_obj = t.get("name", {})
        topic = {
            "topic_id": t.get("topicId", ""),
            "name_en": name_obj.get("topicNameEn", ""),
            "name_cn": name_obj.get("topicNameCn", ""),
            "type": t.get("type", ""),
            "net_inflow": t.get("topicNetInflow", "0"),
            "net_inflow_1h": t.get("topicNetInflow1h", "0"),
            "net_inflow_ath": t.get("topicNetInflowAth", "0"),
            "token_count": t.get("tokenSize", 0),
            "topic_link": t.get("topicLink", ""),
            "ai_summary": t.get("aiSummary", {}),
            "tokens": [],
        }
        for tk in t.get("tokenList", [])[:5]:
            topic["tokens"].append({
                "symbol": tk.get("symbol", ""),
                "contract": tk.get("contractAddress", ""),
                "market_cap": tk.get("marketCap", "0"),
                "price_change_24h": tk.get("priceChange24h", "0"),
                "net_inflow": tk.get("netInflow", "0"),
                "holders": tk.get("holders", 0),
            })
        parsed.append(topic)
    return parsed


# ---------------------------------------------------------------------------
# 4. Token Security Audit (辅助验证)
# ---------------------------------------------------------------------------
@cached(category="onchain_data")
def audit_token(chain_id: str, contract_address: str) -> dict:
    """对单个代币进行安全审计"""
    url = "https://web3.binance.com/bapi/defi/v1/public/wallet-direct/security/token/audit"
    payload = {
        "binanceChainId": chain_id,
        "contractAddress": contract_address,
        "requestId": str(uuid.uuid4()),
    }
    try:
        resp = requests.post(url, json=payload, headers=HEADERS_JSON, timeout=10)
        data = resp.json()
        if data.get("success") and data.get("data"):
            d = data["data"]
            return {
                "has_result": d.get("hasResult", False),
                "risk_level": d.get("riskLevelEnum", "UNKNOWN"),
                "risk_num": d.get("riskLevel", -1),
                "buy_tax": d.get("extraInfo", {}).get("buyTax", "N/A"),
                "sell_tax": d.get("extraInfo", {}).get("sellTax", "N/A"),
            }
    except Exception as e:
        print(f"[L2] Token Audit 请求失败: {e}")
    return {"has_result": False, "risk_level": "UNKNOWN", "risk_num": -1}


# ---------------------------------------------------------------------------
# 5. 巨鲸异动检测
# ---------------------------------------------------------------------------
def detect_whale_alerts(signals: list, inflow_data: list) -> list:
    """从智能钱信号和流入数据中提取巨鲸异动"""
    whale_alerts = []

    # 从信号中提取大额买入
    for s in signals:
        if s["smart_money_count"] >= 3 and s["direction"] == "buy":
            whale_alerts.append({
                "type": "SMART_MONEY_BUY",
                "ticker": s["ticker"],
                "detail": f"{s['smart_money_count']}个智能钱地址买入，最大涨幅{s['max_gain_pct']}%",
                "severity": "HIGH" if s["smart_money_count"] >= 5 else "MEDIUM",
            })
        elif s["direction"] == "sell" and s["exit_rate"] > 50:
            whale_alerts.append({
                "type": "SMART_MONEY_SELL",
                "ticker": s["ticker"],
                "detail": f"智能钱退出率{s['exit_rate']}%，当前价格变化{s['price_change_pct']}%",
                "severity": "HIGH",
            })

    # 从流入数据中提取异常流入
    for item in inflow_data:
        if item["inflow_usd"] > 50000:
            whale_alerts.append({
                "type": "MASSIVE_INFLOW",
                "ticker": item["symbol"],
                "detail": f"智能钱净流入${item['inflow_usd']:,.0f}，{item['traders']}个地址参与",
                "severity": "HIGH" if item["inflow_usd"] > 200000 else "MEDIUM",
            })

    return whale_alerts


# ---------------------------------------------------------------------------
# 6. 综合链上异动评分
# ---------------------------------------------------------------------------
def calculate_anomaly_score(signals: list, inflow: list, topics: list, whale_alerts: list) -> int:
    """计算综合链上异动评分 (0-100)"""
    score = 0

    # 活跃信号数量 (max 25)
    active_signals = [s for s in signals if s.get("status") == "active"]
    score += min(len(active_signals) * 3, 25)

    # 高 smart_money_count 信号 (max 15)
    high_sm = [s for s in signals if s["smart_money_count"] >= 5]
    score += min(len(high_sm) * 5, 15)

    # 智能钱净流入总额 (max 20)
    total_inflow = sum(item["inflow_usd"] for item in inflow)
    if total_inflow > 1000000:
        score += 20
    elif total_inflow > 500000:
        score += 15
    elif total_inflow > 100000:
        score += 10
    elif total_inflow > 50000:
        score += 5

    # 热点话题数量 (max 15)
    score += min(len(topics) * 2, 15)

    # 巨鲸异动 (max 15)
    high_alerts = [a for a in whale_alerts if a["severity"] == "HIGH"]
    score += min(len(high_alerts) * 5, 15)

    # 卖出信号比例惩罚 (max -10)
    sell_signals = [s for s in signals if s["direction"] == "sell"]
    if len(signals) > 0:
        sell_ratio = len(sell_signals) / len(signals)
        if sell_ratio > 0.6:
            score -= 10
        elif sell_ratio > 0.4:
            score -= 5

    return max(0, min(100, score))


# ---------------------------------------------------------------------------
# 7. 生成中文摘要
# ---------------------------------------------------------------------------
def generate_anomaly_summary(signals: list, inflow: list, topics: list,
                              whale_alerts: list, score: int) -> str:
    """生成链上异动中文摘要"""
    lines = []
    tz_cn = timezone(timedelta(hours=8))
    now_str = datetime.now(tz_cn).strftime("%Y-%m-%d %H:%M")

    lines.append(f"## L2 链上异动报告 ({now_str} UTC+8)")
    lines.append(f"**异动评分: {score}/100**")
    lines.append("")

    # 智能钱信号摘要
    if signals:
        buy_signals = [s for s in signals if s["direction"] == "buy"]
        sell_signals = [s for s in signals if s["direction"] == "sell"]
        lines.append(f"### 智能钱信号")
        lines.append(f"买入信号 {len(buy_signals)} 个 | 卖出信号 {len(sell_signals)} 个")
        if buy_signals:
            top3 = buy_signals[:3]
            for s in top3:
                lines.append(
                    f"- **{s['ticker']}** ({s['chain_id']}): "
                    f"{s['smart_money_count']}个地址{s['direction']}，"
                    f"涨幅{s['max_gain_pct']}%，退出率{s['exit_rate']}%"
                )
        lines.append("")

    # 智能钱流入 Top 5
    if inflow:
        lines.append("### 智能钱净流入 Top 5")
        for item in inflow[:5]:
            lines.append(
                f"- **{item['symbol']}**: 净流入${item['inflow_usd']:,.0f}，"
                f"{item['traders']}个地址，价格变化{item['price_change_pct']}%"
            )
        lines.append("")

    # 热点话题
    if topics:
        lines.append("### AI 热点话题")
        for t in topics[:5]:
            name = t["name_cn"] or t["name_en"]
            lines.append(
                f"- **{name}**: 净流入${float(t['net_inflow']):,.0f}，"
                f"关联{t['token_count']}个代币"
            )
        lines.append("")

    # 巨鲸异动
    if whale_alerts:
        lines.append("### 巨鲸异动预警")
        for a in whale_alerts[:5]:
            emoji = "🔴" if a["severity"] == "HIGH" else "🟡"
            lines.append(f"- {emoji} **{a['ticker']}** [{a['type']}]: {a['detail']}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 主函数
# ---------------------------------------------------------------------------
def run_onchain_anomaly(chains: list = None) -> dict:
    """执行完整的链上异动监控

    Args:
        chains: 要监控的链列表，默认 [SOL_CHAIN, BSC_CHAIN]

    Returns:
        on_chain_anomaly_report (dict)
    """
    if chains is None:
        chains = [SOL_CHAIN, BSC_CHAIN]

    all_signals = []
    all_inflow = []
    all_topics = []

    for chain in chains:
        # 1. 智能钱信号
        raw_signals = fetch_smart_money_signals(chain_id=chain)
        parsed_signals = parse_smart_money_signals(raw_signals)
        all_signals.extend(parsed_signals)

        # 2. 智能钱净流入
        raw_inflow = fetch_smart_money_inflow(chain_id=chain)
        parsed_inflow = parse_inflow_rank(raw_inflow)
        all_inflow.extend(parsed_inflow)

        # 3. 热点话题（Viral + Rising）
        for rt in [30, 20]:
            raw_topics = fetch_topic_rush(chain_id=chain, rank_type=rt)
            parsed_topics = parse_topic_rush(raw_topics)
            all_topics.extend(parsed_topics)

    # 4. 巨鲸异动检测
    whale_alerts = detect_whale_alerts(all_signals, all_inflow)

    # 5. 综合评分
    anomaly_score = calculate_anomaly_score(
        all_signals, all_inflow, all_topics, whale_alerts
    )

    # 6. 生成摘要
    summary = generate_anomaly_summary(
        all_signals, all_inflow, all_topics, whale_alerts, anomaly_score
    )

    report = {
        "smart_money_signals": all_signals[:20],
        "smart_money_inflow": all_inflow[:15],
        "topic_rush": all_topics[:10],
        "whale_alerts": whale_alerts,
        "anomaly_score": anomaly_score,
        "anomaly_summary": summary,
        "timestamp": int(time.time()),
        "chains_monitored": chains,
    }

    return report


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("[L2] 链上异动监控启动...")
    report = run_onchain_anomaly()
    print(report["anomaly_summary"])
    print(f"\n[L2] 异动评分: {report['anomaly_score']}/100")
    print(f"[L2] 智能钱信号: {len(report['smart_money_signals'])} 条")
    print(f"[L2] 净流入代币: {len(report['smart_money_inflow'])} 个")
    print(f"[L2] 热点话题: {len(report['topic_rush'])} 个")
    print(f"[L2] 巨鲸预警: {len(report['whale_alerts'])} 条")

    # 保存报告
    with open("/tmp/L2_onchain_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)
    print("[L2] 报告已保存至 /tmp/L2_onchain_report.json")
