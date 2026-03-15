#!/usr/bin/env python3
"""
文章生成引擎 v1.0 (终版)
================================================================
- 彻底移除所有 AI 模型选配配置，统一调用 OpenClaw 系统 API
"""

import os
import json
import re
from glob import glob

from writing_skill import WritingSkill
from data_digest import build_core_digest, digest_to_text

# ---------------------------------------------------------------------------
# 全局初始化
# ---------------------------------------------------------------------------
WRITING_SKILL = WritingSkill()
PROMPT_TEMPLATES = {}

print("[L7] v1.0 | 统一调用 OpenClaw 系统 API")

# ---------------------------------------------------------------------------
# Prompt 模板加载
# ---------------------------------------------------------------------------
def _load_prompt_templates():
    """加载 prompts/ 目录下的所有 .md 文件作为模板"""
    global PROMPT_TEMPLATES
    prompt_dir = os.path.join(os.path.dirname(__file__), "prompts")
    if not os.path.exists(prompt_dir):
        return
    template_files = glob(os.path.join(prompt_dir, "*.md"))
    for f in template_files:
        style_name = os.path.basename(f).replace(".md", "")
        with open(f, "r", encoding="utf-8") as file:
            PROMPT_TEMPLATES[style_name] = file.read()
    if PROMPT_TEMPLATES:
        print(f"[L7] 加载 {len(PROMPT_TEMPLATES)} 个 Prompt 模板: {list(PROMPT_TEMPLATES.keys())}")

_load_prompt_templates()

# ---------------------------------------------------------------------------
# 主流程 v1.0: 二阶段写作 + 数据精简
# ---------------------------------------------------------------------------
def generate_article_v1(
    l0_report: dict = None,
    l1_report: dict = None,
    l2_report: dict = None,
    l3_report: dict = None,
    l4_report: dict = None,
    fusion_report: dict = None,
    skills_data: dict = None,
    l6_fingerprint: dict = None,
    user_intent: str = "",
    style: str = "oracle",
) -> dict:
    """
    二阶段写作流程主函数 (v1.0)

    1. 数据精简: 通过 data_digest 提炼核心情报
    2. 生成初稿: 调用 crypto-content-writer skill
    3. 去AI味润色: 内置 humanizer 规则
    """
    print(f"\n[L7] v1.0 文章生成 | 风格: {style} | 意图: {user_intent[:50]}")

    # --- 步骤 1: 数据精简 ---
    print("[L7] 步骤1: 数据精简 (data_digest)...")
    core_digest = build_core_digest(
        l0_report=l0_report,
        l1_report=l1_report,
        l2_report=l2_report,
        l3_report=l3_report,
        l4_report=l4_report,
        fusion_report=fusion_report,
        skills_data=skills_data,
    )
    core_text = digest_to_text(core_digest)
    print(f"  精简完成: {len(core_text)} 字符")

    # --- 步骤 2: 二阶段写作 ---
    result = WRITING_SKILL.generate_article(
        core_digest=core_text,
        style_fingerprint=l6_fingerprint or {},
        user_prompt=user_intent,
        style_prompt=PROMPT_TEMPLATES.get(style, ""),
    )

    result["style"] = style
    result["user_intent"] = user_intent
    result["core_digest"] = core_digest
    result["core_text_length"] = len(core_text)

    return result

# ---------------------------------------------------------------------------
# oracle_main.py 主接口（v1.0）
# ---------------------------------------------------------------------------
def generate_article(
    square_report: dict = None,
    skills_data: dict = None,
    fusion_report: dict = None,
    style: str = "oracle",
    combo: str = None,
    topic: str = None,
    token_symbol: str = None,
    user_prompt: str = None,
    min_words: int = 700,
    l1_report: dict = None,
    l2_report: dict = None,
    l3_report: dict = None,
    l4_report: dict = None,
    l6_fingerprint: dict = None,
    l0_result: dict = None,
    user_intent: str = None,
) -> dict:
    """
    oracle_main.py 调用的主接口（v1.0）
    """
    _l0 = square_report or l0_result or {}

    if user_prompt:
        intent = user_prompt
    elif topic:
        intent = f"写一篇关于{topic}的{style}风格文章"
    elif user_intent:
        intent = user_intent
    else:
        intent = "根据最新市场数据，生成一篇有深度的加密货币分析文章"

    result_v1 = generate_article_v1(
        l0_report=_l0,
        l1_report=l1_report,
        l2_report=l2_report,
        l3_report=l3_report,
        l4_report=l4_report,
        fusion_report=fusion_report,
        skills_data=skills_data,
        l6_fingerprint=l6_fingerprint,
        user_intent=intent,
        style=style,
    )

    final_article = result_v1.get("final_article", "")
    word_count = len(final_article)

    return {
        "article": final_article,
        "word_count": word_count,
        "meets_min_words": word_count >= min_words,
        "title": _extract_title(final_article),
        "hashtags": _extract_hashtags(final_article),
        "style": style,
        "user_intent": intent,
        "draft": result_v1.get("draft", ""),
        "core_digest": result_v1.get("core_digest", {}),
        "core_text_length": result_v1.get("core_text_length", 0),
    }

# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------
def _extract_title(article: str) -> str:
    if not article:
        return ""
    lines = article.strip().split("\n")
    for line in lines:
        line = line.strip()
        if line.startswith("#"):
            return line.lstrip("#").strip()
        if line:
            return line[:60]
    return ""

def _extract_hashtags(article: str) -> list:
    if not article:
        return []
    tags = re.findall(r'#(\w+)', article)
    return list(dict.fromkeys(tags))[:10]

# ---------------------------------------------------------------------------
# 独立测试
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=== L7 文章生成引擎 v1.0 独立测试 ===")

    mock_fusion = {
        "oracle_score": 72,
        "oracle_rating": "流量活跃期",
        "fused_sentiment": {"label": "偏多", "fused_score": 62, "advice": "市场偏暖，适合发布行情分析"},
        "fused_coins": [
            {"symbol": "BTC", "confidence": "HIGH", "sources": ["L0", "L1", "L3"], "details": {"change_24h": "2.5"}},
            {"symbol": "SOL", "confidence": "MEDIUM", "sources": ["L1", "L2"], "details": {"onchain_direction": "buy"}},
        ],
        "fused_topics": [
            {"topic": "Layer2", "fusion_score": 85},
            {"topic": "RWA", "fusion_score": 72},
        ],
        "content_strategy": {
            "recommended_content_types": ["行情分析", "操作记录"],
            "recommended_coins": ["BTC", "SOL", "ETH"],
        },
        "timing_advice": {"window": "晚间黄金期"},
    }

    result = generate_article(
        fusion_report=mock_fusion,
        style="oracle",
        user_prompt="写一篇今日市场综合分析",
        min_words=700,
    )
    print(f"\n[结果] 文章字数: {result['word_count']}")
    print(f"[结果] 达标: {result['meets_min_words']}")
    print(f"[结果] 标题: {result['title']}")
    print(f"[结果] 数据精简长度: {result['core_text_length']} 字符")
    print(f"[结果] 文章预览:\n{result['article'][:300]}...")
