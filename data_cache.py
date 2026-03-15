#!/usr/bin/env python3
"""
data_cache.py - 统一数据缓存层 v2.0 (重构版)
================================================================

重构优化 (v1.0):
  - 调整 TTL：广场/社交热度缓存4小时，链上/新闻缓存4分钟
  - 增量更新支持：通过更精细的缓存键实现
  - 简化实现：移除磁盘缓存，仅保留内存缓存，以适配 OpenClaw 环境

"""

import time
import hashlib
import threading
from functools import wraps

# 缓存 TTL (Time-To-Live) in seconds
CACHE_TTL = {
    "square_posts": 4 * 3600,      # 广场热帖: 4 hours
    "social_hype": 4 * 3600,       # 社交热度: 4 hours
    "onchain_data": 4 * 60,        # 链上数据: 4 minutes
    "news": 4 * 60,                # 新闻: 4 minutes
    "default": 5 * 60,             # 默认: 5 minutes
}

_cache = {}
_lock = threading.Lock()
_stats = {"hits": 0, "misses": 0, "sets": 0, "evictions": 0}

def _generate_key(func_name, *args, **kwargs) -> str:
    """为函数调用生成唯一的缓存键"""
    key_parts = [func_name]
    key_parts.extend(str(a) for a in args)
    key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
    return hashlib.md5(":".join(key_parts).encode()).hexdigest()

def get(key: str):
    """从缓存中获取数据"""
    with _lock:
        entry = _cache.get(key)
        if entry and time.time() < entry["expires_at"]:
            _stats["hits"] += 1
            return entry["data"]
        elif entry:
            del _cache[key]
            _stats["evictions"] += 1
        _stats["misses"] += 1
        return None

def set(key: str, data, ttl: int):
    """向缓存中写入数据"""
    with _lock:
        _cache[key] = {
            "data": data,
            "expires_at": time.time() + ttl,
        }
        _stats["sets"] += 1

def get_stats() -> dict:
    """获取缓存统计信息"""
    total = _stats["hits"] + _stats["misses"]
    hit_rate = (_stats["hits"] / total * 100) if total > 0 else 0
    return {**_stats, "hit_rate": round(hit_rate, 1), "active_entries": len(_cache)}

def cached(category: str):
    """缓存装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = _generate_key(func.__name__, *args, **kwargs)
            cached_data = get(key)
            if cached_data is not None:
                return cached_data
            
            result = func(*args, **kwargs)
            
            if result is not None:
                ttl = CACHE_TTL.get(category, CACHE_TTL["default"])
                set(key, result, ttl)
            
            return result
        return wrapper
    return decorator
