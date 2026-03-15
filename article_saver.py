#!/usr/bin/env python3
"""
article_saver.py - 文章保存与管理模块 v1.0
================================================================
功能：
  - 保存生成的文章（Markdown / 纯文本 / JSON）
  - 自动组织目录结构（按日期 + 风格分类）
  - 保存完整运行报告（含元数据）
  - 历史文章索引与查询
  - 支持 --save 参数一键保存

使用：
    from article_saver import ArticleSaver
    saver = ArticleSaver(output_dir="./output")
    saver.save(oracle_result)
"""

import os
import json
import re
from datetime import datetime, timezone, timedelta

CST = timezone(timedelta(hours=8))

# 默认保存目录
DEFAULT_OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")


class ArticleSaver:
    """文章保存与管理"""

    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or DEFAULT_OUTPUT_DIR
        self.articles_dir = os.path.join(self.output_dir, "articles")
        self.reports_dir = os.path.join(self.output_dir, "reports")
        self.index_file = os.path.join(self.output_dir, "article_index.json")
        os.makedirs(self.articles_dir, exist_ok=True)
        os.makedirs(self.reports_dir, exist_ok=True)

    def save(self, oracle_result: dict, verbose: bool = True) -> dict:
        """
        保存完整的预言机运行结果

        Args:
            oracle_result: run_oracle() 的返回结果
            verbose: 是否打印保存信息

        Returns:
            dict: 保存的文件路径信息
        """
        now = datetime.now(CST)
        ts = now.strftime("%Y%m%d_%H%M%S")
        date_dir = now.strftime("%Y-%m-%d")
        style = oracle_result.get("article_style", "oracle")
        style_name = oracle_result.get("article_style_name", style)

        # 按日期创建子目录
        day_articles_dir = os.path.join(self.articles_dir, date_dir)
        day_reports_dir = os.path.join(self.reports_dir, date_dir)
        os.makedirs(day_articles_dir, exist_ok=True)
        os.makedirs(day_reports_dir, exist_ok=True)

        saved_files = {}

        # 1. 保存文章（Markdown 格式）
        article = oracle_result.get("generated_article", "")
        if article:
            article_md = self._format_article_md(oracle_result, now)
            md_path = os.path.join(day_articles_dir, f"article_{style}_{ts}.md")
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(article_md)
            saved_files["article_md"] = md_path

            # 纯文本版（适合直接复制发布）
            txt_path = os.path.join(day_articles_dir, f"article_{style}_{ts}.txt")
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(article)
            saved_files["article_txt"] = txt_path

        # 2. 保存完整报告（JSON）
        report_path = os.path.join(day_reports_dir, f"oracle_report_{ts}.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(oracle_result, f, ensure_ascii=False, indent=2, default=str)
        saved_files["report_json"] = report_path

        # 3. 保存摘要报告（Markdown）
        summary_md = self._format_summary_md(oracle_result, now)
        summary_path = os.path.join(day_reports_dir, f"oracle_summary_{ts}.md")
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(summary_md)
        saved_files["summary_md"] = summary_path

        # 4. 更新文章索引
        self._update_index(oracle_result, saved_files, now)

        if verbose:
            print(f"\n{'=' * 50}")
            print(f"  文章保存完成")
            print(f"{'=' * 50}")
            if saved_files.get("article_md"):
                print(f"  文章(MD):  {saved_files['article_md']}")
            if saved_files.get("article_txt"):
                print(f"  文章(TXT): {saved_files['article_txt']}")
            print(f"  报告(JSON): {saved_files['report_json']}")
            print(f"  摘要(MD):  {saved_files['summary_md']}")
            print(f"  索引:      {self.index_file}")
            print(f"{'=' * 50}")

        return saved_files

    def _format_article_md(self, result: dict, now: datetime) -> str:
        """格式化文章为 Markdown"""
        article = result.get("generated_article", "")
        meta = result.get("article_metadata", {})
        style_name = result.get("article_style_name", "")
        combo_name = result.get("content_combo_name", "")
        score = result.get("oracle_score", 0)
        word_count = meta.get("word_count", len(article))
        hashtags = meta.get("hashtags", [])

        lines = [
            f"---",
            f"title: \"{meta.get('title', '币安广场流量预言机')}\"",
            f"style: {style_name}",
            f"combo: {combo_name}",
            f"oracle_score: {score}",
            f"word_count: {word_count}",
            f"generated_at: {now.strftime('%Y-%m-%d %H:%M:%S')} CST",
            f"tags: [{', '.join(hashtags[:10])}]",
            f"---",
            f"",
            article,
        ]
        return "\n".join(lines)

    def _format_summary_md(self, result: dict, now: datetime) -> str:
        """格式化运行摘要"""
        lines = [
            f"# 预言机运行摘要",
            f"",
            f"**运行时间**: {now.strftime('%Y-%m-%d %H:%M:%S')} CST",
            f"**版本**: v{result.get('version', '?')}",
            f"**耗时**: {result.get('elapsed_seconds', 0)}s",
            f"",
            f"## 评分",
            f"",
            f"| 指标 | 值 |",
            f"|:---|:---|",
            f"| 预言机评分 | {result.get('oracle_score', 0)}/100 |",
            f"| 评级 | {result.get('oracle_rating', '')} |",
            f"| 文章风格 | {result.get('article_style_name', '')} |",
            f"| 内容组合 | {result.get('content_combo_name', '')} |",
            f"| 使用Skills | {', '.join(result.get('skills_used', []))} |",
            f"",
            f"## 文章信息",
            f"",
        ]
        meta = result.get("article_metadata", {})
        if meta:
            lines.extend([
                f"| 指标 | 值 |",
                f"|:---|:---|",
                f"| 标题 | {meta.get('title', '')} |",
                f"| 字数 | {meta.get('word_count', 0)} |",
                f"| 达标 | {'是' if meta.get('meets_min_words') else '否'} |",
                f"| 标签 | {', '.join(meta.get('hashtags', [])[:10])} |",
            ])

        # 各层报告摘要
        layers = result.get("layer_reports", {})
        if layers:
            lines.extend([f"", f"## 各层数据摘要", f""])
            layer_names = {
                "L0_square_monitor": "L0 广场监控",
                "L1_social_hype": "L1 社交热度",
                "L2_onchain_anomaly": "L2 链上异动",
                "L3_market_analysis": "L3 行情分析",
                "L4_news_kol": "L4 新闻KOL",
                "L5_signal_fusion": "L5 信号融合",
                "L6_style_analyzer": "L6 风格分析",
            }
            for key, name in layer_names.items():
                lr = layers.get(key, {})
                if lr and not lr.get("error"):
                    score_key = [k for k in lr.keys() if k.endswith("_score")]
                    score_val = lr.get(score_key[0], "N/A") if score_key else "N/A"
                    lines.append(f"- **{name}**: 评分 {score_val}")
                else:
                    lines.append(f"- **{name}**: 不可用")

        return "\n".join(lines)

    def _update_index(self, result: dict, saved_files: dict, now: datetime):
        """更新文章索引"""
        index = []
        if os.path.exists(self.index_file):
            try:
                with open(self.index_file, "r", encoding="utf-8") as f:
                    index = json.load(f)
            except Exception:
                index = []

        meta = result.get("article_metadata", {})
        entry = {
            "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
            "style": result.get("article_style", ""),
            "style_name": result.get("article_style_name", ""),
            "combo": result.get("content_combo", ""),
            "oracle_score": result.get("oracle_score", 0),
            "word_count": meta.get("word_count", 0),
            "title": meta.get("title", ""),
            "hashtags": meta.get("hashtags", [])[:5],
            "files": saved_files,
        }
        index.append(entry)

        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)

    def list_articles(self, limit: int = 20) -> list:
        """列出最近的文章"""
        if not os.path.exists(self.index_file):
            return []
        try:
            with open(self.index_file, "r", encoding="utf-8") as f:
                index = json.load(f)
            return index[-limit:]
        except Exception:
            return []

    def get_stats(self) -> dict:
        """获取文章统计信息"""
        articles = self.list_articles(limit=9999)
        if not articles:
            return {"total": 0}

        total = len(articles)
        styles = {}
        scores = []
        word_counts = []
        for a in articles:
            s = a.get("style_name", "unknown")
            styles[s] = styles.get(s, 0) + 1
            scores.append(a.get("oracle_score", 0))
            word_counts.append(a.get("word_count", 0))

        return {
            "total": total,
            "styles": styles,
            "avg_score": round(sum(scores) / len(scores), 1) if scores else 0,
            "avg_word_count": round(sum(word_counts) / len(word_counts)) if word_counts else 0,
            "latest": articles[-1].get("timestamp", "") if articles else "",
        }
