#!/usr/bin/env python3
"""Deep oracle smoke test with optional live LLM execution."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import oracle


RUN_LIVE = os.environ.get("RUN_LIVE_LLM_TESTS") == "1"

MOCK_MARKET_DATA = {
    "spot_ticker": {"symbol": "BTCUSDT", "lastPrice": "84200.00", "priceChangePercent": "2.35"},
    "spot_klines_7d": [{"open": "78000", "high": "86000", "low": "77000", "close": "84200"}],
    "futures_long_short_ratio": {"longShortRatio": "1.23"},
    "futures_funding_rate": {"fundingRate": "0.0001"},
    "futures_open_interest": {"openInterest": "85234.56"},
    "alpha_token_list": [{"symbol": "BTC"}, {"symbol": "ETH"}],
    "social_hype_rank": [{"symbol": "BTC", "rank": 1}],
    "trending_tokens": [{"symbol": "BTC"}, {"symbol": "SOL"}],
    "trading_signals": [{"symbol": "BTCUSDT", "signal": "BUY", "strength": 85}],
    "coingecko_price": {"bitcoin": {"usd": 84200, "usd_24h_change": 2.35}},
    "fear_greed_index": {"data": [{"value": "72", "value_classification": "Greed"}]},
}


def main():
    results = {
        "available_styles": oracle.list_available_styles(),
        "style_template_lengths": {},
        "live_runs": {},
    }

    for style in oracle.list_available_styles():
        content = oracle._load_prompt_template(style)
        results["style_template_lengths"][style] = len(content)

    if RUN_LIVE:
        for style in ["daily_express", "deep_analysis", "kol_style"]:
            started = time.time()
            try:
                output = oracle.generate_article(MOCK_MARKET_DATA, style_name=style, user_intent=f"BTC {style}")
                results["live_runs"][style] = {
                    "status": "OK",
                    "elapsed": round(time.time() - started, 2),
                    "oracle_score": output.get("oracle_score"),
                    "article_length": len(output.get("final_article", "")),
                }
            except Exception as exc:
                results["live_runs"][style] = {
                    "status": "ERROR",
                    "elapsed": round(time.time() - started, 2),
                    "detail": str(exc),
                }
    else:
        results["live_runs"]["skipped"] = {
            "status": "SKIPPED",
            "detail": "Set RUN_LIVE_LLM_TESTS=1 and configure OPENAI_API_KEY to execute live generation.",
        }

    output_path = os.path.join(tempfile.gettempdir(), "binance_square_oracle_oracle_results.json")
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, ensure_ascii=False)

    print(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"Saved results to {output_path}")


if __name__ == "__main__":
    main()
