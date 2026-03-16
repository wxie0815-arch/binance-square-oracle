# Binance Square Oracle

[![Version](https://img.shields.io/badge/version-v1.1-blue)](https://github.com/wxie0815-arch/binance-square-oracle)
[![OpenClaw](https://img.shields.io/badge/OpenClaw-native-green)](https://openclaw.ai)
[![License](https://img.shields.io/badge/license-MIT-yellow)](LICENSE)
[![Skills Hub](https://img.shields.io/badge/Binance-Skills%20Hub-orange)](https://github.com/binance/binance-skills-hub)

**Binance Square Oracle** 是一个面向币安生态的内容生成型 Agent Skill。  
它的核心目标是把币安生态数据整理成**可用于币安广场发布的文章内容**，并支持风格化写作、结构化评分和可选发布。

当前仓库提供两种运行方式：

1. **推荐模式：OpenClaw 原生 Skill 模式**
2. **备用模式：本地 Python 辅助模式**

> 重要说明：本项目**不需要**额外配置任何第三方大模型 API。  
> 在 OpenClaw 中安装后，应直接使用 OpenClaw 系统里已经配置好的模型。

---

## 项目定位

这个项目不是单纯的数据抓取脚本，而是一个**从市场数据到币安广场文章的一键编排器**。

它保留了以下核心思路：

- 多风格写作
- 按风格智能路由数据
- 输出发布就绪文章
- 生成 `oracle_score` 评分
- 可选自动发布到 Binance Square

---

## 当前功能 / Current Features

### 1. 多风格内容生成 / Multi-style Article Generation

内置 9 种风格：

- `daily_express`
- `deep_analysis`
- `onchain_insight`
- `meme_hunter`
- `kol_style`
- `oracle`
- `project_research`
- `trading_signal`
- `tutorial`

同时支持 DIY 风格。你只需要在 [`prompts/`](/D:/文档/Playground/repo_check/prompts) 下新增一个 `.md` 文件，就可以扩展自己的写作风格。

### 2. 智能数据路由 / Intelligent Data Routing

不同风格不会盲目全量抓取数据，而是按需要调用不同的数据能力。

例如：

- `deep_analysis` 更偏向现货、合约、Alpha、交易信号和审计
- `meme_hunter` 更偏向 meme-rush、市场热度和链上信号
- `tutorial` 更偏向轻量级基础市场信息

### 3. 对接官方 Binance 能力 / Official Binance Capability Integration

推荐的 OpenClaw 原生执行路径优先使用这些官方能力：

- `binance/spot`：现货市场数据 / Spot market data
- `binance/derivatives-trading-usds-futures`：U 本位合约数据 / USDs-margined futures data
- `binance/alpha`：Alpha 代币与行情数据 / Alpha token and market data
- `binance-web3/crypto-market-rank`：市场热度与排行 / Market heat and ranking data
- `binance-web3/trading-signal`：交易信号 / Trading signal data
- `binance-web3/meme-rush`：Meme 追踪数据 / Meme discovery data
- `binance-web3/query-token-info`：代币基础信息 / Token information
- `binance-web3/query-token-audit`：代币审计信息 / Token audit information
- `binance-web3/query-address-info`：地址与持仓信息 / Address and position information
- `binance/square-post`：广场发布能力 / Binance Square publishing capability

参考 / References:

- [Binance Skills Hub](https://github.com/binance/binance-skills-hub)
- [Build Your Own Binance Square AI Agent Skill](https://academy.binance.com/ky-KG/articles/build-your-own-binance-square-ai-agent-skill)

### 4. 输出发布就绪文章 / Publish-ready Output

生成结果的目标不是“草稿笔记”，而是尽量接近可以直接上广场的内容包，核心字段包括：

- `article_draft`：文章初稿 / Article draft
- `final_article`：最终文章 / Final article
- `oracle_score`：预言机评分 / Oracle score
- `style_fingerprint`：风格指纹 / Style fingerprint
- `publish_result`：发布结果（启用发布时） / Publish result (when publishing is enabled)

### 5. Oracle 评分机制 / Oracle Scoring

项目会基于采集到的数据和风格要求生成一个 `0-100` 的 `oracle_score`，用于表达当前内容中的市场信心强弱。

### 6. 可选增强能力 / Optional Enhancements

- **L4 增强 / L4 enhancement**：通过 `TOKEN_6551` 接入热点新闻和 KOL 动态
- **L8 发布链路 / L8-style publishing flow**：通过 `SQUARE_API_KEY` 直接发布到 Binance Square

### 7. Binance Square 热门监控子 Skill / Binance Square Monitor Sub-skill

仓库内保留了 [`skills/binance-square-monitor`](/D:/文档/Playground/repo_check/skills/binance-square-monitor) 这个子 skill，可用于监控币安广场热门帖子、互动数据和流量变化。

---

## 风格与数据映射 / Style-to-Data Map

| 风格 Style | 适用场景 Use Case | 核心数据能力 Core Data Route |
| :--- | :--- | :--- |
| `daily_express` | 每日市场速递 / Daily market recap | spot / alpha / market-rank / token-info |
| `deep_analysis` | 深度分析 / Deep thesis write-up | spot / derivatives / alpha / trading-signal / token-info / token-audit |
| `onchain_insight` | 链上洞察 / On-chain insight | trading-signal / address-info / token-info / token-audit |
| `meme_hunter` | Meme 追踪 / Meme discovery | meme-rush / trading-signal / market-rank / token-info / token-audit |
| `kol_style` | KOL 观点输出 / Opinionated KOL style | spot / trading-signal / market-rank |
| `oracle` | 市场预判 / Directional market view | spot / derivatives / trading-signal / market-rank |
| `project_research` | 项目研究 / Project research | token-info / token-audit / alpha / market-rank |
| `trading_signal` | 交易观点 / Tactical setup | spot / derivatives / trading-signal / token-audit |
| `tutorial` | 教育科普 / Educational content | spot / market-rank |

---

## 如何使用 / How To Use

### 方式一：OpenClaw 原生 Skill 模式 / OpenClaw-native Skill Mode

这是当前最推荐的使用方式。

#### 安装 / Install

将这个仓库作为 Skill 安装到 OpenClaw：

```text
https://github.com/wxie0815-arch/binance-square-oracle
```

#### 使用示例 / Usage Examples

```text
Use deep_analysis style to write a Binance Square article about BTC.
```

```text
Use meme_hunter style to find the hottest meme setup and prepare a publish-ready Square post.
```

```text
Use prompts/my_style.md as my custom style and produce a Square-ready article on ETH.
```

#### 推荐执行链路 / Recommended Workflow

1. 输入主题、币种或分析意图 / Provide a topic, asset, or intent
2. 按风格选择数据路径 / Choose the data route by style
3. 生成 `article_draft` / Generate `article_draft`
4. 输出 `oracle_score` / Produce `oracle_score`
5. 润色为 `final_article` / Polish into `final_article`
6. 可选发布 / Optionally publish

> 这一模式下的模型调用由 OpenClaw 自身负责，直接使用 OpenClaw 系统里已经配置好的模型。

### 方式二：本地 Python 辅助模式 / Local Python Helper Mode

这个模式适合做以下事情：

- 数据采集联通性检查
- 发布辅助模块调试
- 仓库 smoke test

它**不负责真实文章生成**。真实生成应在 OpenClaw 中完成。

#### 依赖 / Requirements

- Python 3.8+
- `pip install -r requirements.txt`

#### 环境变量 / Environment Variables

只需要按需配置这些可选能力：

- `SQUARE_API_KEY`
- `TOKEN_6551`
- `API_6551_BASE`

#### 最小调用示例 / Minimal Example

```bash
python3 tests/final_e2e_test.py
```

#### 数据采集示例 / Data Collection Example

```bash
python3 -c "from collect import collect_all; print(list(collect_all(style_name='kol_style').keys()))"
```

---

## 当前仓库结构 / Repository Layout

```text
binance-square-oracle/
├── SKILL.md
├── prompts/
├── references/
│   ├── writing_rules.md
│   └── competition_notes.md
├── collect.py
├── oracle.py
├── publish.py
├── skills/
│   └── binance-square-monitor/
└── tests/
```

### 主要文件说明 / Key Files

- [`SKILL.md`](/D:/文档/Playground/repo_check/SKILL.md)：主 Skill 定义 / Main OpenClaw skill definition
- [`collect.py`](/D:/文档/Playground/repo_check/collect.py)：数据采集与风格路由 / Data collection and style routing
- [`oracle.py`](/D:/文档/Playground/repo_check/oracle.py)：文章生成逻辑骨架 / Article generation workflow skeleton
- [`publish.py`](/D:/文档/Playground/repo_check/publish.py)：发布辅助模块 / Publishing helper
- [`references/writing_rules.md`](/D:/文档/Playground/repo_check/references/writing_rules.md)：写作规则基线 / Writing rules baseline

---

## 当前状态 / Current Status

当前版本已经完成以下整理：

- 去掉缺失 submodule 的硬依赖
- 去掉对外部模型 API 的依赖
- 明确区分 OpenClaw 原生模式和本地辅助模式
- 保留多风格路由、生成、评分和发布能力
- 补齐说明文档

---

## 项目作者 / Author

Project author: `wxie0815-arch`

---

## 💰赞助支持

如果这个项目对您有帮助，欢迎赞助支持！

**BSC（BEP-20）钱包地址：** `0x3B74BE938caB987120C3661C8e3161CD838e5a1A`

支持 USDT / BNB / 任意 BEP-20 代币。感谢每一位支持者🙏

**作者：** 无邪Infinity | 币安广场@wuxie | X @wuxie149
