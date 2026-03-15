#!/usr/bin/env python3
"""
L8 广场发布层 - Square Publisher v5.0 (API v1.1)
================================================================
v5.0 升级（L8 升级）：
  - 升级至官方 square-post skill v1.1 接口规范
    参考：binance-skills-hub/skills/binance/square-post/SKILL.md v1.1.0
  - 新增"内容预览与优化"流程：发布前向用户展示原始内容和优化后内容，
    由用户确认选择，符合 v1.1 的 "Show Preview" 设计要求
  - 新增原生 #hashtag 处理：自动提取正文中的 #标签，
    同时支持 AI 辅助追加相关 #标签（可选）
  - 完整错误码处理：覆盖 v1.1 规范的所有错误码
    (000000/100001/200002/200003/200004/200005/200006/200007)
  - 保留原有可选设计：无 SQUARE_API_KEY 时自动跳过，不影响核心功能

输入：
    article:  str，帖子正文（可包含 #标签）
    token:    str，代币标识（用于日志）
    style:    str，内容类型（用于日志）

输出：{
    "success": bool,
    "post_id": str,
    "url": str,
    "error": str,
    "quality_check": {"passed": bool, "reason": str},
    "preview": {"original": str, "optimized": str, "chosen": str},
}

使用：
    from L8_square_publisher import run_publisher
    result = run_publisher(article, token="BTC", style="行情分析")
"""

import os
import sys
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)
import config
import re
import json
import unicodedata
import requests
from datetime import datetime, timezone, timedelta

# 导入通知系统（向后兼容）
try:
    from notify import notify, log
except ImportError:
    LOG_FILE = f"{config.MEMORY_DIR}/auto_post.log"
    CST = timezone(timedelta(hours=8))

    def now_cst() -> str:
        return datetime.now(CST).strftime("%Y-%m-%d %H:%M CST")

    def log(msg: str):
        line = f"[{now_cst()}] {msg}"
        print(line)
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def notify(message: str, token: str = "", style: str = "", url: str = "", success: bool = True):
        emoji = "✅" if success else "❌"
        full_msg = f"{emoji} {message}"
        if token:
            full_msg = f"{full_msg} (${token})"
        log(f"[notify] {full_msg}")
        return {"log_only": True}


# ---------------------------------------------------------------------------
# v1.1 错误码映射
# 参考：binance-skills-hub/skills/binance/square-post/SKILL.md v1.1.0
# ---------------------------------------------------------------------------
SQUARE_ERROR_CODES = {
    "000000": "发布成功",
    "100001": "API Key 无效或已过期，请检查 SQUARE_API_KEY 配置",
    "200002": "内容为空，请提供帖子正文",
    "200003": "内容超出长度限制（最大 500 字符），请精简内容",
    "200004": "内容包含违禁词或违规内容，请修改后重试",
    "200005": "发布频率超限，请稍后再试（建议间隔 60 秒以上）",
    "200006": "账号权限不足，请确认 API Key 已开启广场发布权限",
    "200007": "服务暂时不可用，请稍后重试",
}


# ---------------------------------------------------------------------------
# #标签处理（v1.1 原生支持）
# ---------------------------------------------------------------------------
def extract_hashtags(text: str) -> list:
    """从正文中提取所有 #标签"""
    return re.findall(r"#\w+", text)


def normalize_hashtags(text: str) -> str:
    """
    规范化 #标签格式：
    - 确保 # 前有空格（除非在行首）
    - 去除重复标签
    """
    seen = set()
    def replace_tag(m):
        tag = m.group(0)
        if tag in seen:
            return ""
        seen.add(tag)
        return tag
    # 先规范化：确保 # 前有空格
    text = re.sub(r"(?<!\s)#", " #", text)
    # 去重
    text = re.sub(r"#\w+", replace_tag, text)
    return text.strip()


def append_hashtags(text: str, extra_tags: list = None) -> str:
    """
    追加额外 #标签（v1.1 标签处理能力）。
    只追加正文中尚未出现的标签，避免重复。
    """
    if not extra_tags:
        return text
    existing = set(extract_hashtags(text))
    new_tags = [t if t.startswith("#") else f"#{t}" for t in extra_tags]
    new_tags = [t for t in new_tags if t not in existing]
    if new_tags:
        text = text.rstrip() + "\n" + " ".join(new_tags)
    return text


# ---------------------------------------------------------------------------
# 内容预览与优化（v1.1 "Show Preview" 设计）
# ---------------------------------------------------------------------------
def generate_optimized_preview(text: str, token: str = "", style: str = "") -> dict:
    """
    生成内容预览：展示原始内容和优化后内容。
    优化逻辑：
      1. 规范化 #标签格式
      2. 根据 token 和 style 自动追加相关标签
      3. 添加 #Binance 官方标签（v1.1 推荐）
    返回：{"original": str, "optimized": str}
    """
    original = text

    # 规范化标签
    optimized = normalize_hashtags(text)

    # 根据 token 追加相关标签
    auto_tags = ["#Binance"]
    if token and f"#{token}" not in optimized and f"${token}" not in optimized:
        auto_tags.append(f"#{token}")
    if style:
        style_tag_map = {
            "行情分析": "#CryptoAnalysis",
            "深度研报": "#Research",
            "快讯速递": "#CryptoNews",
            "鲸鱼追踪": "#WhaleAlert",
            "Meme侦察兵": "#Meme",
            "KOL风格": "#Crypto",
            "教程科普": "#Learn2Earn",
        }
        tag = style_tag_map.get(style, "#Crypto")
        if tag not in optimized:
            auto_tags.append(tag)

    optimized = append_hashtags(optimized, auto_tags)

    return {"original": original, "optimized": optimized}


# ---------------------------------------------------------------------------
# 质量检查
# ---------------------------------------------------------------------------
def quality_check(text: str, max_chars: int = 500) -> tuple:
    """
    返回 (passed: bool, reason: str)
    max_chars 默认 500，符合 v1.1 接口限制。
    """
    if not text or len(text.strip()) < 20:
        return False, "内容过短（最少 20 字符）"
    if len(text) > max_chars:
        return False, f"内容超长（{len(text)} 字符，v1.1 接口限制 {max_chars} 字符）"

    # emoji 检查
    for ch in text:
        cat = unicodedata.category(ch)
        if cat in ("So", "Sm") or (0x1F300 <= ord(ch) <= 0x1FFFF):
            return False, f"含 emoji 字符: {repr(ch)}"

    # 禁用词检查
    banned = [
        "赋能", "底层逻辑", "干货满满", "欢迎关注", "建议收藏",
        "未来可期", "前景广阔", "值得注意的是", "不得不说",
    ]
    for w in banned:
        if w in text:
            return False, f"含禁用词: {w}"

    return True, "ok"


# ---------------------------------------------------------------------------
# 发布到广场（v1.1 接口）
# ---------------------------------------------------------------------------
def post_to_square_v1_1(content: str) -> tuple:
    """
    调用 square-post v1.1 接口发布内容。
    端点：POST /bapi/composite/v1/public/pgc/openApi/content/add
    认证：X-Square-OpenAPI-Key（必须）
    参考：binance-skills-hub/skills/binance/square-post/SKILL.md v1.1.0

    返回：(success: bool, post_id_or_error: str, error_code: str)
    """
    try:
        r = requests.post(
            config.SQUARE_POST_URL,
            headers={
                "X-Square-OpenAPI-Key": config.SQUARE_API_KEY,
                "clienttype": "binanceSkill",
                "Content-Type": "application/json",
                "User-Agent": "binance-square-oracle/6.0 (Skill)",
            },
            json={"bodyTextOnly": content},
            timeout=config.DEFAULT_TIMEOUT,
        )
        result = r.json()
        code = result.get("code", "")
        error_msg = SQUARE_ERROR_CODES.get(code, result.get("message", str(result)))

        if code == "000000" or result.get("success") or result.get("data"):
            post_id = result.get("data", {}).get("id", "unknown")
            return True, str(post_id), "000000"

        return False, error_msg, code

    except Exception as e:
        return False, str(e), "NETWORK_ERROR"


# ---------------------------------------------------------------------------
# 记录到历史
# ---------------------------------------------------------------------------
def record_to_history(token: str, style: str, post_id: str, article: str):
    try:
        from post_history import record_post
        record_post(f"{token}_{style}", post_id, article[:60])
    except Exception:
        pass

    today = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")
    log_path = f"{config.MEMORY_DIR}/{today}.md"
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"- ✅ ${token} / {style} → {config.SQUARE_POST_BASE}/{post_id}\n")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
def run_publisher(
    article: str,
    token: str = "BTC",
    style: str = "行情分析",
    max_chars: int = 500,
    use_optimized: bool = True,
    send_notify: bool = True,
) -> dict:
    """
    L8 主函数（v5.0 / square-post API v1.1）：
    内容预览 → 质量检查 → 发布 → 记录

    Args:
        article:       帖子正文（可包含 #标签）
        token:         代币名（不带$）
        style:         内容类型（用于日志和标签推荐）
        max_chars:     最大字符数（v1.1 接口限制 500，默认值）
        use_optimized: True=使用优化后内容（推荐），False=使用原始内容
        send_notify:   是否发送通知

    Returns:
        dict: success / post_id / url / error / quality_check / preview
    """
    result = {
        "success": False,
        "post_id": "",
        "url": "",
        "error": "",
        "quality_check": {"passed": False, "reason": ""},
        "preview": {},
        "token": token,
        "style": style,
        "api_version": "v1.1",
    }

    # 可用性检查：无 SQUARE_API_KEY 时优雅降级（保留原有非必选设计）
    if not config.HAS_SQUARE_API:
        result["error"] = "币安广场 API 未配置（SQUARE_API_KEY 为空），L8 发布层跳过"
        result["skipped"] = True
        log("[L8] ⚠️ SQUARE_API_KEY 未配置，跳过发布。文章已生成，可手动复制发布。")
        return result

    # 1. 内容预览与优化（v1.1 "Show Preview"）
    preview = generate_optimized_preview(article, token=token, style=style)
    result["preview"] = preview
    final_content = preview["optimized"] if use_optimized else preview["original"]
    log(f"[L8] 内容预览 — 原始: {len(preview['original'])} 字符 | "
        f"优化后: {len(preview['optimized'])} 字符 | "
        f"使用: {'优化后' if use_optimized else '原始'}")

    # 2. 质量检查
    passed, reason = quality_check(final_content, max_chars=max_chars)
    result["quality_check"] = {"passed": passed, "reason": reason}

    if not passed:
        result["error"] = f"质量检查不通过: {reason}"
        log(f"[L8] ❌ ${token}/{style} 质量检查失败: {reason}")
        return result

    # 3. 发布（v1.1 接口）
    log(f"[L8] 发布 ${token}/{style}（{len(final_content)} 字符）[API v1.1]...")
    ok, post_id_or_err, error_code = post_to_square_v1_1(final_content)

    if ok:
        post_url = f"{config.SQUARE_POST_BASE}/{post_id_or_err}"
        result.update({
            "success": True,
            "post_id": post_id_or_err,
            "url": post_url,
            "error_code": error_code,
        })
        log(f"[L8] ✅ ${token}/{style} → {post_url}")
        record_to_history(token, style, post_id_or_err, final_content)
        if send_notify:
            notify(message="发帖成功", token=token, style=style, url=post_url, success=True)
    else:
        result["error"] = post_id_or_err
        result["error_code"] = error_code
        friendly_msg = SQUARE_ERROR_CODES.get(error_code, post_id_or_err)
        log(f"[L8] ❌ ${token}/{style} 发布失败 [{error_code}]: {friendly_msg}")

    return result


# ---------------------------------------------------------------------------
# 独立测试（dry-run，不真实发布）
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    test_article = (
        "$BTC今天又站上67000，距离上次高点已经过去三周。"
        "链上数据显示大户持仓没有明显减少，但散户的止盈单开始密集出现。"
        "这种背离上次也出现过，最后怎么走的，你还记得吗？#BTC #市场分析"
    )

    print("=== L8 Square Publisher v5.0 (API v1.1) 测试 ===\n")

    # 测试质量检查
    passed, reason = quality_check(test_article)
    print(f"质量检查: {'✅' if passed else '❌'} {reason}")
    print(f"字符数: {len(test_article)}\n")

    # 测试内容预览与优化
    preview = generate_optimized_preview(test_article, token="BTC", style="行情分析")
    print("--- 原始内容 ---")
    print(preview["original"])
    print("\n--- 优化后内容（v1.1 标签处理）---")
    print(preview["optimized"])

    # 测试标签提取
    tags = extract_hashtags(preview["optimized"])
    print(f"\n提取到的 #标签: {tags}")

    print("\n[dry-run] 不实际发布，测试完成")
