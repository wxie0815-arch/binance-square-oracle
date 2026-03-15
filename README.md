# 🔮 Binance Square Oracle v1.0

[![Version](https://img.shields.io/badge/version-v1.0-blue)](https://github.com/wxie0815-arch/binance-square-oracle)
[![OpenClaw](https://img.shields.io/badge/OpenClaw-compatible-green)](https://openclaw.ai)
[![License](https://img.shields.io/badge/license-MIT-yellow)](LICENSE)
[![Skills Hub](https://img.shields.io/badge/Binance-Skills%20Hub-orange)](https://github.com/binance/binance-skills-hub)

> **币安广场智能内容预言机** — 一个基于币安官方 Skills Hub 的全栈数据驱动内容创作引擎。它能根据您选择的创作风格，智能地调用所需的数据接口，高效生成专业、高质量的币安广场文章。

---

## ✨ 核心特色

| 特色 | 说明 |
| :--- | :--- |
| ⚡ **智能数据路由** | 根据创作风格，**仅调用必要的数据源**，告别全量采集，极大提升运行效率和内容相关性。 |
| 🏦 **12 个官方 Skill 集成** | 完整覆盖 `spot`, `derivatives`, `alpha`, `crypto-market-rank`, `trading-signal`, `meme-rush`, `query-token-info` 等全部 12 个官方数据类 Skill。 |
| 🎨 **9+ 种创作风格** | 内置 9 种专业风格，覆盖从深度分析到 Meme 追踪的全场景。 |
| ✍️ **DIY 自定义风格** | **支持用户创建自己的 `.md` 风格文件**，实现无限的创作可能性。 |
| 🤖 **2 次 LLM 调用** | 第一次：分析数据 + 生成初稿 + 预言机评分；第二次：去 AI 味润色，确保内容真实自然。 |
| 📊 **预言机评分** | LLM 根据多维度数据给出 0-100 分市场信心评分，为您的判断提供参考。 |
| 📰 **L4 新闻增强（可选）** | 接入 6551 API，获取高热新闻和 KOL 推文，有 `TOKEN_6551` 时自动启用。 |
| 📢 **L8 广场发布（可选）** | 对接官方 `square-post` 接口，有 `SQUARE_API_KEY` 时自动发布文章。 |
| 🧠 **零配置开箱即用** | 在 OpenClaw 环境下，无需配置任何 AI 模型密钥，安装即可使用。 |

---

## 🚀 快速开始 (OpenClaw 环境)

1.  **安装 Skill**
    在 OpenClaw Agent 中，提供本仓库的 Git 地址即可自动完成安装。

2.  **配置可选增强功能（重要提示）**
    安装后，预言机即可在无任何配置下运行。但为了解锁全部潜力，建议配置以下环境变量：

    *   **启用 L8 广场自动发布**: 设置 `SQUARE_API_KEY` 环境变量。您可以在币安广场的开发者后台获取此 Key。启用后，生成的文章将自动发布到您的币安广场账号。
    *   **启用 L4 新闻 + KOL 信号增强**: 设置 `TOKEN_6551` 环境变量。这将为预言机提供实时的高热新闻和 KOL 动态，极大丰富文章的数据维度。

    > **提示**: 如果不配置以上 Key，预言机将以基础模式运行，自动跳过这些增强功能，不影响核心文章的生成。

3.  **开始使用**
    安装配置完成后，您可以直接通过自然语言向 Agent 发出指令。

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

## 🏗️ 架构总览 (v1.0)

```
┌─────────────────────────────────────────────────────────────────┐
│                   Binance Square Oracle v1.0                    │
│                   Style-Driven Architecture                     │
└─────────────────────────────────────────────────────────────────┘

           Style: "deep_analysis" / "meme_hunter" / "my_style.md"
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│  collect.py — 智能数据采集层                                      │
│                                                                  │
│  1. 根据风格名称，从 STYLE_DATA_ROUTES 查找对应的 Skill 组合。     │
│  2. 如果是 DIY 风格，则使用默认数据路由（DEFAULT_DATA_ROUTE）。      │
│  3. 并发调用被路由到的数据源，例如：                             │
│     - "deep_analysis" -> [spot, derivatives, trading-signal, ...]  │
│     - "meme_hunter"   -> [meme-rush, social-hype, trading-signal]  │
│                                                                  │
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
│  调用官方 binance/square-post 接口，自动发布文章到币安广场。       │
│  - 自动从文章内容提取 #hashtags 和 $mentionedCoins。             │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

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

## 📦 文件结构

```
binance-square-oracle/
├── collect.py              # 智能数据采集层（按风格路由）
├── oracle.py               # 核心引擎（2次 LLM 调用，生成文章 + 评分）
├── publish.py              # L8 广场发布（可选）
├── config.py               # 统一配置（版本号、目录、LLM 调用）
├── requirements.txt        # Python 依赖
├── .env.example            # 环境变量模板
├── prompts/                # 9 种内置风格 + DIY 风格存放目录
│   ├── kol_style.md
│   └── ... (8 more styles)
├── skills/                 # 依赖的 Skill 子模块
│   └── crypto-content-writer/
└── SKILL.md                # OpenClaw Skill 声明文件
```

---

## 🙏 赞助支持

如果这个项目对您有帮助，欢迎赞助支持，让预言机持续进化！

**BSC（BEP-20）钱包地址：**

```
0x3B74BE938caB987120C3661C8e3161CD838e5a1A
```

支持 USDT / BNB / 任意 BEP-20 代币。感谢每一位支持者 🙏

---

**作者：** [wxie0815-arch](https://github.com/wxie0815-arch)
