#!/usr/bin/env python3
"""
deep_test_oracle.py — 深度测试：验证 9 种风格的完整 LLM 调用流程
使用真实 LLM 调用（通过 OpenClaw 系统 API），模拟真实数据
"""

import sys
import os
import json
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import oracle
import config

# ============================================================
# 模拟市场数据（模拟 collect_all 返回值，覆盖各风格所需字段）
# ============================================================
MOCK_MARKET_DATA = {
    # spot
    "spot_ticker": {
        "symbol": "BTCUSDT",
        "lastPrice": "84200.00",
        "priceChangePercent": "2.35",
        "volume": "28450.123",
        "quoteVolume": "2398000000",
        "highPrice": "85500.00",
        "lowPrice": "82100.00"
    },
    "spot_klines_7d": [
        {"openTime": 1700000000000, "open": "78000", "high": "86000", "low": "77000", "close": "84200", "volume": "25000"},
        {"openTime": 1700086400000, "open": "84200", "high": "87000", "low": "83000", "close": "85500", "volume": "22000"},
    ],
    # derivatives
    "futures_long_short_ratio": {"longShortRatio": "1.23", "longAccount": "55.2", "shortAccount": "44.8"},
    "futures_top_account_ratio": {"longShortRatio": "1.45", "longAccount": "59.2", "shortAccount": "40.8"},
    "futures_funding_rate": {"fundingRate": "0.0001", "nextFundingTime": 1700100000000},
    "futures_open_interest": {"openInterest": "85234.56", "symbol": "BTCUSDT"},
    # alpha
    "alpha_token_list": [
        {"symbol": "BTC", "name": "Bitcoin", "price": "84200", "priceChangePercent": "2.35"},
        {"symbol": "ETH", "name": "Ethereum", "price": "3200", "priceChangePercent": "1.8"},
        {"symbol": "SOL", "name": "Solana", "price": "185", "priceChangePercent": "4.2"},
    ],
    # crypto-market-rank
    "social_hype_rank": [
        {"symbol": "BTC", "rank": 1, "hypeScore": 98.5},
        {"symbol": "ETH", "rank": 2, "hypeScore": 87.2},
        {"symbol": "SOL", "rank": 3, "hypeScore": 79.1},
    ],
    "alpha_rank": [
        {"symbol": "PEPE", "rank": 1, "score": 95.3},
        {"symbol": "WIF", "rank": 2, "score": 88.7},
    ],
    "trending_tokens": [
        {"symbol": "BTC", "name": "Bitcoin", "priceChangePercent": "2.35"},
        {"symbol": "SOL", "name": "Solana", "priceChangePercent": "4.2"},
        {"symbol": "PEPE", "name": "Pepe", "priceChangePercent": "15.7"},
    ],
    "smart_money_inflow": [
        {"address": "0xabc...def", "chain": "BSC", "inflow": "2500000", "token": "BTC"},
        {"address": "0x123...456", "chain": "ETH", "inflow": "1800000", "token": "ETH"},
    ],
    "meme_exclusive_rank": [
        {"symbol": "PEPE", "rank": 1, "volume24h": "450000000"},
        {"symbol": "WIF", "rank": 2, "volume24h": "280000000"},
    ],
    # trading-signal
    "trading_signals": [
        {"symbol": "BTCUSDT", "signal": "BUY", "strength": 85, "chain": "SOL"},
        {"symbol": "ETHUSDT", "signal": "HOLD", "strength": 60, "chain": "ETH"},
        {"symbol": "SOLUSDT", "signal": "BUY", "strength": 92, "chain": "SOL"},
    ],
    "trading_signals_bsc": [
        {"symbol": "BNBUSDT", "signal": "BUY", "strength": 78},
    ],
    # meme-rush
    "meme_rush_new": [
        {"name": "DOGE2025", "symbol": "DOGE2025", "marketCap": "5000000", "priceChange1h": "45.2"},
        {"name": "PEPE2", "symbol": "PEPE2", "marketCap": "3200000", "priceChange1h": "28.7"},
    ],
    "meme_rush_migrated": [
        {"name": "BONK2", "symbol": "BONK2", "marketCap": "12000000", "priceChange24h": "65.3"},
    ],
    "meme_rush_bsc_new": [
        {"name": "SHIB2", "symbol": "SHIB2", "marketCap": "2800000", "priceChange1h": "33.1"},
    ],
    "topic_rush": [
        {"topic": "AI tokens", "heatScore": 95, "topTokens": ["FET", "RNDR", "AGIX"]},
        {"topic": "DeFi revival", "heatScore": 82, "topTokens": ["UNI", "AAVE", "CRV"]},
    ],
    # query-token-info
    "token_search": [
        {"symbol": "BTC", "name": "Bitcoin", "price": "84200", "marketCap": "1650000000000"},
        {"symbol": "ETH", "name": "Ethereum", "price": "3200", "marketCap": "385000000000"},
    ],
    # query-token-audit
    "token_audit": {
        "symbol": "BTC",
        "auditScore": 98,
        "isHoneypot": False,
        "liquidityLocked": True,
        "ownershipRenounced": True
    },
    # third-party
    "coingecko_price": {
        "bitcoin": {"usd": 84200, "usd_24h_change": 2.35, "usd_market_cap": 1650000000000}
    },
    "fear_greed_index": {
        "data": [{"value": "72", "value_classification": "Greed", "timestamp": "1700000000"}]
    },
    "blockchain_info": {
        "hash_rate": "650000000000000000",
        "difficulty": "72000000000000",
        "n_blocks_total": 820000,
        "minutes_between_blocks": 9.8
    }
}

ALL_STYLES = [
    "daily_express", "deep_analysis", "onchain_insight", "meme_hunter",
    "kol_style", "oracle", "project_research", "trading_signal", "tutorial"
]

RESULTS = {}

def section(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")

# ============================================================
# Phase 1: 测试风格模板加载
# ============================================================
section("Phase 1: Style Template Loading")

for style in ALL_STYLES:
    try:
        content = oracle._load_prompt_template(style)
        print(f"  ✅ {style:20s}: {len(content)} chars loaded")
    except Exception as e:
        print(f"  ❌ {style:20s}: {e}")

# ============================================================
# Phase 2: 测试 generate_article（使用真实 LLM + 模拟数据）
# ============================================================
section("Phase 2: Full LLM Pipeline (Real LLM + Mock Data)")

for style in ALL_STYLES:
    print(f"\n--- Testing style: {style} ---")
    start = time.time()
    try:
        result = oracle.generate_article(MOCK_MARKET_DATA, style_name=style, user_intent=f"BTC analysis ({style})")
        elapsed = time.time() - start

        if "error" in result:
            print(f"  ❌ FAILED: {result['error']}")
            RESULTS[style] = {"status": "ERROR", "elapsed": round(elapsed, 2), "error": result["error"]}
        else:
            article = result.get("final_article", "")
            score = result.get("oracle_score", "N/A")
            fingerprint = result.get("style_fingerprint", "")

            # 质量检查
            issues = []
            if len(article) < 100:
                issues.append(f"article too short ({len(article)} chars)")
            if not isinstance(score, int) or not (0 <= score <= 100):
                issues.append(f"invalid oracle_score: {score}")
            if not fingerprint:
                issues.append("empty style_fingerprint")
            # 检查是否有 JSON 残留
            if "```json" in article or '"article_draft"' in article:
                issues.append("JSON leakage in final article")
            # 检查是否有 AI 痕迹词
            ai_words = ["as an AI", "I cannot", "I'm unable", "language model"]
            for w in ai_words:
                if w.lower() in article.lower():
                    issues.append(f"AI phrase detected: '{w}'")

            status = "OK" if not issues else "WARNING"
            icon = "✅" if status == "OK" else "⚠️"
            print(f"  {icon} [{status}] Score: {score}/100 | Article: {len(article)} chars | Time: {elapsed:.1f}s")
            print(f"  Fingerprint: {fingerprint[:80]}")
            if issues:
                for issue in issues:
                    print(f"  ⚠️  Issue: {issue}")
            print(f"  Article preview: {article[:200]}...")

            RESULTS[style] = {
                "status": status,
                "elapsed": round(elapsed, 2),
                "oracle_score": score,
                "article_length": len(article),
                "fingerprint": fingerprint,
                "issues": issues,
                "article_preview": article[:300]
            }
    except Exception as e:
        elapsed = time.time() - start
        print(f"  ❌ EXCEPTION: {e}")
        traceback.print_exc()
        RESULTS[style] = {"status": "EXCEPTION", "elapsed": round(elapsed, 2), "error": str(e)}

# ============================================================
# Phase 3: 测试 DIY 风格
# ============================================================
section("Phase 3: DIY Style Test")

# 创建一个临时 DIY 风格文件
diy_style_path = os.path.join(config.PROMPTS_DIR, "test_diy_style.md")
with open(diy_style_path, "w") as f:
    f.write("""# Test DIY Style

Write the article as a pirate captain who loves crypto. Use pirate language (Arrr!, Matey, etc.) 
but keep the market analysis accurate. The article should be fun, engaging, and informative.
Structure: Hook -> Market Data -> Analysis -> Call to Action.
""")

try:
    print("\n--- Testing DIY style: test_diy_style ---")
    start = time.time()
    result = oracle.generate_article(MOCK_MARKET_DATA, style_name="test_diy_style", user_intent="BTC pirate analysis")
    elapsed = time.time() - start
    if "error" in result:
        print(f"  ❌ DIY style failed: {result['error']}")
    else:
        print(f"  ✅ DIY style OK | Score: {result['oracle_score']}/100 | {len(result['final_article'])} chars | {elapsed:.1f}s")
        print(f"  Preview: {result['final_article'][:200]}...")
except Exception as e:
    print(f"  ❌ DIY style EXCEPTION: {e}")
finally:
    os.remove(diy_style_path)
    print("  (DIY style file cleaned up)")

# ============================================================
# Phase 4: 测试 list_available_styles
# ============================================================
section("Phase 4: Style Discovery")

styles = oracle.list_available_styles()
print(f"  Available styles ({len(styles)}): {', '.join(styles)}")
for s in ALL_STYLES:
    if s in styles:
        print(f"  ✅ {s}")
    else:
        print(f"  ❌ {s} NOT FOUND")

# ============================================================
# Phase 5: 测试错误处理
# ============================================================
section("Phase 5: Error Handling")

# 测试空数据
print("\n--- Test: Empty market data ---")
try:
    result = oracle.generate_article({}, style_name="kol_style", user_intent="test")
    if "error" in result:
        print(f"  ✅ Empty data handled gracefully: {result['error'][:60]}")
    else:
        print(f"  ✅ Empty data: article generated ({len(result.get('final_article',''))} chars)")
except Exception as e:
    print(f"  ❌ Exception on empty data: {e}")

# 测试不存在的风格
print("\n--- Test: Non-existent style ---")
try:
    result = oracle.generate_article(MOCK_MARKET_DATA, style_name="nonexistent_xyz")
    print(f"  ❌ Should have raised FileNotFoundError, got: {result}")
except FileNotFoundError as e:
    print(f"  ✅ FileNotFoundError raised correctly: {str(e)[:80]}")
except Exception as e:
    print(f"  ⚠️  Unexpected exception: {type(e).__name__}: {e}")

# ============================================================
# Summary
# ============================================================
section("Final Summary")

ok = sum(1 for r in RESULTS.values() if r["status"] == "OK")
warn = sum(1 for r in RESULTS.values() if r["status"] == "WARNING")
err = sum(1 for r in RESULTS.values() if r["status"] in ("ERROR", "EXCEPTION"))

print(f"\n  Total styles tested: {len(RESULTS)}")
print(f"  ✅ OK: {ok} | ⚠️ Warning: {warn} | ❌ Error: {err}")
print()

for style, r in RESULTS.items():
    icon = "✅" if r["status"] == "OK" else ("⚠️" if r["status"] == "WARNING" else "❌")
    score = r.get("oracle_score", "N/A")
    length = r.get("article_length", 0)
    elapsed = r.get("elapsed", 0)
    issues = r.get("issues", [])
    print(f"  {icon} {style:20s}: score={score:>3} | {length:>4}chars | {elapsed:.1f}s", end="")
    if issues:
        print(f" | Issues: {'; '.join(issues)}")
    else:
        print()

# 保存结果
with open("/tmp/deep_test_oracle_results.json", "w", encoding="utf-8") as f:
    json.dump(RESULTS, f, indent=2, ensure_ascii=False)
print("\nResults saved to /tmp/deep_test_oracle_results.json")
