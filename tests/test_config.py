#!/usr/bin/env python3
"""
tests/test_config.py — 配置中心测试 v1.1
验证 config.py 的版本号、目录常量、LLM 调用函数等核心属性。
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class TestConfigCenter(unittest.TestCase):
    """测试统一配置中心 v1.1"""

    def test_version(self):
        """版本号应为 1.1"""
        self.assertEqual(config.VERSION, "1.1")

    def test_prompts_dir_defined(self):
        """PROMPTS_DIR 应已定义"""
        self.assertTrue(hasattr(config, "PROMPTS_DIR"))
        self.assertIsInstance(config.PROMPTS_DIR, str)

    def test_skills_dir_defined(self):
        """SKILLS_DIR 应已定义"""
        self.assertTrue(hasattr(config, "SKILLS_DIR"))
        self.assertIsInstance(config.SKILLS_DIR, str)

    def test_workspace_dir_defined(self):
        """WORKSPACE_DIR 应已定义"""
        self.assertTrue(hasattr(config, "WORKSPACE_DIR"))
        self.assertIsInstance(config.WORKSPACE_DIR, str)

    def test_square_post_base_defined(self):
        """SQUARE_POST_BASE 应已定义且包含 binance.com"""
        self.assertTrue(hasattr(config, "SQUARE_POST_BASE"))
        self.assertIn("binance.com", config.SQUARE_POST_BASE)

    def test_call_llm_callable(self):
        """call_llm 应为可调用函数"""
        self.assertTrue(callable(config.call_llm))

    def test_square_api_key_optional(self):
        """SQUARE_API_KEY 应存在（可为空字符串）"""
        self.assertTrue(hasattr(config, "SQUARE_API_KEY"))
        self.assertIsInstance(config.SQUARE_API_KEY, str)

    def test_no_old_attributes(self):
        """旧版属性应已移除"""
        self.assertFalse(hasattr(config, "get_llm_config"))
        self.assertFalse(hasattr(config, "SYSTEM_FALLBACK_MODELS"))
        self.assertFalse(hasattr(config, "HAS_ALPHA_MONITOR"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
