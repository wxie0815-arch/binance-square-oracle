#!/usr/bin/env python3
"""
run_monitor.py - 性能监控与日志模块 v2.0 (重构版)
================================================================

重构优化 (v1.0):
  - 响应时间监控：记录主流程和各层的处理时间
  - API 调用统计：通过与 data_cache 联动，记录成功/失败/缓存命中率
  - 预警机制：当关键 API 连续失败时触发告警
  - 结构化日志：所有监控数据输出为结构化 JSON，便于后续处理

"""

import os
import json
import time
import logging
from datetime import datetime

from config import LOG_DIR

# 全局 logger
logger = None

def get_logger():
    global logger
    if logger is None:
        os.makedirs(LOG_DIR, exist_ok=True)
        log_file = os.path.join(LOG_DIR, f"oracle_run_{datetime.now().strftime('%Y%m%d')}.log")
        
        logger = logging.getLogger("OracleMonitor")
        logger.setLevel(logging.INFO)
        
        # 文件 handler
        fh = logging.FileHandler(log_file, encoding='utf-8')
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        
        # 控制台 handler
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        logger.addHandler(ch)
    return logger

class PerformanceMonitor:
    """性能监控器，记录各阶段耗时"""
    def __init__(self):
        self.checkpoints = [("start", time.time())]
        self.log = get_logger()

    def checkpoint(self, name: str):
        """打点记录一个检查点"""
        self.checkpoints.append((name, time.time()))

    def get_report(self) -> dict:
        """生成耗时报告"""
        report = {}
        total_duration = self.checkpoints[-1][1] - self.checkpoints[0][1]
        report['total_duration_ms'] = round(total_duration * 1000)
        
        durations = {}
        for i in range(len(self.checkpoints) - 1):
            name = self.checkpoints[i+1][0]
            duration = self.checkpoints[i+1][1] - self.checkpoints[i][1]
            durations[name] = round(duration * 1000)
        report['durations_ms'] = durations
        return report

class APIMonitor:
    """API 调用监控器"""
    def __init__(self):
        self.records = {}
        self.consecutive_failures = {}
        self.log = get_logger()

    def record_call(self, api_name: str, success: bool, from_cache: bool):
        """记录一次 API 调用"""
        if api_name not in self.records:
            self.records[api_name] = {"success": 0, "failure": 0, "from_cache": 0, "total": 0}
        
        self.records[api_name]["total"] += 1
        if from_cache:
            self.records[api_name]["from_cache"] += 1
        elif success:
            self.records[api_name]["success"] += 1
            self.consecutive_failures[api_name] = 0
        else:
            self.records[api_name]["failure"] += 1
            self.consecutive_failures[api_name] = self.consecutive_failures.get(api_name, 0) + 1
            self.check_alert(api_name)

    def check_alert(self, api_name: str, threshold: int = 3):
        """检查是否需要触发告警"""
        if self.consecutive_failures.get(api_name, 0) >= threshold:
            self.log.warning(f"[ALERT] API '{api_name}' has failed {self.consecutive_failures[api_name]} consecutive times.")

    def get_report(self) -> dict:
        """生成 API 调用报告"""
        report = {}
        for name, stats in self.records.items():
            live_calls = stats['success'] + stats['failure']
            success_rate = (stats['success'] / live_calls * 100) if live_calls > 0 else 100
            report[name] = {
                **stats,
                "live_success_rate_percent": round(success_rate, 1)
            }
        return report

# 全局监控实例
perf_monitor = PerformanceMonitor()
api_monitor = APIMonitor()

def log_run(run_data: dict):
    """将单次运行的完整监控数据写入日志"""
    log = get_logger()
    log.info(json.dumps(run_data, ensure_ascii=False, default=str))
