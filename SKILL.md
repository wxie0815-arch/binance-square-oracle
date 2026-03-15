---
name: binance-square-oracle
version: "1.0"
description: "币安广场流量预言机 v1.0 (重构版) — 基于 9 层数据架构的币安广场热点预测与内容创作引擎。集成 Alpha 早期项目监控、合约多空比/清算数据（L3 升级）、square-post v1.1 接口（L8 升级）、智能缓存、性能监控与日志。零配置开箱即用，所有模块均为非必选设计。"
author: "wxie0815-arch"

inputs:
  - name: style
    type: string
    description: |
      文章风格，支持以下选项：
      - oracle（默认）：综合预言机型，全面市场综合报告
      - deep_research：深度研报型，代币/项目深度研究
      - whale_tracker：鲸鱼追踪型，聪明钱动向分析
      - meme_scout：Meme侦察兵型，Meme赛道热点发现
      - news_flash：快讯速递型，简洁市场快讯
      - kol_style：KOL风格型，个人观点输出
      - tutorial：教程科普型，新手教育、概念解释
      - daily_express：日常快讯型（官方推荐组合）
      - deep_analysis：深度分析型（官方推荐组合）
      - onchain_insight：链上洞察型（官方推荐组合）
      - meme_hunter：Meme猎手型（官方推荐组合）
    default: "oracle"
  - name: token
    type: string
    description: "指定分析的代币符号，例如 BTC, ETH, SOL。留空时分析全市场热点。"
    default: ""
  - name: quick
    type: boolean
    description: "快速模式，跳过链上数据（L2）和新闻（L4）分析，响应时间从 15-20 秒降至 5 秒。"
    default: false
  - name: prompt
    type: string
    description: "创作意图描述，例如：'写一篇关于近期BTC行情的分析'，用于引导 L7 文章生成方向。"
    default: ""
  - name: enable_alpha
    type: boolean
    description: "是否启用 Alpha 早期项目监控（L3 可选模块）。默认启用，无需任何 API 密钥。"
    default: true
  - name: enable_derivatives
    type: boolean
    description: "是否启用合约多空比/清算数据（L3 可选模块）。默认启用，无需任何 API 密钥。"
    default: true

outputs:
  - name: final_article
    type: string
    description: "生成的最终文章内容，已完成去 AI 味润色，适合直接发布到币安广场。"
  - name: oracle_score
    type: integer
    description: "预言机总评分（0-100），评估当前广场的流量活跃度和内容发布时机。"
  - name: market_summary
    type: string
    description: "市场综合摘要，包含 BTC/ETH 行情、恐惧贪婪指数、热门代币和话题。"
  - name: final_report
    type: object
    description: "包含所有层级（L0-L5）数据和分析结果的完整报告 JSON。"
---

# 币安广场流量预言机 v1.0 (重构版)

本 Skill 旨在通过多维数据采集与融合分析，为您在币安广场（Binance Square）的创作提供数据支撑和策略指导。

通过调用 9 层数据架构，预言机能够实时洞察市场情绪、挖掘热门叙事、捕捉链上异动，并结合时间窗口为您生成最具潜力的内容选题和高质量文章。

**v1.0 是一次全面的系统性重构**，在保留 v6.0 所有功能的基础上，从工程层面进行了深度优化：配置中心化、智能缓存、性能监控与日志，使 Skill 达到生产级标准。

---

## 架构说明 (9-Layer Architecture)

预言机系统由以下 9 个核心层级构成，自下而上层层递进：

- **L0 广场实时热帖 (Square Monitor)**：抓取广场当前浏览量、点赞数最高的热门帖子（1000-2000+ 条），提取热门标签和互动率。**[v1.0]** 应用 4 小时缓存。
- **L1 社交热度排名 (Social Hype)**：基于币安官方 `crypto-market-rank`，分析全网代币的社交讨论热度和情绪偏向。**[v1.0]** 应用 4 小时缓存。
- **L2 链上异动监控 (On-chain Anomaly)**：基于币安官方 `trading-signal` 和 `smart-money`，追踪巨鲸买卖信号和资金净流入。**[v1.0]** 应用 4 分钟缓存。
- **L3 行情分析引擎 (Market Analysis)**：结合币安现货行情与 K 线数据，配合恐惧贪婪指数，输出技术面分析。**[v6.0 新增]** Alpha 早期项目监控和合约多空比/清算数据（均为可选模块，无需认证）。
- **L4 新闻与 KOL 信号 (News & KOL)**：**[可选]** 接入 6551 API，实时监控加密媒体新闻和顶级 KOL 推文，提取全网热词。**[v1.0]** 应用 4 分钟缓存。
- **L5 信号融合引擎 (Signal Fusion)**：核心调度层，将 L0-L4 数据进行加权交叉验证（L0 30%, L1 15%, L2 20%, L3 20%, L4 15%），输出综合评分和策略建议。
- **L6 个人风格分析 (Style Analyzer)**：抓取指定个人主页的 100+ 条历史帖子，提取写作风格指纹。
- **L7 多风格文章创作 (Article Generator)**：通过 `data_digest` 数据精简层将海量数据提炼为核心情报，再经二阶段写作（初稿 + 去 AI 味润色）生成最终文章。**[v1.0]** 所有 LLM 调用统一使用 OpenClaw 预置环境，零配置。
- **L8 广场发布层 (Square Post)**：**[可选]** 对接官方 `square-post` v1.1 接口，支持内容预览、原生 `#标签` 处理和完整错误码处理，实现一键发布。

---

## 使用方法

### 在 OpenClaw 中直接调用

```json
{
  "style": "oracle",
  "prompt": "写一篇关于近期BTC行情的分析"
}
```

### 通过命令行运行

```bash
# 推荐：深度模式，指定创作意图
python3 oracle_main.py --deep --prompt "写一篇关于近期BTC行情的分析"

# 指定风格
python3 oracle_main.py --style deep_research --prompt "分析ETH近期链上数据"

# 快速模式（跳过链上和新闻，约5秒）
python3 oracle_main.py --quick --prompt "快速生成BTC快讯"

# 一次生成官方4种组合文章
python3 oracle_main.py --all-combos --deep --prompt "市场热点解读"

# 禁用可选模块
python3 oracle_main.py --no-alpha --no-derivatives --prompt "快速生成BTC快讯"

# 将报告保存为 JSON 和 Markdown 文件
python3 oracle_main.py --save /home/ubuntu/reports --prompt "市场分析"
```

---

## 报告内容解读

预言机报告包含以下关键模块：

1. **预言机评分 (Oracle Score)**：0-100 分，评估当前广场的流量活跃度（如：流量爆发期、流量平稳期）。
2. **综合市场情绪**：基于技术面、社交面和链上数据融合计算出的市场情绪（极度贪婪、偏多、中性、偏空、极度恐惧）。
3. **融合话题与代币**：交叉验证出的高确信度热门话题和代币，建议优先作为发帖素材。
4. **发布时机建议**：根据当前北京时间，评估流量系数，建议最佳发帖时段。
5. **内容策略与标题**：基于情绪和热点生成的发帖策略和爆款标题模板。
6. **[v6.0 新增] Alpha 监控报告**：Alpha 平台高潜力早期项目列表，包含价格变动和市值数据。
7. **[v6.0 新增] 合约数据报告**：多空比、大户持仓比、主动买卖比和最新清算数据。
8. **[v1.0 新增] 性能报告**：各层处理耗时、API 调用成功率和缓存命中率。

---

## 可选模块说明

| 模块 | 默认状态 | 所需配置 | 禁用方式 |
|------|----------|----------|----------|
| **L3 Alpha 监控** | ✅ 自动启用 | 无需配置 | `enable_alpha: false` 或 `--no-alpha` |
| **L3 合约数据** | ✅ 自动启用 | 无需配置 | `enable_derivatives: false` 或 `--no-derivatives` |
| **L4 新闻+KOL** | ⚙️ 需配置 | `TOKEN_6551` | 不设置环境变量即自动跳过 |
| **L8 广场发布** | ⚙️ 需配置 | `SQUARE_API_KEY` | 不设置环境变量即自动跳过 |

---

## 故障排查

**Q: Skill 运行缓慢或超时（超过 20 秒）**
A: 尝试使用 `"quick": true` 参数以快速模式运行，跳过耗时较长的链上数据（L2）和新闻（L4）数据源。

**Q: 生成的文章内容不理想**
A: 尝试更换 `style` 参数，使用不同的写作风格。同时，提供更具体的 `prompt` 创作意图描述，可以显著提升文章质量。

**Q: Alpha 监控或合约数据显示"不可用"**
A: 这两个模块的 API 端点可能受地区网络限制。系统会自动降级，不影响核心功能。您也可以通过 `--no-alpha` 和 `--no-derivatives` 参数手动禁用。

**Q: L4 新闻+KOL 数据为空**
A: 请确认 `TOKEN_6551` 环境变量已正确配置。如果未配置，L4 层会自动跳过，其权重（15%）会动态分配给 L0 和 L3。

**Q: L8 广场发布失败**
A: 请检查 `SQUARE_API_KEY` 是否有效。常见错误码：`100001`（API Key 无效）、`200003`（内容超出 500 字符限制）、`200007`（发布频率过高）。

---

## 依赖与环境

- 依赖币安官方 API（`api.binance.com` / `data-api.binance.vision` / `web3.binance.com`）
- 依赖 6551 开放 API（可选，需配置环境变量 `TOKEN_6551`）
- 依赖 OpenClaw 预置的 OpenAI 兼容 API（`gpt-4.1-mini`，自动注入，无需配置）
- 无需额外部署数据库，所有计算在内存中完成，轻量高效。

---

## 赞助支持

如果这个项目对您有帮助，欢迎赞助支持！

**BSC（BEP-20）钱包地址：**
`0x3B74BE938caB987120C3661C8e3161CD838e5a1A`

支持 USDT / BNB / 任意 BEP-20 代币。感谢每一位支持者 🙏

**作者/贡献者：** [wxie0815-arch](https://github.com/wxie0815-arch) | 币安广场 [@wuxie](https://www.binance.com/en/square/profile/wuxie) | X [@wuxie149](https://x.com/wuxie149)
