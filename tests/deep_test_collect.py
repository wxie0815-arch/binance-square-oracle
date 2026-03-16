#!/usr/bin/env python3
"""Deep collection smoke test with optional live API checks."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import collect


SYMBOL = "bitcoin"
FUTURES_SYMBOL = "BTCUSDT"
RUN_LIVE = os.environ.get("RUN_LIVE_BINANCE_TESTS") == "1"


def describe_result(value):
    if isinstance(value, dict):
        if "error" in value:
            return "ERROR", value["error"][:120]
        if value.get("skipped"):
            return "SKIPPED", value.get("reason", "")
        return "OK", f"keys={list(value.keys())[:5]}"
    if isinstance(value, list):
        return ("OK" if value else "EMPTY"), f"len={len(value)}"
    return "OK", str(value)[:120]


def main():
    results = {
        "routes": collect.get_available_routes(),
        "styles": {},
        "live_checks": {},
    }

    for style in collect.STYLE_DATA_ROUTES:
        started = time.time()
        route = collect.STYLE_DATA_ROUTES[style]
        task_map = route["tasks"](SYMBOL, FUTURES_SYMBOL)
        results["styles"][style] = {
            "description": route["description"],
            "skills": route["skills"],
            "task_count": len(task_map),
            "elapsed": round(time.time() - started, 4),
        }

    if RUN_LIVE:
        live_tests = {
            "spot_ticker": lambda: collect.get_spot_ticker(FUTURES_SYMBOL),
            "trending_tokens": collect.get_trending_tokens,
            "social_hype_rank": collect.get_social_hype_rank,
            "fear_greed_index": collect.get_fear_greed_index,
        }
        for name, fn in live_tests.items():
            value = fn()
            status, detail = describe_result(value)
            results["live_checks"][name] = {"status": status, "detail": detail}
    else:
        results["live_checks"]["skipped"] = {
            "status": "SKIPPED",
            "detail": "Set RUN_LIVE_BINANCE_TESTS=1 to enable live endpoint checks.",
        }

    output_path = os.path.join(tempfile.gettempdir(), "binance_square_oracle_collect_results.json")
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, ensure_ascii=False)

    print(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"Saved results to {output_path}")


if __name__ == "__main__":
    main()
