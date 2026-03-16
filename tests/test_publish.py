#!/usr/bin/env python3
"""Publishing helper tests."""

from __future__ import annotations

import unittest

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import publish


class TestPublishHelpers(unittest.TestCase):
    def test_extract_hashtags_deduplicates_defaults(self):
        tags = publish._extract_hashtags("$BTC looks strong. #Binance #BTC #Binance")
        self.assertEqual(tags.count("#Binance"), 1)
        self.assertIn("#BTC", tags)
        self.assertIn("#CryptoAnalysis", tags)

    def test_build_publish_payload_uses_mentioned_coins(self):
        payload = publish._build_publish_payload("BTC and ETH are strong today.")
        self.assertIn("mentionedCoins", payload)
        self.assertIn("BTC", payload["mentionedCoins"])
        self.assertIn("ETH", payload["mentionedCoins"])

    def test_build_publish_payload_appends_missing_markers(self):
        payload = publish._build_publish_payload("BTC is strong today.")
        body = payload["bodyTextOnly"]
        self.assertIn("$BTC", body)
        self.assertIn("#Binance", body)

    def test_publish_without_key_skips(self):
        result = publish.publish_to_square("Test article")
        self.assertTrue(result.get("skipped"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
