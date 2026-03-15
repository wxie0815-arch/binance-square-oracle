#!/usr/bin/env python3
"""
tests/test_l7_generator.py — oracle.py 核心引擎测试 v1.1
验证 oracle.py 的函数接口、风格加载、数据清理逻辑。
"""

import os
import sys
import json
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import oracle


class TestOracleImports(unittest.TestCase):
    """oracle.py 导入和接口测试"""

    def test_imports_without_error(self):
        """oracle 模块应可正常导入"""
        self.assertIsNotNone(oracle)

    def test_run_oracle_exists(self):
        """run_oracle 函数应存在"""
        self.assertTrue(hasattr(oracle, "run_oracle"))
        self.assertTrue(callable(oracle.run_oracle))

    def test_run_oracle_signature(self):
        """run_oracle 应接受 symbol、futures_symbol、style_name、user_intent 参数"""
        import inspect
        sig = inspect.signature(oracle.run_oracle)
        params = list(sig.parameters.keys())
        for expected in ["symbol", "futures_symbol", "style_name", "user_intent"]:
            self.assertIn(expected, params, f"run_oracle 缺少参数: {expected}")

    def test_no_model_param_in_run_oracle(self):
        """run_oracle 不应接受 model 参数（统一使用 OpenClaw 系统 API）"""
        import inspect
        sig = inspect.signature(oracle.run_oracle)
        self.assertNotIn("model", sig.parameters)


class TestOracleStyleLoading(unittest.TestCase):
    """风格模板加载测试"""

    def test_load_prompt_template_callable(self):
        """_load_prompt_template 应可调用"""
        self.assertTrue(callable(oracle._load_prompt_template))

    def test_load_writing_rules_callable(self):
        """_load_writing_rules 应可调用"""
        self.assertTrue(callable(oracle._load_writing_rules))

    def test_official_styles_available(self):
        """官方 4 种风格模板应可加载"""
        for style in ["daily_express", "deep_analysis", "onchain_insight", "meme_hunter"]:
            result = oracle._load_prompt_template(style)
            self.assertIsInstance(result, str, f"风格模板加载失败: {style}")
            self.assertGreater(len(result), 0)

    def test_extended_styles_available(self):
        """扩展 5 种风格模板应可加载"""
        for style in ["kol_style", "tutorial", "trading_signal", "project_research", "oracle"]:
            result = oracle._load_prompt_template(style)
            self.assertIsInstance(result, str, f"风格模板加载失败: {style}")
            self.assertGreater(len(result), 0)

    def test_total_styles_count(self):
        """应支持至少 9 种风格"""
        styles = [
            "kol_style", "deep_analysis", "daily_express", "meme_hunter",
            "onchain_insight", "oracle", "project_research", "trading_signal", "tutorial"
        ]
        self.assertGreaterEqual(len(styles), 9)


class TestOracleTwoStageFlow(unittest.TestCase):
    """两阶段 LLM 调用流程测试（使用 mock）"""

    @patch("oracle.config.call_llm")
    @patch("collect.collect_all")
    def test_two_stage_flow_with_mock(self, mock_collect, mock_llm):
        """run_oracle 应完成两次 LLM 调用并返回正确结构"""
        mock_collect.return_value = {
            "spot_ticker": {"lastPrice": "85000"},
            "coingecko_price": {"bitcoin": {"usd": 85000}},
            "fear_greed_index": {"data": [{"value": "65", "value_classification": "Greed"}]},
        }
        # 第一次 LLM 调用返回 JSON
        first_response = json.dumps({
            "article_draft": "BTC 今日强势上涨，预言机评分 75 分。",
            "oracle_score": 75,
            "style_fingerprint": "数据驱动，简洁有力"
        })
        # 第二次 LLM 调用返回润色后的文章
        second_response = "BTC 今日强势上涨，预言机评分 75 分（润色版）。"
        mock_llm.side_effect = [first_response, second_response]

        result = oracle.run_oracle(
            symbol="bitcoin",
            futures_symbol="BTCUSDT",
            style_name="kol_style",
            user_intent="BTC 分析"
        )

        self.assertIn("final_article", result)
        self.assertIn("oracle_score", result)
        self.assertIn("article_draft", result)
        self.assertEqual(result["oracle_score"], 75)
        self.assertEqual(mock_llm.call_count, 2)

    @patch("oracle.config.call_llm")
    @patch("collect.collect_all")
    def test_data_digest_integration(self, mock_collect, mock_llm):
        """数据清理逻辑应正确过滤错误项"""
        mock_collect.return_value = {
            "spot_ticker": {"lastPrice": "85000"},
            "bad_field": {"error": "timeout"},
            "none_field": None,
        }
        first_response = json.dumps({
            "article_draft": "测试文章",
            "oracle_score": 60,
            "style_fingerprint": "测试风格"
        })
        mock_llm.side_effect = [first_response, "润色后的测试文章"]

        result = oracle.run_oracle()
        self.assertNotIn("error", result)
        self.assertIn("final_article", result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
