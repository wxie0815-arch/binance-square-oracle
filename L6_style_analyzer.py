#!/usr/bin/env python3
"""
L6 个人风格分析层 - Style Analyzer v1.0 (终版)
================================================================
- 彻底移除所有 AI 模型选配配置，统一调用 OpenClaw 系统 API
"""

import os
import sys
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)
import config
import json
import glob
import time
import subprocess
from datetime import datetime, timezone, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE = config.WORKSPACE

# ---------------------------------------------------------------------------
# 路径配置
# ---------------------------------------------------------------------------
STYLE_FILE = f"{WORKSPACE}/memory/oracle-style.md"
ANALYZER_SCRIPT = os.path.abspath(os.path.join(SCRIPT_DIR, "skills", "binance-square-profile-analyzer", "scripts", "binance_profile_analyzer.py"))
CACHE_DIR = f"{WORKSPACE}/memory/style_cache"

DEFAULT_USER = os.environ.get("STYLE_SOURCE_USER", "binance_square_official")
FINGERPRINT_TTL_HOURS = int(os.environ.get("STYLE_FINGERPRINT_TTL_HOURS", "48"))
SAMPLE_TTL_HOURS = int(os.environ.get("STYLE_SAMPLE_TTL_HOURS", "12"))

CST = timezone(timedelta(hours=8))

# ---------------------------------------------------------------------------
# 统一 LLM 调用（直接使用 OpenClaw 系统 API）
# ---------------------------------------------------------------------------
def _call_llm(prompt: str, system_prompt: str = None, max_tokens: int = 1000) -> str:
    """统一 LLM 调用，直接使用 config.call_llm()"""
    sys_prompt = system_prompt or "你是一个专业的写作风格分析专家，擅长分析加密货币社区的写作风格。"
    try:
        return config.call_llm(
            system_prompt=sys_prompt,
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
    """加载风格指南，如果不存在则返回基础预言机准则"""
    try:
        if os.path.exists(STYLE_FILE):
            with open(STYLE_FILE, "r", encoding="utf-8") as f:
                return f.read()
    except Exception:
        pass
    return "专业加密预言机风格：数据驱动，客观中性，多用数据表格，结构清晰，包含风险提示。"

# ---------------------------------------------------------------------------
# 抓取近期帖子样本（带缓存）
# ---------------------------------------------------------------------------
def fetch_recent_posts(username: str = None, n: int = 15) -> list:
    username = username or DEFAULT_USER
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_file = f"{CACHE_DIR}/{username}_posts.json"

    if os.path.exists(cache_file):
        age_h = (time.time() - os.path.getmtime(cache_file)) / 3600
        if age_h < SAMPLE_TTL_HOURS:
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    posts = json.load(f)
                if posts:
                    print(f"[L6] 帖子样本缓存命中: {username}（{age_h:.1f}h前，{len(posts)}条）")
                    return posts[:n]
            except Exception:
                pass

    if not os.path.exists(ANALYZER_SCRIPT):
        print(f"[L6] analyzer脚本不存在，跳过实时抓取")
        return []

    print(f"[L6] 抓取 {username} 近期帖子（目标{n}条）...")
    try:
        out_dir = f"/tmp/style_sample_{username}"
        os.makedirs(out_dir, exist_ok=True)
        fetch_count = max(n * 2, 50)
        result = subprocess.run(
            [sys.executable, ANALYZER_SCRIPT, "analyze", username,
             "--output", out_dir, "--max-posts", str(fetch_count)],
            capture_output=True, text=True, timeout=120,
            cwd=os.path.dirname(ANALYZER_SCRIPT)
        )
        json_candidates = glob.glob(f"{out_dir}/posts_*.json")
        if json_candidates:
            with open(json_candidates[0], "r", encoding="utf-8") as f:
                data = json.load(f)
            posts = data if isinstance(data, list) else data.get("posts", [])
            posts = [p for p in posts if p.get("content_type", "") in
                     ("short_post", "long_article", "") and
                     len(p.get("body_text", "") or p.get("content", "")) > 10]
            posts.sort(
                key=lambda x: x.get("published_at") or x.get("post_time") or "",
                reverse=True
            )
            posts = posts[:n]
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(posts, f, ensure_ascii=False)
            print(f"[L6] 获取 {len(posts)} 条有效样本，已缓存")
            return posts
        else:
            print(f"[L6] 未找到帖子文件: {result.stderr[:200]}")
    except Exception as e:
        print(f"[L6] 抓取失败: {e}")
    return []

# ---------------------------------------------------------------------------
# 核心：提炼风格指纹
# ---------------------------------------------------------------------------
def distill_fingerprint(style_guide: str, recent_posts: list, username: str = None) -> str:
    username = username or DEFAULT_USER
    os.makedirs(CACHE_DIR, exist_ok=True)
    fp_file = f"{CACHE_DIR}/{username}_fingerprint.md"

    if os.path.exists(fp_file):
        age_h = (time.time() - os.path.getmtime(fp_file)) / 3600
        if age_h < FINGERPRINT_TTL_HOURS:
            try:
                with open(fp_file, "r", encoding="utf-8") as f:
                    cached = f.read()
                if cached.strip():
                    print(f"[L6] 风格指纹缓存命中: {username}（{age_h:.1f}h前）")
                    return cached
            except Exception:
                pass

    print(f"[L6] 提炼风格指纹: {username}（{len(recent_posts)}条样本）...")

    sample_texts = ""
    if recent_posts:
        samples = [p.get("content", "")[:200] for p in recent_posts[:12] if p.get("content")]
        sample_texts = "\n".join([f'  [{i+1}] "{s}"' for i, s in enumerate(samples)])

    prompt = f"""你是一个写作风格深度分析专家。请分析以下币安广场的写作样本，提炼出该作者的"风格指纹"。

## 基础风格准则
{style_guide[:600]}

## 写作样本（共{len(recent_posts)}条）
{sample_texts if sample_texts else "（无样本，请基于基础准则生成理想的预言机风格）"}

## 分析任务
请从样本中提取该作者最显著的写作特征，形成一套可被AI模型直接学习的"风格指纹"。

### 开头句式（最常见的3种钩子模式）
-

### 高频词汇/短语
-

### 句式节奏
-

### 情绪基调
-

### 结尾模式
-

### 数字使用习惯
-

### 绝对禁忌
-

只输出以上结构内容，不要额外解释："""

    fingerprint = _call_llm(prompt, max_tokens=700)

    if fingerprint:
        ts = datetime.now(CST).strftime("%Y-%m-%d %H:%M CST")
        with open(fp_file, "w", encoding="utf-8") as f:
            f.write(f"# {username} 风格指纹\n> 提炼时间: {ts} | 样本数: {len(recent_posts)}条\n\n{fingerprint}")
        print(f"[L6] 风格指纹提炼完成，已缓存: {fp_file}")
        return fingerprint

    print("[L6] 指纹提炼失败，降级到静态档案")
    return style_guide[:800]

# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
def run_style_analyzer(username: str = None, force_refresh: bool = False, n_posts: int = 100) -> dict:
    """L6 主函数：分析风格 → 提炼指纹 → 返回结构化结果"""
    username = username or DEFAULT_USER

    if force_refresh:
        for f_path in [f"{CACHE_DIR}/{username}_fingerprint.md", f"{CACHE_DIR}/{username}_posts.json"]:
            try:
                os.remove(f_path)
            except Exception:
                pass

    style_guide = load_style_guide()
    recent_posts = fetch_recent_posts(username=username, n=n_posts)

    fp_cache_file = f"{CACHE_DIR}/{username}_fingerprint.md"
    cache_hit = (
        os.path.exists(fp_cache_file) and
        (time.time() - os.path.getmtime(fp_cache_file)) / 3600 < FINGERPRINT_TTL_HOURS
    )

    style_fingerprint = distill_fingerprint(style_guide, recent_posts, username=username)

    return {
        "style_fingerprint": style_fingerprint,
        "style_guide": style_guide,
        "recent_posts": recent_posts,
        "style_user": username,
        "cache_hit": cache_hit,
        "sample_count": len(recent_posts),
    }

# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="L6 风格分析器 v1.0")
    parser.add_argument("--user", default=None, help="风格来源用户名")
    parser.add_argument("--refresh", action="store_true", help="强制刷新缓存")
    args = parser.parse_args()

    result = run_style_analyzer(username=args.user, force_refresh=args.refresh)
    print("\n========== L6 风格指纹 ==========")
    print(result["style_fingerprint"][:800])
    print(f"\n样本数: {result['sample_count']} | 缓存命中: {result['cache_hit']}")
