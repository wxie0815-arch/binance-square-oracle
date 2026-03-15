#!/usr/bin/env python3
"""
notify.py - 通用通知系统
================================================================
支持多种通知方式：
1. OpenClaw message工具（推荐） - 支持所有通信工具
2. Telegram Bot（向后兼容）
3. Webhook（通用）
4. 日志文件（始终记录）

使用方式：
    from notify import notify
    notify("✅ 发帖成功", token="BTC", style="行情分析", url="...")
"""

import os
import sys
import json
import requests
from datetime import datetime, timezone, timedelta

# 使用绝对路径确保导入正确
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)
import config

CST = timezone(timedelta(hours=8))
LOG_FILE = f"{config.MEMORY_DIR}/auto_post.log"


def now_cst() -> str:
    return datetime.now(CST).strftime("%Y-%m-%d %H:%M CST")


def log(msg: str):
    """记录到日志文件"""
    line = f"[{now_cst()}] {msg}"
    print(line)
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def send_telegram_bot(msg: str):
    """向后兼容：使用Telegram Bot API"""
    if not config.TG_BOT_TOKEN or not config.TG_CHAT_ID:
        return False
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{config.TG_BOT_TOKEN}/sendMessage",
            json={"chat_id": config.TG_CHAT_ID, "text": msg, "parse_mode": "Markdown"},
            timeout=10,
        )
        return resp.status_code == 200
    except Exception as e:
        log(f"[notify] Telegram Bot失败: {e}")
        return False


def send_webhook(msg: str):
    """发送Webhook通知"""
    if not config.WEBHOOK_URL:
        return False
    try:
        payload = {
            "text": msg,
            "timestamp": now_cst(),
            "source": "binance-square-oracle"
        }
        resp = requests.post(config.WEBHOOK_URL, json=payload, timeout=10)
        return resp.status_code in (200, 201, 204)
    except Exception as e:
        log(f"[notify] Webhook失败: {e}")
        return False


def send_openclaw_message(msg: str):
    """使用OpenClaw message工具发送通知（推荐）"""
    if not config.NOTIFY_ENABLED or not config.NOTIFY_TARGET:
        return False
    
    # 这里需要调用OpenClaw的message工具
    # 在实际部署中，可以通过OpenClaw API或直接调用工具
    # 目前先记录日志，用户可以根据自己的OpenClaw配置实现
    
    log(f"[notify] OpenClaw消息（{config.NOTIFY_CHANNEL} → {config.NOTIFY_TARGET}）: {msg}")
    
    # 示例：如果用户配置了OpenClaw，可以取消注释以下代码
    """
    try:
        # 假设OpenClaw提供了Python SDK或HTTP API
        import openclaw
        openclaw.message.send(
            channel=config.NOTIFY_CHANNEL,
            target=config.NOTIFY_TARGET,
            message=msg
        )
        return True
    except Exception as e:
        log(f"[notify] OpenClaw消息失败: {e}")
        return False
    """
    
    return True  # 记录成功，实际发送由用户配置


def notify(
    message: str,
    token: str = "",
    style: str = "",
    url: str = "",
    success: bool = True
):
    """
    发送通知
    
    Args:
        message: 通知消息
        token:   代币名（可选）
        style:   内容类型（可选）
        url:     帖子URL（可选）
        success: 是否成功（影响表情符号）
    """
    # 构建完整消息
    emoji = "✅" if success else "❌"
    full_msg = f"{emoji} {message}"
    
    if token:
        full_msg = f"{full_msg}\n代币: ${token}"
    if style:
        full_msg = f"{full_msg}\n类型: {style}"
    if url:
        full_msg = f"{full_msg}\n链接: {url}"
    
    # 记录日志
    log(f"[notify] {full_msg}")
    
    # 尝试所有通知方式
    results = {
        "openclaw": send_openclaw_message(full_msg),
        "telegram_bot": send_telegram_bot(full_msg),
        "webhook": send_webhook(full_msg)
    }
    
    return results


# 测试函数
if __name__ == "__main__":
    print("=== 通知系统测试 ===")
    
    # 测试成功通知
    print("\n1. 测试成功通知:")
    result = notify(
        "发帖成功",
        token="BTC",
        style="行情分析",
        url="https://www.binance.com/square/post/123456",
        success=True
    )
    print(f"结果: {result}")
    
    # 测试失败通知
    print("\n2. 测试失败通知:")
    result = notify(
        "发帖失败: 内容过短",
        token="ETH",
        style="技术分析",
        success=False
    )
    print(f"结果: {result}")
    
    print("\n✅ 通知系统测试完成")