#!/usr/bin/env python3
"""
run_monitor.py — C 方案性能监控层 v1.1
"""

import time

class PerformanceMonitor:
    def __init__(self):
        self.timers = {}

    def start(self, name):
        self.timers[name] = time.time()

    def end(self, name):
        if name in self.timers:
            elapsed = time.time() - self.timers[name]
            print(f"[monitor] {name}: {elapsed:.2f}s")
            return elapsed
        return 0
