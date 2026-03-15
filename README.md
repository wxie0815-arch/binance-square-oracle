# 🔮 Binance Square Oracle

[![Version](https://img.shields.io/badge/version-v1.1-blue)](https://github.com/wxie0815-arch/binance-square-oracle)
[![OpenClaw](https://img.shields.io/badge/OpenClaw-compatible-green)](https://openclaw.ai)
[![License](https://img.shields.io/badge/license-MIT-yellow)](LICENSE)
[![Skills Hub](https://img.shields.io/badge/Binance-Skills%20Hub-orange)](https://github.com/binance/binance-skills-hub)

> **币安广场智能内容预言机** — 基于币安官方 Skills Hub 的全栈数据驱动内容创作引擎。
> 并发采集 12 个官方 Skill 数据源，2 次 LLM 调用，生成带预言机评分的高质量广场文章。

---

## ✨ 核心特色

| 特色 | 说明 |
| :--- | :--- |
| 🏦 **12 个官方 Skill 数据源** | 完整覆盖 `binance/spot`、`binance/alpha`、`binance/derivatives-trading-usds-futures`、`binance-web3/crypto-market-rank`、`binance-web3/trading-signal`、`binance-web3/meme-rush` 等官方 Skill |
| ⚡ **并发采集，极速响应** | 所有数据源并发请求，采集时间从串行的 15-20 秒压缩至约 5 秒 |
| 🎨 **9 种文章风格** | KOL 风格、深度分析、每日快讯、Meme 猎手、链上洞察、预言机、项目研究、交易信号、教程，覆盖全场景 |
| 🤖 **2 次 LLM 调用** | 第一次：分析数据 + 生成初稿 + 预言机评分；第二次：去 AI 味润色，确保内容真实自然 |
| 📊 **预言机评分** | LLM 根据多维度数据给出 0-100 分市场信心评分，并提供评分理由 |
| 🔬 **Alpha 早期项目监控** | 实时追踪币安 Alpha 平台的早期项目列表，第一时间发现潜力代币 |
| 📈 **合约多空比 / 清算数据** | 接入 `fapi.binance.com` 公开合约数据，分析市场多空情绪 |
| 💡 **智能钱流入追踪** | 实时监控链上聪明钱的资金流向，捕捉机构级别的信号 |
| 🐸 **Meme 叙事追踪** | 追踪 Meme Rush 新发和迁移代币，不错过任何叙事风口 |
| 📰 **L4 新闻 + KOL 信号（可选）** | 接入 6551 私有 API，获取高热新闻和 KOL 推文，有 `TOKEN_6551` 时自动启用 |
| 📢 **L8 广场自动发布（可选）** | 对接官方 `square-post` v1.1 接口，有 `SQUARE_API_KEY` 时自动启用 |
| 🧠 **零配置开箱即用** | 直接使用 OpenClaw 系统 LLM，无需配置任何 AI 模型密钥 |

---

## 🏗️ 架构总览（C 方案 v1.1）

```
┌─────────────────────────────────────────────────────────────────┐
│                   Binance Square Oracle v1.1                    │
│                         C 方案极简架构                           │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│  collect.py — 并发数据采集层                                      │
│                                                                  │
│  官方 Skill 数据源（全部无需认证）：                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │ binance/spot    │  │ binance/alpha   │  │ binance/        │  │
│  │ 现货行情         │  │ 早期项目监控     │  │ derivatives-    │  │
│  │ 24h ticker      │  │ Alpha 代币列表   │  │ trading         │  │
│  │ K 线数据         │  │ Alpha 行情       │  │ 多空比/清算      │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │ binance-web3/   │  │ binance-web3/   │  │ binance-web3/   │  │
│  │ crypto-market-  │  │ trading-signal  │  │ meme-rush       │  │
│  │ rank            │  │ 链上智能钱信号   │  │ Meme 叙事追踪    │  │
│  │ 社交热度/Alpha   │  │                 │  │ 新发/迁移代币    │  │
│  │ 智能钱流入       │  │                 │  │                 │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
│                                                                  │
│  第三方补充数据（公开接口，无需认证）：                             │
│  CoinGecko 价格  ·  Blockchain.info 链上统计  ·  恐惧贪婪指数     │
│                                                                  │
│  可选增强层（有 TOKEN_6551 时自动启用）：                          │
│  L4 / 6551：高热新闻（6h内）  ·  KOL 推文信号                    │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼ 结构化市场数据字典
┌──────────────────────────────────────────────────────────────────┐
│  oracle.py — 2 次 LLM 调用核心引擎                                │
│                                                                  │
│  第一次 LLM 调用（分析 + 写作）：                                  │
│    输入：全部市场数据 + 风格模板（prompts/） + 写作规则（skills/）  │
│    输出：初稿 + 预言机评分（0-100）+ 个人风格指纹                  │
│                                                                  │
│  第二次 LLM 调用（去 AI 味润色）：                                 │
│    输入：初稿 + Humanizer 规则                                    │
│    输出：终稿（自然、真实、无 AI 痕迹）                             │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼ 终稿 + 评分 + 风格指纹
┌──────────────────────────────────────────────────────────────────┐
│  publish.py — 可选发布层（有 SQUARE_API_KEY 时自动启用）           │
│                                                                  │
│  官方 square-post v1.1 接口：                                     │
│    · 内容预览（原始版 vs 优化版）                                  │
│    · #标签原生处理（自动规范化、去重、追加相关标签）                 │
│    · 500 字符硬限制检查                                           │
│    · 完整 8 个错误码映射                                          │
└──────────────────────────────────────────────────────────────────┘
```

---

## 🚀 快速开始

### 1. 安装

```bash
# 克隆仓库（包含 skill 子模块）
git clone --recurse-submodules https://github.com/wxie0815-arch/binance-square-oracle.git
cd binance-square-oracle

# 安装 Python 依赖
pip3 install -r requirements.txt
```

### 2. 配置（可选）

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件（以下均为可选配置）
# SQUARE_API_KEY=...    # 启用 L8 广场自动发布
# TOKEN_6551=...        # 启用 L4 新闻 + KOL 信号增强
# OPENCLAW_MODEL=...    # 指定 LLM 模型（默认 gpt-4.1-mini）
```

### 3. 运行

```bash
# 最简运行（BTC 深度分析，KOL 风格）
python3 oracle.py

# 指定代币和风格
python3 -c "
from oracle import run_oracle
result = run_oracle(
    symbol='ethereum',
    futures_symbol='ETHUSDT',
    style_name='deep_analysis',
    user_intent='ETH 以太坊深度分析'
)
print(result['final_article'])
print(f'预言机评分: {result[\"oracle_score\"]}/100')
"

# 启用 L4 增强层
TOKEN_6551=your_token python3 -c "from oracle import run_oracle; r = run_oracle(enable_l4=True); print(r['final_article'])"

# 启用 L8 自动发布
SQUARE_API_KEY=your_key python3 -c "
from oracle import run_oracle
from publish import publish_to_square
result = run_oracle(style_name='kol_style')
publish_to_square(result['final_article'])
"
```

---

## 🎨 9 种文章风格

| 风格名称 | 文件 | 适用场景 | 特点 |
| :--- | :--- | :--- | :--- |
| **KOL 风格** | `kol_style.md` | 日常行情评论 | 个人化、有观点、引发互动 |
| **深度分析** | `deep_analysis.md` | 重大行情解读 | 数据驱动、逻辑严密、专业权威 |
| **每日快讯** | `daily_express.md` | 每日市场速报 | 简洁、快速、信息密度高 |
| **Meme 猎手** | `meme_hunter.md` | Meme 叙事追踪 | 活泼、接地气、捕捉情绪 |
| **链上洞察** | `onchain_insight.md` | 链上数据解读 | 技术性强、聪明钱视角 |
| **预言机** | `oracle.md` | 市场预测 | 神秘感、预测性、高互动 |
| **项目研究** | `project_research.md` | 新项目介绍 | 结构化、客观、适合 Alpha 项目 |
| **交易信号** | `trading_signal.md` | 交易建议 | 直接、有操作性、风险提示 |
| **教程** | `tutorial.md` | 科普教育 | 易懂、循序渐进、适合新手 |

---

## 📡 官方 Skill 数据源清单

| Skill | 数据接口 | 认证 | 数据内容 |
| :--- | :--- | :--- | :--- |
| `binance/spot` | `api.binance.com/api/v3/ticker/24hr` | 无需 | 现货 24h 行情 |
| `binance/spot` | `api.binance.com/api/v3/klines` | 无需 | K 线数据 |
| `binance/alpha` | `binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/cex/alpha/all/token/list` | 无需 | Alpha 早期项目列表 |
| `binance/alpha` | `binance.com/bapi/defi/v1/public/alpha-trade/ticker` | 无需 | Alpha 代币行情 |
| `binance/derivatives` | `fapi.binance.com/futures/data/globalLongShortAccountRatio` | 无需 | 全球多空比 |
| `binance/derivatives` | `fapi.binance.com/futures/data/topLongShortAccountRatio` | 无需 | 顶级账户多空比 |
| `binance/derivatives` | `fapi.binance.com/fapi/v1/fundingRate` | 无需 | 资金费率 |
| `binance/derivatives` | `fapi.binance.com/fapi/v1/openInterest` | 无需 | 未平仓合约量 |
| `binance-web3/crypto-market-rank` | `web3.binance.com/.../social/hype/rank/leaderboard` | 无需 | 社交热度排行 |
| `binance-web3/crypto-market-rank` | `web3.binance.com/.../unified/rank/list` (rankType=20) | 无需 | Alpha 发现排行 |
| `binance-web3/crypto-market-rank` | `web3.binance.com/.../unified/rank/list` (rankType=10) | 无需 | 热门趋势排行 |
| `binance-web3/crypto-market-rank` | `web3.binance.com/.../tracker/wallet/token/inflow/rank/query` | 无需 | 智能钱流入排行 |
| `binance-web3/trading-signal` | `web3.binance.com/.../web/signal/smart-money` | 无需 | 链上智能钱信号 |
| `binance-web3/meme-rush` | `web3.binance.com/.../market/token/pulse/rank/list` (rankType=10) | 无需 | Meme 新发代币 |
| `binance-web3/meme-rush` | `web3.binance.com/.../market/token/pulse/rank/list` (rankType=30) | 无需 | Meme 迁移代币 |

---

## 🔧 可选模块

| 模块 | 默认状态 | 启用条件 | 功能 |
| :--- | :--- | :--- | :--- |
| **L4 新闻 + KOL 信号** | 自动跳过 | 设置 `TOKEN_6551` 环境变量 | 6h 内高热新闻 + 指定 KOL 最新推文 |
| **L8 广场自动发布** | 自动跳过 | 设置 `SQUARE_API_KEY` 环境变量 | 对接官方 `square-post` v1.1 接口，自动发布终稿 |

---

## 📦 文件结构

```
binance-square-oracle/
├── collect.py              # 并发数据采集层（12个官方 Skill + 3个第三方 + L4 可选）
├── oracle.py               # 核心引擎（2次 LLM 调用，生成文章 + 评分）
├── publish.py              # L8 广场发布（可选，square-post v1.1）
├── data_6551.py            # L4 增强层（新闻 + KOL，可选）
├── data_cache.py           # 智能缓存（广场/社交 4h，链上/新闻 4min）
├── run_monitor.py          # 性能监控（各层耗时 + API 成功率 + 预警）
├── config.py               # 统一配置（版本号、目录、LLM 调用）
├── requirements.txt        # Python 依赖
├── .env.example            # 环境变量模板
├── install.sh              # 一键安装脚本
├── prompts/                # 9 种文章风格模板
│   ├── kol_style.md
│   ├── deep_analysis.md
│   ├── daily_express.md
│   ├── meme_hunter.md
│   ├── onchain_insight.md
│   ├── oracle.md
│   ├── project_research.md
│   ├── trading_signal.md
│   └── tutorial.md
├── skills/                 # 写作规则 Skill（Git Submodule）
│   └── crypto-content-writer/
│       └── SKILL.md        # 写作规则：禁用词、文章结构、代币格式
├── tests/                  # 单元测试
│   ├── test_config.py
│   ├── test_writing_skill.py
│   └── test_l7_generator.py
└── SKILL.md                # OpenClaw Skill 声明文件
```

---

## 📋 更新日志

### v1.1（C 方案极简重构）— 当前版本

- **架构重构**：从 9 层流水线（6591 行）精简为 3 个核心文件（约 1500 行），代码量减少 77%
- **LLM 调用优化**：从最多 10 次减少为固定 2 次，成本降低 80%
- **并发采集**：所有数据源并发请求，采集时间从 15-20 秒压缩至约 5 秒
- **官方 Skill 完整覆盖**：通过正确的请求头和 API 端点，成功接入全部 12 个官方 Skill 数据源
- **SKILL.md 强制声明**：明确列出所有官方 Skill 依赖，确保 AI Agent 如实调用
- **L4 / L8 可选模块**：保留新闻增强和广场发布功能，有对应 Key 时自动启用

### v1.0（系统性重构）

- 去除 L7 独立 LLM 配置，统一调用 OpenClaw 系统 API
- 智能缓存：广场/社交 4h，链上/新闻 4min
- 性能监控：各层耗时打点、API 成功率统计、连续失败预警
- 配置中心化：统一到 `config.py`，删除 `config.yaml` 和 `ai_models.py`

### v6.0（L3 + L8 升级）

- L3 升级：集成 `binance/alpha` 早期项目监控和 `binance/derivatives-trading-usds-futures` 合约数据
- L8 升级：`square-post` 升级至官方 v1.1 接口，支持标题优化和 #标签处理

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
**币安广场：** [@wuxie](https://www.binance.com/en/square/profile/wuxie)
**X（Twitter）：** [@wuxie149](https://x.com/wuxie149)
**参赛：** [Binance Skills Hub Agent Competition](https://github.com/binance/binance-skills-hub)
