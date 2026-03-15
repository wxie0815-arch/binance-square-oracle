#!/usr/bin/env python3
"""
oracle.py — Binance Square Oracle v1.0 核心引擎
2 次 LLM 调用，完成分析、写作、润色。

- 第一次 LLM 调用：分析 + 写作
  - 输入：按风格路由采集的市场数据 + 风格模板 + 写作规则
  - 输出：初稿 + 预言机评分 + 个人风格指纹
- 第二次 LLM 调用：去 AI 味润色
  - 输入：初稿 + Humanizer 规则
  - 输出：终稿

支持 9 种内置风格 + 用户 DIY 自定义风格。
"""

import json
import os
import re

import config

# ---------------------------------------------------------------------------
# 核心 Prompt 模板
# ---------------------------------------------------------------------------
ANALYSIS_WRITING_PROMPT = """
# Role: Binance Square Top Analyst (Oracle)

## 1. Your Task
Analyze the real-time market data provided below and write a high-quality, engaging article for Binance Square. The article must be in the requested style and follow all writing rules.

## 2. Real-time Market Data
```json
{market_data}
```

## 3. Writing Style: {style_name}
{style_prompt}

## 4. Writing Rules
{writing_rules}

## 5. Your Output (JSON format ONLY)
Provide your response as a single JSON object with three fields:
- `article_draft`: The initial draft of the article (string).
- `oracle_score`: An integer score from 0 to 100, representing your confidence in the market trend based on the data. 0 is extremely bearish, 100 is extremely bullish.
- `style_fingerprint`: A concise, one-sentence summary of the author's writing style based on the provided style prompt.

**Do not add any extra text or explanations outside the JSON object.**
"""

HUMANIZER_PROMPT = """
# Role: AI Content Polisher

## Your Task
Revise the following article draft to make it sound more natural, human, and less like AI-generated content. Remove any overly formal language, clichés, or repetitive sentence structures. Ensure the final text is engaging and authentic.

## Article Draft
```
{article_draft}
```

## Your Output
Provide only the revised, final article text. Do not add any extra text or explanations.
"""

# ---------------------------------------------------------------------------
# 核心函数
# ---------------------------------------------------------------------------
def _load_prompt_template(style_name):
    """
    加载指定风格的 prompt 模板。
    支持内置风格和 DIY 自定义风格（用户在 prompts/ 目录下添加 .md 文件即可）。
    """
    path = os.path.join(config.PROMPTS_DIR, f"{style_name}.md")
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Style '{style_name}' not found at {path}\n"
            f"Available styles: {', '.join(list_available_styles())}\n"
            f"To create a DIY style, add a file: prompts/{style_name}.md"
        )
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _load_writing_rules():
    """加载写作规则 Skill"""
    path = os.path.join(config.SKILLS_DIR, "crypto-content-writer", "SKILL.md")
    if not os.path.exists(path):
        return "No specific writing rules provided."
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def generate_article(market_data, style_name="kol_style", user_intent="BTC analysis"):
    """
    核心入口：2 次 LLM 调用，生成最终文章。
    """
    # --- 第一次 LLM 调用：分析 + 写作 ---
    print(f"[oracle] LLM call 1/2: Analyzing data with '{style_name}' style...")
    style_prompt = _load_prompt_template(style_name)
    writing_rules = _load_writing_rules()

    # 清理 market_data：移除错误项和空字段
    cleaned_data = {}
    for k, v in market_data.items():
        if v is None or (isinstance(v, dict) and "error" in v):
            continue
        if isinstance(v, dict) and v.get("skipped"):
            continue
        cleaned_data[k] = v

    prompt1 = ANALYSIS_WRITING_PROMPT.format(
        market_data=json.dumps(cleaned_data, indent=2, ensure_ascii=False),
        style_name=style_name,
        style_prompt=style_prompt,
        writing_rules=writing_rules,
    )

    response1_raw = config.call_llm(
        system_prompt="You are a crypto analyst.",
        user_prompt=prompt1
    )

    try:
        # 提取 JSON 内容
        match = re.search(r"```json\n(.*?)\n```", response1_raw, re.DOTALL)
        if match:
            json_str = match.group(1)
        else:
            json_str = response1_raw

        response1_json = json.loads(json_str)
        article_draft = response1_json["article_draft"]
        oracle_score = response1_json["oracle_score"]
        style_fingerprint = response1_json["style_fingerprint"]
    except (json.JSONDecodeError, KeyError) as e:
        print(f"[oracle] LLM call 1 failed: cannot parse JSON. Raw response:\n{response1_raw[:500]}")
        return {"error": "Failed to parse LLM response", "raw_response": response1_raw}

    print(f"[oracle] Draft complete. Oracle Score: {oracle_score}/100")

    # --- 第二次 LLM 调用：去 AI 味润色 ---
    print("[oracle] LLM call 2/2: Humanizing...")
    prompt2 = HUMANIZER_PROMPT.format(article_draft=article_draft)
    final_article = config.call_llm(
        system_prompt="You are a content polisher.",
        user_prompt=prompt2
    )

    return {
        "final_article": final_article,
        "article_draft": article_draft,
        "oracle_score": oracle_score,
        "style_fingerprint": style_fingerprint,
        "style_name": style_name,
        "user_intent": user_intent,
    }


def list_available_styles():
    """
    返回 prompts/ 目录下所有可用风格名称列表。
    包括 9 种内置风格和用户添加的 DIY 风格。
    """
    if not os.path.isdir(config.PROMPTS_DIR):
        return []
    return sorted([
        os.path.splitext(f)[0]
        for f in os.listdir(config.PROMPTS_DIR)
        if f.endswith(".md")
    ])


def is_builtin_style(style_name):
    """判断是否为内置风格"""
    builtin = [
        "kol_style", "deep_analysis", "daily_express", "meme_hunter",
        "onchain_insight", "oracle", "project_research", "trading_signal", "tutorial"
    ]
    return style_name in builtin


def run_oracle(symbol="bitcoin", futures_symbol="BTCUSDT", style_name="kol_style",
               user_intent="BTC analysis", enable_l4=False, enable_l8=False):
    """
    主入口：按风格路由采集数据 + 生成文章 + 可选发布。
    """
    from collect import collect_all

    print(f"[oracle] Binance Square Oracle v{config.VERSION}")
    print(f"[oracle] Topic: {user_intent} | Style: {style_name}")
    if not is_builtin_style(style_name):
        print(f"[oracle] DIY style detected: '{style_name}' (using default data route)")

    # 按风格路由采集数据
    market_data = collect_all(
        symbol=symbol,
        futures_symbol=futures_symbol,
        style_name=style_name,
        enable_l4=enable_l4
    )

    # 生成文章
    result = generate_article(market_data, style_name=style_name, user_intent=user_intent)

    # 可选 L8 广场发布
    if enable_l8 and "final_article" in result:
        from publish import publish_to_square
        pub_result = publish_to_square(result["final_article"])
        result["publish_result"] = pub_result
        if pub_result.get("success"):
            print("[oracle] Article published to Binance Square!")
        elif pub_result.get("skipped"):
            print(f"[oracle] Publish skipped: {pub_result.get('reason')}")
        else:
            print(f"[oracle] Publish failed: {pub_result}")

    return result


if __name__ == "__main__":
    print("Available styles:", list_available_styles())
    print("\nTo run the oracle:")
    print("  from oracle import run_oracle")
    print("  result = run_oracle(style_name='deep_analysis')")
