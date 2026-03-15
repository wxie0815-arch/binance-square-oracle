#!/usr/bin/env python3
"""
tests/test_l7_generator.py - L7 文章生成器测试 v1.0 (终版)
================================================================
- 适配 v1.0 终版接口（移除旧版 v4 接口引用）
- 统一调用 OpenClaw 系统 API，不测试模型选配
"""

import os
import sys
import json
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestL7StyleLoading(unittest.TestCase):
    """L7 风格加载测试"""

    def test_l7_imports_without_error(self):
        """L7 应能正常导入"""
        import L7_article_generator as L7
        self.assertIsNotNone(L7)

    def test_official_styles_available(self):
        """官方4种风格应在 PROMPT_TEMPLATES 中"""
        import L7_article_generator as L7
        for style in ["daily_express", "deep_analysis", "onchain_insight", "meme_hunter"]:
            self.assertIn(style, L7.PROMPT_TEMPLATES, f"官方风格缺失: {style}")

    def test_extended_styles_available(self):
        """扩展风格应在 PROMPT_TEMPLATES 中"""
        import L7_article_generator as L7
        for style in ["kol_style", "tutorial", "trading_signal", "project_research", "oracle"]:
            self.assertIn(style, L7.PROMPT_TEMPLATES, f"扩展风格缺失: {style}")

    def test_total_styles_count(self):
        """应有至少9种风格"""
        import L7_article_generator as L7
        self.assertGreaterEqual(len(L7.PROMPT_TEMPLATES), 9)


class TestL7Interfaces(unittest.TestCase):
    """L7 接口兼容性测试"""

    def test_generate_article_v1_exists(self):
        """generate_article_v1 函数应存在"""
        import L7_article_generator as L7
        self.assertTrue(callable(L7.generate_article_v1))

    def test_generate_article_exists(self):
        """主接口 generate_article 应存在"""
        import L7_article_generator as L7
        self.assertTrue(callable(L7.generate_article))

    def test_generate_article_v1_signature(self):
        """generate_article_v1 应接受正确的参数"""
        import inspect
        import L7_article_generator as L7
        sig = inspect.signature(L7.generate_article_v1)
        params = list(sig.parameters.keys())
        self.assertIn("fusion_report", params)
        self.assertIn("skills_data", params)
        self.assertIn("l6_fingerprint", params)
        self.assertIn("user_intent", params)
        self.assertIn("style", params)

    def test_no_model_param_in_generate(self):
        """generate_article 不应接受 model 参数（v1.0 终版）"""
        import inspect
        import L7_article_generator as L7
        sig = inspect.signature(L7.generate_article)
        self.assertNotIn('model', sig.parameters,
                         "generate_article 不应有 model 参数，应统一使用 OpenClaw 系统 API")


class TestL7TwoStageFlow(unittest.TestCase):
    """L7 二阶段写作流程测试"""

    def test_two_stage_flow_with_mock(self):
        """二阶段流程应能正常运行（使用 Mock WritingSkill）"""
        import L7_article_generator as L7

        mock_draft = "这是文章初稿内容，包含市场分析和数据。"
        mock_final = "这是经过人性化处理的最终文章，读起来更自然。"

        mock_result = {
            "draft": mock_draft,
            "final_article": mock_final,
        }

        with patch.object(L7.WRITING_SKILL, "generate_article", return_value=mock_result):
            result = L7.generate_article_v1(
                fusion_report={
                    "oracle_score": 72,
                    "fused_sentiment": {"label": "偏多", "fused_score": 62, "advice": "测试"},
                    "fused_coins": [{"symbol": "BTC", "confidence": "HIGH", "sources": ["L0"], "details": {}}],
                    "fused_topics": [{"topic": "Layer2", "fusion_score": 85}],
                },
                user_intent="生成一篇市场分析文章",
                style="oracle"
            )

            self.assertIsInstance(result, dict)
            self.assertIn("final_article", result)
            self.assertIn("draft", result)
            self.assertIn("style", result)
            self.assertIn("core_digest", result)
            self.assertEqual(result["style"], "oracle")
            self.assertEqual(result["final_article"], mock_final)

    def test_data_digest_integration(self):
        """数据精简层应正确提取核心数据"""
        from data_digest import build_core_digest, digest_to_text

        mock_fusion = {
            "fused_sentiment": {"label": "偏多", "fused_score": 62, "advice": "测试"},
            "fused_coins": [{"symbol": "BTC", "confidence": "HIGH", "sources": ["L0"], "details": {}}],
            "fused_topics": [{"topic": "Layer2", "fusion_score": 85}],
        }

        digest = build_core_digest(fusion_report=mock_fusion)
        self.assertIn("sentiment", digest)
        self.assertIn("top_coins", digest)
        self.assertIn("top_topics", digest)

        text = digest_to_text(digest)
        self.assertIsInstance(text, str)
        self.assertGreater(len(text), 0)
        self.assertIn("偏多", text)
        self.assertIn("BTC", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
