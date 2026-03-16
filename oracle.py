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

MAX_RETRIES = 2  # JSON 解析失败时的最大重试次数

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
Respond with ONLY a valid JSON object. No extra text before or after.
Keep `article_draft` concise (under 800 characters) to avoid truncation.

```json
{{
  "article_draft": "<your article here, max 800 chars>",
  "oracle_score": <integer 0-100>,
  "style_fingerprint": "<one sentence describing the writing style>"
}}
```

**CRITICAL: The JSON must be complete and valid. Do not truncate.**
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
# JSON 解析辅助函数
# ---------------------------------------------------------------------------
def _parse_llm_json(raw_text):
    """
    尝试从 LLM 响应中解析 JSON。
    支持多种格式：纯 JSON、```json 代码块、内嵌 JSON 等。
    """
    if not raw_text or not raw_text.strip():
        return None

    # 方法1: 尝试直接解析整个响应
    try:
        return json.loads(raw_text.strip())
    except json.JSONDecodeError:
        pass

    # 方法2: 提取 ```json ... ``` 代码块
    match = re.search(r'```json\s*\n(.*?)\n```', raw_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # 方法3: 提取第一个 { ... } 块
    brace_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass

    # 方法4: 尝试修复截断的 JSON（添加缺失的结尾）
    # 找到最后一个完整的字段
    truncated = raw_text.strip()
    if truncated.startswith('{'):
        # 尝试修复：找到最后一个完整的属性
        for end_pattern in [r'"oracle_score"\s*:\s*(\d+)', r'"style_fingerprint"\s*:\s*"([^"]*?)"']:
            m = re.search(end_pattern, truncated)
            if m:
                # 找到了部分内容，返回 None 以触发重试
                pass

    return None


def _extract_draft_fallback(raw_text):
    """从截断的 LLM 响应中尝试提取 article_draft"""
    # 尝试提取 article_draft 字段的内容
    match = re.search(r'"article_draft"\s*:\s*"(.*?)(?:",|"\s*,|"\s*})', raw_text, re.DOTALL)
    if match:
        draft = match.group(1)
        # 处理 JSON 转义字符
        draft = draft.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')
        return draft.strip()

    # 如果无法提取，尝试获取 article_draft 开头后的内容（即使是截断的）
    match2 = re.search(r'"article_draft"\s*:\s*"(.*)', raw_text, re.DOTALL)
    if match2:
        draft = match2.group(1)
        # 移除末尾不完整的部分
        draft = draft.rstrip('\n').rstrip(',')
        if draft.endswith('"'):
            draft = draft[:-1]
        draft = draft.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')
        # 确保至少有 50 个字符
        if len(draft.strip()) >= 50:
            return draft.strip() + "..."
    return None


def _extract_score_fallback(raw_text):
    """从截断的 LLM 响应中尝试提取 oracle_score"""
    match = re.search(r'"oracle_score"\s*:\s*(\d+)', raw_text)
    if match:
        score = int(match.group(1))
        return max(0, min(100, score))
    return 50  # 默认中性评分


def _extract_fingerprint_fallback(raw_text):
    """从截断的 LLM 响应中尝试提取 style_fingerprint"""
    match = re.search(r'"style_fingerprint"\s*:\s*"([^"]{10,}?)"', raw_text)
    if match:
        return match.group(1)
    return "Style-driven crypto analysis"


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
    path = os.path.join(config.REFERENCES_DIR, "writing_rules.md")
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

    article_draft = None
    oracle_score = 50
    style_fingerprint = ""
    last_raw = ""

    for attempt in range(1, MAX_RETRIES + 2):  # 最多尝试 MAX_RETRIES+1 次
        if attempt > 1:
            print(f"[oracle] Retry {attempt-1}/{MAX_RETRIES}: re-requesting LLM...")

        response1_raw = config.call_llm(
            system_prompt="You are a crypto analyst. Always respond with valid, complete JSON only.",
            user_prompt=prompt1
        )
        last_raw = response1_raw

        parsed = _parse_llm_json(response1_raw)
        if parsed is not None:
            article_draft = parsed.get("article_draft", "")
            oracle_score = parsed.get("oracle_score", 50)
            style_fingerprint = parsed.get("style_fingerprint", "")
            break
        else:
            print(f"[oracle] Attempt {attempt}: JSON parse failed.")

    if article_draft is None:
        print(f"[oracle] All {MAX_RETRIES+1} attempts failed. Attempting fallback extraction...")
        # Fallback：尝试从截断的响应中提取部分内容
        article_draft = _extract_draft_fallback(last_raw)
        if not article_draft:
            print(f"[oracle] Fallback failed. Raw response:\n{last_raw[:500]}")
            return {"error": "Failed to parse LLM response after retries", "raw_response": last_raw}
        oracle_score = _extract_score_fallback(last_raw)
        style_fingerprint = _extract_fingerprint_fallback(last_raw)

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
