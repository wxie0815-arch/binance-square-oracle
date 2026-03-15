#!/usr/bin/env python3
"""
L6 文章生成引擎 - Article Generator v1.0 (终版)
================================================================
- 彻底移除所有 AI 模型选配配置，统一调用 OpenClaw 系统 API
"""

import os
import sys
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)
import config
import json
import re
import subprocess
import glob
from datetime import datetime, timezone, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE = config.WORKSPACE

STYLE_FILE = f"{WORKSPACE}/memory/oracle-style.md"
PATTERN_FILE = f"{WORKSPACE}/memory/engagement_patterns.md"
MASTERY_FILE = f"{WORKSPACE}/memory/writing_mastery.md"
ANALYZER_SCRIPT = os.path.abspath(os.path.join(SCRIPT_DIR, "skills", "binance-square-profile-analyzer", "scripts", "binance_profile_analyzer.py"))

DEFAULT_STYLE_USER = os.environ.get("STYLE_SOURCE_USER", "binance_square_official")
FINGERPRINT_TTL_HOURS = 24

CST = timezone(timedelta(hours=8))

# ---------------------------------------------------------------------------
# 统一 LLM 调用（直接使用 OpenClaw 系统 API）
# ---------------------------------------------------------------------------
def _call_llm(prompt: str, system_prompt: str = None, max_tokens: int = 1000) -> str:
    sys_p = system_prompt or "你是一名顶级的加密货币内容创作者，专注于币安广场。"
    try:
        return config.call_llm(
            system_prompt=sys_p,
            user_prompt=prompt,
            max_tokens=max_tokens
        )
    except Exception as e:
        print(f"[L6] LLM 调用失败: {e}")
        return ""

# ---------------------------------------------------------------------------
# 读取静态风格档案
# ---------------------------------------------------------------------------
def load_style_guide() -> str:
    try:
        if os.path.exists(STYLE_FILE):
            with open(STYLE_FILE, "r", encoding="utf-8") as f:
                return f.read()
    except Exception:
        pass
    return "专业加密预言机风格：数据驱动，客观中性，多用数据表格，结构清晰，包含风险提示。"

def load_engagement_patterns() -> str:
    try:
        if os.path.exists(PATTERN_FILE):
            with open(PATTERN_FILE, "r", encoding="utf-8") as f:
                return f.read()
    except Exception:
        pass
    return ""

def load_writing_mastery() -> str:
    try:
        if os.path.exists(MASTERY_FILE):
            with open(MASTERY_FILE, "r", encoding="utf-8") as f:
                return f.read()
    except Exception:
        pass
    return ""

# ---------------------------------------------------------------------------
# 按需分析任意用户风格（带7天缓存）
# ---------------------------------------------------------------------------
def analyze_user_style(username: str, max_posts: int = 100) -> str:
    import time as _time
    cache_dir = f"{WORKSPACE}/memory/style_cache"
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = f"{cache_dir}/{username}.md"

    if os.path.exists(cache_file):
        age_days = (_time.time() - os.path.getmtime(cache_file)) / 86400
        if age_days < 7:
            with open(cache_file, "r", encoding="utf-8") as f:
                cached = f.read()
            if cached.strip():
                print(f"[L6] 命中风格缓存: {username}（{age_days:.1f}天前）")
                return cached

    if not os.path.exists(ANALYZER_SCRIPT):
        print(f"[L6] analyzer脚本不存在，跳过风格分析")
        return ""

    print(f"[L6] 分析用户风格: {username}（抓取{max_posts}条帖子）...")
    try:
        out_dir = f"/tmp/style_analysis_{username}"
        os.makedirs(out_dir, exist_ok=True)
        result = subprocess.run(
            [sys.executable, ANALYZER_SCRIPT, "analyze", username,
             "--output", out_dir, "--max-posts", str(max_posts)],
            capture_output=True, text=True, timeout=120,
            cwd=os.path.dirname(ANALYZER_SCRIPT)
        )
        md_files = glob.glob(f"{out_dir}/analysis_report_*.md")
        if md_files:
            with open(md_files[0], "r", encoding="utf-8") as f:
                full_report = f.read()
            summary = full_report[:1500]
            with open(cache_file, "w", encoding="utf-8") as f:
                f.write(f"# {username} 写作风格分析\n")
                f.write(f"> 分析时间: {datetime.now(CST).strftime('%Y-%m-%d %H:%M CST')}\n\n")
                f.write(summary)
            print(f"[L6] 风格分析完成，已缓存: {cache_file}")
            return summary
        else:
            print(f"[L6] 未找到分析报告，stderr: {result.stderr[:200]}")
    except Exception as e:
        print(f"[L6] 风格分析失败: {e}")
    return ""

# ---------------------------------------------------------------------------
# 动态抓取近期帖子样本
# ---------------------------------------------------------------------------
def fetch_recent_posts(n: int = 10, username: str = None) -> list:
    target = username or DEFAULT_STYLE_USER
    try:
        out_dir = f"/tmp/style_sample_{target}"
        os.makedirs(out_dir, exist_ok=True)
        result = subprocess.run(
            [sys.executable, ANALYZER_SCRIPT, "analyze", target,
             "--output", out_dir, "--max-posts", str(max(n * 3, 30))],
            capture_output=True, text=True, timeout=90,
            cwd=os.path.dirname(ANALYZER_SCRIPT)
        )
        json_candidates = glob.glob(f"{out_dir}/posts_*.json")
        if json_candidates:
            with open(json_candidates[0], "r", encoding="utf-8") as f:
                data = json.load(f)
            posts = data if isinstance(data, list) else data.get("posts", [])
            short_posts = [p for p in posts if p.get("content_type", "") in ("short_post", "")]
            short_posts.sort(key=lambda x: x.get("published_at", ""), reverse=True)
            return short_posts[:n]
        else:
            print(f"[L6] 未找到帖子文件，stderr: {result.stderr[:200]}")
    except Exception as e:
        print(f"[L6] 抓取近期帖子失败: {e}")
    return []

# ---------------------------------------------------------------------------
# 风格指纹提炼（带24h缓存）
# ---------------------------------------------------------------------------
def distill_style_fingerprint(style_guide: str, recent_posts: list, username: str = "oracle") -> str:
    import time as _time
    cache_dir = f"{WORKSPACE}/memory/style_cache"
    os.makedirs(cache_dir, exist_ok=True)
    fp_file = f"{cache_dir}/{username}_fingerprint.md"

    if os.path.exists(fp_file):
        age_h = (_time.time() - os.path.getmtime(fp_file)) / 3600
        if age_h < FINGERPRINT_TTL_HOURS:
            with open(fp_file, "r", encoding="utf-8") as f:
                cached = f.read()
            if cached.strip():
                print(f"[L6] 命中风格指纹缓存: {username}（{age_h:.1f}h前）")
                return cached

    print(f"[L6] 提炼风格指纹: {username}...")
    sample_texts = ""
    if recent_posts:
        samples = [p.get("content", "")[:200] for p in recent_posts[:10] if p.get("content")]
        sample_texts = "\n".join([f'  [{i+1}] "{s}"' for i, s in enumerate(samples)])

    distill_prompt = f"""你是一个写作风格分析专家。请分析以下写作样本，提炼出结构化的风格指纹。

## 静态风格档案参考
{style_guide[:800]}

## 近期真实帖子样本（{len(recent_posts)}条）
{sample_texts if sample_texts else "（无样本）"}

## 任务
从以上样本中提炼出严格的风格指纹，输出以下结构（每项不超过3点，要具体可执行）：

### 开头句式（最常见的3种钩子句式）
- 

### 高频关键词/词组
- 

### 句式节奏
- 

### 情绪基调
- 

### 结尾模式
- 

### 绝对禁忌
- 

只输出以上结构，不要解释，不要多余内容："""

    fingerprint = _call_llm(distill_prompt, max_tokens=600)
    if fingerprint:
        ts = datetime.now(CST).strftime("%Y-%m-%d %H:%M CST")
        with open(fp_file, "w", encoding="utf-8") as f:
            f.write(f"# {username} 风格指纹\n> 提炼时间: {ts}\n\n{fingerprint}")
        print(f"[L6] 风格指纹提炼完成，已缓存: {fp_file}")
        return fingerprint

    print("[L6] 指纹提炼失败，降级使用静态档案")
    return style_guide[:600]

# ---------------------------------------------------------------------------
# 构建写作提示词
# ---------------------------------------------------------------------------
def build_prompt(fusion_report: dict, style_guide: str, recent_posts: list,
                 max_words: int = 150, patterns: str = "", mastery: str = "",
                 style_fingerprint: str = "") -> str:
    fused_topics = fusion_report.get("fused_topics", [])[:3]
    fused_coins = fusion_report.get("fused_coins", [])[:3]
    sentiment = fusion_report.get("fused_sentiment", {})
    headlines = fusion_report.get("headlines", [])[:3]
    oracle_score = fusion_report.get("oracle_score", 50)

    topics_str = " / ".join([t["topic"] for t in fused_topics]) if fused_topics else "市场动态"
    coins_str = " / ".join([f"${c['symbol'].replace('USDT','')}" for c in fused_coins]) if fused_coins else "$BTC"
    sentiment_label = sentiment.get("label", "中性")
    sentiment_score = sentiment.get("fused_score", 50)
    headline_examples = "\n".join([f"  - {h}" for h in headlines]) if headlines else ""

    if max_words <= 150:
        structure = "结构: 钩子(1句) → 背景(2-3句) → 转折(1句) → 结果(数字) → 开放结尾(问句)"
        length_req = "长度：60-150字"
    else:
        structure = """结构（长文）：
1. 钩子（1-2句）：强烈事实或反常数据，直接开门见山
2. 背景（3-5句）：交代当前市场状况，用具体数字支撑
3. 核心观点（5-8句）：从数据出发分析，不给结论，描述现象
4. 转折（2-3句）：提出市场上容易忽视的反向信号或矛盾点
5. 历史对比（3-5句）：类似情况历史上怎么走的，中性描述
6. 开放结尾（1-2句）：抛出问题，引发读者思考，绝不下定论"""
        length_req = f"长度：{max_words}字左右（可在±100字范围内）"

    style_section = style_fingerprint if style_fingerprint else style_guide

    prompt = f"""你是无邪Infinity，一个Web3博主和交易员，在币安广场（Binance Square）发帖。

## 锁定风格指纹（严格按此执行，不得偏离）
{style_section}

## 广场当前高互动规律（参考但不照抄）
{patterns if patterns else "（无规律数据）"}

## 爆款写作法则
{mastery[:800] if mastery else "（无法则数据）"}

## 当前市场数据（预言机评分: {oracle_score}/100）
- 热点话题：{topics_str}
- 关注代币：{coins_str}
- 市场情绪：{sentiment_label}（{sentiment_score}/100）
- 标题参考：
{headline_examples}

## 写作任务
根据以上数据，写一篇币安广场帖子。

{length_req}
{structure}
代币格式：$BTC / $ETH（大写，加$符号）

完全禁止：
- emoji或任何表情符号
- 排比三段式
- "赋能/底层逻辑/干货/不得不说/值得注意"等AI词
- 升华式结尾（"让我们一起……"等）
- 下定论（不说"一定会/肯定/必然"）

只输出帖子正文，不要标题、不要解释、不要markdown格式："""

    return prompt

# ---------------------------------------------------------------------------
# 后处理：去除残留AI痕迹
# ---------------------------------------------------------------------------
def post_process(text: str) -> str:
    emoji_pattern = re.compile(
        "[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F9FF\U0000200D\u2600-\u26FF\u2700-\u27BF]+",
        flags=re.UNICODE
    )
    text = emoji_pattern.sub("", text)
    bad_starts = ["当然", "好的", "以下是", "这是一篇", "根据"]
    for s in bad_starts:
        if text.startswith(s):
            text = text[len(s):].lstrip("，。：:")
    banned = ["赋能", "底层逻辑", "干货", "升华", "共识", "价值洼地"]
    for word in banned:
        text = text.replace(word, "")
    return text.strip()

# ---------------------------------------------------------------------------
# 主函数
# ---------------------------------------------------------------------------
def generate_article(fusion_report: dict, use_recent_posts: bool = True,
                     max_words: int = 150, style_user: str = None) -> str:
    """生成广场文章"""
    target_user = style_user or DEFAULT_STYLE_USER
    print(f"[L6] 加载写作风格档案（风格来源: {target_user}）...")

    if style_user and style_user != DEFAULT_STYLE_USER:
        style_guide = analyze_user_style(style_user, max_posts=100)
        if not style_guide:
            print(f"[L6] 无法分析 {style_user} 风格，回退到默认档案")
            style_guide = load_style_guide()
    else:
        style_guide = load_style_guide()

    patterns = load_engagement_patterns()
    mastery = load_writing_mastery()

    recent_posts = []
    if use_recent_posts and os.path.exists(ANALYZER_SCRIPT):
        print(f"[L6] 抓取 {target_user} 近期帖子样本...")
        recent_posts = fetch_recent_posts(10, username=target_user)
        print(f"[L6] 获取 {len(recent_posts)} 条样本帖子")
    else:
        print("[L6] 跳过实时抓取，使用静态风格档案")

    print("[L6] 提炼风格指纹，锁定写作风格...")
    style_fingerprint = distill_style_fingerprint(style_guide, recent_posts, username=target_user)

    print("[L6] 构建写作提示词...")
    prompt = build_prompt(fusion_report, style_guide, recent_posts, max_words=max_words,
                          patterns=patterns, mastery=mastery, style_fingerprint=style_fingerprint)

    max_tokens = max(400, max_words * 3)
    print("[L6] 调用 OpenClaw LLM 生成文章...")
    raw_article = _call_llm(prompt, max_tokens=max_tokens)

    if not raw_article:
        return "[L6错误] 文章生成失败"

    article = post_process(raw_article)
    print(f"[L6] 生成完成，长度: {len(article)}字")
    return article

# ---------------------------------------------------------------------------
# 独立测试
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    test_report = {
        "oracle_score": 62,
        "fused_topics": [
            {"topic": "BTC突破关键阻力位", "fusion_score": 88},
            {"topic": "山寨季信号", "fusion_score": 72},
        ],
        "fused_coins": [
            {"symbol": "BTCUSDT", "total_score": 90},
            {"symbol": "ETHUSDT", "total_score": 75},
        ],
        "fused_sentiment": {"label": "中性偏多", "fused_score": 58},
        "headlines": ["$BTC突破关键位，山寨还要等多久？"],
    }
    article = generate_article(test_report, use_recent_posts=True)
    print("\n========== 生成文章 ==========")
    print(article)
    print("================================")
