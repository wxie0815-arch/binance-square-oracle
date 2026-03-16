---
name: binance-square-oracle
description: >
  币安广场智能内容预言机。原生集成币安官方 Skills Hub 全部 12 个 Skill 的数据能力，
  按创作风格智能路由数据采集，支持 9 种内置风格 + 用户 DIY 自定义风格，
  通过 2 次 LLM 调用生成带预言机评分的高质量广场文章。安装即用，无需额外配置。
metadata: {"openclaw": {"requires": {"bins": ["python3"]}}}
---

# Binance Square Oracle v1.0

币安广场智能内容预言机 — 一个基于币安官方 Skills Hub 的全栈数据驱动内容创作引擎。

本预言机**原生集成**了币安官方 Skills Hub（[binance/binance-skills-hub](https://github.com/binance/binance-skills-hub)）发布的全部 12 个 Skill 的数据能力，通过直接调用官方 API 端点实现数据采集，无需用户额外安装 Skills Hub。安装本 Skill 后即可立即使用全部功能。

---

## 依赖说明

### Python 依赖

本 Skill 仅依赖以下 Python 包，安装脚本会自动处理：

| 依赖包 | 用途 |
| :--- | :--- |
| `requests` | HTTP 请求（备用） |
| `python-dotenv` | 加载 `.env` 环境变量 |

> **注意**: 本 Skill **不依赖** `openai` 或任何第三方大模型 SDK。所有 LLM 推理能力由 OpenClaw 平台内置提供，用户无需配置任何大模型 API Key。

### 系统依赖

| 依赖 | 版本要求 | 说明 |
| :--- | :--- | :--- |
| Python | 3.8+ | 核心运行环境 |
| pip | 任意 | 安装 Python 依赖 |

### LLM 能力

本 Skill 的文章生成依赖 LLM 推理能力。**LLM 完全由 OpenClaw 平台内置提供**，通过平台的 Chat Completions 端点完成调用，用户无需配置任何大模型 API Key 或端点地址。

---

## 已集成的币安官方 Skill 数据能力

本预言机内置了以下全部 12 个币安官方 Skill 的 API 调用能力：

### 核心数据 Skill（自动调用，无需认证）

| 官方 Skill | 集成能力 | 用途 |
| :--- | :--- | :--- |
| `binance/spot` | 24h Ticker、7 日 K 线 | 现货行情数据 |
| `binance/derivatives-trading-usds-futures` | 全球多空比、顶级账户多空比、资金费率、未平仓合约 | 合约市场数据 |
| `binance/alpha` | Alpha 代币列表、代币行情 | Alpha 代币发现 |
| `binance-web3/crypto-market-rank` | 社交热度排名、热门代币、智能钱流入、Meme 排行 | 市场排名数据 |
| `binance-web3/trading-signal` | 智能钱买卖信号（Solana / BSC） | 链上交易信号 |
| `binance-web3/meme-rush` | 新 Meme 币、已迁移 Meme、话题叙事追踪 | Meme 币发现 |
| `binance-web3/query-token-info` | 代币搜索、动态信息、元数据 | 代币基础信息 |
| `binance-web3/query-token-audit` | 代币合约安全审计 | 合约安全检测 |
| `binance-web3/query-address-info` | 链上地址活跃持仓查询 | 鲸鱼地址分析 |

### 需认证 Skill（已集成接口，用户按需启用）

| 官方 Skill | 集成能力 | 说明 |
| :--- | :--- | :--- |
| `binance/assets` | 资产查询 | 需要 Binance API Key |
| `binance/margin-trading` | 杠杆交易数据 | 需要 Binance API Key |

### 可选增强 Skill

| 官方 Skill | 集成能力 | 说明 |
| :--- | :--- | :--- |
| `binance/square-post` | 广场自动发布 | 需配置 `SQUARE_API_KEY` |

### 第三方补充数据（公开接口，无需认证）

| 数据源 | 集成能力 | 用途 |
| :--- | :--- | :--- |
| CoinGecko | 实时价格、24h 成交量、7 日涨跌 | 价格交叉验证 |
| Blockchain.info | 全网算力、交易量、区块信息 | 链上基础数据 |
| Alternative.me | 恐惧贪婪指数（7 日历史） | 市场情绪指标 |

---

## 安装与使用

### 第一步：安装

在 OpenClaw 环境中，提供本仓库的 Git 地址即可自动安装：

```
https://github.com/wxie0815-arch/binance-square-oracle
```

安装完成后，预言机**立即可用**，无需额外安装币安官方 Skills Hub，也无需配置任何大模型 API Key。

### 第二步：配置增强功能（可选）

安装后，预言机即可在**零配置**下运行基础模式。如需解锁全部潜力，可配置以下环境变量：

| 环境变量 | 功能 | 说明 |
| :--- | :--- | :--- |
| `SQUARE_API_KEY` | L8 广场自动发布 | 启用后，生成的文章将自动发布到您的币安广场账号 |
| `TOKEN_6551` | L4 新闻 + KOL 信号增强 | 提供实时高热新闻和 KOL 动态，丰富文章数据维度 |

> **提示**: 如果不配置以上 Key，预言机将以基础模式运行，自动跳过这些增强功能，不影响核心文章的生成。

### 第三步：开始创作

安装配置完成后，您可以直接通过自然语言向 Agent 发出指令。

---

## Inputs

| 名称 | 类型 | 描述 | 默认值 | 必填 |
| :--- | :--- | :--- | :--- | :--- |
| `symbol` | `string` | CoinGecko 格式代币 ID（如 `bitcoin`） | `bitcoin` | 否 |
| `futures_symbol` | `string` | 合约交易对（如 `BTCUSDT`） | `BTCUSDT` | 否 |
| `style_name` | `string` | 文章风格（见下方风格列表，支持 DIY） | `kol_style` | 否 |
| `user_intent` | `string` | 分析主题描述（如"BTC 深度分析"） | `BTC analysis` | 否 |
| `enable_l4` | `boolean` | 是否启用 L4 新闻增强（需 `TOKEN_6551`） | `false` | 否 |
| `enable_l8` | `boolean` | 是否启用 L8 广场自动发布（需 `SQUARE_API_KEY`） | `false` | 否 |

## Outputs

| 名称 | 类型 | 描述 |
| :--- | :--- | :--- |
| `final_article` | `string` | 经过去 AI 味润色的最终文章 |
| `oracle_score` | `integer` | 预言机市场信心评分（0-100） |
| `style_fingerprint` | `string` | 文章风格指纹（一句话描述当前风格特征） |
| `publish_result` | `object` | （如果 `enable_l8`）广场发布结果 |

---

## 创作风格

预言机支持 9 种内置风格，并允许您轻松创建自己的 DIY 风格。每种风格会智能路由到对应的币安官方 Skill 数据源，只调用所需的接口，提升运行效率。

### 内置风格

| 风格名称 | 适用场景 | 调用的官方 Skill 数据能力 |
| :--- | :--- | :--- |
| `daily_express` | 每日市场速递 | spot、alpha、crypto-market-rank、query-token-info |
| `deep_analysis` | 代币全方位拆解 | spot、derivatives、alpha、trading-signal、query-token-info、query-token-audit |
| `onchain_insight` | 鲸鱼在买什么 | trading-signal、query-address-info、query-token-info、query-token-audit |
| `meme_hunter` | 捕捉下一个叙事 | meme-rush、trading-signal、crypto-market-rank、query-token-info、query-token-audit |
| `kol_style` | KOL 观点输出 | spot、trading-signal、crypto-market-rank |
| `oracle` | 市场预测 | spot、derivatives、trading-signal、crypto-market-rank |
| `project_research` | 新项目介绍 | query-token-info、query-token-audit、alpha、crypto-market-rank |
| `trading_signal` | 交易建议 | spot、derivatives、trading-signal、query-token-audit |
| `tutorial` | 科普教育 | spot、crypto-market-rank |

### DIY 自定义风格

您可以非常简单地创建自己的创作风格：

1. 在 `prompts/` 目录下，创建一个新的 `.md` 文件，例如 `my_style.md`。
2. 在该文件中，用自然语言描述您想要的写作风格、文章结构、语言特点等。
3. 在调用预言机时，将 `style_name` 参数设置为您的文件名（不含 `.md` 后缀），例如 `my_style`。

预言机将自动加载您的风格文件，并使用**默认数据路由**（包含各维度的基础数据）来生成文章。

---

## 执行流程

1. **智能数据采集** (`collect.py`): 根据指定的 `style_name`，从风格-数据路由映射表中找到对应的币安官方 Skill API 组合，只并发调用该风格写作所需的数据源。DIY 风格使用默认路由。

2. **分析与写作** (`oracle.py`): 将采集到的数据和风格模板注入核心 Prompt，进行**第一次 LLM 调用**（由 OpenClaw 平台内置提供），生成文章初稿、预言机评分和风格指纹。

3. **润色与定稿** (`oracle.py`): 将初稿注入 Humanizer Prompt，进行**第二次 LLM 调用**，对内容进行去 AI 味的润色，产出自然、真实的最终稿。

4. **可选发布** (`publish.py`): 如果 `enable_l8` 为 `true` 且 `SQUARE_API_KEY` 已配置，则调用 `binance/square-post` Skill API 将最终文章发布到币安广场。

---

## 赞助支持

如果这个 Skill 对您有帮助，欢迎赞助支持！

**BSC（BEP-20）钱包地址：** `0x3B74BE938caB987120C3661C8e3161CD838e5a1A`

支持 USDT / BNB / 任意 BEP-20 代币。
