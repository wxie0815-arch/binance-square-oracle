#!/usr/bin/env python3
"""
fact_checker.py - 增强版事实校验模块 v1.0
================================================================
功能：
  - 多代币价格校验（BTC/ETH/BNB/SOL 等 15+ 代币）
  - 涨跌幅偏差检测
  - 市值排名校验
  - 恐贪指数一致性检查
  - 日期/时间准确性校验
  - 数据自洽性检查（文中数据前后矛盾）
  - 校验报告生成

使用：
    from fact_checker import FactChecker
    checker = FactChecker()
    report = checker.check(article_text, oracle_result)
"""

import re
import time
from datetime import datetime, timezone, timedelta

CST = timezone(timedelta(hours=8))

# 主流代币列表（用于价格校验）
MAJOR_TOKENS = {
    "BTC": {"min_price": 10000, "max_price": 500000, "aliases": ["比特币", "Bitcoin"]},
    "ETH": {"min_price": 500, "max_price": 50000, "aliases": ["以太坊", "Ethereum"]},
    "BNB": {"min_price": 50, "max_price": 5000, "aliases": ["币安币"]},
    "SOL": {"min_price": 5, "max_price": 2000, "aliases": ["Solana"]},
    "XRP": {"min_price": 0.1, "max_price": 50, "aliases": ["瑞波"]},
    "DOGE": {"min_price": 0.01, "max_price": 10, "aliases": ["狗狗币", "Dogecoin"]},
    "ADA": {"min_price": 0.05, "max_price": 20, "aliases": ["Cardano"]},
    "AVAX": {"min_price": 5, "max_price": 500, "aliases": ["Avalanche"]},
    "DOT": {"min_price": 1, "max_price": 200, "aliases": ["波卡", "Polkadot"]},
    "LINK": {"min_price": 1, "max_price": 200, "aliases": ["Chainlink"]},
    "SUI": {"min_price": 0.1, "max_price": 100, "aliases": []},
    "PEPE": {"min_price": 0, "max_price": 0.01, "aliases": []},
    "ARB": {"min_price": 0.1, "max_price": 50, "aliases": ["Arbitrum"]},
    "OP": {"min_price": 0.1, "max_price": 50, "aliases": ["Optimism"]},
    "NEAR": {"min_price": 0.5, "max_price": 100, "aliases": []},
    "MATIC": {"min_price": 0.1, "max_price": 20, "aliases": ["Polygon"]},
}

# 涨跌幅合理范围
PRICE_CHANGE_LIMITS = {
    "1h": 15,     # 1小时内涨跌幅不超过 15%
    "24h": 50,    # 24小时内涨跌幅不超过 50%
    "7d": 100,    # 7天内涨跌幅不超过 100%
}


class FactChecker:
    """增强版事实校验器"""

    def __init__(self, tolerance: float = 0.05):
        """
        Args:
            tolerance: 价格偏差容忍度（默认 5%）
        """
        self.tolerance = tolerance
        self.checks_run = 0
        self.issues_found = 0

    def check(self, article: str, oracle_result: dict = None) -> dict:
        """
        执行全面事实校验

        Args:
            article: 文章文本
            oracle_result: 预言机运行结果（含各层数据）

        Returns:
            dict: {
                "passed": bool,
                "score": int (0-100),
                "issues": list,
                "warnings": list,
                "checks_run": int,
                "summary": str,
            }
        """
        issues = []
        warnings = []
        self.checks_run = 0

        # 提取参考数据
        ref_data = self._extract_reference_data(oracle_result) if oracle_result else {}

        # 1. 多代币价格校验
        price_issues = self._check_token_prices(article, ref_data)
        issues.extend(price_issues)

        # 2. 涨跌幅合理性校验
        change_issues = self._check_price_changes(article)
        issues.extend(change_issues)

        # 3. 恐贪指数校验
        fg_issues = self._check_fear_greed(article, ref_data)
        issues.extend(fg_issues)

        # 4. 日期时间校验
        date_warnings = self._check_dates(article)
        warnings.extend(date_warnings)

        # 5. 数据自洽性校验
        consistency_issues = self._check_data_consistency(article)
        warnings.extend(consistency_issues)

        # 6. 市值排名校验
        rank_issues = self._check_market_cap_rank(article)
        warnings.extend(rank_issues)

        # 7. 百分比合理性校验
        pct_issues = self._check_percentages(article)
        warnings.extend(pct_issues)

        # 计算评分
        total_checks = max(self.checks_run, 1)
        issue_penalty = len(issues) * 15 + len(warnings) * 5
        score = max(0, min(100, 100 - issue_penalty))

        passed = len(issues) == 0
        summary = self._generate_summary(issues, warnings, score)

        return {
            "passed": passed,
            "score": score,
            "issues": issues,
            "warnings": warnings,
            "checks_run": self.checks_run,
            "summary": summary,
        }

    def _extract_reference_data(self, oracle_result: dict) -> dict:
        """从预言机结果中提取参考数据"""
        ref = {}
        layers = oracle_result.get("layer_reports", {})

        # L3 行情数据
        l3 = layers.get("L3_market_analysis", {})
        btc_analysis = l3.get("btc_analysis", {})
        if btc_analysis.get("current_price"):
            ref["BTC_price"] = float(btc_analysis["current_price"])
        if btc_analysis.get("price_change_pct"):
            ref["BTC_change_24h"] = float(btc_analysis["price_change_pct"])

        # 恐贪指数
        fg = l3.get("fear_greed_index") or l3.get("fear_greed", {}).get("value")
        if fg:
            ref["fear_greed"] = int(fg)

        # L5 融合数据
        l5 = layers.get("L5_signal_fusion", {})
        ref["oracle_score"] = l5.get("oracle_score", 50)

        # Skills Hub 数据中的代币价格
        for key in ["spot_tickers", "trending_tokens"]:
            tickers = oracle_result.get(key, [])
            if not tickers and layers:
                for lk, lv in layers.items():
                    if isinstance(lv, dict):
                        tickers = lv.get(key, [])
                        if tickers:
                            break
            for t in (tickers or []):
                if isinstance(t, dict):
                    symbol = t.get("symbol", "").replace("USDT", "")
                    price = t.get("lastPrice") or t.get("price")
                    if symbol and price:
                        try:
                            ref[f"{symbol}_price"] = float(price)
                        except (ValueError, TypeError):
                            pass

        return ref

    def _check_token_prices(self, article: str, ref_data: dict) -> list:
        """校验文中提到的代币价格"""
        issues = []

        for token, info in MAJOR_TOKENS.items():
            self.checks_run += 1

            # 查找文中提到的价格
            patterns = [
                rf'\${token}\s*[：:价格为约]*\s*\$?([\d,]+\.?\d*)',
                rf'{token}\s*(?:价格|现价|报价)[：:为约]*\s*\$?([\d,]+\.?\d*)',
                rf'{token}/USDT[：:]*\s*\$?([\d,]+\.?\d*)',
            ]
            for alias in info["aliases"]:
                patterns.append(rf'{alias}[：:价格为约]*\s*\$?([\d,]+\.?\d*)')

            for pattern in patterns:
                matches = re.findall(pattern, article, re.IGNORECASE)
                for match in matches:
                    try:
                        mentioned_price = float(match.replace(",", ""))
                        if mentioned_price == 0:
                            continue

                        # 与参考数据对比
                        ref_price = ref_data.get(f"{token}_price")
                        if ref_price:
                            deviation = abs(mentioned_price - ref_price) / ref_price
                            if deviation > self.tolerance:
                                issues.append(
                                    f"${token} 价格偏差: 文中 ${mentioned_price:,.2f} "
                                    f"vs 实际 ${ref_price:,.2f} (偏差 {deviation:.1%})"
                                )

                        # 与合理范围对比
                        if mentioned_price < info["min_price"] or mentioned_price > info["max_price"]:
                            issues.append(
                                f"${token} 价格异常: ${mentioned_price:,.2f} "
                                f"(合理范围: ${info['min_price']:,.2f} - ${info['max_price']:,.2f})"
                            )
                    except (ValueError, TypeError):
                        pass

        return issues

    def _check_price_changes(self, article: str) -> list:
        """校验涨跌幅合理性"""
        issues = []
        self.checks_run += 1

        # 匹配百分比变化
        patterns = [
            r'(?:涨|跌|上涨|下跌|涨幅|跌幅|变化)[了约为：:]*\s*([\d.]+)\s*%',
            r'([\d.]+)\s*%\s*(?:的涨幅|的跌幅|涨幅|跌幅)',
            r'[+-]?([\d.]+)\s*%',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, article)
            for match in matches:
                try:
                    pct = float(match)
                    # 24h 涨跌幅超过 50% 的标记为可疑
                    if pct > PRICE_CHANGE_LIMITS["24h"]:
                        issues.append(f"涨跌幅异常: {pct}% (24h 通常不超过 {PRICE_CHANGE_LIMITS['24h']}%)")
                except (ValueError, TypeError):
                    pass

        return issues

    def _check_fear_greed(self, article: str, ref_data: dict) -> list:
        """校验恐贪指数"""
        issues = []
        self.checks_run += 1

        ref_fg = ref_data.get("fear_greed")
        if not ref_fg:
            return issues

        # 查找文中的恐贪指数
        patterns = [
            r'恐(?:惧|贪)(?:指数|指标)[：:为约]*\s*(\d+)',
            r'Fear\s*(?:&|and)\s*Greed[：:]*\s*(\d+)',
            r'FGI[：:]*\s*(\d+)',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, article, re.IGNORECASE)
            for match in matches:
                try:
                    mentioned_fg = int(match)
                    if abs(mentioned_fg - ref_fg) > 10:
                        issues.append(
                            f"恐贪指数偏差: 文中 {mentioned_fg} vs 实际 {ref_fg} "
                            f"(偏差 {abs(mentioned_fg - ref_fg)})"
                        )
                    # 范围校验
                    if mentioned_fg < 0 or mentioned_fg > 100:
                        issues.append(f"恐贪指数范围错误: {mentioned_fg} (应为 0-100)")
                except (ValueError, TypeError):
                    pass

        return issues

    def _check_dates(self, article: str) -> list:
        """校验日期准确性"""
        warnings = []
        self.checks_run += 1

        now = datetime.now(CST)
        current_year = now.year
        current_month = now.month

        # 查找年份
        years = re.findall(r'(\d{4})年', article)
        for y in years:
            year = int(y)
            if year > current_year + 1 or year < 2009:  # 比特币诞生于2009年
                warnings.append(f"日期可疑: {year}年 (当前 {current_year}年)")

        # 查找完整日期
        dates = re.findall(r'(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})', article)
        for y, m, d in dates:
            try:
                mentioned_date = datetime(int(y), int(m), int(d))
                diff = abs((now - mentioned_date).days)
                if diff > 365:
                    warnings.append(f"日期距今较远: {y}-{m}-{d} (距今 {diff} 天)")
            except ValueError:
                warnings.append(f"无效日期: {y}-{m}-{d}")

        return warnings

    def _check_data_consistency(self, article: str) -> list:
        """检查数据自洽性"""
        warnings = []
        self.checks_run += 1

        # 检查同一代币是否出现矛盾描述
        contradictions = [
            (r'\$BTC\s*(?:上涨|涨)', r'\$BTC\s*(?:下跌|跌)', "BTC 涨跌描述矛盾"),
            (r'\$ETH\s*(?:上涨|涨)', r'\$ETH\s*(?:下跌|跌)', "ETH 涨跌描述矛盾"),
            (r'市场.*?看涨|牛市', r'市场.*?看跌|熊市', "市场情绪描述矛盾"),
        ]

        for pattern_a, pattern_b, msg in contradictions:
            if re.search(pattern_a, article) and re.search(pattern_b, article):
                # 可能是在不同时间段描述，只作为警告
                warnings.append(f"数据自洽性: {msg}（请确认是否在不同时间段描述）")

        return warnings

    def _check_market_cap_rank(self, article: str) -> list:
        """校验市值排名"""
        warnings = []
        self.checks_run += 1

        # 已知的大致排名（前10）
        known_top10 = ["BTC", "ETH", "BNB", "SOL", "XRP", "DOGE", "ADA", "AVAX", "DOT", "LINK"]

        patterns = [
            r'\$(\w+)\s*(?:市值排名|排名)[：:第]*\s*(\d+)',
            r'排名第\s*(\d+)\s*的\s*\$?(\w+)',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, article)
            for match in matches:
                try:
                    if len(match) == 2:
                        token, rank = match if match[0].isalpha() else (match[1], match[0])
                        rank = int(rank)
                        token = token.upper()
                        if token in known_top10[:3] and rank > 5:
                            warnings.append(f"${token} 排名可疑: 第{rank}名 (通常在前5)")
                except (ValueError, TypeError):
                    pass

        return warnings

    def _check_percentages(self, article: str) -> list:
        """校验百分比合理性"""
        warnings = []
        self.checks_run += 1

        # 查找所有百分比
        pcts = re.findall(r'([\d.]+)\s*%', article)
        for p in pcts:
            try:
                val = float(p)
                if val > 1000:
                    warnings.append(f"百分比异常: {val}% (超过 1000%)")
            except (ValueError, TypeError):
                pass

        return warnings

    def _generate_summary(self, issues: list, warnings: list, score: int) -> str:
        """生成校验摘要"""
        if not issues and not warnings:
            return f"事实校验通过 (评分: {score}/100, 检查项: {self.checks_run})"

        parts = [f"事实校验评分: {score}/100 (检查项: {self.checks_run})"]
        if issues:
            parts.append(f"  问题 ({len(issues)}):")
            for i, issue in enumerate(issues, 1):
                parts.append(f"    {i}. {issue}")
        if warnings:
            parts.append(f"  警告 ({len(warnings)}):")
            for i, w in enumerate(warnings, 1):
                parts.append(f"    {i}. {w}")

        return "\n".join(parts)
