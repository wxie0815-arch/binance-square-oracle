#!/usr/bin/env python3
"""
final_e2e_test.py — 最终端到端测试
覆盖：9 种风格 LLM 调用 + DIY 风格 + 错误处理 + 发布层 + 数据采集层
"""

import sys, os, json, time, traceback
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import oracle, config, collect, publish

# ============================================================
# 模拟市场数据
# ============================================================
MOCK_DATA = {
    "spot_ticker": {"symbol": "BTCUSDT", "lastPrice": "84200.00", "priceChangePercent": "2.35",
                     "volume": "28450", "highPrice": "85500", "lowPrice": "82100"},
    "spot_klines_7d": [{"open": "78000", "high": "86000", "low": "77000", "close": "84200", "volume": "25000"}],
    "futures_long_short_ratio": {"longShortRatio": "1.23", "longAccount": "55.2", "shortAccount": "44.8"},
    "futures_top_account_ratio": {"longShortRatio": "1.45", "longAccount": "59.2", "shortAccount": "40.8"},
    "futures_funding_rate": {"fundingRate": "0.0001"},
    "futures_open_interest": {"openInterest": "85234.56", "symbol": "BTCUSDT"},
    "alpha_token_list": [{"symbol": "BTC", "price": "84200", "priceChangePercent": "2.35"},
                          {"symbol": "ETH", "price": "3200", "priceChangePercent": "1.8"}],
    "social_hype_rank": [{"symbol": "BTC", "rank": 1, "hypeScore": 98.5}],
    "alpha_rank": [{"symbol": "PEPE", "rank": 1, "score": 95.3}],
    "trending_tokens": [{"symbol": "BTC", "priceChangePercent": "2.35"},
                         {"symbol": "SOL", "priceChangePercent": "4.2"}],
    "smart_money_inflow": [{"address": "0xabc", "chain": "BSC", "inflow": "2500000", "token": "BTC"}],
    "meme_exclusive_rank": [{"symbol": "PEPE", "rank": 1, "volume24h": "450000000"}],
    "trading_signals": [{"symbol": "BTCUSDT", "signal": "BUY", "strength": 85}],
    "trading_signals_bsc": [{"symbol": "BNBUSDT", "signal": "BUY", "strength": 78}],
    "meme_rush_new": [{"name": "DOGE2025", "priceChange1h": "45.2"}],
    "meme_rush_migrated": [{"name": "BONK2", "priceChange24h": "65.3"}],
    "meme_rush_bsc_new": [{"name": "SHIB2", "priceChange1h": "33.1"}],
    "topic_rush": [{"topic": "AI tokens", "heatScore": 95, "topTokens": ["FET", "RNDR"]}],
    "token_search": [{"symbol": "BTC", "name": "Bitcoin", "price": "84200"}],
    "token_audit": {"auditScore": 98, "isHoneypot": False},
    "coingecko_price": {"bitcoin": {"usd": 84200, "usd_24h_change": 2.35}},
    "fear_greed_index": {"data": [{"value": "72", "value_classification": "Greed"}]},
    "blockchain_info": {"hash_rate": "650000000000000000", "n_blocks_total": 820000},
}

ALL_STYLES = ["daily_express", "deep_analysis", "onchain_insight", "meme_hunter",
              "kol_style", "oracle", "project_research", "trading_signal", "tutorial"]

RESULTS = {}
ISSUES = []

def section(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")

def check(name, condition, detail=""):
    icon = "✅" if condition else "❌"
    print(f"  {icon} {name}" + (f" — {detail}" if detail else ""))
    if not condition:
        ISSUES.append(f"{name}: {detail}")
    return condition

# ============================================================
# TEST 1: 9 种风格 LLM 端到端
# ============================================================
section("TEST 1: 9 Styles — Real LLM E2E")

for style in ALL_STYLES:
    print(f"\n--- {style} ---")
    start = time.time()
    try:
        result = oracle.generate_article(MOCK_DATA, style_name=style, user_intent=f"BTC ({style})")
        elapsed = time.time() - start

        if "error" in result:
            check(f"{style}: LLM pipeline", False, result["error"])
            RESULTS[style] = {"status": "ERROR", "elapsed": round(elapsed, 2)}
            continue

        article = result.get("final_article", "")
        score = result.get("oracle_score", -1)
        fp = result.get("style_fingerprint", "")

        ok = True
        issues = []
        if len(article) < 50:
            issues.append(f"too short ({len(article)} chars)")
            ok = False
        if not isinstance(score, int) or not (0 <= score <= 100):
            issues.append(f"bad score: {score}")
            ok = False
        if not fp:
            issues.append("empty fingerprint")
            ok = False
        if "```json" in article or '"article_draft"' in article:
            issues.append("JSON leakage")
            ok = False
        for w in ["as an AI", "I cannot", "language model"]:
            if w.lower() in article.lower():
                issues.append(f"AI phrase: '{w}'")
                ok = False

        status = "OK" if ok else "WARNING"
        check(f"{style}: score={score}/100, {len(article)}chars, {elapsed:.1f}s", ok,
              "; ".join(issues) if issues else "")
        RESULTS[style] = {"status": status, "score": score, "length": len(article),
                          "elapsed": round(elapsed, 2), "issues": issues}
    except Exception as e:
        elapsed = time.time() - start
        check(f"{style}: LLM pipeline", False, f"EXCEPTION: {e}")
        RESULTS[style] = {"status": "EXCEPTION", "elapsed": round(elapsed, 2), "error": str(e)}

# ============================================================
# TEST 2: DIY 风格
# ============================================================
section("TEST 2: DIY Custom Style")

diy_path = os.path.join(config.PROMPTS_DIR, "test_final_diy.md")
with open(diy_path, "w") as f:
    f.write("# Pirate Style\nWrite as a pirate captain. Use Arrr! and Matey. Keep analysis accurate.\n")

try:
    start = time.time()
    result = oracle.generate_article(MOCK_DATA, style_name="test_final_diy", user_intent="BTC pirate")
    elapsed = time.time() - start
    if "error" in result:
        check("DIY style", False, result["error"])
    else:
        check("DIY style", len(result["final_article"]) > 50,
              f"score={result['oracle_score']}, {len(result['final_article'])}chars, {elapsed:.1f}s")
except Exception as e:
    check("DIY style", False, f"EXCEPTION: {e}")
finally:
    os.remove(diy_path)

# ============================================================
# TEST 3: 数据采集层路由
# ============================================================
section("TEST 3: Data Collection Routes")

for style in ALL_STYLES:
    route = collect.STYLE_DATA_ROUTES.get(style)
    check(f"{style} route exists", route is not None, f"skills: {route.get('skills', []) if route else 'N/A'}")

check("DEFAULT_DATA_ROUTE exists", hasattr(collect, "DEFAULT_DATA_ROUTE"))

# 测试真实 API 调用（仅用不受地理限制的端点）
section("TEST 3b: Live API Spot Check (geo-safe endpoints)")

safe_tests = {
    "trading_signals": lambda: collect.get_trading_signals(),
    "social_hype_rank": lambda: collect.get_social_hype_rank(),
    "trending_tokens": lambda: collect.get_trending_tokens(),
    "fear_greed_index": lambda: collect.get_fear_greed_index(),
    "token_search": lambda: collect.get_token_search("bitcoin"),
    "meme_rush_new": lambda: collect.get_meme_rush_new(),
    "alpha_rank": lambda: collect.get_alpha_rank(),
}

for name, fn in safe_tests.items():
    try:
        data = fn()
        ok = data is not None and not (isinstance(data, dict) and "error" in data)
        check(f"API {name}", ok, f"type={type(data).__name__}, len={len(str(data)[:100])}")
    except Exception as e:
        check(f"API {name}", False, str(e))

# ============================================================
# TEST 4: 发布层
# ============================================================
section("TEST 4: Publish Layer")

# 测试 hashtag 提取
tags = publish._extract_hashtags("$BTC is pumping! #Binance #DeFi great day for $ETH")
check("_extract_hashtags", "#Binance" in tags and "#DeFi" in tags, f"tags={tags}")

coins = publish._extract_coins("$BTC and $ETH are pumping, $SOL too")
check("_extract_coins", "BTC" in coins and "ETH" in coins, f"coins={coins}")

# 测试无 API Key 时跳过发布
result = publish.publish_to_square("Test article")
check("publish without API key skips", result.get("skipped") == True, f"result={result}")

# ============================================================
# TEST 5: 错误处理
# ============================================================
section("TEST 5: Error Handling")

# 空数据
try:
    result = oracle.generate_article({}, style_name="kol_style", user_intent="empty test")
    check("Empty data handling", "final_article" in result or "error" in result,
          f"{'article generated' if 'final_article' in result else result.get('error', 'unknown')}")
except Exception as e:
    check("Empty data handling", False, f"EXCEPTION: {e}")

# 不存在的风格
try:
    result = oracle.generate_article(MOCK_DATA, style_name="nonexistent_xyz_999")
    check("Nonexistent style", False, "Should have raised FileNotFoundError")
except FileNotFoundError:
    check("Nonexistent style raises FileNotFoundError", True)
except Exception as e:
    check("Nonexistent style", False, f"Wrong exception: {type(e).__name__}: {e}")

# list_available_styles
styles = oracle.list_available_styles()
check("list_available_styles", len(styles) >= 9, f"found {len(styles)} styles: {styles}")

# is_builtin_style
check("is_builtin_style('kol_style')", oracle.is_builtin_style("kol_style") == True)
check("is_builtin_style('my_custom')", oracle.is_builtin_style("my_custom") == False)

# ============================================================
# TEST 6: 版本 & 配置一致性
# ============================================================
section("TEST 6: Version & Config Consistency")

check("config.VERSION == '1.0'", config.VERSION == "1.0", f"actual: {config.VERSION}")
check("PROMPTS_DIR exists", os.path.isdir(config.PROMPTS_DIR))
check("SKILLS_DIR exists", os.path.isdir(config.SKILLS_DIR))
check("9 prompt files", len([f for f in os.listdir(config.PROMPTS_DIR) if f.endswith('.md')]) == 9)

# ============================================================
# FINAL SUMMARY
# ============================================================
section("FINAL SUMMARY")

ok_count = sum(1 for r in RESULTS.values() if r["status"] == "OK")
warn_count = sum(1 for r in RESULTS.values() if r["status"] == "WARNING")
err_count = sum(1 for r in RESULTS.values() if r["status"] in ("ERROR", "EXCEPTION"))

print(f"\n  LLM E2E Results: ✅ {ok_count} OK | ⚠️ {warn_count} Warning | ❌ {err_count} Error")
print()
for style, r in RESULTS.items():
    icon = "✅" if r["status"] == "OK" else ("⚠️" if r["status"] == "WARNING" else "❌")
    score = r.get("score", "N/A")
    length = r.get("length", 0)
    elapsed = r.get("elapsed", 0)
    print(f"  {icon} {style:20s}: score={str(score):>3} | {length:>5}chars | {elapsed:.1f}s")

if ISSUES:
    print(f"\n  ❌ Total issues found: {len(ISSUES)}")
    for issue in ISSUES:
        print(f"    - {issue}")
else:
    print(f"\n  ✅ NO ISSUES FOUND — ALL TESTS PASSED")

print(f"\n  Done.")
