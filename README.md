# Binance Square Oracle v1.0

[![Version](https://img.shields.io/badge/version-v1.0-blue)](https://github.com/wxie0815-arch/binance-square-oracle)
[![OpenClaw](https://img.shields.io/badge/OpenClaw-compatible-green)](https://openclaw.ai)
[![License](https://img.shields.io/badge/license-MIT-yellow)](LICENSE)
[![Skills Hub](https://img.shields.io/badge/Binance-Skills%20Hub-orange)](https://github.com/binance/binance-skills-hub)

> **币安广场智能内容预言机** — 一个基于币安官方 Skills Hub 的全栈数据驱动内容创作引擎。**原生集成**全部 12 个币安官方 Skill 的数据能力，无需额外安装 Skills Hub，安装即用。

---

## 核心特色

| 特色 | 说明 |
| :--- | :--- |
| **原生集成 12 个官方 Skill** | 直接调用币安官方 Skills Hub 全部 12 个 Skill 的 API 端点，覆盖现货、合约、Alpha、链上信号、Meme、安全审计等全维度数据。 |
| **智能数据路由** | 根据创作风格，**仅调用必要的数据源**，告别全量采集，极大提升运行效率和内容相关性。 |
| **9+ 种创作风格** | 内置 9 种专业风格，覆盖从深度分析到 Meme 追踪的全场景。 |
| **DIY 自定义风格** | 支持用户创建自己的 `.md` 风格文件，实现无限的创作可能性。 |
| **2 次 LLM 调用** | 第一次：分析数据 + 生成初稿 + 预言机评分；第二次：去 AI 味润色，确保内容真实自然。 |
| **预言机评分** | LLM 根据多维度数据给出 0-100 分市场信心评分，为您的判断提供参考。 |
| **L4 新闻增强（可选）** | 接入 6551 API，获取高热新闻和 KOL 推文，有 `TOKEN_6551` 时自动启用。 |
| **L8 广场发布（可选）** | 对接官方 `square-post` 接口，有 `SQUARE_API_KEY` 时自动发布文章。 |
| **零配置开箱即用** | 在 OpenClaw 环境下，安装即可使用，无需额外安装币安官方 Skills Hub。 |

---

## 已集成的币安官方 Skill 数据能力

本预言机**原生集成**了 [binance/binance-skills-hub](https://github.com/binance/binance-skills-hub) 发布的全部 12 个 Skill 的 API 调用能力，通过直接调用官方 API 端点实现数据采集。

### 核心数据 Skill（自动调用，无需认证）

| 官方 Skill | 集成能力 | 用途 |
| :--- | :--- | :--- |
| `binance/spot` | 24h Ticker、7 日 K 线 | 现货行情数据 |
| `binance/derivatives-trading-usds-futures` | 全球多空比、顶级账户多空比、资金费率、未平仓合约 | 合约市场数据 |
| `binance/alpha` | Alpha 代币行情、聚合交易、交易所信息 | Alpha 代币发现 |
| `binance-web3/crypto-market-rank` | 热门代币排名、涨跌幅排行 | 市场排名数据 |
| `binance-web3/trading-signal` | 智能钱买卖信号 | 链上交易信号 |
| `binance-web3/meme-rush` | Meme 叙事追踪、热门 Meme 排行 | Meme 币发现 |
| `binance-web3/query-token-info` | 代币搜索、详情查询 | 代币基础信息 |
| `binance-web3/query-token-audit` | 代币安全审计 | 合约安全检测 |
| `binance-web3/query-address-info` | 链上地址持仓查询 | 鲸鱼地址分析 |

### 需认证 Skill（已集成接口，用户按需启用）

| 官方 Skill | 集成能力 | 说明 |
| :--- | :--- | :--- |
| `binance/assets` | 资产查询 | 需要 Binance API Key |
| `binance/margin-trading` | 杠杆交易数据 | 需要 Binance API Key |

### 可选增强 Skill

| 官方 Skill | 集成能力 | 说明 |
| :--- | :--- | :--- |
| `binance/square-post` | 广场自动发布 | 需配置 `SQUARE_API_KEY` |

---

## 快速开始（OpenClaw 环境）

### 第一步：安装

在 OpenClaw Agent 中，提供本仓库的 Git 地址即可自动完成安装：

```
https://github.com/wxie0815-arch/binance-square-oracle
```

安装完成后，预言机**立即可用**，无需额外安装币安官方 Skills Hub。

### 第二步：配置增强功能（可选）

安装后，预言机即可在**零配置**下运行基础模式。如需解锁全部潜力，可配置以下环境变量：

| 环境变量 | 功能 | 说明 |
| :--- | :--- | :--- |
| `SQUARE_API_KEY` | L8 广场自动发布 | 启用后，生成的文章将自动发布到您的币安广场账号 |
| `TOKEN_6551` | L4 新闻 + KOL 信号增强 | 提供实时高热新闻和 KOL 动态，丰富文章数据维度 |

> **提示**: 如果不配置以上 Key，预言机将以基础模式运行，自动跳过这些增强功能，不影响核心文章的生成。

### 第三步：开始创作

安装配置完成后，您可以直接通过自然语言向 Agent 发出指令：

```
请用"深度分析"风格，为我写一篇关于 ETH 的市场分析文章。
```

```
启动预言机，用"Meme 猎手"风格分析当前最火的 Meme 币，并发布到广场。
```

```
我想用自己的风格写文章，这是我的风格文件路径: prompts/my_awesome_style.md
```

---

## 架构总览

```
┌─────────────────────────────────────────────────────────────────┐
│                   Binance Square Oracle v1.0                    │
│              原生集成 12 个币安官方 Skill 数据能力                │
└─────────────────────────────────────────────────────────────────┘

           Style: "deep_analysis" / "meme_hunter" / "my_style.md"
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│  collect.py — 智能数据采集层                                      │
│                                                                  │
│  根据风格名称，从 STYLE_DATA_ROUTES 查找对应的官方 Skill API 组合  │
│  并发调用被路由到的数据源：                                       │
│    - "deep_analysis" -> [spot, derivatives, trading-signal, ...]  │
│    - "meme_hunter"   -> [meme-rush, social-hype, trading-signal]  │
│    - DIY 风格        -> DEFAULT_DATA_ROUTE                        │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼ 结构化市场数据 (仅包含风格所需数据)
┌──────────────────────────────────────────────────────────────────┐
│  oracle.py — 2 次 LLM 调用核心引擎                                │
│                                                                  │
│  第一次 LLM 调用（分析 + 写作）：                                  │
│    输入：(风格化数据) + (风格模板 prompts/) + (写作规则)           │
│    输出：初稿 + 预言机评分（0-100）+ 风格指纹                      │
│                                                                  │
│  第二次 LLM 调用（去 AI 味润色）：                                 │
│    输入：初稿 + Humanizer 规则                                    │
│    输出：终稿（自然、真实、无 AI 痕迹）                             │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼ 终稿 + 评分
┌──────────────────────────────────────────────────────────────────┐
│  publish.py — 可选发布层 (需 SQUARE_API_KEY)                      │
│                                                                  │
│  调用官方 binance/square-post 接口，自动发布文章到币安广场         │
│  自动从文章内容提取 #hashtags 和 $mentionedCoins                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 创作风格

预言机支持 9 种内置风格，并允许您轻松创建自己的 DIY 风格。每种风格会智能路由到对应的币安官方 Skill 数据源，只调用所需的接口，提升运行效率。

### 内置风格

| 风格名称 | 适用场景 | 调用的官方 Skill 数据能力 |
| :--- | :--- | :--- |
| `daily_express` | 每日市场速递 | spot、alpha、crypto-market-rank、trading-signal |
| `deep_analysis` | 代币全方位拆解 | spot、derivatives、alpha、trading-signal、query-token-info、query-token-audit |
| `onchain_insight` | 鲸鱼在买什么 | trading-signal、query-address-info、query-token-info、crypto-market-rank |
| `meme_hunter` | 捕捉下一个叙事 | meme-rush、trading-signal、crypto-market-rank |
| `kol_style` | KOL 观点输出 | spot、trading-signal、crypto-market-rank |
| `oracle` | 市场预测 | spot、derivatives、trading-signal、query-token-info |
| `project_research` | 新项目介绍 | query-token-info、query-token-audit、alpha、crypto-market-rank |
| `trading_signal` | 交易建议 | spot、derivatives、trading-signal |
| `tutorial` | 科普教育 | spot、crypto-market-rank |

### DIY 自定义风格

您可以非常简单地创建自己的创作风格：

1. 在 `prompts/` 目录下，创建一个新的 `.md` 文件，例如 `my_style.md`。
2. 在该文件中，用自然语言描述您想要的写作风格、文章结构、语言特点等。
3. 在调用预言机时，将 `style_name` 参数设置为您的文件名（不含 `.md` 后缀），例如 `my_style`。

预言机将自动加载您的风格文件，并使用**默认数据路由**（包含各维度的基础数据）来生成文章。

---

## 文件结构

```
binance-square-oracle/
├── collect.py              # 智能数据采集层（按风格路由调用官方 Skill API）
├── oracle.py               # 核心引擎（2 次 LLM 调用，生成文章 + 评分）
├── publish.py              # L8 广场发布（可选，调用 square-post API）
├── config.py               # 统一配置（版本号、目录、LLM 调用）
├── requirements.txt        # Python 依赖
├── .env.example            # 环境变量模板
├── prompts/                # 9 种内置风格 + DIY 风格存放目录
│   ├── kol_style.md
│   └── ... (8 more styles)
├── skills/                 # 依赖的 Skill 子模块
│   └── crypto-content-writer/
├── SKILL.md                # OpenClaw Skill 声明文件
└── README.md               # 本文件
```

---

## 赞助支持

如果这个项目对您有帮助，欢迎赞助支持，让预言机持续进化！

**BSC（BEP-20）钱包地址：**

```
0x3B74BE938caB987120C3661C8e3161CD838e5a1A
```

支持 USDT / BNB / 任意 BEP-20 代币。感谢每一位支持者 🙏

---

**作者：** [wxie0815-arch](https://github.com/wxie0815-arch)
