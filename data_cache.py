#!/usr/bin/env python3
"""
data_cache.py — C 方案缓存层 v1.1
"""

import functools
import time

_cache = {}

def cached(ttl):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key = (func.__name__, args, frozenset(kwargs.items()))
            if key in _cache:
                entry = _cache[key]
                if time.time() - entry["timestamp"] < ttl:
                    return entry["value"]
            
            result = func(*args, **kwargs)
            _cache[key] = {"value": result, "timestamp": time.time()}
            return result
        return wrapper
    return decorator
