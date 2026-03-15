#!/usr/bin/env python3
"""
tests/test_writing_skill.py — Data collection and style template tests for v1.0
"""

import os
import sys
import glob
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import collect


class TestCollectFunctions(unittest.TestCase):
    """测试 collect.py 核心函数可调用性"""

    def test_get_spot_ticker_callable(self):
        self.assertTrue(callable(collect.get_spot_ticker))

    def test_get_spot_klines_callable(self):
        self.assertTrue(callable(collect.get_spot_klines))

    def test_get_futures_long_short_ratio_callable(self):
        self.assertTrue(callable(collect.get_futures_long_short_ratio))

    def test_get_futures_funding_rate_callable(self):
        self.assertTrue(callable(collect.get_futures_funding_rate))

    def test_get_futures_open_interest_callable(self):
        self.assertTrue(callable(collect.get_futures_open_interest))

    def test_get_social_hype_rank_callable(self):
        self.assertTrue(callable(collect.get_social_hype_rank))

    def test_get_alpha_rank_callable(self):
        self.assertTrue(callable(collect.get_alpha_rank))

    def test_get_trending_tokens_callable(self):
        self.assertTrue(callable(collect.get_trending_tokens))

    def test_get_smart_money_inflow_callable(self):
        self.assertTrue(callable(collect.get_smart_money_inflow))

    def test_get_trading_signals_callable(self):
        self.assertTrue(callable(collect.get_trading_signals))

    def test_get_meme_rush_new_callable(self):
        self.assertTrue(callable(collect.get_meme_rush_new))

    def test_get_meme_rush_migrated_callable(self):
        self.assertTrue(callable(collect.get_meme_rush_migrated))

    def test_get_coingecko_price_callable(self):
        self.assertTrue(callable(collect.get_coingecko_price))

    def test_get_blockchain_info_callable(self):
        self.assertTrue(callable(collect.get_blockchain_info))

    def test_get_fear_greed_index_callable(self):
        self.assertTrue(callable(collect.get_fear_greed_index))

    def test_collect_all_callable(self):
        self.assertTrue(callable(collect.collect_all))

    def test_get_alpha_token_list_callable(self):
        self.assertTrue(callable(collect.get_alpha_token_list))

    def test_get_token_search_callable(self):
        self.assertTrue(callable(collect.get_token_search))

    def test_get_token_audit_callable(self):
        self.assertTrue(callable(collect.get_token_audit))

    def test_get_address_info_callable(self):
        self.assertTrue(callable(collect.get_address_info))

    def test_style_data_routes_exist(self):
        self.assertTrue(hasattr(collect, 'STYLE_DATA_ROUTES'))
        self.assertGreaterEqual(len(collect.STYLE_DATA_ROUTES), 9)

    def test_default_data_route_exists(self):
        self.assertTrue(hasattr(collect, 'DEFAULT_DATA_ROUTE'))

    def test_collect_all_accepts_style(self):
        import inspect
        sig = inspect.signature(collect.collect_all)
        self.assertIn('style_name', sig.parameters)

    def test_fetch_aliases_exist(self):
        """fetch_* 别名应全部存在"""
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
                self.assertTrue(hasattr(collect, alias), f"缺少别名: {alias}")
                self.assertTrue(callable(getattr(collect, alias)))


class TestPromptTemplates(unittest.TestCase):
    """Prompt 模板测试"""

    def test_prompts_dir_exists(self):
        """prompts 目录应存在"""
        prompts_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts")
        self.assertTrue(os.path.isdir(prompts_dir))

    def test_skills_dir_exists(self):
        """skills 目录应存在"""
        skills_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "skills")
        self.assertTrue(os.path.isdir(skills_dir))

    def test_crypto_content_writer_skill_exists(self):
        """crypto-content-writer SKILL.md 应存在"""
        skill_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "skills", "crypto-content-writer", "SKILL.md"
        )
        self.assertTrue(os.path.exists(skill_path))

    def test_official_four_styles_exist(self):
        """官方 4 种风格模板应存在"""
        prompts_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts")
        for style in ["daily_express", "deep_analysis", "onchain_insight", "meme_hunter"]:
            path = os.path.join(prompts_dir, f"{style}.md")
            self.assertTrue(os.path.exists(path), f"缺少风格模板: {style}.md")

    def test_extended_styles_exist(self):
        """扩展 5 种风格模板应存在"""
        prompts_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts")
        for style in ["kol_style", "tutorial", "trading_signal", "project_research", "oracle"]:
            path = os.path.join(prompts_dir, f"{style}.md")
            self.assertTrue(os.path.exists(path), f"缺少风格模板: {style}.md")

    def test_total_styles_count(self):
        """Should have at least 9 style templates"""
        prompts_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts")
        templates = glob.glob(os.path.join(prompts_dir, "*.md"))
        self.assertGreaterEqual(len(templates), 9, f"风格模板数量不足: {len(templates)}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
