#!/usr/bin/env python3
"""
tests/test_config.py — Configuration tests for v1.0
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class TestConfigCenter(unittest.TestCase):
    """Test unified configuration center v1.0"""

    def test_version(self):
        self.assertEqual(config.VERSION, "1.1")

    def test_prompts_dir_defined(self):
        self.assertTrue(hasattr(config, "PROMPTS_DIR"))
        self.assertIsInstance(config.PROMPTS_DIR, str)

    def test_skills_dir_defined(self):
        self.assertTrue(hasattr(config, "SKILLS_DIR"))
        self.assertIsInstance(config.SKILLS_DIR, str)

    def test_workspace_dir_defined(self):
        self.assertTrue(hasattr(config, "WORKSPACE_DIR"))
        self.assertIsInstance(config.WORKSPACE_DIR, str)

    def test_references_dir_defined(self):
        self.assertTrue(hasattr(config, "REFERENCES_DIR"))
        self.assertIsInstance(config.REFERENCES_DIR, str)

    def test_square_post_base_defined(self):
        self.assertTrue(hasattr(config, "SQUARE_POST_BASE"))
        self.assertIn("binance.com", config.SQUARE_POST_BASE)

    def test_call_llm_callable(self):
        self.assertTrue(callable(config.call_llm))

    def test_square_api_key_optional(self):
        self.assertTrue(hasattr(config, "SQUARE_API_KEY"))
        self.assertIsInstance(config.SQUARE_API_KEY, str)


if __name__ == "__main__":
    unittest.main(verbosity=2)
