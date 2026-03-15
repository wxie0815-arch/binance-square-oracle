---
name: binance-square-oracle
description: 基于 8 层数据架构的币安广场热点预测与内容策略引擎。融合广场实时热帖、社交热度、链上异动、行情分析及 KOL 信号，提供全维度的数据支持和发帖指导。适用于需要分析币安广场热点、寻找创作灵感、获取发帖策略的场景。
---

# 币安广场流量预言机 (Binance Square Oracle v3.0)

本 Skill 旨在通过多维数据采集与融合分析，为您在币安广场（Binance Square）的创作提供数据支撑和策略指导。

通过调用 8 层数据架构，预言机能够实时洞察市场情绪、挖掘热门叙事、捕捉链上异动，并结合时间窗口为您生成最具潜力的内容选题和标题模板。

## 架构说明 (8-Layer Architecture)

预言机系统由以下 8 个核心层级构成，自下而上层层递进：

- **L0 广场实时热帖 (Square Monitor)**：抓取广场当前浏览量、点赞数最高的热门帖子，提取热门标签和互动率。
- **L1 社交热度排名 (Social Hype)**：基于币安官方 `crypto-market-rank`，分析全网代币的社交讨论热度和情绪偏向。
- **L2 链上异动监控 (On-chain Anomaly)**：基于币安官方 `trading-signal` 和 `smart-money`，追踪巨鲸买卖信号和资金净流入。
- **L3 行情分析引擎 (Market Analysis)**：结合币安现货行情与 K 线数据，配合恐惧贪婪指数，输出技术面分析。
- **L4 新闻与 KOL 信号 (News & KOL)**：接入 6551 API，实时监控加密媒体新闻和顶级 KOL 推文，提取全网热词。
- **L5 信号融合引擎 (Signal Fusion)**：核心调度层，将 L0-L4 数据进行加权交叉验证，输出综合评分和策略建议。
- **L6 去 AI 味处理 (Humanizer-CN)**：基于 Web3 中文用户的阅读习惯，对生成的策略和文案进行去 AI 化润色。
- **L7 广场发布层 (Square Post)**：对接官方 `square-post` 技能，实现一键发布（可选）。

## 使用方法

你可以通过运行主控脚本来获取完整的预言机报告：

```bash
# 获取完整的预言机报告（耗时约 15-20 秒）
python3 /home/ubuntu/skills/binance-square-oracle/scripts/oracle_main.py

# 快速模式（跳过链上和新闻分析，耗时约 5 秒）
python3 /home/ubuntu/skills/binance-square-oracle/scripts/oracle_main.py --quick

# 仅运行指定层级（例如只看广场热帖和行情）
python3 /home/ubuntu/skills/binance-square-oracle/scripts/oracle_main.py --layer L0 L3

# 将报告保存为 JSON 和 Markdown 文件
python3 /home/ubuntu/skills/binance-square-oracle/scripts/oracle_main.py --save /home/ubuntu/reports
```

## 报告内容解读

预言机报告包含以下关键模块：

1. **预言机评分 (Oracle Score)**：0-100 分，评估当前广场的流量活跃度（如：流量爆发期、流量平稳期）。
2. **综合市场情绪**：基于技术面、社交面和链上数据融合计算出的市场情绪（极度贪婪、偏多、中性、偏空、极度恐惧）。
3. **融合话题与代币**：交叉验证出的高确信度热门话题和代币，建议优先作为发帖素材。
4. **发布时机建议**：根据当前北京时间，评估流量系数，建议最佳发帖时段。
5. **内容策略与标题**：基于情绪和热点生成的发帖策略和爆款标题模板。

## 依赖与环境

- 依赖币安官方 API（`api.binance.com` / `data-api.binance.vision` / `web3.binance.com`）
- 依赖 6551 开放 API（需配置环境变量 `TOKEN_6551`，脚本内置了默认 Token 用于测试）
- 无需额外部署数据库，所有计算在内存中完成，轻量高效。
