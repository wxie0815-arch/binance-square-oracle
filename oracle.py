#!/usr/bin/env python3
"""
oracle.py — C 方案核心 v1.1
2次 LLM 调用，完成分析、写作、润色，保留全部核心特色

- 第一次 LLM 调用：分析+写作
  - 输入：全部采集数据 + 9种风格模板 + 写作规则
  - 输出：初稿 + 预言机评分 + 个人风格指纹
- 第二次 LLM 调用：去AI味润色
  - 输入：初稿 + Humanizer 规则
  - 输出：终稿
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
    """加载指定风格的 prompt 模板"""
    path = os.path.join(config.PROMPTS_DIR, f"{style_name}.md")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Style \'{style_name}\' not found at {path}")
    with open(path, "r") as f:
        return f.read()

def _load_writing_rules():
    """加载写作规则 skill"""
    path = os.path.join(config.SKILLS_DIR, "crypto-content-writer", "SKILL.md")
    if not os.path.exists(path):
        return "No specific writing rules provided."
    with open(path, "r") as f:
        return f.read()

def generate_article(market_data, style_name="kol_style", user_intent="BTC深度分析"):
    """
    C 方案核心入口：2次 LLM 调用，生成最终文章
    """
    # --- 第一次 LLM 调用：分析+写作 ---
    print(f"[oracle] 第一次 LLM 调用：分析数据并以 {style_name} 风格写作...")
    style_prompt = _load_prompt_template(style_name)
    writing_rules = _load_writing_rules()
    
    # 清理 market_data：移除错误项和空字段
    cleaned_data = {}
    for k, v in market_data.items():
        if v is None or (isinstance(v, dict) and "error" in v):
            continue
        cleaned_data[k] = v
    
    prompt1 = ANALYSIS_WRITING_PROMPT.format(
        market_data=json.dumps(cleaned_data, indent=2, ensure_ascii=False),
        style_name=style_name,
        style_prompt=style_prompt,
        writing_rules=writing_rules,
    )
    
    response1_raw = config.call_llm(system_prompt="You are a crypto analyst.", user_prompt=prompt1)
    
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
        print(f"[oracle] 第一次 LLM 调用失败：无法解析 JSON。原始响应：\n{response1_raw}")
        return {"error": "Failed to parse LLM response", "raw_response": response1_raw}

    print(f"[oracle] 初稿完成。预言机评分: {oracle_score}/100")

    # --- 第二次 LLM 调用：去AI味润色 ---
    print("[oracle] 第二次 LLM 调用：去AI味润色...")
    prompt2 = HUMANIZER_PROMPT.format(article_draft=article_draft)
    final_article = config.call_llm(system_prompt="You are a content polisher.", user_prompt=prompt2)

    return {
        "final_article": final_article,
        "article_draft": article_draft,
        "oracle_score": oracle_score,
        "style_fingerprint": style_fingerprint,
        "style_name": style_name,
        "user_intent": user_intent,
    }


def list_available_styles():
    """返回 prompts/ 目录下所有可用风格名称列表"""
    if not os.path.isdir(config.PROMPTS_DIR):
        return []
    return [
        os.path.splitext(f)[0]
        for f in os.listdir(config.PROMPTS_DIR)
        if f.endswith(".md")
    ]


def run_oracle(symbol="bitcoin", futures_symbol="BTCUSDT", style_name="kol_style", user_intent="BTC深度分析", enable_l4=False):
    """
    C 方案主入口：采集数据 + 生成文章。
    """
    from collect import collect_all
    print(f"[oracle] 启动预言机 v1.1 | 主题: {user_intent} | 风格: {style_name}")
    market_data = collect_all(symbol=symbol, futures_symbol=futures_symbol)
    return generate_article(market_data, style_name=style_name, user_intent=user_intent)


if __name__ == "__main__":
    # 用于测试的模拟数据
    mock_market_data = {
        "coingecko_price": {"bitcoin": {"usd": 68500, "usd_24h_vol": 25000000000, "usd_24h_change": 2.5, "usd_7d_change": -5.1}},
        "fear_greed_index": {"data": [{"value": "25", "value_classification": "Extreme Fear"}]},
        "social_hype_rank": {"data": {"leaderBoardList": [{"metaInfo": {"symbol": "PEPE"}}]}},
    }
    result = generate_article(mock_market_data)
    print("\n--- FINAL ARTICLE ---\n")
    print(result.get("final_article", "Generation failed."))
