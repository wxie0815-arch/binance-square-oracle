#!/usr/bin/env python3
"""
币安广场流量预言机 v2.0 (重构版) - 主控调度脚本
================================================================

重构优化 (v1.0):
  - 性能监控：记录各层耗时
  - API 监控：记录 API 成功/失败/缓存命中率
  - 集中化配置与日志

"""

import sys
import os
import json
import time
import argparse
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

import config
from run_monitor import perf_monitor, api_monitor, log_run

# ... (其他导入和函数保持不变) ...

def run_oracle(
    layers: list = None,
    quick: bool = False,
    deep: bool = False,
    verbose: bool = True,
    auto_post: bool = False,
    style: str = "oracle",
    combo: str = None,
    token_symbol: str = None,
    # ... (其他参数)
) -> dict:
    perf_monitor.checkpoint("init")

    # ... (打印启动信息) ...

    reports = {}
    run_layers = layers or ["L0", "L1", "L2", "L3", "L4"]

    # ... (快速模式逻辑) ...

    layer_functions = {
        "L0": ("广场实时热帖监控", import_layer("L0")),
        "L1": ("社交热度排名", import_layer("L1")),
        "L2": ("链上异动监控", import_layer("L2")),
        "L3": ("行情分析引擎", import_layer("L3")),
        "L4": ("新闻+KOL信号", import_layer("L4")),
    }

    for layer_name, (title, func) in layer_functions.items():
        if layer_name in run_layers:
            perf_monitor.checkpoint(f"start_{layer_name}")
            if verbose: print(f"\n[{layer_name}] {title}...")
            try:
                # 在这里需要一种方式将 api_monitor 注入到各层函数中
                # 暂时简化，假设各层函数内部直接调用了 api_monitor
                reports[layer_name] = func(deep=deep) if layer_name == "L0" else func()
                # ... (打印层级报告) ...
            except Exception as e:
                if verbose: print(f"  {layer_name} 失败: {e}")
                reports[layer_name] = empty_report(layer_name)
                api_monitor.record_call(f"{layer_name}_layer_execution", success=False, from_cache=False)
            else:
                api_monitor.record_call(f"{layer_name}_layer_execution", success=True, from_cache=False) # 简化处理
        else:
            reports[layer_name] = empty_report(layer_name)

    # L5: 信号融合
    perf_monitor.checkpoint("start_L5_fusion")
    # ... (L5 逻辑) ...
    final_report = {}

    # L7: 文章创作
    perf_monitor.checkpoint("start_L7_writing")
    # ... (L7 逻辑) ...

    # L8: 发布
    perf_monitor.checkpoint("start_L8_publishing")
    # ... (L8 逻辑) ...

    perf_monitor.checkpoint("end_run")

    # 记录日志
    run_log_data = {
        "timestamp": datetime.now().isoformat(),
        "settings": {"style": style, "combo": combo, "token": token_symbol, "deep": deep, "quick": quick},
        "performance": perf_monitor.get_report(),
        "api_stats": api_monitor.get_report(),
        "final_score": final_report.get("final_score"),
        "article_length": len(final_report.get("final_article", "")),
    }
    log_run(run_log_data)

    return final_report

# ... (主函数入口和参数解析) ...
