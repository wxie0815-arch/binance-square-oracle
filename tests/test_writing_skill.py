#!/usr/bin/env python3
"""
tests/test_writing_skill.py - 写作引擎测试 v1.0 (终版)
================================================================
- 验证 WritingSkill 类的基本功能
- 统一调用 OpenClaw 系统 API，不测试模型选配
"""

import os
import sys
import glob
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestWritingSkillInit(unittest.TestCase):
    """WritingSkill 初始化测试"""

    def test_skills_dir_exists(self):
        """skills 目录应存在"""
        skills_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "skills")
        self.assertTrue(os.path.isdir(skills_dir), f"skills目录不存在: {skills_dir}")

    def test_crypto_content_writer_skill_exists(self):
        """crypto-content-writer skill 应存在"""
        skill_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "skills", "crypto-content-writer", "SKILL.md"
        )
        self.assertTrue(os.path.exists(skill_path), "crypto-content-writer SKILL.md不存在")

    def test_import_writing_skill(self):
        """WritingSkill 应可正常导入"""
        from writing_skill import WritingSkill
        self.assertTrue(callable(WritingSkill))

    def test_instantiation(self):
        """WritingSkill 应可正常实例化"""
        from writing_skill import WritingSkill
        skill = WritingSkill()
        self.assertIsNotNone(skill)

    def test_has_writer_prompt(self):
        """WritingSkill 应有 writer_prompt 属性"""
        from writing_skill import WritingSkill
        skill = WritingSkill()
        self.assertTrue(hasattr(skill, 'writer_prompt'))
        self.assertIsInstance(skill.writer_prompt, str)

    def test_has_generate_article_method(self):
        """WritingSkill 应有 generate_article 方法"""
        from writing_skill import WritingSkill
        skill = WritingSkill()
        self.assertTrue(callable(skill.generate_article))

    def test_no_model_param_in_generate(self):
        """generate_article 不应接受 model 参数（v1.0 终版）"""
        import inspect
        from writing_skill import WritingSkill
        sig = inspect.signature(WritingSkill.generate_article)
        self.assertNotIn('model', sig.parameters,
                         "generate_article 不应有 model 参数，应统一使用 OpenClaw 系统 API")

    def test_no_llm_config_param(self):
        """WritingSkill.__init__ 不应接受 llm_config 参数（v1.0 终版）"""
        import inspect
        from writing_skill import WritingSkill
        sig = inspect.signature(WritingSkill.__init__)
        self.assertNotIn('llm_config', sig.parameters,
                         "WritingSkill 不应有 llm_config 参数，应统一使用 OpenClaw 系统 API")


class TestWritingSkillGenerate(unittest.TestCase):
    """WritingSkill 生成功能测试（使用 mock）"""

    @patch('config.call_llm')
    def test_generate_article_returns_dict(self, mock_llm):
        """generate_article 应返回包含 draft 和 final_article 的字典"""
        mock_llm.return_value = "这是一篇测试文章，关于 $BTC 的最新动态。"
        from writing_skill import WritingSkill
        skill = WritingSkill()
        result = skill.generate_article(
            core_digest="BTC 今日上涨 2.5%",
            style_fingerprint="简洁直接，数据驱动",
            user_prompt="写一篇 BTC 分析",
            style_prompt="oracle 风格"
        )
        self.assertIsInstance(result, dict)
        self.assertIn('draft', result)
        self.assertIn('final_article', result)

    @patch('config.call_llm')
    def test_call_llm_called_twice(self, mock_llm):
        """generate_article 应调用 call_llm 两次（初稿+润色）"""
        mock_llm.return_value = "测试文章内容"
        from writing_skill import WritingSkill
        skill = WritingSkill()
        skill.generate_article(
            core_digest="测试数据",
            style_fingerprint="测试风格",
            user_prompt="测试",
            style_prompt=""
        )
        self.assertEqual(mock_llm.call_count, 2)

    @patch('config.call_llm')
    def test_final_article_not_empty(self, mock_llm):
        """final_article 不应为空"""
        mock_llm.return_value = "有内容的文章。"
        from writing_skill import WritingSkill
        skill = WritingSkill()
        result = skill.generate_article(
            core_digest="数据",
            style_fingerprint="风格",
            user_prompt="写文章",
            style_prompt=""
        )
        self.assertGreater(len(result['final_article']), 0)


class TestPromptTemplates(unittest.TestCase):
    """Prompt 模板测试"""

    def test_prompts_dir_exists(self):
        """prompts 目录应存在"""
        prompts_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts")
        self.assertTrue(os.path.isdir(prompts_dir))

    def test_official_four_styles_exist(self):
        """官方4种风格的 prompt 模板应存在"""
        prompts_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts")
        for style in ["daily_express", "deep_analysis", "onchain_insight", "meme_hunter"]:
            path = os.path.join(prompts_dir, f"{style}.md")
            self.assertTrue(os.path.exists(path), f"官方风格模板不存在: {style}.md")

    def test_extended_styles_exist(self):
        """扩展风格的 prompt 模板应存在"""
        prompts_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts")
        for style in ["kol_style", "tutorial", "trading_signal", "project_research", "oracle"]:
            path = os.path.join(prompts_dir, f"{style}.md")
            self.assertTrue(os.path.exists(path), f"扩展风格模板不存在: {style}.md")

    def test_total_styles_count(self):
        """应有至少9个风格模板"""
        prompts_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts")
        templates = glob.glob(os.path.join(prompts_dir, "*.md"))
        self.assertGreaterEqual(len(templates), 9, f"风格模板数量不足: {len(templates)}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
