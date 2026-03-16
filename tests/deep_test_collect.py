#!/usr/bin/env python3
"""
deep_test_collect.py — 深度测试：验证所有风格路由的 API 连通性
对每个风格调用 collect_all，记录每个数据源的响应状态
"""

import sys
import os
import json
import time
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from collect import (
    STYLE_DATA_ROUTES, DEFAULT_DATA_ROUTE,
    get_spot_ticker, get_spot_klines,
    get_futures_long_short_ratio, get_futures_top_account_ratio,
    get_futures_funding_rate, get_futures_open_interest,
    get_alpha_token_list, get_alpha_ticker, get_alpha_klines,
    get_social_hype_rank, get_alpha_rank, get_trending_tokens, get_smart_money_inflow,
    get_meme_exclusive_rank, get_trading_signals,
    get_meme_rush_new, get_meme_rush_migrated, get_topic_rush,
    get_token_search, get_token_dynamic_info, get_token_meta_info,
    get_token_audit, get_address_info,
    get_coingecko_price, get_blockchain_info, get_fear_greed_index,
    collect_all
)

SYMBOL = "bitcoin"
FUTURES_SYMBOL = "BTCUSDT"

RESULTS = {}

def test_api(name, func, *args, **kwargs):
    """测试单个 API，返回状态"""
    start = time.time()
    try:
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        if isinstance(result, dict):
            if "error" in result:
                status = "ERROR"
                detail = result["error"][:80]
            elif result.get("skipped"):
                status = "SKIPPED"
                detail = result.get("reason", "")
            else:
                # 检查是否有实际数据
                has_data = any(v for v in result.values() if v)
                status = "OK" if has_data else "EMPTY"
                detail = f"keys={list(result.keys())[:5]}"
        elif isinstance(result, list):
            status = "OK" if len(result) > 0 else "EMPTY"
            detail = f"len={len(result)}"
        else:
            status = "OK"
            detail = str(result)[:80]
    except Exception as e:
        elapsed = time.time() - start
        status = "EXCEPTION"
        detail = str(e)[:80]

    RESULTS[name] = {"status": status, "elapsed": round(elapsed, 2), "detail": detail}
    icon = "✅" if status == "OK" else ("⚠️" if status in ("EMPTY", "SKIPPED") else "❌")
    print(f"  {icon} [{status:9s}] {name:45s} ({elapsed:.2f}s) {detail[:60]}")
    return status

def section(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")

# ============================================================
# Phase 1: 测试所有独立 API 端点
# ============================================================
section("Phase 1: Individual API Endpoint Tests")

print("\n--- binance/spot ---")
test_api("spot_ticker_BTCUSDT",        get_spot_ticker, "BTCUSDT")
test_api("spot_klines_BTCUSDT_1d",     get_spot_klines, "BTCUSDT", "1d", 7)
test_api("spot_ticker_ETHUSDT",        get_spot_ticker, "ETHUSDT")

print("\n--- binance/derivatives ---")
test_api("futures_ls_ratio_BTCUSDT",   get_futures_long_short_ratio, "BTCUSDT")
test_api("futures_top_ratio_BTCUSDT",  get_futures_top_account_ratio, "BTCUSDT")
test_api("futures_funding_BTCUSDT",    get_futures_funding_rate, "BTCUSDT")
test_api("futures_oi_BTCUSDT",         get_futures_open_interest, "BTCUSDT")

print("\n--- binance/alpha ---")
test_api("alpha_token_list",           get_alpha_token_list)
test_api("alpha_ticker_BTCUSDT",       get_alpha_ticker, "BTCUSDT")
test_api("alpha_klines_BTCUSDT",       get_alpha_klines, "BTCUSDT")

print("\n--- binance-web3/crypto-market-rank ---")
test_api("social_hype_rank_bsc56",     get_social_hype_rank, "56")
test_api("alpha_rank",                 get_alpha_rank)
test_api("trending_tokens",            get_trending_tokens)
test_api("smart_money_inflow_bsc56",   get_smart_money_inflow, "56")
test_api("meme_exclusive_rank_sol",    get_meme_exclusive_rank, "CT_501")

print("\n--- binance-web3/trading-signal ---")
test_api("trading_signals_sol",        get_trading_signals, "CT_501")
test_api("trading_signals_bsc",        get_trading_signals, "56")
test_api("trading_signals_eth",        get_trading_signals, "1")

print("\n--- binance-web3/meme-rush ---")
test_api("meme_rush_new_sol",          get_meme_rush_new, "CT_501")
test_api("meme_rush_migrated_sol",     get_meme_rush_migrated, "CT_501")
test_api("meme_rush_new_bsc",          get_meme_rush_new, "56")
test_api("topic_rush_sol",             get_topic_rush, "CT_501")

print("\n--- binance-web3/query-token-info ---")
test_api("token_search_BTC",           get_token_search, "BTC")
test_api("token_search_ETH",           get_token_search, "ETH")
test_api("token_dynamic_no_addr",      get_token_dynamic_info, "56", "")
test_api("token_meta_no_addr",         get_token_meta_info, "56", "")

print("\n--- binance-web3/query-token-audit ---")
test_api("token_audit_no_addr",        get_token_audit, "56", "")

print("\n--- binance-web3/query-address-info ---")
test_api("address_info_no_addr",       get_address_info, "", "56")

print("\n--- Third-party data ---")
test_api("coingecko_bitcoin",          get_coingecko_price, "bitcoin")
test_api("coingecko_ethereum",         get_coingecko_price, "ethereum")
test_api("blockchain_info",            get_blockchain_info)
test_api("fear_greed_index",           get_fear_greed_index)

# ============================================================
# Phase 2: 测试每种风格的完整路由
# ============================================================
section("Phase 2: Full Style Route Tests (collect_all per style)")

ALL_STYLES = list(STYLE_DATA_ROUTES.keys())
STYLE_RESULTS = {}

for style in ALL_STYLES:
    print(f"\n--- Style: {style} ---")
    start = time.time()
    try:
        data = collect_all(SYMBOL, FUTURES_SYMBOL, style_name=style)
        elapsed = time.time() - start
        ok = sum(1 for v in data.values()
                 if isinstance(v, dict) and "error" not in v and not v.get("skipped"))
        ok += sum(1 for v in data.values() if isinstance(v, list) and len(v) > 0)
        total = len(data)
        STYLE_RESULTS[style] = {"ok": ok, "total": total, "elapsed": round(elapsed, 2)}
        icon = "✅" if ok >= total * 0.6 else "⚠️"
        print(f"  {icon} {style}: {ok}/{total} sources OK in {elapsed:.2f}s")

        # 打印每个数据源状态
        for k, v in data.items():
            if isinstance(v, dict):
                if "error" in v:
                    print(f"    ❌ {k}: {v['error'][:60]}")
                elif v.get("skipped"):
                    print(f"    ⏭️  {k}: skipped ({v.get('reason','')})")
                else:
                    print(f"    ✅ {k}: OK")
            elif isinstance(v, list):
                if len(v) == 0:
                    print(f"    ⚠️  {k}: empty list")
                else:
                    print(f"    ✅ {k}: {len(v)} items")
            else:
                print(f"    ❓ {k}: {str(v)[:40]}")
    except Exception as e:
        elapsed = time.time() - start
        STYLE_RESULTS[style] = {"ok": 0, "total": 0, "elapsed": round(elapsed, 2), "error": str(e)}
        print(f"  ❌ {style}: EXCEPTION - {e}")

# ============================================================
# Summary
# ============================================================
section("Summary")

print("\n=== Individual API Results ===")
ok_count = sum(1 for r in RESULTS.values() if r["status"] == "OK")
skip_count = sum(1 for r in RESULTS.values() if r["status"] == "SKIPPED")
empty_count = sum(1 for r in RESULTS.values() if r["status"] == "EMPTY")
err_count = sum(1 for r in RESULTS.values() if r["status"] in ("ERROR", "EXCEPTION"))
print(f"  Total: {len(RESULTS)} | OK: {ok_count} | Empty: {empty_count} | Skipped: {skip_count} | Error: {err_count}")

print("\n=== Style Route Results ===")
for style, sr in STYLE_RESULTS.items():
    if "error" in sr:
        print(f"  ❌ {style:20s}: EXCEPTION")
    else:
        icon = "✅" if sr["ok"] >= sr["total"] * 0.6 else "⚠️"
        print(f"  {icon} {style:20s}: {sr['ok']:2d}/{sr['total']:2d} OK  ({sr['elapsed']:.1f}s)")

print("\n=== APIs with Issues ===")
for name, r in RESULTS.items():
    if r["status"] not in ("OK", "SKIPPED"):
        print(f"  ❌ {name}: [{r['status']}] {r['detail']}")

# 保存结果到 JSON
with open("/tmp/deep_test_results.json", "w") as f:
    json.dump({"individual": RESULTS, "styles": STYLE_RESULTS}, f, indent=2)
print("\nResults saved to /tmp/deep_test_results.json")
