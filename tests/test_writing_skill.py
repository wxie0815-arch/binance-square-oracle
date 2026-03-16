#!/usr/bin/env python3
"""Structure tests for style prompts and collection helpers."""

from __future__ import annotations

import glob
import inspect
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import collect


class TestCollectFunctions(unittest.TestCase):
    def test_collect_helpers_are_callable(self):
        names = [
            "get_spot_ticker",
            "get_spot_klines",
            "get_futures_long_short_ratio",
            "get_futures_funding_rate",
            "get_futures_open_interest",
            "get_social_hype_rank",
            "get_alpha_rank",
            "get_trending_tokens",
            "get_smart_money_inflow",
            "get_trading_signals",
            "get_meme_rush_new",
            "get_meme_rush_migrated",
            "get_coingecko_price",
            "get_blockchain_info",
            "get_fear_greed_index",
            "collect_all",
            "get_alpha_token_list",
            "get_token_search",
            "get_token_audit",
            "get_address_info",
        ]
        for name in names:
            with self.subTest(name=name):
                self.assertTrue(callable(getattr(collect, name)))

    def test_style_data_routes_exist(self):
        self.assertTrue(hasattr(collect, "STYLE_DATA_ROUTES"))
        self.assertGreaterEqual(len(collect.STYLE_DATA_ROUTES), 9)

    def test_default_data_route_exists(self):
        self.assertTrue(hasattr(collect, "DEFAULT_DATA_ROUTE"))

    def test_collect_all_accepts_style_name(self):
        sig = inspect.signature(collect.collect_all)
        self.assertIn("style_name", sig.parameters)

    def test_fetch_aliases_exist(self):
        aliases = [
            "fetch_spot_ticker",
            "fetch_spot_klines",
            "fetch_futures_ls_ratio",
            "fetch_futures_top_ratio",
            "fetch_futures_funding_rate",
            "fetch_futures_open_interest",
            "fetch_social_hype_rank",
            "fetch_alpha_rank",
            "fetch_trending_tokens",
            "fetch_smart_money_inflow",
            "fetch_trading_signal",
            "fetch_meme_new",
            "fetch_meme_migrated",
            "fetch_coingecko_price",
            "fetch_blockchain_stats",
            "fetch_fear_greed",
        ]
        for alias in aliases:
            with self.subTest(alias=alias):
                self.assertTrue(hasattr(collect, alias))
                self.assertTrue(callable(getattr(collect, alias)))


class TestPromptTemplates(unittest.TestCase):
    def setUp(self):
        self.repo_root = os.path.dirname(os.path.dirname(__file__))
        self.prompts_dir = os.path.join(self.repo_root, "prompts")

    def test_prompts_dir_exists(self):
        self.assertTrue(os.path.isdir(self.prompts_dir))

    def test_skills_dir_exists(self):
        self.assertTrue(os.path.isdir(os.path.join(self.repo_root, "skills")))

    def test_writing_rules_reference_exists(self):
        self.assertTrue(os.path.exists(os.path.join(self.repo_root, "references", "writing_rules.md")))

    def test_builtin_styles_exist(self):
        styles = [
            "daily_express",
            "deep_analysis",
            "onchain_insight",
            "meme_hunter",
            "kol_style",
            "tutorial",
            "trading_signal",
            "project_research",
            "oracle",
        ]
        for style in styles:
            with self.subTest(style=style):
                self.assertTrue(os.path.exists(os.path.join(self.prompts_dir, f"{style}.md")))

    def test_total_styles_count(self):
        templates = glob.glob(os.path.join(self.prompts_dir, "*.md"))
        self.assertGreaterEqual(len(templates), 9)


if __name__ == "__main__":
    unittest.main(verbosity=2)
