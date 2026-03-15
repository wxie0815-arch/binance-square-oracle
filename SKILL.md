---
name: binance-square-oracle
version: 1.0
description: >
  币安广场智能内容预言机 v1.0。按创作风格智能路由数据采集，完整集成 12 个币安官方 Skill，
  支持 9 种内置风格 + 用户 DIY 自定义风格。通过 2 次 LLM 调用生成带预言机评分的高质量广场文章，
  可选 L4 新闻增强和 L8 广场自动发布。
author: wxie0815-arch
license: MIT
skills_hub: https://github.com/binance/binance-skills-hub

dependencies:
  # 预言机核心依赖的官方 Skill
  official_skills:
    - binance/spot@1.0.2
    - binance/derivatives-trading-usds-futures@1.0.0
    - binance/alpha@1.0.0
    - binance-web3/crypto-market-rank@1.0.0
    - binance-web3/trading-signal@1.0.0
    - binance-web3/meme-rush@1.0.0
    - binance-web3/query-token-info@1.0.0
    - binance-web3/query-token-audit@1.0.0
    - binance-web3/query-address-info@1.0.0
    # 以下 Skill 已集成，但需要用户认证，当前版本未使用其需认证的端点
    - binance/assets@1.0.0
    - binance/margin-trading@1.0.0

  # 可选功能依赖
  optional_skills:
    - binance/square-post@1.1  # L8 广场发布，需 SQUARE_API_KEY
    - data_6551                # L4 新闻增强，需 TOKEN_6551
---

# Binance Square Oracle v1.0

币安广场智能内容预言机，一个基于币安官方 Skills Hub 的全栈数据驱动内容创作引擎。它能根据您选择的创作风格，智能地调用所需的数据接口，高效生成专业、高质量的币安广场文章。

---

## 🚀 安装与使用

为了获得最佳体验，请在 OpenClaw 环境下安装和使用。

1.  **安装 Skill**
    在 OpenClaw Agent 中，提供本仓库的 Git 地址即可自动安装。

2.  **配置可选增强功能（重要提示）**
    安装后，预言机即可在无任何配置下运行。但为了解锁全部潜力，建议配置以下环境变量：

    *   **启用 L8 广场自动发布**: 设置 `SQUARE_API_KEY` 环境变量。您可以在币安广场的开发者后台获取此 Key。启用后，生成的文章将自动发布到您的币安广场账号。
    *   **启用 L4 新闻 + KOL 信号增强**: 设置 `TOKEN_6551` 环境变量。这将为预言机提供实时的高热新闻和 KOL 动态，极大丰富文章的数据维度。

    > **提示**: 如果不配置以上 Key，预言机将以基础模式运行，自动跳过这些增强功能，不影响核心文章的生成。

3.  **开始使用**
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

## 🎨 创作风格

预言机支持 9 种内置风格，并允许您轻松创建自己的 DIY 风格。

### 内置风格

| 风格名称 | 适用场景 | 数据源路由特点 |
| :--- | :--- | :--- |
| `daily_express` | 每日市场速递 | 侧重现货行情、市场排名、Alpha 信号 |
| `deep_analysis` | 代币全方位拆解 | 侧重现货/合约数据、链上信号、安全审计 |
| `onchain_insight` | 鲸鱼在买什么 | 强依赖智能钱信号、地址查询、代币信息 |
| `meme_hunter` | 捕捉下一个叙事 | 强依赖 Meme 叙事追踪、社交热度、交易信号 |
| `kol_style` | KOL 观点输出 | 侧重现货行情、社交热度、交易信号 |
| `oracle` | 市场预测 | 侧重现货/合约数据、多空比、智能钱信号 |
| `project_research` | 新项目介绍 | 侧重代币信息、安全审计、Alpha 排名 |
| `trading_signal` | 交易建议 | 侧重现货/合约数据、交易信号、风险指标 |
| `tutorial` | 科普教育 | 侧重基础行情、市场排名、通用数据 |

### DIY 自定义风格

您可以非常简单地创建自己的创作风格！

1.  在 `prompts/` 目录下，创建一个新的 `.md` 文件，例如 `my_style.md`。
2.  在该文件中，用自然语言描述您想要的写作风格、文章结构、语言特点等。
3.  在调用预言机时，将 `style_name` 参数设置为您的文件名（不含 `.md` 后缀），例如 `my_style`。

预言机将自动加载您的风格文件，并使用**默认数据路由**（包含各维度的基础数据）来生成文章。

---

## ⚙️ 执行流程

1.  **智能数据采集 (`collect.py`)**: Agent 根据您指定的 `style_name`，从 `STYLE_DATA_ROUTES` 映射表中找到对应的 Skill 组合，只并发调用完成该风格写作所需的数据源。如果是 DIY 风格，则使用 `DEFAULT_DATA_ROUTE` 路由。

2.  **分析与写作 (`oracle.py`)**: 将采集到的数据和风格模板注入核心 Prompt，进行**第一次 LLM 调用**，生成文章初稿、预言机评分和风格指纹。

3.  **润色与定稿 (`oracle.py`)**: 将初稿注入 Humanizer Prompt，进行**第二次 LLM 调用**，对内容进行去 AI 味的润色，产出自然、真实的最终稿。

4.  **可选发布 (`publish.py`)**: 如果 `enable_l8` 为 `true` 且 `SQUARE_API_KEY` 已配置，则调用 `binance/square-post` Skill 将最终文章发布到币安广场。

---

## 赞助支持

如果这个 Skill 对您有帮助，欢迎赞助支持！

**BSC（BEP-20）钱包地址：** `0x3B74BE938caB987120C3661C8e3161CD838e5a1A`

支持 USDT / BNB / 任意 BEP-20 代币。感谢每一位支持者 🙏
