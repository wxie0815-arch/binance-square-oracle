#!/usr/bin/env python3
"""
tests/test_config.py - 配置中心测试 v1.0 (终版)
================================================================
- 验证 config.py 的统一配置中心功能
- 验证 OpenClaw 系统 API 调用接口
- 彻底移除旧版 get_llm_config / SYSTEM_FALLBACK_MODELS 测试
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class TestConfigCenter(unittest.TestCase):
    """测试统一配置中心 v1.0"""

    def test_version(self):
        """版本号应为 1.0"""
        self.assertEqual(config.VERSION, "1.0")

    def test_project_name(self):
        """项目名称应存在"""
        self.assertEqual(config.PROJECT_NAME, "Binance Square Oracle")

    def test_workspace_defined(self):
        """WORKSPACE 路径应已定义"""
        self.assertIsNotNone(config.WORKSPACE)
        self.assertIsInstance(config.WORKSPACE, str)

    def test_api_urls_defined(self):
        """所有 API URL 应已定义"""
        self.assertTrue(config.SQUARE_POST_URL.startswith("https://"))
        self.assertTrue(config.ALPHA_BASE_URL.startswith("https://"))
        self.assertTrue(config.FAPI_BASE_URL.startswith("https://"))
        self.assertTrue(config.FUTURES_DATA_URL.startswith("https://"))

    def test_optional_module_flags(self):
        """可选模块标志应为布尔值"""
        self.assertIsInstance(config.HAS_ALPHA_MONITOR, bool)
        self.assertIsInstance(config.HAS_DERIVATIVES_DATA, bool)
        self.assertIsInstance(config.HAS_6551_API, bool)
        self.assertIsInstance(config.HAS_SQUARE_API, bool)

    def test_call_llm_is_callable(self):
        """call_llm 函数应可调用"""
        self.assertTrue(callable(config.call_llm))

    def test_http_helpers_callable(self):
        """http_get 和 http_post 应可调用"""
        self.assertTrue(callable(config.http_get))
        self.assertTrue(callable(config.http_post))

    def test_no_model_selection_config(self):
        """config.py 不应包含 AI 模型选配逻辑（v1.0 终版）"""
        self.assertFalse(hasattr(config, 'get_llm_config'),
                         "get_llm_config 应已从 config.py 中移除")
        self.assertFalse(hasattr(config, 'SYSTEM_FALLBACK_MODELS'),
                         "SYSTEM_FALLBACK_MODELS 应已从 config.py 中移除")
        self.assertFalse(hasattr(config, 'SYSTEM_DEFAULT_MODEL'),
                         "SYSTEM_DEFAULT_MODEL 应已从 config.py 中移除")
        self.assertFalse(hasattr(config, 'PUCODE_API_KEY'),
                         "PUCODE_API_KEY 应已从 config.py 中移除")
        self.assertFalse(hasattr(config, 'PUCODE_CHAT_URL'),
                         "PUCODE_CHAT_URL 应已从 config.py 中移除")

    def test_get_llm_client_callable(self):
        """get_llm_client 函数应可调用"""
        self.assertTrue(callable(config.get_llm_client))

    def test_http_timeout_valid(self):
        """HTTP 超时应为正整数"""
        self.assertGreater(config.DEFAULT_TIMEOUT, 0)

    def test_max_retries_valid(self):
        """最大重试次数应为正整数"""
        self.assertGreater(config.MAX_RETRIES, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
