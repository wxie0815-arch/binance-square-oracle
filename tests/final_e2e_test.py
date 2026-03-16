#!/usr/bin/env python3
"""Repository-level end-to-end smoke test."""

from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import collect
import config
import oracle
import publish


def main():
    report = {
        "version": config.VERSION,
        "style_count": len(oracle.list_available_styles()),
        "route_count": len(collect.get_available_routes()),
        "publish_without_key": publish.publish_to_square("Test article"),
        "builtin_style_checks": {
            "kol_style": oracle.is_builtin_style("kol_style"),
            "my_custom_style": oracle.is_builtin_style("my_custom_style"),
        },
    }

    output_path = os.path.join(tempfile.gettempdir(), "binance_square_oracle_e2e_results.json")
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)

    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"Saved results to {output_path}")


if __name__ == "__main__":
    main()
