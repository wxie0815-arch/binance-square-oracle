# 🔮 币安广场流量预言机 v1.0 (重构版)

[![Version](https://img.shields.io/badge/version-1.0.0-blue)](https://github.com/wxie0815-arch/binance-square-oracle)
[![OpenClaw](https://img.shields.io/badge/OpenClaw-Compatible-green)](https://openclaw.ai)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**配置中心化 × 智能缓存 × 性能监控 × Alpha早期监控 × 合约多空比/清算 × Square-Post v1.1 × 二阶段写作 × 零配置开箱即用**

v1.0 是对 v6.0 架构的一次全面系统性重构，在保留所有已有功能的基础上，从工程层面进行了深度优化：配置中心化、智能缓存、性能监控与日志。所有功能模块均采用**非必选设计**，缺少配置时自动跳过，不影响核心功能。

---

## 💡 可选模块说明

所有功能模块均采用**非必选设计**，缺少配置时自动跳过，不影响核心功能：

| 模块 | 默认状态 | 所需配置 | 禁用方式 |
|------|----------|----------|----------|
| **L3 Alpha 监控** | ✅ 自动启用 | 无需配置 | `--no-alpha` 或 `config.yaml` |
| **L3 合约数据** | ✅ 自动启用 | 无需配置 | `--no-derivatives` 或 `config.yaml` |
| **L4 新闻+KOL** | ⚙️ 需配置 | `TOKEN_6551` | 不设置环境变量即跳过 |
| **L8 广场发布** | ⚙️ 需配置 | `SQUARE_API_KEY` | 不设置环境变量即跳过 |

---

## 🚀 快速开始

### 1. 克隆仓库（包含Submodule）

```bash
git clone --recurse-submodules https://github.com/wxie0815-arch/binance-square-oracle.git
cd binance-square-oracle
```

### 2. 一键安装

```bash
chmod +x install.sh
./install.sh
```

### 3. 运行预言机

```bash
# 推荐：指定创作意图，深度模式
python3 oracle_main.py --deep --prompt "写一篇关于近期BTC行情的分析"

# 指定风格快速生成
python3 oracle_main.py --style deep_research --prompt "分析ETH近期链上数据"

# 一次生成官方4种组合文章
python3 oracle_main.py --all-combos --deep --prompt "市场热点解读"

# 禁用可选模块（按需）
python3 oracle_main.py --no-alpha --no-derivatives --prompt "快速生成BTC快讯"
```

**无需任何额外配置**，系统自动识别 OpenClaw 环境（`gpt-4.1-mini`），零配置开箱即用。

---

## 🏗️ v1.0 重构亮点

### 优化1+4：配置中心化（去除独立 LLM 配置）

v1.0 移除了 `ai_models.py` 和分散在多个文件中的 LLM 配置，将所有 LLM 调用统一到 `config.py` 的 `call_llm()` 函数中，直接使用 OpenClaw 预置的 API 环境。

| 对比项 | v6.0（旧） | v1.0（新） |
|--------|-----------|-----------|
| LLM 配置 | `ai_models.py` 独立管理 | 统一到 `config.py` `call_llm()` |
| API Key | 需手动配置 `.env` | OpenClaw 环境自动注入 |
| 配置文件 | `.env` + `config.yaml` + 代码硬编码 | 仅 `config.py` 统一管理 |
| 开箱即用 | 需手动配置 | 真正零配置 |

### 优化2：智能缓存机制

v1.0 引入了基于数据更新频率的分级缓存策略，大幅减少重复 API 调用，响应时间从 15-20 秒降低至缓存命中时的 1-3 秒。

| 数据类型 | 缓存 TTL | 适用层级 | 说明 |
|----------|---------|---------|------|
| 广场热帖 | **4 小时** | L0 | 广场热帖更新频率低，4小时内数据有效 |
| 社交热度 | **4 小时** | L1 | 社交排名变化缓慢，4小时内数据有效 |
| 链上数据 | **4 分钟** | L2 | 链上信号实时性强，4分钟快速刷新 |
| 新闻数据 | **4 分钟** | L4 | 新闻时效性强，4分钟快速刷新 |

### 优化3：性能监控与日志

v1.0 新增了全面的性能监控模块（`run_monitor.py`），包含：

- **响应时间监控**：对每个处理层级（L0-L8）进行毫秒级耗时打点，生成完整的性能报告。
- **API 调用统计**：记录每个 API 的调用总次数、成功次数、失败次数和缓存命中次数，计算实时成功率。
- **预警机制**：当关键 API 连续失败达到阈值（默认3次）时，自动触发 `WARNING` 级别告警，写入日志文件。
- **结构化日志**：所有监控数据以结构化 JSON 格式写入 `workspace/logs/` 目录，便于后续分析。

---

## 🧠 L0-L8 完整预言机架构流程

预言机采用 9 层（L0-L8）流水线架构，从数据抓取到最终发布全自动完成：

```
┌─────────────────────────────────────────────────────────────┐
│                    L8: Square Publisher (广场发布)            │
│          square-post v1.1 | 内容预览 | #标签处理              │
├─────────────────────────────────────────────────────────────┤
│                    L7: Article Generator (文章生成)           │
│          二阶段写作: crypto-content-writer + humanizer        │
├─────────────────────────────────────────────────────────────┤
│                  data_digest (数据精简层)                      │
│         L0-L5 海量数据 → 核心情报简报 (~500字符)               │
├─────────────────────────────────────────────────────────────┤
│                  L6: Style Analyzer (风格学习)                │
│              个人主页帖子分析 → 写作风格指纹                    │
├─────────────────────────────────────────────────────────────┤
│              L5: Signal Fusion (信号融合引擎)                  │
│    话题融合 | 代币交叉验证 | 情绪融合 | 时机评估 | 策略生成     │
├──────────┬──────────┬──────────┬──────────┬─────────────────┤
│ L0       │ L1       │ L2       │ L3       │ L4              │
│ 广场热帖  │ 社交热度  │ 链上异动  │ 行情分析  │ 新闻+KOL        │
│          │          │          │ Alpha监控 │                 │
│ 热门帖子  │ 热度排名  │ 智能钱信号│ 合约数据  │ opennews        │
│ 互动率   │ 情绪分析  │ 净流入   │ 技术指标  │ opentwitter     │
│ 热门标签  │ 趋势代币  │ Meme热点 │ 恐惧贪婪  │ @binancezh      │
│ 病毒帖   │ 叙事提取  │ 巨鲸预警 │ 趋势代币  │ 话题分类        │
├──────────┴──────────┴──────────┴──────────┴─────────────────┤
│                   Skills Hub (官方Skill融合)                  │
│  spot-ticker | social-hype | smart-money | meme-rush | ...  │
├─────────────────────────────────────────────────────────────┤
│                   run_monitor.py (性能监控)                   │
│         各层耗时 | API成功率 | 连续失败预警 | 结构化日志        │
└─────────────────────────────────────────────────────────────┘
```

### L0: 广场实时热帖监控
深度抓取币安广场 1000-2000+ 条数据（融合 Latest、Trending、Article、NewsFeed 多源），通过智能算法筛选出热门帖子、高互动内容和核心话题，输出 `square_score` 广场热度评分。**[v1.0]** 广场数据现已应用 4 小时缓存，重复调用时响应时间从 8-10 秒降至毫秒级。

### L1: 社交热度排名
调用官方 `crypto-market-rank` Skill，获取全网社交热度排行榜（Social Hype）和统一代币排名（Unified Token Rank），提取市场情绪偏向和趋势代币，输出 `social_score` 社交热度评分。**[v1.0]** 社交数据现已应用 4 小时缓存。

### L2: 链上异动监控
调用官方 `trading-signal` 和 `smart-money` Skill，监控聪明钱（Smart Money）的买入/卖出信号、资金净流入情况以及 Meme 币热点，输出 `anomaly_score` 链上异动评分。**[v1.0]** 链上数据现已应用 4 分钟缓存，确保数据实时性。

### L3: 行情分析引擎（含 Alpha 和 Derivatives 可选模块）
调用官方 `spot` Skill 和外部 API，获取 BTC/ETH 等主流币种的实时 K 线数据、24小时涨跌幅以及全网恐惧贪婪指数（Fear & Greed），输出 `market_score` 行情状态评分。

**[Alpha 可选] 早期项目监控**：接入官方 `binance-skills-hub/alpha` v1.0.0 公开接口（无需认证），获取 Alpha 平台最新上线项目、价格变动、市值和持有人数，自动筛选高潜力项目（score > 0 且 24h 涨幅 > 5%）。

**[Derivatives 可选] 合约多空比/清算数据**：接入官方 `binance-skills-hub/derivatives-trading-usds-futures` v1.0.0 公开接口（无需认证），获取全局多空持仓人数比、大户持仓多空比、主动买卖量比率和最新强平订单。

### L4: 新闻与 KOL 信号（可选）
**[可选模块]** 调用 6551 开放 API，抓取全网最新加密新闻和头部 KOL（如 @binancezh）的推文动态，进行话题分类和热度评估，输出 `news_score` 新闻热度评分。**[v1.0]** 新闻数据现已应用 4 分钟缓存。
> **优雅降级**：如果 `TOKEN_6551` 环境变量未配置，此层将自动跳过，其权重（15%）会动态分配给 L0 和 L3。

### L5: 信号融合引擎
接收 L0-L4 的五层报告，执行加权融合（L0 30%, L1 15%, L2 20%, L3 20%, L4 15%）。进行话题交叉验证、情绪融合和时机评估，最终输出预言机总评分（`oracle_score`）和内容推荐策略。

### L6: 个人风格分析
抓取指定个人主页（默认官方账号或用户账号）的 100+ 条历史帖子，提取其写作习惯、常用词汇、段落结构和语气，生成独一无二的"写作风格指纹"（Style Fingerprint）。

### L7: 多风格文章创作
1. **数据精简 (`data_digest`)**：将 L0-L5 和 Skills Hub 的海量原始 JSON 数据提炼为约 500 字符的"核心情报简报"，避免 LLM 截断丢失信息。
2. **二阶段写作 (`crypto-content-writer`)**：
   - **阶段一**：根据精简数据、用户意图和 L6 风格指纹，直接生成高质量文章初稿。
   - **阶段二**：内置 `humanizer` 规则，对初稿进行去 AI 味润色，替换套话，调整为真实的 Web3 中文语境。

**[v1.0]** 所有 LLM 调用现在统一通过 `config.py` 的 `call_llm()` 函数，直接使用 OpenClaw 预置的 `gpt-4.1-mini` 模型，无需任何额外配置。

### L8: 广场自动发布（可选，square-post v1.1 接口）
**[可选模块]** 对 L7 生成的文章进行增强版事实校验（价格、涨跌幅、逻辑自洽性），校验通过后，通过官方 `square-post` Skill 自动发布到币安广场。

**[v1.1 接口升级]** 升级至官方 square-post v1.1.0 接口规范：

| 对比项 | 旧版 | v1.1（新） |
|--------|------|-----------|
| 内容预览 | 无 | 发布前展示原始/优化两版内容，用户可选择 |
| #标签处理 | 手动添加 | 原生支持：自动规范化、去重、追加相关标签 |
| 错误码处理 | 仅 success/fail | 完整覆盖 v1.1 全部 8 个错误码 |
| 字符限制 | 500 字（软限制） | 500 字符（v1.1 接口硬限制，自动检查） |

> **优雅降级**：如果 `SQUARE_API_KEY` 环境变量未配置，此层将自动跳过，仅生成文章而不发布。

---

## 📊 评分体系

| 层级 | 评分字段 | 权重 | 说明 |
|------|---------|------|------|
| L0 | `square_score` | 30% | 广场热度（帖子数、浏览量、互动率） |
| L1 | `social_score` | 15% | 社交热度（代币讨论量、情绪偏向） |
| L2 | `anomaly_score` | 20% | 链上异动（智能钱信号、资金流向） |
| L3 | `market_score` | 20% | 行情状态（技术指标、恐惧贪婪） |
| L4 | `news_score` | 15% | 新闻热度（新闻量、KOL互动量） |

---

## 📝 9种文章风格

### ★ 官方推荐组合（4种）—— 使用 `--combo` 参数

| 组合 ID | 名称 | 适用场景 |
|---------|------|----------|
| `daily_express` | 日常快讯型 | 每日行情速报、热点资讯 |
| `deep_analysis` | 深度分析型 | 代币研报、技术深度解析 |
| `onchain_insight` | 链上洞察型 | 鲸鱼追踪、链上数据解读 |
| `meme_hunter` | Meme猎手型 | Meme币热点、社区情绪 |

### ◆ 扩展风格（5种）—— 使用 `--style` 参数

| 风格 ID | 名称 | 适用场景 |
|---------|------|----------|
| `oracle` | 综合预言机型 | 全面市场综合报告（默认） |
| `news_flash` | 快讯速递型 | 简洁市场快讯 |
| `deep_research` | 深度研报型 | 代币/项目深度研究 |
| `whale_tracker` | 鲸鱼追踪型 | 聪明钱动向分析 |
| `meme_scout` | Meme侦察兵型 | Meme赛道热点发现 |
| `kol_style` | KOL风格型 | 个人观点输出 |
| `tutorial` | 教程科普型 | 新手教育、概念解释 |

> **扩展新风格**：在 `prompts/` 目录下新建 `.md` 文件，系统下次启动时自动加载，无需修改任何代码。

---

## 🔗 API 端点清单

| 层级 | API 端点 | 认证 | 说明 |
|------|----------|------|------|
| L0 | `binance.com/bapi/composite/v3/.../article/list` | 无需 | 广场热门帖子 |
| L1 | `web3.binance.com/.../social/hype/rank/leaderboard` | 无需 | 社交热度排名 |
| L1 | `web3.binance.com/.../unified/rank/list` | 无需 | 趋势代币排名 |
| L2 | `web3.binance.com/.../trading-signal/signal/list` | 无需 | 智能钱信号 |
| L2 | `web3.binance.com/.../smart-money/net-inflow` | 无需 | 资金净流入 |
| L2 | `web3.binance.com/.../meme-rush/topic/list` | 无需 | Meme热点 |
| L3 | `data-api.binance.vision/api/v3/klines` | 无需 | K线数据 |
| L3 | `data-api.binance.vision/api/v3/ticker/24hr` | 无需 | 24h行情 |
| L3 | `api.alternative.me/fng/` | 无需 | 恐惧贪婪指数 |
| L3 | `binance.com/bapi/defi/v1/public/alpha-trade/...` | 无需 | **[Alpha]** 早期项目列表 |
| L3 | `fapi.binance.com/futures/data/globalLongShortAccountRatio` | 无需 | **[Derivatives]** 全局多空比 |
| L3 | `fapi.binance.com/futures/data/topLongShortPositionRatio` | 无需 | **[Derivatives]** 大户持仓多空比 |
| L3 | `fapi.binance.com/fapi/v1/allForceOrders` | 无需 | **[Derivatives]** 强平订单 |
| L4 | `ai.6551.io/open/news_search` | Bearer Token | 新闻搜索（可选） |
| L4 | `ai.6551.io/open/twitter_user_tweets` | Bearer Token | KOL推文（可选） |

---

## 🔗 依赖 Skill

本 Skill 安装时自动下载以下依赖（Git Submodule）：

| Skill | 来源 | 用途 |
|-------|------|------|
| `crypto-content-writer` | [GitHub](https://github.com/wxie0815-arch/crypto-content-writer) | 二合一写作引擎（初稿+润色） |
| `binance-square-monitor` | [GitHub](https://github.com/wxie0815-arch/binance-square-monitor) | L0 广场数据深度抓取 |
| `binance-square-profile-analyzer` | [GitHub](https://github.com/wxie0815-arch/binance-square-profile-analyzer) | L6 个人主页风格分析 |

---

## 🛠️ 高级配置（可选）

编辑 `config.yaml` 为不同写作阶段指定不同 LLM 模型，或强制关闭可选模块：

```yaml
llm:
  default_model: "gpt-4.1-mini"
  roles:
    writer: "gpt-4.1-mini"
    humanizer: "gpt-4.1-nano"
    analyzer: "gpt-4.1-mini"

optional_modules:
  force_disable_alpha_monitor: false      # 设为 true 可禁用 Alpha 监控
  force_disable_derivatives_data: false   # 设为 true 可禁用合约数据
  force_disable_6551: false
  force_disable_square_publish: false
```

---

## 📁 文件结构

```
binance-square-oracle/
├── oracle_main.py          # 主入口（支持 --no-alpha / --no-derivatives）
├── config.py               # 统一配置中心（v1.0 重构，LLM + API + 缓存配置）
├── config.yaml             # 高级配置（可选）
├── data_cache.py           # 智能缓存（v1.0 重构，分级 TTL 策略）
├── run_monitor.py          # 性能监控与日志（v1.0 新增）
├── data_digest.py          # 数据精简层
├── writing_skill.py        # 二阶段写作流程控制器（v1.0 重构）
├── L0_square_monitor.py    # 广场数据抓取层（4h 缓存）
├── L1_social_hype.py       # 社交热度层（4h 缓存）
├── L2_onchain_anomaly.py   # 链上异动层（4min 缓存）
├── L3_market_analysis.py   # 行情分析层（含 Alpha + Derivatives 可选模块）
├── L4_news_kol.py          # 新闻+KOL层（可选，4min 缓存）
├── L5_signal_fusion.py     # 信号融合层
├── L6_style_analyzer.py    # 个人风格分析层
├── L7_article_generator.py # 文章生成层
├── L8_square_publisher.py  # 广场发布层（square-post v1.1 接口）
├── binance_skills_hub.py   # 官方8大Skill融合
├── square_oracle.py        # 预言机核心逻辑
├── install.sh              # 一键安装脚本
├── requirements.txt        # Python依赖
├── prompts/                # 9种风格的Prompt模板
└── skills/                 # 写作Skill（Git Submodule）
    └── crypto-content-writer/
```

---

## 📋 更新日志

### v1.0 (2026-03-15) — 系统性重构

- **[优化1+4] 配置中心化**：删除 `ai_models.py`，所有 LLM 调用统一通过 `config.py` 的 `call_llm()` 函数，直接使用 OpenClaw 预置环境，零配置开箱即用
- **[优化2] 智能缓存**：重构 `data_cache.py`，广场/社交数据 TTL 设为 4 小时，链上/新闻数据 TTL 设为 4 分钟；为 L1、L2、L4 的数据抓取函数应用 `@cached` 装饰器
- **[优化3] 性能监控**：重构 `run_monitor.py`，新增 `PerformanceMonitor`（各层耗时打点）和 `APIMonitor`（成功率统计 + 连续失败预警），结构化日志写入 `workspace/logs/`
- **[优化6] 文档更新**：全面重写 `SKILL.md` 和 `README.md`，提供更完整的使用说明、架构图、API 端点清单和故障排查指南

### v6.0 (2026-03-15) — L3 + L8 双升级

- **[L3 升级] Alpha 早期项目监控**：接入官方 `binance-skills-hub/alpha` v1.0.0 公开接口，无需认证，自动筛选高潜力项目
- **[L3 升级] 合约多空比/清算数据**：接入官方 `binance-skills-hub/derivatives-trading-usds-futures` v1.0.0 公开接口，获取全局多空比、大户持仓比、主动买卖比和强平订单
- **[L8 升级] Square-Post v1.1**：升级至官方 v1.1.0 接口规范，新增内容预览流程、原生 `#标签` 处理（规范化/去重/自动追加）、完整 8 个错误码映射

### v5.0 (2026-03-15) — 写作流程优化

- 新增 `data_digest.py` 数据精简层，传入数据量减少 **83%**
- 二阶段写作流程，LLM 调用从 3 次降至 2 次，响应时间缩短 **50%**
- 消除重复 API 调用，3 个旧 Skill 仓库合并为 1 个

---

## 💰 赞助支持

如果这个项目对您有帮助，欢迎赞助支持！

**BSC（BEP-20）钱包地址：**
`0x3B74BE938caB987120C3661C8e3161CD838e5a1A`

支持 USDT / BNB / 任意 BEP-20 代币。感谢每一位支持者 🙏

**作者/贡献者：** [wxie0815-arch](https://github.com/wxie0815-arch) | 币安广场 [@wuxie](https://www.binance.com/en/square/profile/wuxie) | X [@wuxie149](https://x.com/wuxie149)
